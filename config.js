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
};
