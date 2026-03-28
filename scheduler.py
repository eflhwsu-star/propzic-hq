"""
PROPZIC HQ Scheduler — Asia/Seoul 기준 자동화
매일 07:00 모니터링 → 08:00 인프라 → 09:00 브리핑 생성+발송
매주 월요일 09:00 주간 브리핑
scheduler.py 실행 시 api_server.py도 함께 구동 (포트 8001)
"""

import threading
import logging
from datetime import datetime

from brand_config import BRAND_NAME

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import uvicorn

from ai_team.monitor_agent import run as monitor_run
from ai_team.infra_agent import run as infra_run
from ai_team.ceo_agent import generate_daily_briefing, generate_weekly_briefing
from ai_team.secretary import send_briefing
from hq_debate_engine import run_debate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("scheduler")

# 결과 저장 (브리핑 생성 시 참조)
latest_monitor = ""
latest_infra = ""


def job_monitor():
    """07:00 — 모니터링 (이경규+전현무)"""
    global latest_monitor
    logger.info("🕐 07:00 모니터링 시작")
    try:
        latest_monitor = monitor_run()
        logger.info("모니터링 완료")
    except Exception as e:
        latest_monitor = f"모니터링 실패: {e}"
        logger.error(f"모니터링 실패: {e}")


def job_infra():
    """08:00 — 인프라 점검 (하정우+최민식)"""
    global latest_infra
    logger.info("🕐 08:00 인프라 점검 시작")
    try:
        latest_infra = infra_run()
        logger.info("인프라 점검 완료")
    except Exception as e:
        latest_infra = f"인프라 점검 실패: {e}"
        logger.error(f"인프라 점검 실패: {e}")


def job_daily_briefing():
    """09:00 — 일일 브리핑 생성 + 카카오톡 발송"""
    logger.info("🕐 09:00 일일 브리핑 생성 시작")
    try:
        briefing = generate_daily_briefing(
            monitor_result=latest_monitor,
            infra_result=latest_infra,
        )
        logger.info("일일 브리핑 생성 완료")

        success = send_briefing(briefing)
        if success:
            logger.info("카카오톡 브리핑 발송 성공")
        else:
            logger.warning("카카오톡 브리핑 발송 실패")
    except Exception as e:
        logger.error(f"일일 브리핑 실패: {e}")


def job_weekly_briefing():
    """월요일 09:00 — 주간 브리핑 생성 + 카카오톡 발송"""
    logger.info("🕐 월요일 09:00 주간 브리핑 생성 시작")
    try:
        briefing = generate_weekly_briefing()
        logger.info("주간 브리핑 생성 완료")

        success = send_briefing(briefing)
        if success:
            logger.info("카카오톡 주간 브리핑 발송 성공")
        else:
            logger.warning("카카오톡 주간 브리핑 발송 실패")
    except Exception as e:
        logger.error(f"주간 브리핑 실패: {e}")


def job_daily_debate():
    """09:30 — 일일 자율 토론 (AI 직원)"""
    import random
    topics = [
        ("오늘 부동산 시장 동향과 집알기 서비스 전략", "market"),
        ("집값해독 DAU 증가를 위한 개선 방향", "strategy"),
        ("중개오토 B2B 영업 확대 전략", "strategy"),
        ("최근 부동산 정책 변화가 서비스에 미치는 영향", "market"),
        ("기술 인프라 개선 및 사용자 경험 향상 방안", "tech"),
        ("경쟁사 대비 차별화 전략", "strategy"),
        ("서비스 법적 리스크 점검", "legal"),
    ]
    topic, category = random.choice(topics)
    logger.info(f"🕐 09:30 일일 토론 시작: [{category}] {topic}")
    try:
        debate_id, conclusion = run_debate(topic, category, "scheduled")
        logger.info(f"일일 토론 완료: {debate_id}")
    except Exception as e:
        logger.error(f"일일 토론 실패: {e}")


def start_scheduler():
    """스케줄러 시작"""
    scheduler = BackgroundScheduler(timezone="Asia/Seoul")

    # 매일 07:00 — 모니터링
    scheduler.add_job(
        job_monitor,
        CronTrigger(hour=7, minute=0, timezone="Asia/Seoul"),
        id="daily_monitor",
        name="일일 모니터링 (이경규+전현무)",
    )

    # 매일 08:00 — 인프라 점검
    scheduler.add_job(
        job_infra,
        CronTrigger(hour=8, minute=0, timezone="Asia/Seoul"),
        id="daily_infra",
        name="일일 인프라 점검 (하정우+최민식)",
    )

    # 매일 09:00 — 일일 브리핑 생성 + 발송
    scheduler.add_job(
        job_daily_briefing,
        CronTrigger(hour=9, minute=0, timezone="Asia/Seoul"),
        id="daily_briefing",
        name="일일 브리핑 (이준서→강수미)",
    )

    # 매주 월요일 09:00 — 주간 브리핑
    scheduler.add_job(
        job_weekly_briefing,
        CronTrigger(day_of_week="mon", hour=9, minute=0, timezone="Asia/Seoul"),
        id="weekly_briefing",
        name="주간 브리핑 (이준서→강수미)",
    )

    # 매일 09:30 — 일일 자율 토론
    scheduler.add_job(
        job_daily_debate,
        CronTrigger(hour=9, minute=30, timezone="Asia/Seoul"),
        id="daily_debate",
        name="일일 자율 토론 (AI 직원)",
    )

    scheduler.start()
    logger.info("=" * 50)
    logger.info(f"{BRAND_NAME} HQ Scheduler 시작 (Asia/Seoul)")
    logger.info("  07:00 — 모니터링 (이경규+전현무)")
    logger.info("  08:00 — 인프라 점검 (하정우+최민식)")
    logger.info("  09:00 — 일일 브리핑 (이준서→강수미 카카오)")
    logger.info("  09:30 — 일일 자율 토론 (AI 직원)")
    logger.info("  월 09:00 — 주간 브리핑")
    logger.info("=" * 50)
    return scheduler


def start_api_server():
    """API 서버를 별도 스레드에서 실행"""
    from api_server import app
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")


if __name__ == "__main__":
    logger.info(f"{BRAND_NAME} HQ 시작...")

    # API 서버 스레드 실행
    api_thread = threading.Thread(target=start_api_server, daemon=True)
    api_thread.start()
    logger.info("API 서버 시작 (포트 8001)")

    # 스케줄러 실행
    scheduler = start_scheduler()

    try:
        # 메인 스레드 유지
        import time
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info(f"{BRAND_NAME} HQ 종료")
