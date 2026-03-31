"""Neon PostgreSQL DB 퍼블리셔 — 리포트 INSERT/UPSERT"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "config" / ".env")

logger = logging.getLogger(__name__)

CREATE_TABLES_SQL = """\
-- 기존 리포트 테이블
CREATE TABLE IF NOT EXISTS stock_reports (
    id SERIAL PRIMARY KEY,
    report_date DATE NOT NULL,
    report_type VARCHAR(20) NOT NULL,
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    summary TEXT,
    meta_description VARCHAR(300),
    market_data JSONB,
    top_gainers JSONB,
    top_losers JSONB,
    themes JSONB,
    disclosures JSONB,
    supply_data JSONB,
    news_links JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    published_at TIMESTAMP,
    telegram_sent BOOLEAN DEFAULT FALSE,
    UNIQUE(report_date, report_type)
);

CREATE INDEX IF NOT EXISTS idx_stock_reports_date ON stock_reports(report_date DESC);
CREATE INDEX IF NOT EXISTS idx_stock_reports_type ON stock_reports(report_type);

-- 뉴스 아카이브 (7일간 보관, 최근 뉴스 맥락 파악용)
CREATE TABLE IF NOT EXISTS news_archive (
    id SERIAL PRIMARY KEY,
    collected_date DATE NOT NULL,
    category VARCHAR(30) NOT NULL,          -- 'main', 'world', 'economy', 'stock'
    stock_code VARCHAR(20),                  -- 종목뉴스일 때 종목코드
    title TEXT NOT NULL,
    url TEXT,
    press VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_news_archive_date ON news_archive(collected_date DESC);
CREATE INDEX IF NOT EXISTS idx_news_archive_category ON news_archive(category);

-- 테마 사전 (무기한 누적, Claude 테마 분류에 활용)
CREATE TABLE IF NOT EXISTS stock_themes (
    id SERIAL PRIMARY KEY,
    theme_name VARCHAR(200) NOT NULL UNIQUE, -- 테마명 (예: "원전 관련주")
    description TEXT,                         -- 테마 설명
    stocks JSONB,                             -- 관련 종목 리스트 [{"code","name"}, ...]
    keywords JSONB,                           -- 테마 인식 키워드 ["원전","SMR","핵발전"]
    importance INTEGER DEFAULT 3,             -- 중요도 1~5 (★ 갯수)
    status VARCHAR(20) DEFAULT 'active',      -- 'active', 'dormant', 'ended'
    first_seen DATE,                          -- 최초 발견일
    last_active DATE,                         -- 마지막 활성화일
    hit_count INTEGER DEFAULT 1,              -- 활성화 횟수
    history JSONB,                            -- 활성화 이력 [{"date","direction","lead_stocks","trigger"}]
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_stock_themes_name ON stock_themes(theme_name);
CREATE INDEX IF NOT EXISTS idx_stock_themes_status ON stock_themes(status);
CREATE INDEX IF NOT EXISTS idx_stock_themes_last_active ON stock_themes(last_active DESC);

-- 테마 스케줄 (예정된 이벤트/일정)
CREATE TABLE IF NOT EXISTS theme_schedule (
    id SERIAL PRIMARY KEY,
    event_date DATE,                          -- 이벤트 날짜 (NULL이면 미정)
    event_text TEXT NOT NULL,                 -- 이벤트 내용
    related_themes JSONB,                     -- 관련 테마명 리스트
    related_stocks JSONB,                     -- 관련 종목 리스트
    importance INTEGER DEFAULT 3,             -- 중요도 1~5
    status VARCHAR(20) DEFAULT 'upcoming',    -- 'upcoming', 'passed', 'cancelled'
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_theme_schedule_date ON theme_schedule(event_date);
CREATE INDEX IF NOT EXISTS idx_theme_schedule_status ON theme_schedule(status);
"""

UPSERT_SQL = """\
INSERT INTO stock_reports
    (report_date, report_type, title, content, summary,
     meta_description, market_data, top_gainers, top_losers,
     themes, disclosures, supply_data, news_links, published_at)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (report_date, report_type)
DO UPDATE SET
    title = EXCLUDED.title,
    content = EXCLUDED.content,
    summary = EXCLUDED.summary,
    meta_description = EXCLUDED.meta_description,
    market_data = EXCLUDED.market_data,
    top_gainers = EXCLUDED.top_gainers,
    top_losers = EXCLUDED.top_losers,
    themes = EXCLUDED.themes,
    disclosures = EXCLUDED.disclosures,
    supply_data = EXCLUDED.supply_data,
    news_links = EXCLUDED.news_links,
    published_at = EXCLUDED.published_at
WHERE EXCLUDED.content IS NOT NULL AND EXCLUDED.content != ''
"""


def _json_dumps(obj) -> str | None:
    if obj is None:
        return None
    return json.dumps(obj, ensure_ascii=False, default=str)


from contextlib import contextmanager


class DBPublisher:
    """Neon PostgreSQL DB 퍼블리셔"""

    def __init__(self):
        self.dsn = os.getenv("NEON_DATABASE_URL", "")

    def _connect(self):
        return psycopg2.connect(self.dsn)

    @contextmanager
    def _conn_cursor(self):
        """커넥션 + 커서를 안전하게 관리하는 context manager"""
        conn = self._connect()
        try:
            cur = conn.cursor()
            yield conn, cur
            cur.close()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def setup_tables(self):
        """테이블 생성 (최초 1회)"""
        with self._conn_cursor() as (conn, cur):
            cur.execute(CREATE_TABLES_SQL)
            conn.commit()
            logger.info("DB 테이블 설정 완료 (stock_reports, news_archive, stock_themes, theme_schedule)")

    def publish(self, report_data: dict):
        """
        리포트를 DB에 INSERT (중복 시 UPDATE)

        Args:
            report_data: {
                "date": "2026-03-18",
                "type": "morning" | "closing",
                "title": str,
                "content": str (HTML),
                "summary": str (텔레그램 요약),
                "meta_description": str,
                "market_data": dict | None,
                "top_gainers": list | None,
                "top_losers": list | None,
                "themes": dict | None,
                "disclosures": dict | None,
                "supply_data": dict | None,
                "news_links": list | None,
            }
        """
        with self._conn_cursor() as (conn, cur):
            cur.execute(UPSERT_SQL, (
                report_data["date"],
                report_data["type"],
                report_data["title"],
                report_data["content"],
                report_data.get("summary", ""),
                report_data.get("meta_description", ""),
                _json_dumps(report_data.get("market_data")),
                _json_dumps(report_data.get("top_gainers")),
                _json_dumps(report_data.get("top_losers")),
                _json_dumps(report_data.get("themes")),
                _json_dumps(report_data.get("disclosures")),
                _json_dumps(report_data.get("supply_data")),
                _json_dumps(report_data.get("news_links")),
                datetime.now(),
            ))
            conn.commit()
            logger.info(
                f"DB 저장 완료: {report_data['date']} {report_data['type']}"
            )

    def mark_telegram_sent(self, report_date: str, report_type: str):
        """텔레그램 발송 완료 표시"""
        with self._conn_cursor() as (conn, cur):
            cur.execute(
                "UPDATE stock_reports SET telegram_sent = TRUE "
                "WHERE report_date = %s AND report_type = %s",
                (report_date, report_type),
            )
            conn.commit()


    # ── 뉴스 아카이브 ────────────────────────────────

    def save_news(self, news_list: list[dict], category: str, date: str | None = None):
        """뉴스 아카이브에 저장"""
        if not news_list:
            return
        date = date or datetime.now().strftime("%Y-%m-%d")
        with self._conn_cursor() as (conn, cur):
            for n in news_list:
                cur.execute(
                    "INSERT INTO news_archive (collected_date, category, stock_code, title, url, press) "
                    "VALUES (%s, %s, %s, %s, %s, %s) "
                    "ON CONFLICT DO NOTHING",
                    (date, category, n.get("stock_code"), n.get("title", ""),
                     n.get("url", ""), n.get("press", "")),
                )
            conn.commit()
            logger.info(f"뉴스 아카이브 저장: {category} {len(news_list)}건")

    def get_recent_news(self, days: int = 7, category: str | None = None) -> list[dict]:
        """최근 N일 뉴스 조회"""
        with self._conn_cursor() as (conn, cur):
            if category:
                cur.execute(
                    "SELECT collected_date, category, title, url, press "
                    "FROM news_archive WHERE collected_date >= CURRENT_DATE - %s "
                    "AND category = %s ORDER BY collected_date DESC",
                    (days, category),
                )
            else:
                cur.execute(
                    "SELECT collected_date, category, title, url, press "
                    "FROM news_archive WHERE collected_date >= CURRENT_DATE - %s "
                    "ORDER BY collected_date DESC",
                    (days,),
                )
            rows = cur.fetchall()
            return [
                {"date": str(r[0]), "category": r[1], "title": r[2], "url": r[3], "press": r[4]}
                for r in rows
            ]

    def cleanup_old_news(self, days: int = 7):
        """오래된 뉴스 삭제"""
        with self._conn_cursor() as (conn, cur):
            cur.execute(
                "DELETE FROM news_archive WHERE collected_date < CURRENT_DATE - %s",
                (days,),
            )
            deleted = cur.rowcount
            conn.commit()
            if deleted:
                logger.info(f"뉴스 아카이브 정리: {deleted}건 삭제")

    # ── 테마 사전 ──────────────────────────────────

    def upsert_theme(self, theme: dict):
        """
        테마 INSERT 또는 UPDATE

        Args:
            theme: {
                "name": "원전 관련주",
                "description": "체코 원전 수출 이후 지속...",
                "stocks": [{"code": "034020", "name": "두산에너빌리티"}, ...],
                "keywords": ["원전", "SMR", "핵발전"],
                "importance": 4,
                "status": "active",
                "history_entry": {"date": "2026-03-18", "direction": "up",
                                  "lead_stocks": ["두산에너빌리티"], "trigger": "..."}
            }
        """
        with self._conn_cursor() as (conn, cur):
            today = datetime.now().strftime("%Y-%m-%d")

            cur.execute(
                "SELECT id, hit_count, history FROM stock_themes WHERE theme_name = %s",
                (theme["name"],),
            )
            existing = cur.fetchone()

            if existing:
                theme_id, hit_count, old_history = existing
                history = old_history if isinstance(old_history, list) else []
                if theme.get("history_entry"):
                    history.append(theme["history_entry"])

                cur.execute(
                    "UPDATE stock_themes SET "
                    "description = COALESCE(%s, description), "
                    "stocks = COALESCE(%s, stocks), "
                    "keywords = COALESCE(%s, keywords), "
                    "importance = COALESCE(%s, importance), "
                    "status = %s, "
                    "last_active = %s, "
                    "hit_count = %s, "
                    "history = %s, "
                    "updated_at = NOW() "
                    "WHERE id = %s",
                    (
                        theme.get("description"),
                        _json_dumps(theme.get("stocks")),
                        _json_dumps(theme.get("keywords")),
                        theme.get("importance"),
                        theme.get("status", "active"),
                        today,
                        hit_count + 1,
                        _json_dumps(history),
                        theme_id,
                    ),
                )
                logger.info(f"테마 업데이트: {theme['name']} (hit: {hit_count + 1})")
            else:
                history = [theme["history_entry"]] if theme.get("history_entry") else []
                cur.execute(
                    "INSERT INTO stock_themes "
                    "(theme_name, description, stocks, keywords, importance, "
                    " status, first_seen, last_active, hit_count, history) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1, %s)",
                    (
                        theme["name"],
                        theme.get("description", ""),
                        _json_dumps(theme.get("stocks")),
                        _json_dumps(theme.get("keywords")),
                        theme.get("importance", 3),
                        theme.get("status", "active"),
                        today,
                        today,
                        _json_dumps(history),
                    ),
                )
                logger.info(f"테마 신규 등록: {theme['name']}")

            conn.commit()

    def get_active_themes(self, limit: int = 50) -> list[dict]:
        """활성 테마 사전 조회 (Claude에 전달용)"""
        with self._conn_cursor() as (conn, cur):
            cur.execute(
                "SELECT theme_name, description, stocks, keywords, importance, "
                "       status, first_seen, last_active, hit_count "
                "FROM stock_themes "
                "WHERE status IN ('active', 'dormant') "
                "ORDER BY last_active DESC NULLS LAST "
                "LIMIT %s",
                (limit,),
            )
            rows = cur.fetchall()
            return [
                {
                    "name": r[0], "description": r[1],
                    "stocks": r[2] if isinstance(r[2], list) else [],
                    "keywords": r[3] if isinstance(r[3], list) else [],
                    "importance": r[4], "status": r[5],
                    "first_seen": str(r[6]) if r[6] else "",
                    "last_active": str(r[7]) if r[7] else "",
                    "hit_count": r[8],
                }
                for r in rows
            ]

    def get_all_themes_summary(self) -> list[dict]:
        """전체 테마 요약 (블로그 '테마 사전' 섹션용)"""
        with self._conn_cursor() as (conn, cur):
            cur.execute(
                "SELECT theme_name, description, importance, status, "
                "       last_active, hit_count "
                "FROM stock_themes ORDER BY importance DESC, last_active DESC"
            )
            rows = cur.fetchall()
            return [
                {"name": r[0], "description": r[1], "importance": r[2],
                 "status": r[3], "last_active": str(r[4]) if r[4] else "", "hit_count": r[5]}
                for r in rows
            ]

    # ── 테마 스케줄 ────────────────────────────────

    def save_schedule(self, event: dict):
        """테마 스케줄 저장"""
        with self._conn_cursor() as (conn, cur):
            cur.execute(
                "INSERT INTO theme_schedule "
                "(event_date, event_text, related_themes, related_stocks, importance) "
                "VALUES (%s, %s, %s, %s, %s)",
                (
                    event.get("date"),
                    event["text"],
                    _json_dumps(event.get("themes")),
                    _json_dumps(event.get("stocks")),
                    event.get("importance", 3),
                ),
            )
            conn.commit()

    def get_upcoming_schedules(self, days: int = 14) -> list[dict]:
        """향후 N일 이내 예정 이벤트 조회"""
        with self._conn_cursor() as (conn, cur):
            cur.execute(
                "SELECT event_date, event_text, related_themes, related_stocks, importance "
                "FROM theme_schedule "
                "WHERE status = 'upcoming' "
                "AND (event_date IS NULL OR event_date <= CURRENT_DATE + %s) "
                "ORDER BY event_date ASC NULLS LAST",
                (days,),
            )
            rows = cur.fetchall()
            return [
                {"date": str(r[0]) if r[0] else "미정", "text": r[1],
                 "themes": r[2] or [], "stocks": r[3] or [], "importance": r[4]}
                for r in rows
            ]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    pub = DBPublisher()
    pub.setup_tables()
    print("DB 테이블 설정 완료")
