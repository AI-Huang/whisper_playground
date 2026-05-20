#!/usr/bin/env python3
"""
批量语音生成脚本

从 ASS 文件提取文本，去重后批量调用曼波配音 API 生成语音。

用法:
    python scripts/batch_generate_voice.py <input_ass_file>

示例:
    python scripts/batch_generate_voice.py "~/Documents/Arctime Documents/20260520155624.ass"
"""

import argparse
import asyncio
import os
import re
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import httpx

from src.config.settings import MANBO_API_URL, MILORAPART_API_KEY
from src.tools.ass_helper import extract_ass_text


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


async def generate_single_voice(
    text: str, output_dir: str, session: httpx.AsyncClient
) -> bool:
    """
    生成单个语音文件

    :param text: 要转换的文本
    :param output_dir: 输出目录
    :param session: HTTP 会话
    :return: 是否成功
    """
    # 构建请求参数
    params = {"text": text, "format": "mp3"}

    # 构建请求头
    headers = {}
    if MILORAPART_API_KEY:
        headers["Authorization"] = f"Bearer {MILORAPART_API_KEY}"

    try:
        # 第一步：调用 API 获取音频 URL
        response = await session.get(
            MANBO_API_URL, params=params, headers=headers, timeout=30
        )
        response.raise_for_status()

        # 解析 JSON 响应
        result = response.json()

        # 检查 API 返回状态
        if result.get("code") != 200:
            msg = result.get("msg", "未知错误")
            print(f"✗ API 返回错误 [{text[:30]}...]: {msg}", file=sys.stderr)
            return False

        # 获取音频 URL（清理反引号）
        audio_url = result.get("url", "").strip().strip("`")
        if not audio_url:
            print(f"✗ 未获取到音频 URL [{text[:30]}...]", file=sys.stderr)
            return False

        # 第二步：从 URL 下载音频文件
        audio_response = await session.get(audio_url, timeout=30)
        audio_response.raise_for_status()

        audio_content = audio_response.content
        content_length = len(audio_content)

        # 检查是否是有效音频
        if content_length < 1000:
            print(
                f"✗ 音频文件过小 [{text[:30]}...]: {content_length} bytes",
                file=sys.stderr,
            )
            return False

        # 生成文件名
        filename = sanitize_filename(text) + ".mp3"
        filepath = os.path.join(output_dir, filename)

        # 保存音频文件
        with open(filepath, "wb") as f:
            f.write(audio_content)

        print(f"✓ 生成语音: {text[:30]}... -> {filename} ({content_length} bytes)")
        return True

    except httpx.HTTPError as e:
        print(f"✗ 生成失败 [{text[:30]}...]: HTTP 错误 - {e}", file=sys.stderr)
        return False
    except ValueError as e:
        print(f"✗ 解析响应失败 [{text[:30]}...]: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"✗ 生成失败 [{text[:30]}...]: {e}", file=sys.stderr)
        return False


async def batch_generate_voices(text_list: list, output_dir: str) -> tuple:
    """
    批量生成语音文件

    :param text_list: 文本列表
    :param output_dir: 输出目录
    :return: (成功数量, 失败数量)
    """
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    success_count = 0
    fail_count = 0

    # 创建 HTTP 会话
    async with httpx.AsyncClient() as session:
        # 逐个生成语音（避免请求过快）
        for i, text in enumerate(text_list, 1):
            print(f"\n[{i}/{len(text_list)}] 正在生成: {text[:50]}...")

            success = await generate_single_voice(text, output_dir, session)
            if success:
                success_count += 1
            else:
                fail_count += 1

            # 添加延迟，避免触发限流
            await asyncio.sleep(1)

    return success_count, fail_count


def main():
    parser = argparse.ArgumentParser(description="批量从 ASS 文件生成语音")
    parser.add_argument("input", help="输入的 ASS 文件路径")
    parser.add_argument(
        "--output-dir",
        default="outputs/voices",
        help="输出目录（默认：outputs/voices）",
    )

    args = parser.parse_args()

    # 1. 提取 ASS 文件中的文本
    print("步骤1: 提取 ASS 文件中的文本...")
    try:
        text_list = extract_ass_text(args.input)
        print(f"   提取到 {len(text_list)} 个段落")
    except Exception as e:
        print(f"   提取失败: {e}", file=sys.stderr)
        sys.exit(1)

    if not text_list:
        print("   未找到任何文本内容", file=sys.stderr)
        sys.exit(0)

    # 2. 去重
    print("步骤2: 对文本列表去重...")
    unique_texts = list(dict.fromkeys(text_list))  # 保持顺序的去重
    print(f"   去重后剩余 {len(unique_texts)} 个段落")

    if len(unique_texts) == 0:
        print("   去重后为空", file=sys.stderr)
        sys.exit(0)

    # 3. 批量生成语音
    print("步骤3: 批量生成语音...")
    success, failed = asyncio.run(batch_generate_voices(unique_texts, args.output_dir))

    # 4. 输出统计信息
    print(f"\n=== 生成完成 ===")
    print(f"成功: {success} 个")
    print(f"失败: {failed} 个")
    print(f"输出目录: {os.path.abspath(args.output_dir)}")


if __name__ == "__main__":
    main()
