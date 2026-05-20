import asyncio
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse
from faster_whisper import WhisperModel
from huggingface_hub import snapshot_download

app = FastAPI(title="Whisper Playground API")

# 导入曼波配音路由
from src.api.v1.manbo import router as manbo_router

app.include_router(manbo_router)


# 模型名称与本地目录的映射字典
MODEL_PATH_MAPPING = {
    "faster-distil-whisper-large-v2": "./models/faster-distil-whisper-large-v2",
    "faster-distil-whisper-large-v3": "./models/faster-distil-whisper-large-v3",
    "faster-distil-whisper-small.en": "./models/faster-distil-whisper-small.en",
    "faster-distil-whisper-medium.en": "./models/faster-distil-whisper-medium.en",
    "faster-whisper-large-v2": "./models/faster-whisper-large-v2",
    "faster-whisper-large-v1": "./models/faster-whisper-large-v1",
    "faster-whisper-medium.en": "./models/faster-whisper-medium.en",
    "faster-whisper-medium": "./models/faster-whisper-medium",
    "faster-whisper-base.en": "./models/faster-whisper-base.en",
    "faster-whisper-base": "./models/faster-whisper-base",
    "faster-whisper-small.en": "./models/faster-whisper-small.en",
    "faster-whisper-small": "./models/faster-whisper-small",
    "faster-whisper-tiny.en": "./models/faster-whisper-tiny.en",
    "faster-whisper-tiny": "./models/faster-whisper-tiny",
    "faster-whisper-large-v3": "./models/faster-whisper-large-v3",
}

# 新增：Hugging Face仓库ID映射
HF_REPO_IDS = {
    "faster-distil-whisper-large-v2": "Systran/faster-distil-whisper-large-v2",
    "faster-distil-whisper-large-v3": "Systran/faster-distil-whisper-large-v3",
    "faster-distil-whisper-small.en": "Systran/faster-distil-whisper-small.en",
    "faster-distil-whisper-medium.en": "Systran/faster-distil-whisper-medium.en",
    "faster-whisper-large-v2": "Systran/faster-whisper-large-v2",
    "faster-whisper-large-v1": "Systran/faster-whisper-large-v1",
    "faster-whisper-medium.en": "Systran/faster-whisper-medium.en",
    "faster-whisper-medium": "Systran/faster-whisper-medium",
    "faster-whisper-base.en": "Systran/faster-whisper-base.en",
    "faster-whisper-base": "Systran/faster-whisper-base",
    "faster-whisper-small.en": "Systran/faster-whisper-small.en",
    "faster-whisper-small": "Systran/faster-whisper-small",
    "faster-whisper-tiny.en": "Systran/faster-whisper-tiny.en",
    "faster-whisper-tiny": "Systran/faster-whisper-tiny",
    "faster-whisper-large-v3": "Systran/faster-whisper-large-v3",
}

# 缓存已加载模型
loaded_models = {}


def get_model(model_name: str, device: str = "cpu", compute_type: str = "float16"):
    """
    根据映射关系从本地路径加载模型并缓存，自动下载缺失模型。
    对于不支持 FP16 的设备，自动降级到 float32 或 int8。
    参数:
      - model_name: 模型名称或 Hugging Face 仓库 ID
      - device: "cpu" 或 "cuda"
      - compute_type: 计算精度，如 "float16"、"float32" 或 "int8"
    """
    # 如果请求 FP16 但设备非 CUDA，自动降级
    if compute_type == "float16" and device != "cuda":
        print("[Warning] 当前设备不支持 FP16，已自动降级到 float32。")
        compute_type = "float32"

    key = f"{model_name}_{device}_{compute_type}"
    if key not in loaded_models:
        model_dir = MODEL_PATH_MAPPING.get(model_name, f"./models/{model_name}")

        # 自动下载模型
        if not os.path.exists(model_dir):
            os.makedirs(model_dir, exist_ok=True)
            hf_repo_id = HF_REPO_IDS.get(model_name, model_name)
            print(f"Downloading model {hf_repo_id} to {model_dir}...")
            try:
                snapshot_download(
                    repo_id=hf_repo_id,
                    local_dir=model_dir,
                    local_dir_use_symlinks=False,
                    resume_download=True,
                    token=None,
                )
                print(f"Model downloaded successfully to {model_dir}")
            except Exception as e:
                raise RuntimeError(f"模型下载失败: {e}")

        if not os.path.isdir(model_dir):
            raise RuntimeError(f"模型目录 {model_dir} 不存在，请检查路径或下载配置")

        try:
            loaded_models[key] = WhisperModel(
                model_dir,
                device=device,
                compute_type=compute_type,
                local_files_only=True,  # 仅使用本地文件
            )
        except Exception as e:
            raise RuntimeError(f"加载模型失败: {e}") from e

    return loaded_models[key]


# 线程池用于并发处理任务
executor = ThreadPoolExecutor(max_workers=4)


def transcribe_audio(model: WhisperModel, file_path: str, beam_size: int):
    """音频转录实现"""
    try:
        segments, info = model.transcribe(file_path, beam_size=beam_size)
        segments = list(segments)
        transcript = "".join(segment.text for segment in segments)
        return {
            "transcript": transcript,
            "language": info.language,
            "segments": [
                {"start": seg.start, "end": seg.end, "text": seg.text}
                for seg in segments
            ],
        }
    except Exception as e:
        return {"error": str(e)}


@app.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    model_name: str = Query(
        "faster-whisper-base", description="模型名称或 Hugging Face 仓库 ID"
    ),
    beam_size: int = Query(5, description="Beam Size"),
    device: str = Query("cpu", description="运行设备: cpu/cuda"),
    compute_type: str = Query("float16", description="计算精度: float16/float32/int8"),
):
    # 验证音频格式
    allowed_types = [
        "audio/wav",
        "audio/x-wav",
        "audio/wave",
        "audio/x-pn-wav",
        "audio/mpeg",
        "audio/mp3",
    ]
    if file.content_type not in allowed_types:
        raise HTTPException(400, detail="不支持的音频格式")

    # 保存临时文件
    try:
        suffix = "." + file.filename.split(".")[-1]
    except Exception:
        suffix = ".wav"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        contents = await file.read()
        tmp.write(contents)
        tmp_path = tmp.name

    loop = asyncio.get_running_loop()
    try:
        # 异步加载模型并转录
        model = await loop.run_in_executor(
            executor, get_model, model_name, device, compute_type
        )
        result = await loop.run_in_executor(
            executor, transcribe_audio, model, tmp_path, beam_size
        )
    except Exception as e:
        raise HTTPException(500, detail=str(e))
    finally:
        os.unlink(tmp_path)

    if "error" in result:
        raise HTTPException(500, detail=result["error"])

    return JSONResponse(content=result)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
