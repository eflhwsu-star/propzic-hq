"""
PROPZIC HQ — SQLite 마이그레이션
hq_debates + hq_debate_messages + kb_price_data 테이블 생성

사용법:
  python db/migrate_debates.py        # 직접 실행
  또는 api_server.py 시작 시 자동 실행
"""

import sqlite3
import os
from pathlib import Path

DB_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DB_DIR / "hq.db"


def get_db_path() -> str:
    return str(DB_PATH)


def migrate():
    """토론 테이블 생성 (이미 있으면 무시)"""
    DB_DIR.mkdir(exist_ok=True)

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")

    conn.executescript("""
        -- 토론 세션 테이블
        CREATE TABLE IF NOT EXISTS hq_debates (
            id TEXT PRIMARY KEY,
            topic TEXT NOT NULL,
            topic_category TEXT NOT NULL,
            status TEXT DEFAULT 'in_progress',
            participants TEXT NOT NULL,
            conclusion TEXT,
            action_items TEXT,
            triggered_by TEXT DEFAULT 'scheduled',
            created_at TEXT DEFAULT (datetime('now')),
            concluded_at TEXT
        );

        -- 토론 발언 테이블
        CREATE TABLE IF NOT EXISTS hq_debate_messages (
            id TEXT PRIMARY KEY,
            debate_id TEXT NOT NULL REFERENCES hq_debates(id) ON DELETE CASCADE,
            speaker_key TEXT NOT NULL,
            speaker_name TEXT NOT NULL,
            speaker_emoji TEXT NOT NULL,
            speaker_dept TEXT NOT NULL,
            content TEXT NOT NULL,
            round_number INTEGER NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );

        -- 인덱스
        CREATE INDEX IF NOT EXISTS idx_debates_created
            ON hq_debates(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_debate_messages_debate
            ON hq_debate_messages(debate_id, created_at);

        -- KB시세 데이터 테이블
        CREATE TABLE IF NOT EXISTS kb_price_data (
            id TEXT PRIMARY KEY,
            publish_date TEXT NOT NULL,
            data_type TEXT NOT NULL,
            nationwide_index REAL,
            seoul_index REAL,
            metropolitan_index REAL,
            nationwide_mom REAL,
            seoul_mom REAL,
            metropolitan_mom REAL,
            nationwide_yoy REAL,
            seoul_yoy REAL,
            metropolitan_yoy REAL,
            raw_summary TEXT,
            analysis TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_kb_price_date
            ON kb_price_data(publish_date DESC);

        -- 직원 업무 실행 로그
        CREATE TABLE IF NOT EXISTS worker_logs (
            id TEXT PRIMARY KEY,
            worker_name TEXT NOT NULL,
            status TEXT DEFAULT 'success',
            result_summary TEXT,
            kakao_sent INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_worker_logs_created
            ON worker_logs(created_at DESC);
    """)

    conn.commit()
    conn.close()
    print(f"✅ 마이그레이션 완료: {DB_PATH}")
    return str(DB_PATH)


if __name__ == "__main__":
    migrate()
