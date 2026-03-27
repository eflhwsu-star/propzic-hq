"""
PropAI 모니터링 에이전트
- 이경규 (서비스반응·리뷰수집·커뮤니티모니터링)
- 전현무 (경쟁사인텔팀장·크롤링·시장분석)
"""

import os
import sys
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
import anthropic
from dotenv import load_dotenv

# brand_config import (상위 디렉토리)
sys.path.insert(0, str(Path(__file__).parent.parent))
from brand_config import BRAND_NAME, SERVICE_B2C, SERVICE_B2B, DEFAULT_MODEL

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = DEFAULT_MODEL

BASE_DIR = Path(__file__).parent.parent
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

logger = logging.getLogger("monitor")
handler = logging.FileHandler(
    LOGS_DIR / f"monitor_{datetime.now().strftime('%Y-%m-%d')}.log",
    encoding="utf-8",
)
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# 경쟁사 모니터링 대상
COMPETITORS = {
    "호갱노노": "https://hogangnono.com",
    "직방": "https://www.zigbang.com",
    "아실": "https://asil.kr",
    "다방": "https://www.dabangapp.com",
}

HASH_FILE = LOGS_DIR / "competitor_hashes.json"


def load_hashes() -> dict:
    if HASH_FILE.exists():
        return json.loads(HASH_FILE.read_text(encoding="utf-8"))
    return {}


def save_hashes(hashes: dict):
    HASH_FILE.write_text(json.dumps(hashes, ensure_ascii=False, indent=2), encoding="utf-8")


# ===== 이경규: 서비스 반응 모니터링 =====
def monitor_service_mentions() -> str:
    """네이버 검색으로 '집값해독', '중개오토' 언급 수집"""
    results = []
    keywords = [SERVICE_B2C, SERVICE_B2B]

    for keyword in keywords:
        try:
            url = f"https://search.naver.com/search.naver?query={keyword}&where=news"
            res = requests.get(url, headers=HEADERS, timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")

            news_items = soup.select(".news_tit")[:5]
            mentions = []
            for item in news_items:
                title = item.get_text(strip=True)
                link = item.get("href", "")
                mentions.append(f"  - {title}")
                # 부정 키워드 체크
                negative_words = ["사기", "피해", "문제", "오류", "버그", "불만", "환불"]
                if any(w in title for w in negative_words):
                    logger.warning(f"🔴 부정 언급 감지: {title}")
                    mentions[-1] = f"  - 🔴 [부정] {title}"

            if mentions:
                results.append(f"[{keyword}] 최근 뉴스 {len(mentions)}건:\n" + "\n".join(mentions))
            else:
                results.append(f"[{keyword}] 최근 뉴스 언급 없음")

        except Exception as e:
            logger.error(f"'{keyword}' 검색 실패: {e}")
            results.append(f"[{keyword}] 검색 실패: {e}")

    report = "👁️ 이경규 — 서비스 반응 모니터링\n" + "\n".join(results)
    logger.info(report)
    return report


# ===== 전현무: 경쟁사 인텔 =====
def monitor_competitors() -> str:
    """경쟁사 페이지 해시 비교 → 변경 감지 → Claude로 분석"""
    old_hashes = load_hashes()
    new_hashes = {}
    changes = []

    for name, url in COMPETITORS.items():
        try:
            res = requests.get(url, headers=HEADERS, timeout=15)
            page_hash = hashlib.md5(res.text.encode()).hexdigest()
            new_hashes[name] = page_hash

            if name in old_hashes and old_hashes[name] != page_hash:
                logger.info(f"🕵️ {name} 변경 감지!")
                # Claude로 변경 분석
                snippet = res.text[:3000]
                analysis = analyze_change(name, snippet)
                changes.append(f"🕵️ {name} 변경 감지:\n{analysis}")
            else:
                logger.info(f"{name}: 변경 없음")

        except Exception as e:
            logger.error(f"{name} 크롤링 실패: {e}")
            new_hashes[name] = old_hashes.get(name, "error")

    save_hashes(new_hashes)

    if changes:
        report = "🕵️ 전현무 — 경쟁사 인텔 리포트\n" + "\n".join(changes)
    else:
        report = "🕵️ 전현무 — 경쟁사 인텔: 모든 경쟁사 변경 없음"

    logger.info(report)
    return report


def analyze_change(competitor: str, snippet: str) -> str:
    """Claude API로 경쟁사 변경 분석"""
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=500,
            system=f"당신은 {BRAND_NAME} 경쟁사 분석가입니다. 경쟁사 페이지 변경을 한국어로 간결하게 분석하세요.",
            messages=[{
                "role": "user",
                "content": f"{competitor} 페이지에서 변경이 감지되었습니다. 아래 내용을 분석해주세요:\n\n{snippet}"
            }],
        )
        return response.content[0].text
    except Exception as e:
        return f"분석 실패: {e}"


# ===== 통합 실행 =====
def run() -> str:
    """모니터링 전체 실행"""
    logger.info("=" * 50)
    logger.info("모니터링 시작")

    mention_report = monitor_service_mentions()
    competitor_report = monitor_competitors()

    full_report = f"{mention_report}\n\n{competitor_report}"
    logger.info("모니터링 완료")
    return full_report


if __name__ == "__main__":
    print(run())
