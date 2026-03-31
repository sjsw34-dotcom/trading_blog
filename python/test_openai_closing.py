"""OpenAI API 마감 리포트 테스트
기존 파이프라인(데이터 수집 → 분석)은 그대로 사용하고,
블로그 생성만 OpenAI GPT-4o로 교체하여 테스트
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / "config" / ".env")

from collectors.common import collect_with_fallback
from collectors.dart_collector import DARTCollector
from collectors.kis_collector import KISCollector
from collectors.krx_collector import KRXCollector
from collectors.news_crawler import NewsCrawler
from analyzers.rank_analyzer import RankAnalyzer
from analyzers.theme_analyzer import ThemeAnalyzer
from analyzers.disclosure_analyzer import DisclosureAnalyzer
from analyzers.supply_analyzer import SupplyAnalyzer
from generators.blog_generator import (
    CLOSING_SYSTEM, CLOSING_USER, TITLE_META_PROMPT, DISCLAIMER,
)
from publishers.db_publisher import DBPublisher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

OPENAI_MODEL = "gpt-4o"


def call_openai(system: str, user_content: str, max_tokens: int = 4000) -> str:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
    )
    return response.choices[0].message.content.strip()


def call_openai_json(prompt: str) -> dict:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]
    return json.loads(raw)


def main():
    today = datetime.now().strftime("%Y-%m-%d")
    today_kr = datetime.now().strftime("%Y년 %m월 %d일")
    logger.info(f"=== OpenAI 마감 리포트 테스트: {today} ===")

    db = DBPublisher()
    kis = KISCollector()
    krx = KRXCollector()

    # 1. 데이터 수집
    logger.info("[1/8] 한국장 데이터 수집")
    kr_market = collect_with_fallback(
        kis.get_kr_market_data, krx.get_kr_market_data, "한국시세"
    )

    logger.info("[2/8] 수급 데이터 수집")
    supply_raw = collect_with_fallback(
        kis.get_investor_trading, krx.get_investor_trading, "수급"
    )

    logger.info("[3/8] DART 공시 수집")
    dart = DARTCollector()
    disclosures_raw = dart.get_disclosures()

    logger.info("[4/8] 등락률 분석")
    rank_analyzer = RankAnalyzer()
    stocks = kr_market.get("stocks", []) if kr_market else []
    rank_data = rank_analyzer.analyze(stocks)

    logger.info("[5/8] 뉴스 크롤링")
    crawler = NewsCrawler()
    stock_codes = rank_analyzer.get_stock_codes(rank_data)
    stock_names = {}
    for s in rank_data.get("gainers", []) + rank_data.get("losers", []):
        stock_names[s["code"]] = s.get("name", "")
    stock_news = crawler.get_multi_stock_news(stock_codes, stock_names=stock_names)
    main_news = crawler.get_main_news()
    world_news = crawler.get_world_news()
    economy_news = crawler.get_economy_news()

    rank_data = rank_analyzer.analyze(stocks, stock_news=stock_news)

    logger.info("[6/8] 테마 분류")
    existing_themes = db.get_active_themes(limit=30)
    recent_news = db.get_recent_news(days=7)
    theme_analyzer = ThemeAnalyzer()
    themes = theme_analyzer.analyze(
        rank_data.get("gainers", []),
        existing_themes=existing_themes,
        recent_news_context=recent_news,
    )

    logger.info("[7/8] 공시/수급 분석")
    disc_analyzer = DisclosureAnalyzer()
    disclosures = disc_analyzer.analyze(disclosures_raw)
    supply_analyzer = SupplyAnalyzer()
    supply = supply_analyzer.analyze(supply_raw or {})

    # 2. OpenAI로 블로그 생성
    logger.info("[8/8] OpenAI GPT-4o 블로그 생성 중...")
    user_content = CLOSING_USER.format(
        today=today_kr,
        market_data=json.dumps(kr_market, ensure_ascii=False, indent=2, default=str),
        rank_data=json.dumps(rank_data, ensure_ascii=False, indent=2),
        themes=json.dumps(themes, ensure_ascii=False, indent=2),
        disclosures=json.dumps(disclosures, ensure_ascii=False, indent=2),
        supply=json.dumps(supply, ensure_ascii=False, indent=2),
        main_news=json.dumps(main_news[:20], ensure_ascii=False, indent=2),
        world_news=json.dumps(world_news[:20] if world_news else [], ensure_ascii=False, indent=2),
        economy_news=json.dumps(economy_news[:15] if economy_news else [], ensure_ascii=False, indent=2),
        disclaimer=DISCLAIMER,
    )

    html_content = call_openai(CLOSING_SYSTEM, user_content, max_tokens=12000)
    logger.info(f"HTML 생성 완료 ({len(html_content)}자)")

    # 제목/메타 추출
    content_preview = html_content[:500]
    title_prompt = TITLE_META_PROMPT.format(today=today_kr, content_preview=content_preview)
    try:
        title_meta = call_openai_json(title_prompt)
    except Exception as e:
        logger.warning(f"제목 추출 실패, 기본값 사용: {e}")
        title_meta = {"title": f"{today} 주식 시장 마감 리포트", "meta_description": ""}

    logger.info(f"제목: {title_meta.get('title', '')}")

    # 3. DB 저장
    report_data = {
        "date": today,
        "type": "closing",
        "title": title_meta.get("title", f"{today} 주식 시장 마감 리포트"),
        "content": html_content,
        "summary": "",
        "meta_description": title_meta.get("meta_description", ""),
        "market_data": kr_market,
        "top_gainers": rank_data.get("gainers"),
        "top_losers": rank_data.get("losers"),
        "themes": themes,
        "disclosures": disclosures,
        "supply_data": supply,
        "news_links": main_news + world_news + economy_news,
    }
    db.publish(report_data)

    logger.info(f"=== OpenAI 마감 리포트 완료: {today} ===")
    logger.info(f"확인: https://kjusik.com/report/{today}?type=closing")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"테스트 실패: {e}", exc_info=True)
        sys.exit(1)
