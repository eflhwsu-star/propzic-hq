"""
PROPZIC HQ — 브랜드 및 글로벌 설정 상수
브랜드명 변경 시 이 파일만 수정하면 전체 반영됩니다.

최초 생성: 2026-03-27
"""

# ===== 브랜드 =====
BRAND_NAME = "PROPZIC"
BRAND_NAME_KR = "프롭직"
HQ_TITLE = "PROPZIC HQ 지휘본부"
HQ_DOMAIN = "hq.propzic.com"

# ===== 서비스 =====
SERVICE_B2C = "집값해독"
SERVICE_B2B = "중개오토"

# ===== CEO =====
CEO_NAME = "이준서"
CEO_ROLE = "전체총괄·일일주간브리핑"

# ===== Claude 모델 =====
DEFAULT_MODEL = "claude-sonnet-4-20250514"

# ===== 전 직원 부서별 딕셔너리 =====
EMPLOYEES_BY_DEPT = {
    "C-Suite": [
        {"name": "이준서", "role": "전체총괄·일일주간브리핑", "emoji": "👑"},
        {"name": "강수미", "role": "일정관리·카카오브리핑발송·CEO보좌", "emoji": "💜"},
    ],
    "법무·컴플라이언스": [
        {"name": "한동훈", "role": "법무팀장·계약검토·법률자문", "emoji": "⚖️"},
        {"name": "김능환", "role": "판사출신변호사·부동산분쟁·소송·계약법률", "emoji": "🔨"},
        {"name": "채동욱", "role": "검사출신변호사·사기방지·형사리스크·수사대응", "emoji": "🛡️"},
        {"name": "안철수", "role": "IP·특허관리·상표등록", "emoji": "💡"},
        {"name": "장영실", "role": "변리사·서비스특허·상표·IP출원", "emoji": "📋"},
        {"name": "박성수", "role": "퇴직경찰30년·사기피해예방·이상거래탐지·범죄예방", "emoji": "🚔"},
    ],
    "부동산현장전문가": [
        {"name": "함영진", "role": "공인중개사고문·현장중개실무자문·중개오토기능검토", "emoji": "🏠"},
        {"name": "박원갑", "role": "감정평가사·부동산시세·적정가격검토·감정평가", "emoji": "📊"},
        {"name": "김현정", "role": "세무사·양도세·취득세·절세전략·중개오토계산기자문", "emoji": "🧾"},
        {"name": "이헌재", "role": "금융전문가·금리분석·대출규제·DSR·LTV해석", "emoji": "🏦"},
        {"name": "유현준", "role": "건축사·건물가치·리모델링·건축법·재건축검토", "emoji": "🏗️"},
        {"name": "오세훈", "role": "도시계획전문가·재개발·재건축·구역지정·개발호재분석", "emoji": "🌆"},
        {"name": "김경란", "role": "경매전문가·낙찰가분석·명도절차·경매물건분석", "emoji": "🔔"},
        {"name": "이순신", "role": "보험전문가·화재보험·임대인배상·권리보험·중개오토보험안내", "emoji": "🛡️"},
    ],
    "기술팀": [
        {"name": "하정우", "role": "인프라팀장·서버·인프라관리·배포", "emoji": "🖥️"},
        {"name": "최민식", "role": "보안감시·보안·기술이슈감시·취약점분석", "emoji": "🔒"},
        {"name": "손석희", "role": "데이터분석·지표모니터링·통계", "emoji": "📈"},
    ],
    "마케팅팀": [
        {"name": "전지현", "role": "마케팅팀장·광고기획·집행·캠페인관리", "emoji": "📣"},
        {"name": "이윤서", "role": "바이럴마케팅·SNS·인플루언서", "emoji": "🔥"},
        {"name": "김선태", "role": "홍보PR·홍보·PR·언론대응", "emoji": "📰"},
        {"name": "송지효", "role": "콘텐츠제작·블로그·뉴스레터", "emoji": "✍️"},
        {"name": "김범수", "role": "그로스해킹·앱지표·퍼널최적화·리텐션", "emoji": "🚀"},
    ],
    "고객경험팀": [
        {"name": "신동엽", "role": "CS팀장·고객지원·문의처리·VOC관리", "emoji": "🎧"},
        {"name": "장원영", "role": "UX디자인·사용자경험·UI개선", "emoji": "🎨"},
        {"name": "이경규", "role": "서비스반응·리뷰수집·커뮤니티모니터링", "emoji": "👁️"},
    ],
    "전략·인텔팀": [
        {"name": "전현무", "role": "경쟁사인텔팀장·크롤링·시장분석", "emoji": "🕵️"},
        {"name": "이재명", "role": "부동산정책·법령리서치·규제변화", "emoji": "📜"},
        {"name": "홍라희", "role": "투자분석·거시경제·수익률계산·포트폴리오", "emoji": "📈"},
        {"name": "오건영", "role": "부동산투자전문가·아파트·재개발·상가·토지·NPL·경매 전유형 투자분석", "emoji": "💎"},
    ],
    "경영지원팀": [
        {"name": "조세호", "role": "세금·회계·비용관리", "emoji": "🧮"},
        {"name": "염경환", "role": "개인정보보호·CISO·GDPR·보안정책", "emoji": "🔐"},
        {"name": "김미경", "role": "CFO·재무전략·투자유치·IR·수익모델", "emoji": "💰"},
    ],
}

# 전 직원 플랫 리스트 (검색용)
ALL_EMPLOYEES = []
for dept_members in EMPLOYEES_BY_DEPT.values():
    ALL_EMPLOYEES.extend(dept_members)

# 직원명→정보 매핑
EMPLOYEE_MAP = {e["name"]: e for e in ALL_EMPLOYEES}

# ===== CEO 업무명령 시스템 프롬프트 =====
_staff_list_str = ", ".join(
    f'{e["name"]}({e["role"]})' for e in ALL_EMPLOYEES if e["name"] != "이준서"
)

CEO_COMMAND_SYSTEM = f"""당신은 {BRAND_NAME} CEO AI 이준서(전체총괄)입니다.
{SERVICE_B2C}(B2C)과 {SERVICE_B2B}(B2B) 두 서비스를 총괄합니다.

오너의 업무명령을 분석하여 적합한 담당 직원을 배정하세요.

직원 목록:
{_staff_list_str}

반드시 아래 JSON 형식으로만 응답하세요 (마크다운 코드블록 없이 순수 JSON만):
{{
  "analysis": "명령 분석 내용 (핵심 2-3줄 요약)",
  "priority": "🔴긴급 또는 🟡주의 또는 🟢정상",
  "assignments": [
    {{"name": "직원이름", "role": "담당역할", "emoji": "이모지", "task": "이 직원에게 내릴 구체적 업무지시"}}
  ]
}}

규칙:
- 최소 1명, 최대 3명 배정
- 각 직원에게 구체적이고 명확한 업무지시를 작성
- 긴급도를 정확히 판단
- CEO(이준서)와 비서실장(강수미)은 배정 대상에서 제외"""
