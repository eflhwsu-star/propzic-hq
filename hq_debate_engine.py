"""
PROPZIC HQ — AI 직원 자율 토론 엔진
직원들이 주제를 놓고 라운드별 토론 후 CEO가 결론 도출
"""

import os
import json
import logging
import time
from datetime import datetime

import anthropic
import requests
from dotenv import load_dotenv

from brand_config import BRAND_NAME, SERVICE_B2C, SERVICE_B2B, DEFAULT_MODEL

load_dotenv()

logger = logging.getLogger("debate-engine")

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")  # service_role 키 사용

HAIKU_MODEL = "claude-haiku-4-5-20251001"
SONNET_MODEL = DEFAULT_MODEL

MAX_RETRIES = 3
RETRY_DELAY = 3


def _is_retryable(e: Exception) -> bool:
    if isinstance(e, anthropic.APIStatusError):
        return e.status_code >= 500 or e.status_code == 529
    return "overloaded" in str(e).lower()


def _call_claude(*, model, system, prompt, max_tokens=400, retries=MAX_RETRIES):
    """Claude API 호출 (재시도 래핑)"""
    for attempt in range(1, retries + 1):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except Exception as e:
            if attempt < retries and _is_retryable(e):
                logger.warning(f"[retry {attempt}/{retries}] {e} — {RETRY_DELAY}s 후 재시도")
                time.sleep(RETRY_DELAY)
            else:
                raise


# ===== Supabase REST helpers =====

def _supabase_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _supabase_insert(table: str, data: dict) -> dict:
    """Supabase REST API로 데이터 삽입"""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    res = requests.post(url, headers=_supabase_headers(), json=data, timeout=10)
    res.raise_for_status()
    return res.json()[0] if res.json() else {}


def _supabase_update(table: str, match: dict, data: dict) -> dict:
    """Supabase REST API로 데이터 업데이트"""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    params = {f"{k}": f"eq.{v}" for k, v in match.items()}
    res = requests.patch(url, headers=_supabase_headers(), params=params, json=data, timeout=10)
    res.raise_for_status()
    return res.json()[0] if res.json() else {}


def _supabase_select(table: str, params: dict = None) -> list:
    """Supabase REST API로 데이터 조회"""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = _supabase_headers()
    headers["Prefer"] = ""  # select에서는 필요 없음
    res = requests.get(url, headers=headers, params=params or {}, timeout=10)
    res.raise_for_status()
    return res.json()


# ===== 직원 정의 =====

HQ_EMPLOYEES = {
    "이준서": {
        "emoji": "👔", "dept": "C-Suite", "role": "CEO",
        "prompt": f"당신은 {BRAND_NAME}의 CEO 이준서입니다. {SERVICE_B2C}(B2C)과 {SERVICE_B2B}(B2B) 두 서비스를 총괄합니다. 전략적 사고와 결단력이 뛰어나며, 직원들의 의견을 종합해 최종 결론을 내립니다. 간결하고 명확하게 발언하며 항상 실행 가능한 결론을 도출합니다. 항상 한국어로 답변합니다."
    },
    "강수미": {
        "emoji": "📋", "dept": "C-Suite", "role": "비서실장",
        "prompt": f"당신은 {BRAND_NAME}의 비서실장 강수미입니다. 회의 진행을 조율하고 중요한 포인트를 정리합니다. 논리적이고 체계적이며 각 발언의 핵심을 날카롭게 짚어냅니다. 항상 한국어로 답변합니다."
    },
    "함영진": {
        "emoji": "🏠", "dept": "부동산현장전문가", "role": "시장분석전문가",
        "prompt": f"당신은 {BRAND_NAME}의 시장분석전문가 함영진입니다. 20년 이상의 부동산 현장 경험을 바탕으로 시장 흐름을 정확히 읽습니다. 데이터와 현장 감각을 결합한 통찰력 있는 분석을 제공합니다. 항상 한국어로 답변합니다."
    },
    "박원갑": {
        "emoji": "📊", "dept": "부동산현장전문가", "role": "부동산수석전문위원",
        "prompt": f"당신은 {BRAND_NAME}의 수석전문위원 박원갑입니다. 거시경제와 부동산 정책의 연결고리를 분석하는 전문가입니다. 균형 잡힌 시각으로 단기와 장기 전망을 모두 제시합니다. 항상 한국어로 답변합니다."
    },
    "오건영": {
        "emoji": "💹", "dept": "전략인텔팀", "role": "부동산투자전문가",
        "prompt": f"당신은 {BRAND_NAME}의 부동산투자전문가 오건영입니다. 금리, 환율, 글로벌 자금흐름과 부동산의 관계를 꿰뚫고 있습니다. 투자자 관점의 날카로운 통찰을 제공합니다. 항상 한국어로 답변합니다."
    },
    "하정우": {
        "emoji": "💻", "dept": "기술팀", "role": "기술총괄",
        "prompt": f"당신은 {BRAND_NAME}의 기술총괄 하정우입니다. AI와 데이터 기술로 부동산 문제를 해결하는 전문가입니다. 기술적 실현 가능성과 사용자 경험 관점에서 의견을 제시합니다. 항상 한국어로 답변합니다."
    },
    "전지현": {
        "emoji": "✨", "dept": "마케팅팀", "role": "마케팅총괄",
        "prompt": f"당신은 {BRAND_NAME}의 마케팅총괄 전지현입니다. 브랜드 전략과 사용자 획득에 탁월합니다. 고객의 니즈를 정확히 파악하고 효과적인 커뮤니케이션 전략을 제시합니다. 항상 한국어로 답변합니다."
    },
    "전현무": {
        "emoji": "🎯", "dept": "전략인텔팀", "role": "전략총괄",
        "prompt": f"당신은 {BRAND_NAME}의 전략총괄 전현무입니다. 시장 기회를 포착하고 경쟁 전략을 수립하는 전문가입니다. 항상 3~5년 앞을 내다보며 전략적 방향을 제시합니다. 항상 한국어로 답변합니다."
    },
    "한동훈": {
        "emoji": "⚖️", "dept": "법무컴플라이언스", "role": "법무총괄",
        "prompt": f"당신은 {BRAND_NAME}의 법무총괄 한동훈입니다. 부동산 관련 법규와 규제 환경에 정통합니다. 리스크를 사전에 파악하고 컴플라이언스 관점의 조언을 제공합니다. 항상 한국어로 답변합니다."
    },
}

# 주제별 참여 직원 매핑
TOPIC_PARTICIPANTS = {
    "market": ["함영진", "박원갑", "오건영", "전현무", "이준서"],
    "strategy": ["전현무", "전지현", "하정우", "강수미", "이준서"],
    "tech": ["하정우", "전지현", "강수미", "이준서"],
    "legal": ["한동훈", "전현무", "강수미", "이준서"],
    "operation": ["강수미", "하정우", "전지현", "이준서"],
    "ceo_order": ["강수미", "전현무", "함영진", "하정우", "이준서"],
}


def run_debate(topic: str, category: str, triggered_by: str = "scheduled") -> tuple:
    """
    동기식 토론 실행.
    Returns: (debate_id, conclusion)
    """
    participants = TOPIC_PARTICIPANTS.get(category, TOPIC_PARTICIPANTS["strategy"])

    # 1. 토론 세션 생성
    debate = _supabase_insert("hq_debates", {
        "topic": topic,
        "topic_category": category,
        "status": "in_progress",
        "participants": participants,
        "triggered_by": triggered_by,
    })
    debate_id = debate["id"]
    logger.info(f"토론 시작: [{category}] {topic} (id={debate_id})")

    conversation_history = []
    non_ceo = [p for p in participants if p != "이준서"]

    # 2. 직원 토론 (5라운드)
    for round_num in range(1, 6):
        for speaker_name in non_ceo:
            employee = HQ_EMPLOYEES[speaker_name]

            # 최근 6개 발언 컨텍스트
            history_text = "\n".join(
                f"{m['speaker_name']}: {m['content']}"
                for m in conversation_history[-6:]
            )

            prompt = f"""주제: {topic}

지금까지의 토론:
{history_text if history_text else "(토론 시작)"}

위 토론에 이어서 당신의 전문 영역 관점에서 발언해주세요.
- 다른 직원의 의견에 동의하거나 반박하세요
- 구체적인 데이터나 사례를 들어 주장하세요
- 150자 내외로 핵심만 간결하게 말하세요
- 반드시 한국어로 답변하세요"""

            try:
                content = _call_claude(
                    model=HAIKU_MODEL,
                    system=employee["prompt"],
                    prompt=prompt,
                    max_tokens=400,
                )
            except Exception as e:
                logger.error(f"토론 발언 실패 ({speaker_name}): {e}")
                content = f"[발언 오류: {e}]"

            # DB 저장
            _supabase_insert("hq_debate_messages", {
                "debate_id": debate_id,
                "speaker_key": speaker_name,
                "speaker_name": speaker_name,
                "speaker_emoji": employee["emoji"],
                "speaker_dept": employee["dept"],
                "content": content,
                "round_number": round_num,
            })

            conversation_history.append({
                "speaker_name": speaker_name,
                "content": content,
            })

            logger.info(f"  R{round_num} {speaker_name}: {content[:50]}...")

    # 3. CEO 최종 결론
    full_history = "\n".join(
        f"{m['speaker_name']}: {m['content']}"
        for m in conversation_history
    )

    ceo_prompt = f"""주제: {topic}

직원들의 토론 내용:
{full_history}

위 토론을 바탕으로 CEO로서 최종 결론과 액션 아이템을 정리해주세요.

다음 형식으로 답변하세요:
[결론] (2~3문장으로 핵심 결론)
[액션1] (구체적 실행 과제)
[액션2] (구체적 실행 과제)
[액션3] (구체적 실행 과제)"""

    try:
        ceo_content = _call_claude(
            model=SONNET_MODEL,
            system=HQ_EMPLOYEES["이준서"]["prompt"],
            prompt=ceo_prompt,
            max_tokens=600,
        )
    except Exception as e:
        logger.error(f"CEO 결론 도출 실패: {e}")
        ceo_content = f"[결론 도출 오류: {e}]"

    # CEO 발언 저장
    _supabase_insert("hq_debate_messages", {
        "debate_id": debate_id,
        "speaker_key": "이준서",
        "speaker_name": "이준서",
        "speaker_emoji": "👔",
        "speaker_dept": "C-Suite",
        "content": ceo_content,
        "round_number": 99,
    })

    # 4. 토론 완료 처리
    _supabase_update("hq_debates", {"id": debate_id}, {
        "status": "concluded",
        "conclusion": ceo_content,
        "concluded_at": datetime.now().isoformat(),
    })

    logger.info(f"토론 완료: {debate_id}")
    return debate_id, ceo_content


def run_debate_streaming(topic: str, category: str, triggered_by: str = "ceo_order"):
    """
    SSE 스트리밍 토론 실행 (제너레이터).
    API 엔드포인트에서 StreamingResponse로 사용.
    """
    participants = TOPIC_PARTICIPANTS.get(category, TOPIC_PARTICIPANTS["strategy"])

    # 세션 생성
    debate = _supabase_insert("hq_debates", {
        "topic": topic,
        "topic_category": category,
        "status": "in_progress",
        "participants": participants,
        "triggered_by": triggered_by,
    })
    debate_id = debate["id"]

    yield _sse({"phase": "debate_start", "debate_id": debate_id, "topic": topic, "participants": participants})

    conversation_history = []
    non_ceo = [p for p in participants if p != "이준서"]

    # 직원 토론 (5라운드)
    for round_num in range(1, 6):
        yield _sse({"phase": "round_start", "round": round_num})

        for speaker_name in non_ceo:
            employee = HQ_EMPLOYEES[speaker_name]

            yield _sse({
                "phase": "speaking_start",
                "name": speaker_name,
                "emoji": employee["emoji"],
                "dept": employee["dept"],
                "role": employee["role"],
                "round": round_num,
            })

            history_text = "\n".join(
                f"{m['speaker_name']}: {m['content']}"
                for m in conversation_history[-6:]
            )

            prompt = f"""주제: {topic}

지금까지의 토론:
{history_text if history_text else "(토론 시작)"}

위 토론에 이어서 당신의 전문 영역 관점에서 발언해주세요.
- 다른 직원의 의견에 동의하거나 반박하세요
- 구체적인 데이터나 사례를 들어 주장하세요
- 150자 내외로 핵심만 간결하게 말하세요
- 반드시 한국어로 답변하세요"""

            try:
                content = _call_claude(
                    model=HAIKU_MODEL,
                    system=employee["prompt"],
                    prompt=prompt,
                    max_tokens=400,
                )
            except Exception as e:
                content = f"[발언 오류: {e}]"

            # DB 저장
            _supabase_insert("hq_debate_messages", {
                "debate_id": debate_id,
                "speaker_key": speaker_name,
                "speaker_name": speaker_name,
                "speaker_emoji": employee["emoji"],
                "speaker_dept": employee["dept"],
                "content": content,
                "round_number": round_num,
            })

            conversation_history.append({
                "speaker_name": speaker_name,
                "content": content,
            })

            yield _sse({
                "phase": "speaking_done",
                "name": speaker_name,
                "emoji": employee["emoji"],
                "content": content,
                "round": round_num,
            })

    # CEO 결론
    yield _sse({"phase": "ceo_concluding"})

    full_history = "\n".join(
        f"{m['speaker_name']}: {m['content']}"
        for m in conversation_history
    )

    ceo_prompt = f"""주제: {topic}

직원들의 토론 내용:
{full_history}

위 토론을 바탕으로 CEO로서 최종 결론과 액션 아이템을 정리해주세요.

다음 형식으로 답변하세요:
[결론] (2~3문장으로 핵심 결론)
[액션1] (구체적 실행 과제)
[액션2] (구체적 실행 과제)
[액션3] (구체적 실행 과제)"""

    try:
        ceo_content = _call_claude(
            model=SONNET_MODEL,
            system=HQ_EMPLOYEES["이준서"]["prompt"],
            prompt=ceo_prompt,
            max_tokens=600,
        )
    except Exception as e:
        ceo_content = f"[결론 도출 오류: {e}]"

    _supabase_insert("hq_debate_messages", {
        "debate_id": debate_id,
        "speaker_key": "이준서",
        "speaker_name": "이준서",
        "speaker_emoji": "👔",
        "speaker_dept": "C-Suite",
        "content": ceo_content,
        "round_number": 99,
    })

    _supabase_update("hq_debates", {"id": debate_id}, {
        "status": "concluded",
        "conclusion": ceo_content,
        "concluded_at": datetime.now().isoformat(),
    })

    yield _sse({
        "phase": "ceo_conclusion",
        "debate_id": debate_id,
        "content": ceo_content,
    })

    yield "data: [DONE]\n\n"


def get_debates(limit: int = 10) -> list:
    """최근 토론 목록 조회"""
    return _supabase_select("hq_debates", {
        "select": "*",
        "order": "created_at.desc",
        "limit": str(limit),
    })


def get_debate_detail(debate_id: str) -> dict:
    """토론 상세 + 전체 발언 조회"""
    debates = _supabase_select("hq_debates", {
        "select": "*",
        "id": f"eq.{debate_id}",
    })
    debate = debates[0] if debates else None

    messages = _supabase_select("hq_debate_messages", {
        "select": "*",
        "debate_id": f"eq.{debate_id}",
        "order": "created_at.asc",
    })

    return {"debate": debate, "messages": messages}


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
