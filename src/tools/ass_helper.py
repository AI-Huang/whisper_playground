import re
from typing import List

import pysubs2


def remove_ass_formatting(text: str) -> str:
    """
    移除 ASS 字幕中的样式标签

    :param text: 原始文本（可能包含样式标签）
    :type text: str
    :return: 移除样式标签后的纯文本
    :rtype: str
    """
    # 移除 ASS 样式标签，格式为 {\...}
    clean_text = re.sub(r"\{[^}]+\}", "", text)
    # 移除多余的空格和换行
    clean_text = " ".join(clean_text.split())
    return clean_text


def extract_ass_text(ass_file_path: str) -> List[str]:
    """
    从 ASS 文件中提取所有对话的纯文本

    :param ass_file_path: ASS 文件路径
    :type ass_file_path: str
    :return: 纯文本段落列表
    :rtype: List[str]
    :raises FileNotFoundError: 如果文件不存在
    :raises Exception: 如果读取文件失败
    """
    subs = pysubs2.load(ass_file_path)
    text_segments = []

    for line in subs:
        # 跳过空行或注释
        if not line.text or line.text.strip() == "":
            continue

        # 移除 ASS 样式标签
        clean_text = remove_ass_formatting(line.text)

        if clean_text and clean_text.strip():
            text_segments.append(clean_text.strip())

    return text_segments
