"""
PROPZIC 인프라 에이전트
- 하정우 (인프라팀장·서버·인프라관리·배포)
- 최민식 (보안감시·보안·기술이슈감시·취약점분석)
"""

import os
import logging
from datetime import datetime
from pathlib import Path

import psutil
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

logger = logging.getLogger("infra")
handler = logging.FileHandler(
    LOGS_DIR / f"infra_{datetime.now().strftime('%Y-%m-%d')}.log",
    encoding="utf-8",
)
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# 서비스 헬스체크 대상
HEALTH_ENDPOINTS = {
    "중개오토 API": "http://localhost:8000/health",
    "집값해독": "https://house-data-kr.pages.dev",
}


# ===== 하정우: 인프라 점검 =====
def check_system_resources() -> str:
    """CPU, 메모리, 디스크 사용률 점검"""
    results = []

    # CPU
    cpu = psutil.cpu_percent(interval=1)
    if cpu > 80:
        results.append(f"🟡 CPU: {cpu}% (주의)")
        logger.warning(f"CPU 사용률 높음: {cpu}%")
    else:
        results.append(f"🟢 CPU: {cpu}%")

    # Memory
    mem = psutil.virtual_memory()
    mem_pct = mem.percent
    if mem_pct > 85:
        results.append(f"🟡 메모리: {mem_pct}% ({mem.used // (1024**3)}GB/{mem.total // (1024**3)}GB)")
        logger.warning(f"메모리 사용률 높음: {mem_pct}%")
    else:
        results.append(f"🟢 메모리: {mem_pct}%")

    # Disk
    disk = psutil.disk_usage("/")
    disk_pct = disk.percent
    if disk_pct > 90:
        results.append(f"🔴 디스크: {disk_pct}% (긴급)")
        logger.error(f"디스크 사용률 위험: {disk_pct}%")
    elif disk_pct > 80:
        results.append(f"🟡 디스크: {disk_pct}%")
    else:
        results.append(f"🟢 디스크: {disk_pct}%")

    return "\n".join(results)


def check_health_endpoints() -> str:
    """서비스 헬스체크"""
    results = []

    for name, url in HEALTH_ENDPOINTS.items():
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                results.append(f"🟢 {name}: 정상 (응답시간 {res.elapsed.total_seconds():.2f}s)")
            else:
                results.append(f"🟡 {name}: 응답 {res.status_code}")
                logger.warning(f"{name} 비정상 응답: {res.status_code}")
        except requests.exceptions.ConnectionError:
            results.append(f"🔴 {name}: 연결 불가")
            logger.error(f"{name} 연결 불가: {url}")
        except requests.exceptions.Timeout:
            results.append(f"🔴 {name}: 타임아웃")
            logger.error(f"{name} 타임아웃: {url}")
        except Exception as e:
            results.append(f"🔴 {name}: 오류 ({e})")
            logger.error(f"{name} 오류: {e}")

    return "\n".join(results)


# ===== 최민식: 보안 감시 =====
def check_security() -> str:
    """보안 관련 점검"""
    results = []

    # 로그 파일에서 에러 패턴 검색
    log_dir = LOGS_DIR
    error_count = 0
    for log_file in log_dir.glob("*.log"):
        try:
            content = log_file.read_text(encoding="utf-8")
            errors = [line for line in content.split("\n") if "[ERROR]" in line]
            error_count += len(errors)
        except Exception:
            pass

    if error_count > 50:
        results.append(f"🔴 최근 에러 로그: {error_count}건 (급증)")
        logger.error(f"에러 로그 급증: {error_count}건")
    elif error_count > 20:
        results.append(f"🟡 최근 에러 로그: {error_count}건")
    else:
        results.append(f"🟢 최근 에러 로그: {error_count}건")

    # 프로세스 이상 확인
    suspicious = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent"]):
        try:
            if proc.info["cpu_percent"] and proc.info["cpu_percent"] > 90:
                suspicious.append(f"{proc.info['name']} (PID:{proc.info['pid']}, CPU:{proc.info['cpu_percent']}%)")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    if suspicious:
        results.append(f"🟡 고CPU 프로세스: {', '.join(suspicious[:3])}")
    else:
        results.append("🟢 비정상 프로세스 없음")

    return "\n".join(results)


# ===== 통합 실행 =====
def run() -> str:
    """인프라 점검 전체 실행"""
    logger.info("=" * 50)
    logger.info("인프라 점검 시작")

    system_report = check_system_resources()
    health_report = check_health_endpoints()
    security_report = check_security()

    full_report = (
        f"🖥️ 하정우 — 시스템 리소스\n{system_report}\n\n"
        f"🖥️ 하정우 — 서비스 헬스체크\n{health_report}\n\n"
        f"🔒 최민식 — 보안 감시\n{security_report}"
    )

    logger.info("인프라 점검 완료")
    return full_report


if __name__ == "__main__":
    print(run())
