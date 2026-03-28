"""
💹 오건영 — KB시세 분석 리포트
매주 월요일 + 매월 1일 09:00 KST 실행 → 카카오톡 발송
부동산투자전문가 스타일: 거시경제 관점, 금리/환율/자금흐름 연결
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
from brand_config import BRAND_NAME, DEFAULT_MODEL
from db.migrate_debates import get_db_path

load_dotenv()

logger = logging.getLogger("worker.okungyoung")
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = f"""당신은 {BRAND_NAME}의 부동산투자전문가 오건영입니다.
금리, 환율, 글로벌 자금흐름과 부동산의 관계를 꿰뚫고 있습니다.
KB시세 데이터를 분석하여 투자자 관점의 날카로운 통찰을 제공합니다.
특징:
- 숫자 변화를 거시경제와 연결하여 해석
- "금리가 이렇게 움직이면 부동산은~" 스타일
- 전국/서울/수도권 비교 분석
- 전월비, 전년비 트렌드 해석
항상 한국어로 답변합니다."""


def run(data_type: str = "weekly") -> str:
    """KB시세 분석 리포트 생성
    data_type: 'weekly' (주간) 또는 'monthly' (월간)
    """
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")

    # 1. 웹서치로 최신 KB시세 데이터 수집
    kb_data = _fetch_kb_data(data_type)

    # 2. 이전 데이터 조회 (비교용)
    prev_data = _get_previous_data(data_type, limit=3)

    # 3. 분석 리포트 생성
    type_label = "주간" if data_type == "weekly" else "월간"

    prompt = f"""오늘: {today_str}
분석 유형: KB시세 {type_label} 리포트

[최신 KB시세 데이터]
{kb_data}

[이전 3회 데이터]
{prev_data}

위 데이터를 바탕으로 KB시세 {type_label} 분석 리포트를 작성하세요.

형식:
💹 오건영 KB시세 {type_label} 분석
📅 {today_str}

📊 주요 지표
- 전국: (지수 + 전월비 + 전년비)
- 서울: (지수 + 전월비 + 전년비)
- 수도권: (지수 + 전월비 + 전년비)

📈 트렌드 분석
(이전 데이터와 비교하여 3줄 분석)

🌍 거시경제 연결
(금리/환율/글로벌 자금흐름과 연결하여 해석)

🎯 오건영의 투자 시그널
(투자자 관점 핵심 한마디)"""

    response = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=1200,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    report = response.content[0].text

    # 4. DB에 데이터 저장
    _save_kb_data(today_str, data_type, kb_data, report)
    _save_log("okungyoung", report)

    return report


def _fetch_kb_data(data_type: str) -> str:
    """웹서치로 최신 KB시세 데이터 수집"""
    type_label = "주간" if data_type == "weekly" else "월간"

    try:
        response = client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=800,
            system="최신 KB부동산 시세 데이터를 검색하여 정리해주세요. 숫자 데이터 중심으로.",
            tools=[{"type": "web_search_20250305"}],
            messages=[{
                "role": "user",
                "content": f"KB부동산 {type_label} 시세 최신 발표 데이터를 검색해주세요. "
                           f"전국/서울/수도권 아파트 매매가격지수, 전월비, 전년비 포함."
            }],
        )
        texts = []
        for block in response.content:
            if hasattr(block, "text"):
                texts.append(block.text)
        return "\n".join(texts) if texts else "데이터 수집 실패"

    except Exception as e:
        logger.error(f"KB시세 웹서치 실패: {e}")
        return f"웹서치 실패: {e}. 최신 KB시세 데이터를 기반으로 분석해주세요."


def _get_previous_data(data_type: str, limit: int = 3) -> str:
    """이전 KB시세 데이터 조회"""
    try:
        conn = sqlite3.connect(get_db_path())
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT publish_date, nationwide_index, seoul_index, metropolitan_index, "
            "nationwide_mom, seoul_mom, metropolitan_mom "
            "FROM kb_price_data WHERE data_type=? ORDER BY publish_date DESC LIMIT ?",
            (data_type, limit),
        ).fetchall()
        conn.close()

        if not rows:
            return "이전 데이터 없음 (최초 수집)"

        lines = []
        for r in rows:
            lines.append(
                f"{r['publish_date']}: 전국 {r['nationwide_index'] or '-'} "
                f"(전월비 {r['nationwide_mom'] or '-'}%), "
                f"서울 {r['seoul_index'] or '-'} "
                f"(전월비 {r['seoul_mom'] or '-'}%)"
            )
        return "\n".join(lines)

    except Exception as e:
        logger.error(f"이전 데이터 조회 실패: {e}")
        return "이전 데이터 조회 실패"


def _save_kb_data(publish_date: str, data_type: str, raw: str, analysis: str):
    """KB시세 데이터 DB 저장"""
    try:
        conn = sqlite3.connect(get_db_path())
        conn.execute(
            "INSERT INTO kb_price_data (id, publish_date, data_type, raw_summary, analysis) "
            "VALUES (?, ?, ?, ?, ?)",
            (str(uuid4()), publish_date, data_type, raw[:2000], analysis[:2000]),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"KB 데이터 저장 실패: {e}")


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
    import sys as _sys
    dt = _sys.argv[1] if len(_sys.argv) > 1 else "weekly"
    print(run(dt))
