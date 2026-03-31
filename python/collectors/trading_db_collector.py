"""자동매매 시스템 Trading DB에서 테마/종목 데이터 수집

- 당일 시그널 발생 테마 Top N
- 상승/하락 종목의 테마 분류 매칭
- 테마별 관련 종목 리스트
"""

import logging
import os
from collections import Counter
from datetime import datetime
from pathlib import Path

import psycopg2
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "config" / ".env")

logger = logging.getLogger(__name__)


class TradingDBCollector:
    """Trading DB에서 테마/종목 데이터를 조회"""

    def __init__(self):
        self.db_url = os.getenv("TRADING_NEON_DATABASE_URL", "")
        if not self.db_url:
            logger.warning("TRADING_NEON_DATABASE_URL 미설정 — 테마 DB 비활성")

    def _get_conn(self):
        return psycopg2.connect(self.db_url)

    def get_today_signal_themes(self, top_n: int = 10) -> list[dict]:
        """당일 시그널이 많이 발생한 테마 Top N 조회

        Returns:
            [{"theme": "반도체 장비", "signal_count": 5,
              "stocks": [{"code": "045100", "name": "한양이엔지"}]}]
        """
        if not self.db_url:
            return []

        today = datetime.now().strftime("%Y-%m-%d")
        try:
            conn = self._get_conn()
            cur = conn.cursor()

            # 당일 시그널에서 테마별 집계 (테마가 None인 ETF 등 제외)
            cur.execute("""
                SELECT theme, COUNT(*) as cnt,
                       array_agg(DISTINCT stock_code) as codes,
                       array_agg(DISTINCT stock_name) as names
                FROM signals
                WHERE signal_time::date = %s AND theme IS NOT NULL
                GROUP BY theme
                ORDER BY cnt DESC
                LIMIT %s
            """, (today, top_n))

            results = []
            for row in cur.fetchall():
                stocks = []
                for code, name in zip(row[2], row[3]):
                    stocks.append({"code": code, "name": name})
                results.append({
                    "theme": row[0],
                    "signal_count": row[1],
                    "stocks": stocks,
                })

            conn.close()
            logger.info(f"당일 시그널 테마 {len(results)}개 조회 완료")
            return results

        except Exception as e:
            logger.error(f"시그널 테마 조회 실패: {e}")
            return []

    def match_stock_themes(self, stock_codes: list[str]) -> dict[str, list[str]]:
        """종목 코드 리스트에 대해 각 종목이 속한 테마 목록 반환

        Returns:
            {"045100": ["반도체 장비", "반도체(장비)"], "033780": ["건강기능식품"]}
        """
        if not self.db_url or not stock_codes:
            return {}

        try:
            conn = self._get_conn()
            cur = conn.cursor()

            placeholders = ",".join(["%s"] * len(stock_codes))
            cur.execute(f"""
                SELECT stock_code, array_agg(DISTINCT theme)
                FROM stock_themes
                WHERE stock_code IN ({placeholders})
                GROUP BY stock_code
            """, stock_codes)

            result = {}
            for row in cur.fetchall():
                result[row[0]] = row[1]

            conn.close()
            logger.info(f"종목-테마 매칭 완료: {len(result)}개 종목")
            return result

        except Exception as e:
            logger.error(f"종목-테마 매칭 실패: {e}")
            return {}

    def get_theme_stocks(self, theme_name: str, limit: int = 15) -> list[dict]:
        """특정 테마에 속한 종목 리스트 반환

        Returns:
            [{"code": "045100", "name": "한양이엔지", "sub_theme": "..."}]
        """
        if not self.db_url:
            return []

        try:
            conn = self._get_conn()
            cur = conn.cursor()

            cur.execute("""
                SELECT stock_code, stock_name, sub_theme
                FROM stock_themes
                WHERE theme = %s
                LIMIT %s
            """, (theme_name, limit))

            results = [
                {"code": row[0], "name": row[1], "sub_theme": row[2]}
                for row in cur.fetchall()
            ]

            conn.close()
            return results

        except Exception as e:
            logger.error(f"테마 종목 조회 실패: {e}")
            return []

    @staticmethod
    def _fetch_stock_prices(codes: list[str]) -> dict[str, dict]:
        """네이버 금융에서 종목 코드 리스트의 당일 시세 조회

        Returns:
            {"005930": {"close": 59000, "change_rate": 1.5}, ...}
        """
        result = {}
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        for code in codes:
            try:
                url = f"https://m.stock.naver.com/api/stock/{code}/basic"
                r = requests.get(url, headers=headers, timeout=5)
                if r.status_code != 200:
                    continue
                data = r.json()
                close_str = data.get("closePrice", "0").replace(",", "")
                rate_str = data.get("fluctuationsRatio", "0").replace(",", "")
                result[code] = {
                    "close": int(close_str) if close_str else 0,
                    "change_rate": float(rate_str) if rate_str else 0.0,
                }
            except Exception:
                continue
        return result

    @staticmethod
    def _filter_themes_by_keywords(db_themes: list[str], theme_keywords: list[str]) -> list[str]:
        """AI 분류 테마명의 키워드로 DB 테마를 필터링

        예: theme_keywords=["벤처", "캐피탈", "VC"]
            DB 테마 ["벤처캐피탈", "코로나19(백신)"] → ["벤처캐피탈"]만 남김
        """
        if not theme_keywords:
            return db_themes

        filtered = []
        for db_theme in db_themes:
            db_lower = db_theme.lower()
            if any(kw.lower() in db_lower for kw in theme_keywords):
                filtered.append(db_theme)
        return filtered

    def get_companion_stocks_with_prices(
        self,
        stock_codes: list[str],
        theme_hint: str = "",
        limit: int = 20,
    ) -> list[dict]:
        """종목 코드들과 같은 테마에 속한 동반 상승 종목을 시세 포함하여 반환

        Args:
            stock_codes: 대장주/기존 종목 코드 리스트
            theme_hint: AI가 분류한 테마명 (DB 테마 필터링에 사용)
            limit: 최대 후보 수

        Returns:
            [{"code": "045100", "name": "한양이엔지", "themes": [...],
              "change_rate": 3.5, "close": 12000}]
        """
        if not self.db_url or not stock_codes:
            return []

        try:
            conn = self._get_conn()
            cur = conn.cursor()

            placeholders = ",".join(["%s"] * len(stock_codes))
            cur.execute(f"""
                SELECT DISTINCT theme
                FROM stock_themes
                WHERE stock_code IN ({placeholders})
            """, stock_codes)
            all_db_themes = [row[0] for row in cur.fetchall()]

            if not all_db_themes:
                conn.close()
                return []

            # AI 테마명에서 키워드 추출 → DB 테마 필터링
            import re
            keywords = [w for w in re.split(r'[/·\-\s()（）]', theme_hint) if len(w) >= 2]
            filtered_themes = self._filter_themes_by_keywords(all_db_themes, keywords)

            # 필터링 결과가 없으면 원본 사용 (but 코로나, 백신 등 범용 테마 제외)
            EXCLUDE_PATTERNS = ["코로나", "백신", "마스크", "진단키트", "방역"]
            if not filtered_themes:
                filtered_themes = [
                    t for t in all_db_themes
                    if not any(ex in t for ex in EXCLUDE_PATTERNS)
                ]
            if not filtered_themes:
                filtered_themes = all_db_themes[:3]  # 최후 fallback

            logger.info(
                f"테마 필터링: DB {len(all_db_themes)}개 → '{theme_hint}' 키워드 → {len(filtered_themes)}개 "
                f"({', '.join(filtered_themes[:5])})"
            )

            theme_placeholders = ",".join(["%s"] * len(filtered_themes))
            code_placeholders = ",".join(["%s"] * len(stock_codes))
            cur.execute(f"""
                SELECT stock_code, stock_name, array_agg(DISTINCT theme) as themes
                FROM stock_themes
                WHERE theme IN ({theme_placeholders})
                  AND stock_code NOT IN ({code_placeholders})
                GROUP BY stock_code, stock_name
                LIMIT %s
            """, filtered_themes + stock_codes + [limit])

            candidates = [
                {"code": row[0], "name": row[1], "themes": row[2]}
                for row in cur.fetchall()
            ]
            conn.close()

            logger.info(f"동반 종목 후보: {len(candidates)}개")

            if not candidates:
                return []

            # 네이버에서 시세 조회
            candidate_codes = [c["code"] for c in candidates]
            prices = self._fetch_stock_prices(candidate_codes)

            results = []
            for c in candidates:
                price = prices.get(c["code"])
                if price and price["change_rate"] > 0:
                    c["change_rate"] = price["change_rate"]
                    c["close"] = price["close"]
                    results.append(c)

            results.sort(key=lambda x: x["change_rate"], reverse=True)
            logger.info(f"동반 상승 종목: {len(results)}개 (후보 {len(candidates)}개 중)")
            return results

        except Exception as e:
            logger.error(f"동반 종목 조회 실패: {e}")
            return []

    def collect_for_blog(self, gainer_codes: list[str] = None, loser_codes: list[str] = None) -> dict:
        """블로그 생성에 필요한 테마 데이터를 한번에 수집

        Returns:
            {
                "signal_themes": [...],    # 당일 시그널 많은 테마 Top 10
                "gainer_themes": {...},    # 상승 종목별 테마 매칭
                "loser_themes": {...},     # 하락 종목별 테마 매칭
            }
        """
        if not self.db_url:
            logger.warning("Trading DB URL 미설정 — 빈 데이터 반환")
            return {"signal_themes": [], "gainer_themes": {}, "loser_themes": {}}

        signal_themes = self.get_today_signal_themes(top_n=10)

        all_codes = list(set((gainer_codes or []) + (loser_codes or [])))
        all_matches = self.match_stock_themes(all_codes) if all_codes else {}

        gainer_themes = {c: all_matches[c] for c in (gainer_codes or []) if c in all_matches}
        loser_themes = {c: all_matches[c] for c in (loser_codes or []) if c in all_matches}

        logger.info(
            f"Trading DB 수집 완료 — 시그널테마:{len(signal_themes)}, "
            f"상승매칭:{len(gainer_themes)}, 하락매칭:{len(loser_themes)}"
        )

        return {
            "signal_themes": signal_themes,
            "gainer_themes": gainer_themes,
            "loser_themes": loser_themes,
        }
