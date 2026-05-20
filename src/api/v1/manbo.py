import asyncio
import os
from datetime import date

import httpx
from fastapi import APIRouter, HTTPException, Query, Request, status

from src.config.settings import MANBO_API_URL, MANBO_DAILY_LIMIT, MILORAPART_API_KEY

router = APIRouter(prefix="/apis", tags=["曼波配音"])

# 简单的 IP 限流存储（生产环境应使用 Redis）
ip_request_counts = {}


def get_today_key(ip: str) -> str:
    """生成今日的 IP 统计键"""
    today = date.today().strftime("%Y-%m-%d")
    return f"{ip}_{today}"


def check_rate_limit(ip: str) -> bool:
    """检查 IP 是否超过每日请求限制"""
    key = get_today_key(ip)
    count = ip_request_counts.get(key, 0)
    return count < MANBO_DAILY_LIMIT


def increment_request_count(ip: str):
    """增加请求计数"""
    key = get_today_key(ip)
    ip_request_counts[key] = ip_request_counts.get(key, 0) + 1


@router.get("/mbAIsc", summary="曼波配音生成试用版")
async def generate_manbo_voice(
    request: Request,
    text: str = Query(..., description="要转换的文本"),
    format: str = Query("mp3", description="输出格式，支持 mp3 等"),
):
    """
    通过文字生成曼波语音

    **限制**: 单 IP 一天限制 50 次

    **参数**:
    - text: 要转换为语音的文本内容
    - format: 输出格式，默认 mp3

    **返回**:
    - 成功时返回音频数据（字节流）
    - 失败时返回 JSON 错误信息
    """
    client_ip = request.client.host

    # 检查限流
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"今日请求次数已达上限（{MANBO_DAILY_LIMIT}次），请明日再试",
        )

    # 构建请求参数
    params = {"text": text, "format": format}

    # 构建请求头
    headers = {}
    if MILORAPART_API_KEY:
        headers["Authorization"] = f"Bearer {MILORAPART_API_KEY}"

    # 调用曼波配音 API
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.get(MANBO_API_URL, params=params, headers=headers)
            response.raise_for_status()

            # 增加请求计数
            increment_request_count(client_ip)

            # 根据响应内容类型返回
            if response.headers.get("content-type", "").startswith("audio/"):
                return response.content
            else:
                return response.json()

        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"调用曼波配音服务失败: {str(e)}",
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"服务器内部错误: {str(e)}",
            )
