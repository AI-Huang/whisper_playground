#!/usr/bin/env python3
"""
批量下载音频文件脚本

从日志文件中提取音频 URL 和对应文本，使用文本作为文件名批量下载。

用法:
    python scripts/batch_download_voices.py <log_file> [output_dir]

示例:
    python scripts/batch_download_voices.py outputs/voice.txt outputs/downloaded_voices
"""

import argparse
import asyncio
import os
import re
import sys

import httpx


def sanitize_filename(text: str, max_length: int = 50) -> str:
    """
    将文本转换为安全的文件名

    :param text: 原始文本
    :param max_length: 文件名最大长度
    :return: 安全的文件名
    """
    # 移除非法字符
    sanitized = re.sub(r'[\\/*?:"<>|]', "_", text)
    # 移除空白字符
    sanitized = re.sub(r"\s+", "_", sanitized)
    # 截断到最大长度
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    # 确保文件名不为空
    if not sanitized or sanitized == "_":
        sanitized = "voice"
    return sanitized


def extract_text_and_urls(log_file_path: str) -> list:
    """
    从日志文件中提取文本和对应的音频 URL

    :param log_file_path: 日志文件路径
    :return: [(text, url), ...] 列表
    """
    # 匹配格式: [文本内容...]: {'url': 'xxx.mp3'}
    pattern = re.compile(
        r"\[(.*?)\.\.\.\].*?url'\s*:\s*['\"](https://api\.milorapart\.top/voice/[\w]+\.mp3)['\"]"
    )
    results = []

    try:
        with open(log_file_path, "r", encoding="utf-8") as f:
            for line in f:
                match = pattern.search(line)
                if match:
                    text = match.group(1).strip()
                    url = match.group(2).strip()
                    results.append((text, url))
    except FileNotFoundError:
        print(f"错误：文件不存在 - {log_file_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"读取文件失败: {e}", file=sys.stderr)
        sys.exit(1)

    # 去重（基于 URL）
    unique_results = []
    seen_urls = set()
    for text, url in results:
        if url not in seen_urls:
            seen_urls.add(url)
            unique_results.append((text, url))

    print(f"从日志中提取到 {len(results)} 条记录，去重后 {len(unique_results)} 条")

    return unique_results


async def download_single_file(
    text: str, url: str, output_dir: str, session: httpx.AsyncClient
) -> bool:
    """
    下载单个文件，使用文本作为文件名

    :param text: 文本内容（用于生成文件名）
    :param url: 文件 URL
    :param output_dir: 输出目录
    :param session: HTTP 会话
    :return: 是否成功
    """
    try:
        # 生成文件名
        filename = sanitize_filename(text) + ".mp3"
        filepath = os.path.join(output_dir, filename)

        # 检查文件是否已存在
        if os.path.exists(filepath):
            print(f"✓ 已存在: {filename}")
            return True

        # 下载文件
        response = await session.get(url, timeout=30)
        response.raise_for_status()

        content = response.content
        content_length = len(content)

        # 检查是否是有效音频
        if content_length < 1000:
            print(f"✗ 文件过小: {filename} ({content_length} bytes)", file=sys.stderr)
            return False

        # 保存文件
        with open(filepath, "wb") as f:
            f.write(content)

        print(f"✓ 下载成功: {filename} ({content_length} bytes)")
        return True

    except httpx.HTTPError as e:
        print(f"✗ 下载失败 [{text[:20]}...]: HTTP 错误: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"✗ 下载失败 [{text[:20]}...]: {e}", file=sys.stderr)
        return False


async def batch_download(items: list, output_dir: str) -> tuple:
    """
    批量下载文件

    :param items: [(text, url), ...] 列表
    :param output_dir: 输出目录
    :return: (成功数量, 失败数量)
    """
    os.makedirs(output_dir, exist_ok=True)

    success_count = 0
    fail_count = 0

    async with httpx.AsyncClient() as session:
        for i, (text, url) in enumerate(items, 1):
            print(f"\n[{i}/{len(items)}] 正在下载: {text[:50]}...")

            success = await download_single_file(text, url, output_dir, session)
            if success:
                success_count += 1
            else:
                fail_count += 1

            # 添加延迟，避免触发限流
            await asyncio.sleep(0.5)

    return success_count, fail_count


def main():
    parser = argparse.ArgumentParser(description="从日志文件批量下载音频文件")
    parser.add_argument("log_file", help="包含音频 URL 的日志文件")
    parser.add_argument(
        "--output-dir",
        default="outputs/downloaded_voices",
        help="输出目录（默认：outputs/downloaded_voices）",
    )

    args = parser.parse_args()

    # 1. 提取文本和 URL
    print("步骤1: 从日志文件提取文本和音频 URL...")
    items = extract_text_and_urls(args.log_file)

    if not items:
        print("未找到任何音频 URL", file=sys.stderr)
        sys.exit(0)

    # 2. 批量下载
    print("\n步骤2: 批量下载音频文件...")
    success, failed = asyncio.run(batch_download(items, args.output_dir))

    # 3. 输出统计信息
    print(f"\n=== 下载完成 ===")
    print(f"成功: {success} 个")
    print(f"失败: {failed} 个")
    print(f"输出目录: {os.path.abspath(args.output_dir)}")


if __name__ == "__main__":
    main()
