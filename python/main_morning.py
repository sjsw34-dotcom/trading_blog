"""아침 7시 브리핑 파이프라인
GitHub Actions에서 매일 아침 KST 06:00 (UTC 21:00 전날)에 실행

흐름: 미국장 데이터 수집 → 뉴스 크롤링 → Claude 블로그 생성 → DB 저장 → 텔레그램 발송
"""

import asyncio
import logging
import sys
from datetime import datetime

from collectors.kis_collector import KISCollector
from collectors.news_crawler import NewsCrawler
from generators.blog_generator import BlogGenerator
from generators.telegram_generator import TelegramGenerator
from publishers.db_publisher import DBPublisher
from publishers.telegram_publisher import TelegramPublisher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

PIPELINE_NAME = "아침 브리핑"


def main():
    today = datetime.now().strftime("%Y-%m-%d")
    date_short = f"{datetime.now().month}/{datetime.now().strftime('%d')}"
    logger.info(f"=== 아침 브리핑 파이프라인 시작: {today} ===")

    # 1. 미국장 데이터 수집
    logger.info("[1/6] 미국장 데이터 수집")
    kis = KISCollector()
    us_market = kis.get_us_market_data()

    # 2. 뉴스 크롤링 + DB 아카이브 저장
    logger.info("[2/6] 뉴스 크롤링 (Google RSS)")
    crawler = NewsCrawler()
    world_news = crawler.get_world_news()
    main_news = crawler.get_main_news()
    economy_news = crawler.get_economy_news()

    # 뉴스 DB 아카이브 저장
    db = DBPublisher()
    db.cleanup_old_news(days=7)
    db.save_news(world_news, "world", today)
    db.save_news(main_news, "main", today)
    db.save_news(economy_news, "economy", today)

    # 3. Claude API로 아침 브리핑 생성
    logger.info("[3/6] 아침 브리핑 블로그 생성")
    blog_gen = BlogGenerator()
    blog = blog_gen.generate_morning(
        us_market=us_market,
        world_news=world_news,
        main_news=main_news,
        economy_news=economy_news,
    )

    if not blog.get("content"):
        raise RuntimeError("블로그 콘텐츠 생성 실패 — DB 저장 건너뜀")

    # 4. 텔레그램 요약 생성
    logger.info("[4/6] 텔레그램 요약 생성")
    tg_gen = TelegramGenerator()
    tg_summary = tg_gen.generate_morning(
        us_market=us_market,
        world_news=world_news,
        date_str=date_short,
    )

    # 5. DB에 INSERT
    logger.info("[5/6] DB 저장")
    report_data = {
        "date": today,
        "type": "morning",
        "title": blog.get("title", f"{today} 미국장 마감 브리핑"),
        "content": blog.get("content", ""),
        "summary": tg_summary,
        "meta_description": blog.get("meta_description", ""),
        "market_data": us_market,
        "top_gainers": None,
        "top_losers": None,
        "themes": None,
        "disclosures": None,
        "supply_data": None,
        "news_links": world_news + main_news + economy_news,
    }
    db.publish(report_data)

    # 6. 텔레그램 발송 (async)
    logger.info("[6/6] 텔레그램 발송")
    blog_url = f"https://kjusik.com/report/{today}?type=morning"
    tg_pub = TelegramPublisher()
    sent = asyncio.run(tg_pub.send_message(tg_summary, blog_url=blog_url))
    if sent:
        db.mark_telegram_sent(today, "morning")

    logger.info(f"=== 아침 브리핑 파이프라인 완료: {today} ===")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"아침 파이프라인 실패: {e}", exc_info=True)
        # 에러 시 텔레그램 알림
        try:
            tg_pub = TelegramPublisher()
            asyncio.run(
                tg_pub.send_error_alert(PIPELINE_NAME, str(e))
            )
        except Exception:
            logger.error("에러 알림 발송도 실패")
        sys.exit(1)
