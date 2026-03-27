"""
PropAI CEO Agent — 이준서 (전체총괄·일일주간브리핑)
일일/주간 브리핑 생성 + 채팅
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-20250514"

BASE_DIR = Path(__file__).parent.parent
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

CEO_SYSTEM = """당신은 PropAI CEO AI 이준서(전체총괄·일일주간브리핑)입니다.
집값해독(B2C 부동산 데이터)과 중개오토(B2B 중개사 자동화) 두 서비스를 총괄합니다.
24시간 즉각 응답. 핵심 먼저, 3줄 요약 후 상세 설명.
문제 발견 시 해결책 함께 제시. 긴급도: 🔴긴급 🟡주의 🟢정상.
항상 한국어로 답변."""


def generate_daily_briefing(monitor_result: str = "", infra_result: str = "") -> str:
    """일일 오전 브리핑 생성 → reports/YYYY-MM-DD.md 저장"""
    today = datetime.now().strftime("%Y-%m-%d")
    prompt = f"""오늘 날짜: {today}

[모니터링 결과]
{monitor_result or '데이터 없음'}

[인프라 점검 결과]
{infra_result or '데이터 없음'}

위 데이터를 바탕으로 오전 브리핑을 작성하세요.

형식:
# PropAI 일일 브리핑 — {today}

## 🔴 긴급사항
(없으면 "없음")

## 🟡 주의사항
(없으면 "없음")

## 🟢 정상 현황

## 📌 오늘 우선순위 TOP 2
1.
2.

---
👑 이준서 CEO AI · PropAI HQ"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=CEO_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    briefing = response.content[0].text

    path = REPORTS_DIR / f"{today}.md"
    path.write_text(briefing, encoding="utf-8")
    print(f"[CEO] 일일 브리핑 저장: {path}")
    return briefing


def generate_weekly_briefing() -> str:
    """주간 브리핑: 최근 7일 브리핑 취합 → 주간 요약"""
    today = datetime.now()
    week_reports = []

    for i in range(7):
        date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        path = REPORTS_DIR / f"{date}.md"
        if path.exists():
            week_reports.append(f"### {date}\n{path.read_text(encoding='utf-8')}")

    if not week_reports:
        return "주간 브리핑 생성 불가: 최근 7일 일일 브리핑 없음"

    combined = "\n\n".join(week_reports)
    prompt = f"""아래는 최근 7일간의 일일 브리핑입니다. 주간 요약을 작성하세요.

{combined}

형식:
# PropAI 주간 브리핑 — {today.strftime('%Y-%m-%d')} 기준

## 📊 이번 주 요약 (3줄)

## 🔴 해결된 긴급사항

## 🟡 진행 중 주의사항

## 📈 핵심 지표 변화

## 📌 다음 주 우선순위 TOP 3
1.
2.
3.

---
👑 이준서 CEO AI · PropAI HQ 주간보고"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=3000,
        system=CEO_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    briefing = response.content[0].text

    path = REPORTS_DIR / f"weekly_{today.strftime('%Y-%m-%d')}.md"
    path.write_text(briefing, encoding="utf-8")
    print(f"[CEO] 주간 브리핑 저장: {path}")
    return briefing


def chat_stream(message: str, history: list):
    """CEO 채팅 스트리밍 generator"""
    messages = []
    for h in history[-10:]:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": message})

    with client.messages.stream(
        model=MODEL,
        max_tokens=4096,
        system=CEO_SYSTEM,
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            yield text
