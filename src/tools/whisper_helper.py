import whisper


class WhisperHelper:
    """
    Whisper 音频转写工具类。

    提供音频转写和字幕文件生成功能，基于 OpenAI Whisper 模型。

    :param model_name: Whisper 模型名称，可选值: tiny, base, small, medium, large
    :type model_name: str
    :ivar model: Whisper 模型实例

    **Example**::

        >>> helper = WhisperHelper(model_name="base")
        >>> result = helper.transcribe("audio.mp3", language="zh")
        >>> helper.save_as_srt(result, "output.srt")
    """

    def __init__(self, model_name="base"):
        """
        初始化 WhisperHelper。

        :param model_name: Whisper 模型名称，可选值: tiny, base, small, medium, large
                          默认值为 "base"
        :type model_name: str
        """
        self.model = whisper.load_model(model_name)

    def _format_time(self, seconds):
        """
        将秒数转换为 SRT 时间格式。

        :param seconds: 时间（秒）
        :type seconds: float
        :return: SRT 时间字符串，格式为 "HH:MM:SS,mmm"
        :rtype: str
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"

    def transcribe(self, filepath, language=None):
        """
        转录音频文件。

        :param filepath: 音频文件路径
        :type filepath: str
        :param language: 语言代码（如 "zh", "en", "ja"），为 None 时自动检测
        :type language: str or None
        :return: 转录结果字典，包含以下键:
                    - text: 完整转录文本
                    - segments: 分段列表，每段包含 start, end, text 等信息
                    - language: 检测到的语言代码
        :rtype: dict
        """
        return self.model.transcribe(filepath, language=language)

    def save_as_srt(self, result, output_path):
        """
        将转录结果保存为 SRT 字幕文件。

        :param result: transcribe() 方法返回的结果字典
        :type result: dict
        :param output_path: 输出 SRT 文件路径
        :type output_path: str
        """
        with open(output_path, "w", encoding="utf-8") as f:
            for i, segment in enumerate(result["segments"], start=1):
                start = self._format_time(segment["start"])
                end = self._format_time(segment["end"])
                text = segment["text"].strip()
                f.write(f"{i}\n")
                f.write(f"{start} --> {end}\n")
                f.write(f"{text}\n\n")
