"""뉴스 제목+URL 크롤링 모듈 — Google News RSS + 네이버 + 언론사 RSS"""

import json
import logging
import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

import requests
import yaml

logger = logging.getLogger(__name__)

_settings_path = Path(__file__).parent.parent / "config" / "settings.yaml"
with open(_settings_path, "r", encoding="utf-8") as f:
    SETTINGS = yaml.safe_load(f)

CRAWL_CFG = SETTINGS["crawling"]

# 언론사 공식 RSS (합법적 소스)
PRESS_RSS = {
    "아시아경제_증권": "https://www.asiae.co.kr/rss/stock.htm",
    "아시아경제_경제": "https://www.asiae.co.kr/rss/economy.htm",
    "전자신문": "https://rss.etnews.com/Section901.xml",
}

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"


class NewsCrawler:
    """Google News RSS + 네이버 + 언론사 RSS 크롤러"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": CRAWL_CFG["user_agent"],
            "Accept-Language": "ko-KR,ko;q=0.9",
        })
        self.delay = CRAWL_CFG["delay_seconds"]
        self.max_per_stock = CRAWL_CFG["max_news_per_stock"]

    # ── RSS 파싱 공통 ─────────────────────────────

    def _fetch_rss(self, url: str, max_items: int = 20) -> list[dict]:
        """RSS 피드 파싱 → [{title, url, date, press}]"""
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            root = ET.fromstring(resp.content)

            articles = []
            # RSS 2.0 형식
            for item in root.iter("item"):
                title_el = item.find("title")
                link_el = item.find("link")
                pub_el = item.find("pubDate")
                source_el = item.find("source")

                title = title_el.text.strip() if title_el is not None and title_el.text else ""
                link = link_el.text.strip() if link_el is not None and link_el.text else ""
                pub = pub_el.text.strip() if pub_el is not None and pub_el.text else ""
                source = source_el.text.strip() if source_el is not None and source_el.text else ""

                if not title:
                    continue

                articles.append({
                    "title": title,
                    "url": link,
                    "date": pub,
                    "press": source,
                })
                if len(articles) >= max_items:
                    break

            return articles
        except Exception as e:
            logger.warning(f"RSS 파싱 실패 [{url[:80]}]: {e}")
            return []

    def _google_rss(self, query: str, max_items: int = 15) -> list[dict]:
        """Google News RSS 검색"""
        encoded = urllib.parse.quote(query)
        url = GOOGLE_NEWS_RSS.format(query=encoded)
        return self._fetch_rss(url, max_items)

    # ── 네이버 검색 (RSS 보완용) ──────────────────

    def _naver_search(self, query: str, max_results: int = 10) -> list[dict]:
        """네이버 검색 뉴스 — HTML 파싱"""
        from bs4 import BeautifulSoup

        encoded = urllib.parse.quote(query)
        url = f"https://search.naver.com/search.naver?where=news&query={encoded}&sm=tab_opt&sort=1"
        try:
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
        except Exception as e:
            logger.warning(f"네이버 검색 실패: {e}")
            return []

        articles = []
        seen = set()
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            title = a.get_text(strip=True)
            if not title or len(title) < 10:
                continue
            if "naver.com" in href:
                continue
            if not any(kw in href for kw in ["news", "article", "View"]):
                continue
            if href in seen:
                continue
            seen.add(href)
            articles.append({"title": title, "url": href, "date": "", "press": ""})
            if len(articles) >= max_results:
                break
        return articles

    # ── 중복 제거 유틸 ────────────────────────────

    @staticmethod
    def _dedupe(articles: list[dict]) -> list[dict]:
        """제목 기준 중복 제거"""
        seen = set()
        unique = []
        for art in articles:
            key = art["title"][:30]
            if key not in seen:
                seen.add(key)
                unique.append(art)
        return unique

    # ── 카테고리별 수집 ───────────────────────────

    def get_main_news(self) -> list[dict]:
        """한국 주요 증시 뉴스 (Google RSS + 언론사 RSS)"""
        results = []

        # Google News RSS
        for keyword in ["한국 증시 코스피", "코스닥 주식 오늘", "주식시장 장마감"]:
            results.extend(self._google_rss(keyword, 10))
            time.sleep(0.3)

        # 언론사 RSS
        for name, url in PRESS_RSS.items():
            rss = self._fetch_rss(url, 10)
            for art in rss:
                art["press"] = art["press"] or name.split("_")[0]
            results.extend(rss)
            time.sleep(0.2)

        unique = self._dedupe(results)
        logger.info(f"주요 뉴스 {len(unique)}건 수집 (RSS)")
        return unique

    def get_world_news(self) -> list[dict]:
        """미국/해외 뉴스 (Google RSS)"""
        results = []
        for keyword in [
            "뉴욕증시 나스닥 마감",
            "S&P500 미국 경제",
            "환율 달러 원화",
            "국제유가 금 시세",
            "미국 금리 연준 FOMC",
            "트럼프 관세 무역",
        ]:
            results.extend(self._google_rss(keyword, 8))
            time.sleep(0.3)

        unique = self._dedupe(results)
        logger.info(f"해외 뉴스 {len(unique)}건 수집 (RSS)")
        return unique

    def get_economy_news(self) -> list[dict]:
        """국내 경제/정책 뉴스 (Google RSS)"""
        results = []
        for keyword in [
            "한국 경제 정책 정부",
            "기획재정부 산업부 금융위",
            "수출 무역 관세 한국",
            "부동산 주택 공급",
        ]:
            results.extend(self._google_rss(keyword, 8))
            time.sleep(0.3)

        unique = self._dedupe(results)
        logger.info(f"경제/정책 뉴스 {len(unique)}건 수집 (RSS)")
        return unique

    # ── 종목별 뉴스 ───────────────────────────────

    def get_stock_news(self, stock_code: str, stock_name: str = "") -> list[dict]:
        """종목별 뉴스 (Google RSS + 네이버 병합)"""
        query = stock_name if stock_name else stock_code

        # Google News RSS
        google = self._google_rss(f"{query} 주식", max_items=5)
        time.sleep(0.3)

        # 네이버 검색 보완
        naver = self._naver_search(f"{query} 주가", max_results=5)

        merged = self._dedupe(google + naver)[:self.max_per_stock]
        logger.info(f"종목 {query} 뉴스 {len(merged)}건 (구글:{len(google)}, 네이버:{len(naver)})")
        return merged

    def get_multi_stock_news(
        self,
        stock_codes: list[str],
        stock_names: dict[str, str] | None = None,
    ) -> dict[str, list[dict]]:
        """여러 종목 뉴스 일괄 수집"""
        stock_names = stock_names or {}
        result = {}
        for code in stock_codes:
            name = stock_names.get(code, "")
            result[code] = self.get_stock_news(code, stock_name=name)
            time.sleep(self.delay)
        return result

    # ── 통합 수집 ─────────────────────────────────

    def collect_all(self, stock_codes: list[str] | None = None) -> dict:
        """전체 뉴스 수집"""
        logger.info("뉴스 크롤링 시작 (Google RSS + 언론사 RSS)")

        main_news = self.get_main_news()
        time.sleep(self.delay)
        world_news = self.get_world_news()
        time.sleep(self.delay)
        economy_news = self.get_economy_news()
        time.sleep(self.delay)

        stock_news = {}
        if stock_codes:
            stock_news = self.get_multi_stock_news(stock_codes)

        logger.info("뉴스 크롤링 완료")
        return {
            "main_news": main_news,
            "world_news": world_news,
            "economy_news": economy_news,
            "stock_news": stock_news,
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    crawler = NewsCrawler()

    print("=== Google News RSS 테스트 ===")
    world = crawler.get_world_news()
    print(f"해외뉴스: {len(world)}건")
    for n in world[:5]:
        print(f"  [{n['press']}] {n['title'][:50]}")

    print("\n=== 종목 뉴스 테스트 (삼성전자) ===")
    stock = crawler.get_stock_news("005930", "삼성전자")
    for n in stock:
        print(f"  {n['title'][:50]}")
