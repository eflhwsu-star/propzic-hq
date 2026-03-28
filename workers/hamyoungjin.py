"""
🏠 함영진 — 부동산 시장 브리핑
매일 09:00 KST 실행 → 카카오톡 발송
부동산현장전문가 스타일: 현장 감각 + 데이터 중심
"""

import os
import sys
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import anthropic
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
from brand_config import BRAND_NAME, DEFAULT_MODEL
from db.migrate_debates import get_db_path

load_dotenv()

logger = logging.getLogger("worker.hamyoungjin")
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = f"""당신은 {BRAND_NAME}의 시장분석전문가 함영진(공인중개사고문)입니다.
20년 이상의 부동산 현장 경험. 데이터와 현장 감각을 결합한 통찰.
매일 아침 회장님께 부동산 시장 브리핑을 올립니다.
특징:
- 오늘자 부동산 뉴스/이슈를 현장 전문가 시각으로 해석
- "현장에서 보면~", "중개사들 사이에서~" 같은 현장감 있는 톤
- 핵심 3~5개 포인트로 간결하게
- 마지막에 "함영진의 현장 촉" 한 줄
항상 한국어로 답변합니다."""


def run() -> str:
    """부동산 시장 브리핑 생성 (web_search 활용)"""
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    weekday = ["월", "화", "수", "목", "금", "토", "일"][today.weekday()]

    # Claude web_search 툴로 최신 부동산 뉴스 수집 + 브리핑 작성
    prompt = f"""오늘: {today_str} ({weekday}요일)

오늘자 부동산 관련 주요 뉴스를 검색하고, 시장 브리핑을 작성해주세요.
검색 키워드: "부동산 시장", "아파트 매매", "전세 시장", "부동산 정책"

형식:
🏠 함영진 시장 브리핑
📅 {today_str} ({weekday})

📰 오늘의 부동산 뉴스
1. (뉴스 제목 + 핵심 한 줄 해석)
2. (뉴스 제목 + 핵심 한 줄 해석)
3. (뉴스 제목 + 핵심 한 줄 해석)

📊 시장 동향 요약
(3줄로 현재 시장 상황 정리)

🔮 함영진의 현장 촉
(현장 전문가로서 한마디 — "중개사들 사이에서~" 스타일)"""

    try:
        # web_search 툴 사용으로 최신 뉴스 검색
        response = client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=1200,
            system=SYSTEM_PROMPT,
            tools=[{"type": "web_search_20250305"}],
            messages=[{"role": "user", "content": prompt}],
        )

        # 응답에서 텍스트 추출
        report = _extract_text(response)

    except Exception as e:
        logger.error(f"web_search 실패, fallback: {e}")
        # fallback: web_search 없이 Claude 지식 기반
        response = client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=1200,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        report = response.content[0].text

    _save_log("hamyoungjin", report)
    return report


def _extract_text(response) -> str:
    """Claude 응답에서 텍스트 블록만 추출"""
    texts = []
    for block in response.content:
        if hasattr(block, "text"):
            texts.append(block.text)
    return "\n".join(texts) if texts else str(response.content)


def _save_log(worker_name: str, result: str):
    try:
        conn = sqlite3.connect(get_db_path())
        conn.execute(
            "INSERT INTO worker_logs (id, worker_name, status, result_summary) VALUES (?, ?, 'success', ?)",
            (str(uuid4()), worker_name, result[:500]),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"로그 저장 실패: {e}")


if __name__ == "__main__":
    print(run())
