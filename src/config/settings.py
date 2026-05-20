import os
from pathlib import Path

from dotenv import load_dotenv

# 加载 .env 文件
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(env_path)

# 曼波配音 API 配置
MANBO_API_URL = "https://api.milorapart.top/apis/mbAIsc"
MILORAPART_API_KEY = os.getenv("MILORAPART_API_KEY", "")
MANBO_DAILY_LIMIT = 50

# Whisper 模型配置
WHISPER_MODELS = {
    "tiny": "faster-whisper-tiny",
    "base": "faster-whisper-base",
    "small": "faster-whisper-small",
    "medium": "faster-whisper-medium",
    "large": "faster-whisper-large-v3",
}

# 服务配置
MAX_WORKERS = 4
DEFAULT_DEVICE = "cpu"
DEFAULT_COMPUTE_TYPE = "float16"
