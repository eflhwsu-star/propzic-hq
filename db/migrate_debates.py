"""
PROPZIC HQ — 토론 시스템 SQLite 마이그레이션
hq_debates + hq_debate_messages 테이블 생성

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
    """)

    conn.commit()
    conn.close()
    print(f"✅ 마이그레이션 완료: {DB_PATH}")
    return str(DB_PATH)


if __name__ == "__main__":
    migrate()
