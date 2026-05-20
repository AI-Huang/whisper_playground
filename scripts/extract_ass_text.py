#!/usr/bin/env python3
"""
ASS 文件纯文本提取脚本

使用 pysubs2 库解析 ASS 字幕文件，提取所有对话的纯文本内容。

用法:
    python scripts/extract_ass_text.py <input_ass_file> [output_txt_file]

示例:
    python scripts/extract_ass_text.py "/Users/kanhuang/Documents/Arctime Documents/爱音大战立希-20260520155624.ass"
    python scripts/extract_ass_text.py input.ass output.txt
"""

import argparse
import sys

from src.tools.ass_helper import extract_ass_text


def main():
    parser = argparse.ArgumentParser(description="提取 ASS 文件中的纯文本段落")
    parser.add_argument("input", help="输入的 ASS 文件路径")
    parser.add_argument("output", nargs="?", help="输出的 TXT 文件路径（可选）")

    args = parser.parse_args()

    # 提取纯文本
    try:
        text_segments = extract_ass_text(args.input)
    except FileNotFoundError:
        print(f"错误：文件不存在 - {args.input}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"读取文件失败: {e}", file=sys.stderr)
        sys.exit(1)

    if not text_segments:
        print("未找到任何对话内容", file=sys.stderr)
        sys.exit(0)

    # 合并所有段落
    full_text = "\n".join(text_segments)

    if args.output:
        # 保存到文件
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(full_text)
            print(f"文本已保存到: {args.output}")
        except Exception as e:
            print(f"保存文件失败: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # 输出到控制台
        print("=== 提取的纯文本内容 ===")
        print(full_text)
        print(f"\n=== 共 {len(text_segments)} 个段落 ===")


if __name__ == "__main__":
    main()
