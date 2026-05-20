import argparse
import os
import platform
import time
from datetime import datetime

from src.tools import WhisperHelper


def gen_report(
    result, input_path, output_path, model_name, language, start_time, end_time
):
    """
    生成转录报告。

    :param result: 转录结果字典
    :param input_path: 输入文件路径
    :param output_path: SRT输出路径
    :param model_name: 使用的模型名称
    :param language: 指定的语言
    :param start_time: 转录开始时间
    :param end_time: 转录结束时间
    """
    duration = end_time - start_time
    num_segments = len(result["segments"])
    detected_language = result.get("language", "未知")

    report = f"""# 音频转录报告

## 基本信息
- **生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- **机器平台**: {platform.system()} {platform.release()} ({platform.machine()})
- **Python版本**: {platform.python_version()}

## 输入文件
- **文件路径**: {input_path}
- **文件大小**: {os.path.getsize(input_path) / 1024 / 1024:.2f} MB

## 转录配置
- **模型名称**: {model_name}
- **指定语言**: {language or "自动检测"}
- **检测语言**: {detected_language}

## 转录统计
- **分段总数**: {num_segments} 段
- **转录时长**: {duration:.2f} 秒
- **平均每段时长**: {(duration / num_segments) if num_segments > 0 else 0:.2f} 秒

## 输出文件
- **SRT字幕**: {output_path}

---
报告结束
"""

    report_path = output_path.replace(".srt", "_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"报告已保存到 {report_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Whisper 音频转写工具 - 将音频文件转换为 SRT 字幕"
    )

    parser.add_argument("input", help="输入音频文件路径")
    parser.add_argument(
        "-o", "--output", help="输出 SRT 文件路径（默认：outputs/文件名.srt）"
    )
    parser.add_argument(
        "-l", "--language", help="指定语言代码（如 zh, en, ja），不指定则自动检测"
    )
    parser.add_argument(
        "-m",
        "--model",
        default="base",
        help="Whisper 模型名称（tiny, base, small, medium, large），默认 base",
    )

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"错误：输入文件不存在 - {args.input}")
        return

    if args.output:
        out_path = args.output
    else:
        filename = os.path.basename(args.input)
        out_path = f"outputs/{filename}.srt"

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    helper = WhisperHelper(model_name=args.model)

    print(f"开始转录... (模型: {args.model})")
    start_time = time.time()

    result = helper.transcribe(args.input, language=args.language)

    end_time = time.time()
    print(f"转录完成，耗时 {end_time - start_time:.2f} 秒")
    print()

    print("转录文本：")
    print(result["text"])
    print()

    helper.save_as_srt(result, out_path)
    print(f"SRT 文件已保存到 {out_path}")

    gen_report(
        result, args.input, out_path, args.model, args.language, start_time, end_time
    )


if __name__ == "__main__":
    main()
