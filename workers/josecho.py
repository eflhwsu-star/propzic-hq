"""
🧮 조세호 — 일일 업무 보고
매일 09:00 KST 실행 → 카카오톡 발송
경영지원팀 스타일: 숫자 정확, 유머 한 줄
"""

import os
import sys
import json
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import anthropic
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
from brand_config import BRAND_NAME, SERVICE_B2C, SERVICE_B2B, DEFAULT_MODEL, HQ_DOMAIN
from db.migrate_debates import get_db_path

load_dotenv()

logger = logging.getLogger("worker.josecho")
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = f"""당신은 {BRAND_NAME}의 경영지원팀 조세호(세금·회계·비용관리)입니다.
매일 아침 회장님께 일일 업무 보고를 올립니다.
특징:
- 숫자와 팩트 중심, 정확한 현황 파악
- 마지막에 유머 있는 한마디 (부동산/회계 관련 위트)
- 간결하게 핵심만 (카카오톡이라 짧게)
항상 한국어로 답변합니다."""


def run() -> str:
    """일일 업무 보고 생성"""
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    weekday = ["월", "화", "수", "목", "금", "토", "일"][today.weekday()]

    # HQ DB에서 최근 토론/업무 현황 조회
    hq_stats = _get_hq_stats()

    prompt = f"""오늘: {today_str} ({weekday}요일)

[지휘본부 현황]
{hq_stats}

위 데이터를 바탕으로 일일 업무 보고를 작성하세요.

형식:
🧮 조세호 일일 업무 보고
📅 {today_str} ({weekday})

📊 서비스 현황
- {SERVICE_B2C}: (상태 요약)
- {SERVICE_B2B}: (상태 요약)
- 지휘본부: (상태 요약)

📌 오늘 체크포인트
1. (핵심 1)
2. (핵심 2)

💬 조세호의 한마디
(유머 있는 한 줄 - 부동산/경영 관련 위트)"""

    response = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=800,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    report = response.content[0].text

    # 실행 로그 저장
    _save_log("josecho", report)

    return report


def _get_hq_stats() -> str:
    """HQ SQLite에서 현황 조회"""
    try:
        conn = sqlite3.connect(get_db_path())
        conn.row_factory = sqlite3.Row

        # 최근 토론 수
        debate_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM hq_debates WHERE created_at >= date('now', '-7 days')"
        ).fetchone()["cnt"]

        # 최근 토론 주제
        recent = conn.execute(
            "SELECT topic, status FROM hq_debates ORDER BY created_at DESC LIMIT 3"
        ).fetchall()
        recent_topics = "\n".join(
            f"  - {r['topic']} ({r['status']})" for r in recent
        ) if recent else "  - 최근 토론 없음"

        conn.close()

        return f"""최근 7일 토론 수: {debate_count}건
최근 토론:
{recent_topics}"""
    except Exception as e:
        return f"DB 조회 실패: {e}"


def _save_log(worker_name: str, result: str):
    """실행 로그 저장"""
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
