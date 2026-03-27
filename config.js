/**
 * PropAI HQ — 브랜드 및 글로벌 설정 상수
 * 브랜드명 변경 시 이 파일만 수정하면 전체 반영됩니다.
 *
 * 최초 생성: 2026-03-27
 */

const CONFIG = {
  // ===== 브랜드 =====
  BRAND_NAME: "PropAI",
  BRAND_NAME_KR: "프롭AI",
  HQ_TITLE: "PropAI HQ — 지휘본부",
  HQ_DOMAIN: "hq.propai.ai",

  // ===== 서비스 =====
  SERVICE_B2C: "집값해독",
  SERVICE_B2B: "중개오토",

  // ===== API =====
  API_BASE: (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? 'http://localhost:8001'
    : 'https://api-hq.propai.ai',

  // ===== UI =====
  CEO_NAME: "이준서",
  CEO_EMOJI: "👑",

  // ===== 업무명령 프리셋 =====
  COMMAND_PRESETS: [
    { label: "🔴 리스크분석", text: "현재 서비스의 주요 리스크 요인을 분석하고 대응방안을 보고해주세요." },
    { label: "📣 마케팅", text: "이번 주 마케팅 현황과 다음 주 캠페인 계획을 보고해주세요." },
    { label: "⚖️ 법무", text: "현재 진행 중인 법무 이슈와 계약 검토 사항을 보고해주세요." },
    { label: "📊 보고", text: "전체 서비스 현황을 부서별로 간단히 보고해주세요." },
    { label: "🕵️ 경쟁사", text: "최근 경쟁사 동향을 분석하고 대응전략을 제안해주세요." },
  ],
};
