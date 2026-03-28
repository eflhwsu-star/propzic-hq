"""
PROPZIC HQ API Server — FastAPI (포트 8001)
34명 AI직원 채팅 + 끼어들기 시스템
"""

import os
import json
import glob
import time
import logging
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
import anthropic
from dotenv import load_dotenv

from brand_config import (
    BRAND_NAME, SERVICE_B2C, SERVICE_B2B, HQ_DOMAIN, DEFAULT_MODEL,
    CEO_COMMAND_SYSTEM, EMPLOYEE_MAP,
)
from hq_debate_engine import (
    run_debate_streaming, get_debates, get_debate_detail,
    HQ_EMPLOYEES, TOPIC_PARTICIPANTS,
)

load_dotenv()

app = FastAPI(title=f"{BRAND_NAME} HQ API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"https://{HQ_DOMAIN}",
        "http://localhost",
        "http://localhost:8001",
        "http://127.0.0.1",
        "http://127.0.0.1:5500",
        "null",  # file:// 프로토콜용
    ],
    allow_origin_regex=r"http://localhost:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = DEFAULT_MODEL

logger = logging.getLogger("propzic-hq")

MAX_RETRIES = 3
RETRY_DELAY = 3  # seconds


def _is_retryable(e: Exception) -> bool:
    """overloaded_error 또는 APIStatusError(5xx/529)인지 판별"""
    if isinstance(e, anthropic.APIStatusError):
        return e.status_code >= 500 or e.status_code == 529
    err_str = str(e).lower()
    return "overloaded" in err_str


def call_anthropic_create(*, retries=MAX_RETRIES, **kwargs):
    """client.messages.create 를 재시도 래핑 (non-streaming)"""
    for attempt in range(1, retries + 1):
        try:
            return client.messages.create(**kwargs)
        except Exception as e:
            if attempt < retries and _is_retryable(e):
                logger.warning(f"[retry {attempt}/{retries}] {e} — {RETRY_DELAY}s 후 재시도")
                time.sleep(RETRY_DELAY)
            else:
                raise


def call_anthropic_stream(*, retries=MAX_RETRIES, **kwargs):
    """client.messages.stream 을 재시도 래핑 (streaming context manager)
    사용: with call_anthropic_stream(model=..., ...) as stream:
    """
    for attempt in range(1, retries + 1):
        try:
            return client.messages.stream(**kwargs)
        except Exception as e:
            if attempt < retries and _is_retryable(e):
                logger.warning(f"[retry {attempt}/{retries}] {e} — {RETRY_DELAY}s 후 재시도")
                time.sleep(RETRY_DELAY)
            else:
                raise


BASE_DIR = Path(__file__).parent
REPORTS_DIR = BASE_DIR / "reports"
LOGS_DIR = BASE_DIR / "logs"
REPORTS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# ===== 직원 데이터 =====
STAFF = {
    "이준서": {"role": "전체총괄·일일주간브리핑", "emoji": "👑", "dept": "C-Suite"},
    "강수미": {"role": "일정관리·카카오브리핑발송·CEO보좌", "emoji": "💜", "dept": "C-Suite"},
    "한동훈": {"role": "법무팀장·계약검토·법률자문", "emoji": "⚖️", "dept": "법무"},
    "김능환": {"role": "판사출신변호사·부동산분쟁·소송·계약법률", "emoji": "🔨", "dept": "법무"},
    "채동욱": {"role": "검사출신변호사·사기방지·형사리스크·수사대응", "emoji": "🛡️", "dept": "법무"},
    "안철수": {"role": "IP·특허관리·상표등록", "emoji": "💡", "dept": "법무"},
    "장영실": {"role": "변리사·서비스특허·상표·IP출원", "emoji": "📋", "dept": "법무"},
    "박성수": {"role": "퇴직경찰30년·사기피해예방·이상거래탐지·범죄예방", "emoji": "🚔", "dept": "법무"},
    "함영진": {"role": "공인중개사고문·현장중개실무자문·중개오토기능검토", "emoji": "🏠", "dept": "부동산"},
    "박원갑": {"role": "감정평가사·부동산시세·적정가격검토·감정평가", "emoji": "📊", "dept": "부동산"},
    "김현정": {"role": "세무사·양도세·취득세·절세전략·중개오토계산기자문", "emoji": "🧾", "dept": "부동산"},
    "이헌재": {"role": "금융전문가·금리분석·대출규제·DSR·LTV해석", "emoji": "🏦", "dept": "부동산"},
    "유현준": {"role": "건축사·건물가치·리모델링·건축법·재건축검토", "emoji": "🏗️", "dept": "부동산"},
    "오세훈": {"role": "도시계획전문가·재개발·재건축·구역지정·개발호재분석", "emoji": "🌆", "dept": "부동산"},
    "김경란": {"role": "경매전문가·낙찰가분석·명도절차·경매물건분석", "emoji": "🔔", "dept": "부동산"},
    "이순신": {"role": "보험전문가·화재보험·임대인배상·권리보험·중개오토보험안내", "emoji": "🛡️", "dept": "부동산"},
    "하정우": {"role": "인프라팀장·서버·인프라관리·배포", "emoji": "🖥️", "dept": "기술"},
    "최민식": {"role": "보안감시·보안·기술이슈감시·취약점분석", "emoji": "🔒", "dept": "기술"},
    "손석희": {"role": "데이터분석·지표모니터링·통계", "emoji": "📈", "dept": "기술"},
    "전지현": {"role": "마케팅팀장·광고기획·집행·캠페인관리", "emoji": "📣", "dept": "마케팅"},
    "이윤서": {"role": "바이럴마케팅·SNS·인플루언서", "emoji": "🔥", "dept": "마케팅"},
    "김선태": {"role": "홍보PR·홍보·PR·언론대응", "emoji": "📰", "dept": "마케팅"},
    "송지효": {"role": "콘텐츠제작·블로그·뉴스레터", "emoji": "✍️", "dept": "마케팅"},
    "김범수": {"role": "그로스해킹·앱지표·퍼널최적화·리텐션", "emoji": "🚀", "dept": "마케팅"},
    "신동엽": {"role": "CS팀장·고객지원·문의처리·VOC관리", "emoji": "🎧", "dept": "고객경험"},
    "장원영": {"role": "UX디자인·사용자경험·UI개선", "emoji": "🎨", "dept": "고객경험"},
    "이경규": {"role": "서비스반응·리뷰수집·커뮤니티모니터링", "emoji": "👁️", "dept": "고객경험"},
    "전현무": {"role": "경쟁사인텔팀장·크롤링·시장분석", "emoji": "🕵️", "dept": "전략인텔"},
    "이재명": {"role": "부동산정책·법령리서치·규제변화", "emoji": "📜", "dept": "전략인텔"},
    "홍라희": {"role": "투자분석·거시경제·수익률계산·포트폴리오", "emoji": "📈", "dept": "전략인텔"},
    "오건영": {"role": "부동산투자전문가·아파트·재개발·상가·토지·NPL·경매 전유형 투자분석", "emoji": "💎", "dept": "전략인텔"},
    "조세호": {"role": "세금·회계·비용관리", "emoji": "🧮", "dept": "경영지원"},
    "염경환": {"role": "개인정보보호·CISO·GDPR·보안정책", "emoji": "🔐", "dept": "경영지원"},
    "김미경": {"role": "CFO·재무전략·투자유치·IR·수익모델", "emoji": "💰", "dept": "경영지원"},
}

# ===== CEO 시스템 프롬프트 =====
CEO_SYSTEM = f"""당신은 {BRAND_NAME} CEO AI 이준서(전체총괄·일일주간브리핑)입니다.
{SERVICE_B2C}(B2C 부동산 데이터)과 {SERVICE_B2B}(B2B 중개사 자동화) 두 서비스를 총괄합니다.
24시간 즉각 응답. 핵심 먼저, 3줄 요약 후 상세 설명.
문제 발견 시 해결책 함께 제시. 긴급도: 🔴긴급 🟡주의 🟢정상.
오너 업무지시 시 어느 팀 누구에게 배분할지 명확히 언급하세요.
항상 한국어로 답변."""

# ===== 끼어들기 시스템 프롬프트 =====
INTERRUPT_SYSTEM = f"""당신은 {BRAND_NAME} AI직원 코디네이터입니다.
대화 내용을 보고 추가 발언이 필요한 직원을 최대 2명 선별하세요.

직원 목록 (이름·담당업무):
한동훈(법무팀장·계약검토), 김능환(판사출신변호사·분쟁소송),
채동욱(검사출신변호사·사기방지), 안철수(IP특허), 장영실(변리사·출원),
박성수(퇴직경찰30년·이상거래탐지), 함영진(공인중개사고문·중개실무),
박원갑(감정평가사·시세검토), 김현정(세무사·양도세절세),
이헌재(금융전문가·대출DSR), 유현준(건축사·건물가치),
오세훈(도시계획·재개발재건축), 김경란(경매전문가·낙찰가분석),
이순신(보험전문가·임대인배상), 하정우(인프라팀장·서버관리),
최민식(보안·기술이슈감시), 손석희(데이터분석·지표모니터링),
전지현(마케팅팀장·광고기획), 이윤서(바이럴SNS), 김선태(홍보PR),
송지효(콘텐츠제작), 김범수(그로스해킹·앱지표),
신동엽(CS팀장·고객지원), 장원영(UX디자인), 이경규(반응모니터링),
전현무(경쟁사인텔팀장·크롤링), 이재명(정책법령리서치),
홍라희(투자분석·거시경제), 오건영(부동산투자전문가·아파트재개발상가토지NPL경매),
조세호(회계·비용관리), 염경환(개인정보보호·CISO), 김미경(CFO·재무전략)

응답은 반드시 JSON만 반환:
{{
  "interrupts": [
    {{"name": "오건영", "role": "부동산투자전문가", "emoji": "💎", "message": "발언내용"}},
    {{"name": "홍라희", "role": "투자분석", "emoji": "📈", "message": "발언내용"}}
  ]
}}
관련 없으면: {{"interrupts": []}}"""


def make_staff_system(name: str, role: str) -> str:
    return f"""당신은 {BRAND_NAME} AI직원 {name}({role})입니다.
24시간 즉각 응답. 핵심 먼저 3줄 요약. 해결책 함께 제시.
다른 부서 연관사항은 해당 직원 호출 언급.
긴급도: 🔴긴급 🟡주의 🟢정상. 항상 한국어로 답변."""


# ===== API ENDPOINTS =====

@app.post("/api/ceo/chat")
async def ceo_chat(request: Request):
    body = await request.json()
    message = body.get("message", "")
    history = body.get("history", [])

    messages = []
    for h in history[-10:]:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": message})

    async def generate():
        with call_anthropic_stream(
            model=MODEL,
            max_tokens=4096,
            system=CEO_SYSTEM,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                yield f"data: {json.dumps({'text': text}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/api/interrupt")
async def interrupt(request: Request):
    body = await request.json()
    owner_msg = body.get("message", "")
    ceo_response = body.get("ceo_response", "")

    prompt = f"오너 메시지: {owner_msg}\nCEO 이준서 응답: {ceo_response}"

    try:
        response = call_anthropic_create(
            model=MODEL,
            max_tokens=1024,
            system=INTERRUPT_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        # JSON 파싱
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        data = json.loads(text)
        return JSONResponse(data)
    except Exception as e:
        print(f"Interrupt error: {e}")
        return JSONResponse({"interrupts": []})


@app.post("/api/staff/chat")
async def staff_chat(request: Request):
    body = await request.json()
    staff_name = body.get("staff_name", "")
    role = body.get("role", "")
    message = body.get("message", "")
    history = body.get("history", [])

    if not role and staff_name in STAFF:
        role = STAFF[staff_name]["role"]

    system_prompt = make_staff_system(staff_name, role)

    messages = []
    for h in history[-10:]:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": message})

    async def generate():
        with call_anthropic_stream(
            model=MODEL,
            max_tokens=4096,
            system=system_prompt,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                yield f"data: {json.dumps({'text': text}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/api/briefing/today")
async def briefing_today():
    today = datetime.now().strftime("%Y-%m-%d")
    path = REPORTS_DIR / f"{today}.md"
    if path.exists():
        return {"briefing": path.read_text(encoding="utf-8"), "date": today}
    return {"briefing": "오늘 브리핑 미생성", "date": today}


@app.get("/api/briefing/list")
async def briefing_list():
    files = sorted(REPORTS_DIR.glob("*.md"), reverse=True)[:30]
    return {"reports": [f.stem for f in files]}


@app.get("/api/status")
async def status():
    result = {}
    for name, info in STAFF.items():
        result[name] = {
            "role": info["role"],
            "emoji": info["emoji"],
            "dept": info["dept"],
            "status": "online",
        }
    return {"staff": result, "total": len(STAFF), "timestamp": datetime.now().isoformat()}


@app.post("/api/briefing/generate-now")
async def generate_briefing_now():
    from ai_team.ceo_agent import generate_daily_briefing
    try:
        result = generate_daily_briefing(monitor_result="수동 생성 요청", infra_result="수동 생성 요청")
        return {"status": "success", "briefing": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _parse_json_response(text: str) -> dict:
    """Claude 응답에서 JSON 추출 (마크다운 코드블록 처리)"""
    text = text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    return json.loads(text)


@app.post("/api/command")
async def command(request: Request):
    """업무명령: CEO 경유 또는 직접 지시 (SSE 스트리밍)
    mode: "ceo" (기본) — CEO 판단 → 직원 실행 2단계 체인
    mode: "direct" — CEO 건너뛰고 지정 직원 바로 실행
    """
    body = await request.json()
    command_text = body.get("command", "")
    mode = body.get("mode", "ceo")
    assignee = body.get("assignee", "")  # direct 모드에서 직원 이름

    async def generate_ceo():
        """CEO 경유 모드"""
        yield f"data: {json.dumps({'phase': 'ceo_judging'}, ensure_ascii=False)}\n\n"

        try:
            ceo_response = call_anthropic_create(
                model=MODEL,
                max_tokens=1024,
                system=CEO_COMMAND_SYSTEM,
                messages=[{"role": "user", "content": command_text}],
            )
            ceo_text = ceo_response.content[0].text.strip()
            ceo_result = _parse_json_response(ceo_text)

            yield f"data: {json.dumps({'phase': 'ceo_result', **ceo_result}, ensure_ascii=False)}\n\n"

            assignments = ceo_result.get("assignments", [])
            if not assignments:
                yield f"data: {json.dumps({'phase': 'error', 'message': 'CEO가 담당자를 배정하지 않았습니다.'}, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"
                return

        except Exception as e:
            yield f"data: {json.dumps({'phase': 'error', 'message': f'CEO 판단 오류: {str(e)}'}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
            return

        # 직원 순차 실행
        for assignment in assignments:
            async for chunk in _execute_staff(assignment, command_text):
                yield chunk

        yield "data: [DONE]\n\n"

    async def generate_direct():
        """직접 지시 모드 — CEO 판단 건너뛰고 바로 실행"""
        emp = EMPLOYEE_MAP.get(assignee)
        if not emp:
            yield f"data: {json.dumps({'phase': 'error', 'message': f'직원을 찾을 수 없습니다: {assignee}'}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
            return

        yield f"data: {json.dumps({'phase': 'direct_start', 'name': assignee, 'role': emp['role'], 'emoji': emp['emoji']}, ensure_ascii=False)}\n\n"

        assignment = {"name": assignee, "role": emp["role"], "emoji": emp["emoji"], "task": command_text}
        async for chunk in _execute_staff(assignment, command_text):
            yield chunk

        yield "data: [DONE]\n\n"

    if mode == "direct":
        return StreamingResponse(generate_direct(), media_type="text/event-stream")
    return StreamingResponse(generate_ceo(), media_type="text/event-stream")


async def _execute_staff(assignment: dict, fallback_task: str):
    """공통: 직원 1명 실행 → SSE 청크 yield"""
    staff_name = assignment.get("name", "")
    staff_task = assignment.get("task", fallback_task)

    emp = EMPLOYEE_MAP.get(staff_name, assignment)
    role = emp.get("role", assignment.get("role", ""))
    emoji = emp.get("emoji", assignment.get("emoji", "💬"))

    yield f"data: {json.dumps({'phase': 'staff_start', 'name': staff_name, 'role': role, 'emoji': emoji, 'task': staff_task}, ensure_ascii=False)}\n\n"

    try:
        system_prompt = make_staff_system(staff_name, role)
        with call_anthropic_stream(
            model=MODEL,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": staff_task}],
        ) as stream:
            for text in stream.text_stream:
                yield f"data: {json.dumps({'text': text, 'staff': staff_name}, ensure_ascii=False)}\n\n"

        yield f"data: {json.dumps({'phase': 'staff_done', 'name': staff_name}, ensure_ascii=False)}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'phase': 'staff_error', 'name': staff_name, 'message': str(e)}, ensure_ascii=False)}\n\n"


# ===== DEBATE ENDPOINTS =====

@app.get("/api/debates")
async def list_debates(limit: int = 10):
    """토론 목록 조회"""
    try:
        debates = get_debates(limit)
        return JSONResponse(debates)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/debates/{debate_id}")
async def debate_detail(debate_id: str):
    """토론 상세 조회 (전체 대화 포함)"""
    try:
        result = get_debate_detail(debate_id)
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/debates/start")
async def start_debate(request: Request):
    """새 토론 시작 (SSE 스트리밍)"""
    body = await request.json()
    topic = body.get("topic", "")
    category = body.get("category", "ceo_order")

    if not topic:
        return JSONResponse({"error": "주제를 입력해주세요."}, status_code=400)

    def generate():
        yield from run_debate_streaming(topic, category, "ceo_order")

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/api/debates/meta/participants")
async def debate_participants():
    """토론 참여 직원 메타 정보"""
    return JSONResponse({
        "employees": {
            name: {"emoji": e["emoji"], "dept": e["dept"], "role": e["role"]}
            for name, e in HQ_EMPLOYEES.items()
        },
        "topic_categories": {
            cat: members for cat, members in TOPIC_PARTICIPANTS.items()
        },
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
