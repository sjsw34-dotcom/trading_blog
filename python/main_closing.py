"""오후 4시 10분 마감 리포트 파이프라인
GitHub Actions에서 매일 KST 15:35 (UTC 06:35)에 실행

흐름: 한국장 데이터 수집 → 등락 분석 → 뉴스 크롤링(+DB 저장) → 테마 분류(+사전 활용)
     → 공시 분석 → 블로그 생성 → DB 저장 → 텔레그램 발송
"""

import asyncio
import logging
import sys
from datetime import datetime

from collectors.common import collect_with_fallback
from collectors.dart_collector import DARTCollector
from collectors.kis_collector import KISCollector
from collectors.krx_collector import KRXCollector
from collectors.news_crawler import NewsCrawler
from collectors.trading_db_collector import TradingDBCollector
from analyzers.rank_analyzer import RankAnalyzer
from analyzers.theme_analyzer import ThemeAnalyzer
from analyzers.disclosure_analyzer import DisclosureAnalyzer
from generators.blog_generator import BlogGenerator
from generators.telegram_generator import TelegramGenerator
from publishers.db_publisher import DBPublisher
from publishers.telegram_publisher import TelegramPublisher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

PIPELINE_NAME = "마감 리포트"


def main():
    today = datetime.now().strftime("%Y-%m-%d")
    date_short = f"{datetime.now().month}/{datetime.now().strftime('%d')}"
    logger.info(f"=== 마감 리포트 파이프라인 시작: {today} ===")

    db = DBPublisher()
    kis = KISCollector()
    krx = KRXCollector()

    # 0. 오래된 뉴스 정리
    db.cleanup_old_news(days=7)

    # 1. 한국장 데이터 수집
    logger.info("[1/9] 한국장 데이터 수집")
    kr_market = collect_with_fallback(
        kis.get_kr_market_data,
        krx.get_kr_market_data,
        "한국시세",
    )

    # 2. DART 공시
    logger.info("[2/9] DART 공시 수집")
    dart = DARTCollector()
    disclosures_raw = dart.get_disclosures()

    # 3. 등락률 분석
    logger.info("[3/9] 등락률 분석")
    rank_analyzer = RankAnalyzer()
    stocks = kr_market.get("stocks", []) if kr_market else []
    rank_data = rank_analyzer.analyze(stocks)

    # 4. 뉴스 크롤링 + DB 아카이브 저장
    logger.info("[4/9] 뉴스 크롤링 (Google RSS + 언론사 RSS)")
    crawler = NewsCrawler()
    stock_codes = rank_analyzer.get_stock_codes(rank_data)
    stock_names = {}
    for s in rank_data.get("gainers", []) + rank_data.get("losers", []):
        stock_names[s["code"]] = s.get("name", "")
    stock_news = crawler.get_multi_stock_news(stock_codes, stock_names=stock_names)
    main_news = crawler.get_main_news()
    world_news = crawler.get_world_news()
    economy_news = crawler.get_economy_news()

    # 뉴스 DB 아카이브 저장 (7일간 누적)
    db.save_news(main_news, "main", today)
    db.save_news(world_news, "world", today)
    db.save_news(economy_news, "economy", today)
    for code, news_list in stock_news.items():
        for n in news_list:
            n["stock_code"] = code
        db.save_news(news_list, "stock", today)

    # 뉴스 매칭 후 재분석
    rank_data = rank_analyzer.analyze(stocks, stock_news=stock_news)

    # 5. 테마 분류 (기존 테마 사전 + 최근 뉴스 활용)
    logger.info("[5/9] 테마 분류 (테마 사전 활용)")
    existing_themes = db.get_active_themes(limit=30)
    recent_news = db.get_recent_news(days=7)
    theme_analyzer = ThemeAnalyzer()
    themes = theme_analyzer.analyze(
        rank_data.get("gainers", []),
        existing_themes=existing_themes,
        recent_news_context=recent_news,
    )

    # 5-1. 분류된 테마 → DB 사전에 자동 업데이트
    for t in themes.get("themes", []):
        lead_stocks = [s.get("name", "") for s in t.get("stocks", [])[:3]]
        db.upsert_theme({
            "name": t["name"],
            "description": t.get("description", ""),
            "stocks": t.get("stocks"),
            "keywords": [t["name"]],
            "importance": 3,
            "status": "active",
            "history_entry": {
                "date": today,
                "direction": "up",
                "lead_stocks": lead_stocks,
                "trigger": t.get("description", ""),
            },
        })

    # 5-2. Trading DB 테마 데이터 수집 + 테마 종목군 보강
    logger.info("[5-2/9] Trading DB 테마 수집 + 종목군 보강")
    trading_db = TradingDBCollector()
    gainer_codes = [s["code"] for s in rank_data.get("gainers", []) if s.get("code")]
    loser_codes = [s["code"] for s in rank_data.get("losers", []) if s.get("code")]
    trading_theme_data = trading_db.collect_for_blog(
        gainer_codes=gainer_codes,
        loser_codes=loser_codes,
    )

    # 테마별 관련 종목을 Trading DB + 네이버 시세로 보강
    for t in themes.get("themes", []):
        existing_codes = [s["code"] for s in t.get("stocks", []) if s.get("code")]
        if not existing_codes:
            t["companion_stocks"] = []
            continue

        # 대장주/기존 종목과 같은 테마에 속한 동반 상승 종목 조회 (시세 포함)
        companions = trading_db.get_companion_stocks_with_prices(
            existing_codes, theme_hint=t["name"], limit=20
        )
        t["companion_stocks"] = [
            {
                "code": c["code"],
                "name": c["name"],
                "change_rate": c["change_rate"],
                "close": c["close"],
                "db_themes": c.get("themes", []),
                "source": "trading_db",
            }
            for c in companions[:5]
        ]
        logger.info(
            f"테마 '{t['name']}' 보강: 기존 {len(existing_codes)}종목 + 동반상승 {len(t['companion_stocks'])}종목"
        )

    # 6. 공시 분류
    logger.info("[6/9] 공시 분류")
    disc_analyzer = DisclosureAnalyzer()
    disclosures = disc_analyzer.analyze(disclosures_raw)

    # 7. 향후 예정 이벤트 조회
    logger.info("[7/9] 예정 이벤트 조회")
    upcoming = db.get_upcoming_schedules(days=14)

    # 8. 블로그 생성
    logger.info("[8/9] 블로그 생성")
    blog_gen = BlogGenerator()

    blog = blog_gen.generate_closing(
        kr_market=kr_market or {},
        rank_data=rank_data,
        themes=themes,
        disclosures=disclosures,
        main_news=main_news,
        world_news=world_news,
        economy_news=economy_news,
        trading_theme_data=trading_theme_data,
    )

    if not blog.get("content"):
        raise RuntimeError("블로그 콘텐츠 생성 실패 — DB 저장 건너뜀")

    tg_gen = TelegramGenerator()
    tg_summary = tg_gen.generate_closing(
        kr_market=kr_market or {},
        rank_data=rank_data,
        date_str=date_short,
        themes=themes,
    )

    # 9. DB 저장 + 텔레그램 발송
    logger.info("[9/9] DB 저장 + 텔레그램 발송")
    report_data = {
        "date": today,
        "type": "closing",
        "title": blog.get("title", f"{today} 주식 시장 마감 리포트"),
        "content": blog.get("content", ""),
        "summary": tg_summary,
        "meta_description": blog.get("meta_description", ""),
        "market_data": kr_market,
        "top_gainers": rank_data.get("gainers"),
        "top_losers": rank_data.get("losers"),
        "themes": themes,
        "disclosures": disclosures,
        "news_links": main_news + world_news + economy_news,
    }
    db.publish(report_data)

    blog_url = f"https://kjusik.com/report/{today}?type=closing"
    tg_pub = TelegramPublisher()
    sent = asyncio.run(tg_pub.send_message(tg_summary, blog_url=blog_url))
    if sent:
        db.mark_telegram_sent(today, "closing")

    logger.info(f"=== 마감 리포트 파이프라인 완료: {today} ===")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"마감 파이프라인 실패: {e}", exc_info=True)
        try:
            tg_pub = TelegramPublisher()
            asyncio.run(tg_pub.send_error_alert(PIPELINE_NAME, str(e)))
        except Exception:
            logger.error("에러 알림 발송도 실패")
        sys.exit(1)
