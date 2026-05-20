#!/usr/bin/env python3
"""
测试单个语音生成功能

验证文本 "你好，这里是曼波" 的生成结果
"""

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


def sanitize_filename(text: str, max_length: int = 50) -> str:
    """将文本转换为安全的文件名"""
    sanitized = re.sub(r'[\\/*?:"<>|]', "_", text)
    sanitized = re.sub(r"\s+", "_", sanitized)
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    if not sanitized or sanitized == "_":
        sanitized = "voice"
    return sanitized


async def test_generate_single_voice(text: str, output_dir: str) -> bool:
    """测试生成单个语音文件"""
    params = {"text": text, "format": "mp3"}
    headers = {}
    if MILORAPART_API_KEY:
        headers["Authorization"] = f"Bearer {MILORAPART_API_KEY}"

    try:
        async with httpx.AsyncClient() as session:
            # 第一步：调用 API 获取音频 URL
            print(f"正在调用 API，文本: {text}")
            response = await session.get(
                MANBO_API_URL, params=params, headers=headers, timeout=30
            )
            response.raise_for_status()

            # 解析 JSON 响应
            result = response.json()
            print(f"API 响应: {result}")

            # 检查 API 返回状态
            if result.get("code") != 200:
                msg = result.get("msg", "未知错误")
                print(f"✗ API 返回错误: {msg}", file=sys.stderr)
                return False

            # 获取音频 URL（清理反引号）
            audio_url = result.get("url", "").strip().strip("`")
            if not audio_url:
                print("✗ 未获取到音频 URL", file=sys.stderr)
                return False

            print(f"获取到音频 URL: {audio_url}")

            # 第二步：从 URL 下载音频文件
            audio_response = await session.get(audio_url, timeout=30)
            audio_response.raise_for_status()

            audio_content = audio_response.content
            content_length = len(audio_content)

            # 检查是否是有效音频
            if content_length < 1000:
                print(f"✗ 音频文件过小: {content_length} bytes", file=sys.stderr)
                return False

            # 创建输出目录
            os.makedirs(output_dir, exist_ok=True)

            # 生成文件名
            filename = sanitize_filename(text) + ".mp3"
            filepath = os.path.join(output_dir, filename)

            # 保存音频文件
            with open(filepath, "wb") as f:
                f.write(audio_content)

            print(f"✓ 测试成功!")
            print(f"  文本: {text}")
            print(f"  文件: {filepath}")
            print(f"  大小: {content_length} bytes")
            return True

    except httpx.HTTPError as e:
        print(f"✗ HTTP 错误: {e}", file=sys.stderr)
        return False
    except ValueError as e:
        print(f"✗ 解析响应失败: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"✗ 生成失败: {e}", file=sys.stderr)
        return False


def main():
    test_text = "你好，这里是曼波"
    output_dir = "outputs/test"

    print("=== 测试单个语音生成 ===")
    print(f"测试文本: {test_text}")
    print(f"输出目录: {output_dir}")
    print()

    success = asyncio.run(test_generate_single_voice(test_text, output_dir))

    print()
    if success:
        print("=== 测试通过 ===")
    else:
        print("=== 测试失败 ===")
        sys.exit(1)


if __name__ == "__main__":
    main()
