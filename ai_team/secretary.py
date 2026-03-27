"""
PROPZIC 비서실장 — 강수미 (일정관리·카카오브리핑발송·CEO보좌)
카카오톡 나에게 보내기 API로 브리핑 발송
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv, set_key

# brand_config import (상위 디렉토리)
sys.path.insert(0, str(Path(__file__).parent.parent))
from brand_config import BRAND_NAME, HQ_DOMAIN

load_dotenv()

BASE_DIR = Path(__file__).parent.parent
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)
ENV_PATH = BASE_DIR / ".env"

logger = logging.getLogger("secretary")
handler = logging.FileHandler(LOGS_DIR / "kakao.log", encoding="utf-8")
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

KAKAO_SEND_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"


def refresh_kakao_token() -> str | None:
    """카카오 토큰 갱신 → .env 업데이트"""
    refresh_token = os.getenv("KAKAO_REFRESH_TOKEN")
    if not refresh_token:
        logger.error("KAKAO_REFRESH_TOKEN 없음. 갱신 불가.")
        return None

    data = {
        "grant_type": "refresh_token",
        "client_id": os.getenv("KAKAO_REST_API_KEY", ""),
        "refresh_token": refresh_token,
    }
    try:
        res = requests.post(KAKAO_TOKEN_URL, data=data, timeout=10)
        res.raise_for_status()
        result = res.json()

        new_access = result.get("access_token")
        new_refresh = result.get("refresh_token")

        if new_access and ENV_PATH.exists():
            set_key(str(ENV_PATH), "KAKAO_ACCESS_TOKEN", new_access)
            os.environ["KAKAO_ACCESS_TOKEN"] = new_access
            logger.info("카카오 Access Token 갱신 완료")

        if new_refresh and ENV_PATH.exists():
            set_key(str(ENV_PATH), "KAKAO_REFRESH_TOKEN", new_refresh)
            os.environ["KAKAO_REFRESH_TOKEN"] = new_refresh
            logger.info("카카오 Refresh Token 갱신 완료")

        return new_access
    except Exception as e:
        logger.error(f"토큰 갱신 실패: {e}")
        return None


def send_briefing(text: str) -> bool:
    """카카오톡 나에게 보내기로 브리핑 발송"""
    access_token = os.getenv("KAKAO_ACCESS_TOKEN")
    if not access_token:
        logger.error("KAKAO_ACCESS_TOKEN 없음")
        return False

    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    message = f"[{BRAND_NAME} 오전 브리핑] 👑 이준서 CEO 보고\n\n{text}\n\n📍 {HQ_DOMAIN}\n⏰ {today}"

    # 카카오톡 텍스트 메시지 최대 길이 제한
    if len(message) > 2000:
        message = message[:1997] + "..."

    template = {
        "object_type": "text",
        "text": message,
        "link": {
            "web_url": f"https://{HQ_DOMAIN}",
            "mobile_web_url": f"https://{HQ_DOMAIN}",
        },
        "button_title": "HQ 대시보드 열기",
    }

    headers = {"Authorization": f"Bearer {access_token}"}
    data = {"template_object": json.dumps(template, ensure_ascii=False)}

    try:
        res = requests.post(KAKAO_SEND_URL, headers=headers, data=data, timeout=10)

        if res.status_code == 401:
            logger.warning("401 Unauthorized → 토큰 갱신 시도")
            new_token = refresh_kakao_token()
            if new_token:
                headers["Authorization"] = f"Bearer {new_token}"
                res = requests.post(KAKAO_SEND_URL, headers=headers, data=data, timeout=10)
            else:
                logger.error("토큰 갱신 실패. 발송 중단.")
                return False

        if res.status_code == 200:
            logger.info(f"카카오톡 브리핑 발송 성공 ({len(message)}자)")
            return True
        else:
            logger.error(f"발송 실패: {res.status_code} {res.text}")
            return False

    except Exception as e:
        logger.error(f"발송 예외: {e}")
        return False
