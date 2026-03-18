# TASK-3: Next.js 사이트 + DB + GitHub Actions 자동화

> 먼저 `docs/COMMON.md`를 읽을 것. TASK-1, TASK-2가 완성된 상태에서 진행.

---

## 목표

1. Neon PostgreSQL DB 설정 + 퍼블리셔 모듈
2. Next.js 프론트엔드 (DB에서 읽어서 보여주기만)
3. GitHub Actions cron 워크플로우
4. main_morning.py / main_closing.py 메인 파이프라인

---

## 1. publishers/db_publisher.py — DB에 직접 쓰기

### 기능
- Neon DB에 리포트 데이터 INSERT
- psycopg2 사용
- 중복 방지 (report_date + report_type UNIQUE 제약)

```python
import psycopg2
import json
import os
from datetime import datetime

def publish_to_db(report_data: dict):
    """블로그 리포트를 Neon DB에 INSERT"""
    conn = psycopg2.connect(os.environ["NEON_DATABASE_URL"])
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO stock_reports
        (report_date, report_type, title, content, summary,
         meta_description, market_data, top_gainers, top_losers,
         themes, disclosures, supply_data, news_links, published_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (report_date, report_type)
        DO UPDATE SET content = EXCLUDED.content,
                      summary = EXCLUDED.summary,
                      published_at = EXCLUDED.published_at
    """, (
        report_data["date"],
        report_data["type"],  # 'morning' or 'closing'
        report_data["title"],
        report_data["content"],  # HTML 블로그 본문
        report_data["summary"],  # 텔레그램 요약
        report_data["meta_description"],
        json.dumps(report_data.get("market_data"), ensure_ascii=False),
        json.dumps(report_data.get("top_gainers"), ensure_ascii=False),
        json.dumps(report_data.get("top_losers"), ensure_ascii=False),
        json.dumps(report_data.get("themes"), ensure_ascii=False),
        json.dumps(report_data.get("disclosures"), ensure_ascii=False),
        json.dumps(report_data.get("supply_data"), ensure_ascii=False),
        json.dumps(report_data.get("news_links"), ensure_ascii=False),
        datetime.now(),
    ))

    conn.commit()
    cur.close()
    conn.close()
```

---

## 2. main_morning.py — 아침 7시 파이프라인

```python
"""아침 7시 브리핑 파이프라인
GitHub Actions에서 매일 아침 6시(KST)에 실행"""

def main():
    # 1. 미국장 데이터 수집
    us_data = kis_collector.get_us_market_data()

    # 2. 환율 수집
    fx_data = kis_collector.get_exchange_rate()

    # 3. 미국/해외 뉴스 크롤링
    us_news = news_crawler.get_us_news()

    # 4. 오늘 한국장 주요 일정 (DART 공시 예정 등)
    today_schedule = dart_collector.get_today_schedule()

    # 5. Claude API로 아침 브리핑 생성
    blog_content = blog_generator.generate_morning(us_data, fx_data, us_news, today_schedule)
    telegram_summary = telegram_generator.generate_morning_summary(us_data, fx_data, us_news)

    # 6. DB에 INSERT
    db_publisher.publish_to_db({
        "date": today,
        "type": "morning",
        "title": f"오늘 장 시작 전 브리핑 — {today} 미국장 마감 정리",
        "content": blog_content,
        "summary": telegram_summary,
        "meta_description": f"{today} 미국 증시 마감 정리, S&P500 나스닥 환율 유가 등",
        "market_data": us_data,
        "news_links": us_news,
    })

    # 7. 텔레그램 발송
    telegram_publisher.send(telegram_summary)
```

---

## 3. main_closing.py — 오후 4시 파이프라인

```python
"""오후 4시 10분 마감 리포트 파이프라인
GitHub Actions에서 매일 오후 3:35(KST)에 실행"""

def main():
    # 1. 한국장 마감 데이터 수집
    kr_data = collect_with_fallback(
        lambda: kis_collector.get_kr_market_data(),
        lambda: krx_collector.get_kr_market_data(),
        name="한국시세"
    )

    # 2. 수급 데이터
    supply = collect_with_fallback(
        lambda: kis_collector.get_investor_trading(),
        lambda: krx_collector.get_investor_trading(),
        name="수급"
    )

    # 3. DART 공시
    disclosures = dart_collector.get_today_disclosures()

    # 4. 상승 TOP 15 종목별 뉴스 크롤링
    gainers = rank_analyzer.get_top_gainers(kr_data, n=15)
    for stock in gainers:
        stock["news"] = news_crawler.get_stock_news(stock["code"])

    losers = rank_analyzer.get_top_losers(kr_data, n=15)
    for stock in losers:
        stock["news"] = news_crawler.get_stock_news(stock["code"])

    # 5. 테마 분류 (Claude API)
    themes = theme_analyzer.classify_themes(gainers)

    # 6. 공시 분류
    disc_categorized = disclosure_analyzer.categorize(disclosures)

    # 7. 수급 분석
    supply_analysis = supply_analyzer.analyze(supply)

    # 8. Claude API로 최종 블로그 글 생성
    blog_content = blog_generator.generate_closing(
        kr_data, gainers, losers, themes, disc_categorized, supply_analysis
    )
    telegram_summary = telegram_generator.generate_closing_summary(
        kr_data, gainers, themes
    )

    # 9. DB에 INSERT
    db_publisher.publish_to_db({
        "date": today,
        "type": "closing",
        "title": f"오늘 주식 시장 마감 정리 — {today} 상승/하락 종목 테마 분석",
        "content": blog_content,
        "summary": telegram_summary,
        ...
    })

    # 10. 텔레그램 발송
    telegram_publisher.send(telegram_summary)
```

---

## 4. GitHub Actions 워크플로우

### .github/workflows/daily-report.yml

```yaml
name: Daily Stock Report

on:
  schedule:
    # 아침 브리핑: KST 06:00 = UTC 21:00 (전날)
    - cron: '0 21 * * 0-4'
    # 마감 리포트: KST 15:35 = UTC 06:35
    - cron: '35 6 * * 1-5'
  workflow_dispatch:  # 수동 실행 가능

jobs:
  morning-report:
    if: github.event.schedule == '0 21 * * 0-4' || github.event_name == 'workflow_dispatch'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r python/requirements.txt
      - name: Run morning pipeline
        env:
          KIS_APP_KEY: ${{ secrets.KIS_APP_KEY }}
          KIS_APP_SECRET: ${{ secrets.KIS_APP_SECRET }}
          KIS_ACCOUNT_NO: ${{ secrets.KIS_ACCOUNT_NO }}
          KIS_HTS_ID: ${{ secrets.KIS_HTS_ID }}
          DART_API_KEY: ${{ secrets.DART_API_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          NEON_DATABASE_URL: ${{ secrets.NEON_DATABASE_URL }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: |
          cd python
          python main_morning.py

  closing-report:
    if: github.event.schedule == '35 6 * * 1-5'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r python/requirements.txt
      - name: Run closing pipeline
        env:
          KIS_APP_KEY: ${{ secrets.KIS_APP_KEY }}
          KIS_APP_SECRET: ${{ secrets.KIS_APP_SECRET }}
          KIS_ACCOUNT_NO: ${{ secrets.KIS_ACCOUNT_NO }}
          KIS_HTS_ID: ${{ secrets.KIS_HTS_ID }}
          DART_API_KEY: ${{ secrets.DART_API_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          NEON_DATABASE_URL: ${{ secrets.NEON_DATABASE_URL }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: |
          cd python
          python main_closing.py
```

---

## 5. Next.js 프론트엔드

### 핵심 원칙
- **DB에서 읽기만 함** (SSR 또는 ISR)
- Vercel 배포 연동 불필요 — 코드 수정 시 `vercel --prod`로 수동 배포
- Vercel 무료 플랜 (Hobby) 충분

### src/app/page.tsx — 메인 페이지
- 최신 리포트 목록 (날짜 역순)
- 각 리포트 카드: 제목, 날짜, 요약 미리보기

### src/app/report/[date]/page.tsx — 일일 리포트 페이지
- URL: `/report/2026-03-18`
- DB에서 해당 날짜 리포트 조회 → content (HTML) 렌더링
- SSR로 구현 (매 요청마다 DB에서 최신 데이터 읽기)
- SEO: title, meta description 동적 설정

### src/lib/db.ts — DB 연결
```typescript
import { Pool } from '@neondatabase/serverless';

const pool = new Pool({
  connectionString: process.env.NEON_DATABASE_URL,
});

export async function getLatestReports(limit = 20) {
  const { rows } = await pool.query(
    'SELECT report_date, report_type, title, summary, meta_description FROM stock_reports ORDER BY report_date DESC, report_type DESC LIMIT $1',
    [limit]
  );
  return rows;
}

export async function getReport(date: string, type: string = 'closing') {
  const { rows } = await pool.query(
    'SELECT * FROM stock_reports WHERE report_date = $1 AND report_type = $2',
    [date, type]
  );
  return rows[0] || null;
}
```

### SEO 설정
- 제목: `{날짜} 주식 상승 종목 하락 종목 정리 | 사이트명`
- meta description: DB의 meta_description 필드
- Open Graph 태그
- sitemap.xml 자동 생성 (모든 리포트 날짜)

---

## 완료 기준

- [ ] db_publisher: Neon DB에 리포트 INSERT 동작
- [ ] main_morning.py: 아침 파이프라인 전체 동작 (수집→분석→생성→DB저장→텔레그램)
- [ ] main_closing.py: 마감 파이프라인 전체 동작
- [ ] GitHub Actions yml: cron 설정 완료, secrets 설정 안내
- [ ] Next.js: 메인 페이지 + 리포트 상세 페이지 동작
- [ ] Next.js: DB에서 데이터 읽어서 렌더링 동작
- [ ] SEO: title, meta, OG 태그 동적 설정
- [ ] Vercel 배포 테스트 (`vercel --prod`)
