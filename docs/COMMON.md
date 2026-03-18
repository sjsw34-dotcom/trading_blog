# COMMON — 공통 참조 정보

> 모든 TASK 파일에서 이 문서를 함께 참조할 것.

---

## 프로젝트 개요

한국/미국 주식시장 일일 리포트 자동 생성 → 자체 블로그 + 텔레그램 배포 시스템.
매일 2회 발행 (아침 7시 미국장 브리핑 + 오후 4시 10분 한국장 마감 리포트).

---

## 기술 스택

- **프론트엔드**: Next.js 14+ (App Router) + TypeScript + Tailwind CSS
- **백엔드**: Python 3.11+
- **AI**: Claude API (claude-sonnet-4-20250514)
- **DB**: Neon PostgreSQL
- **호스팅**: Vercel 무료 (읽기 전용) + GitHub Actions (Python cron + DB 쓰기)
- **알림**: 텔레그램 봇

---

## 핵심 인프라 패턴: GitHub Actions → DB 직접 쓰기

**Vercel 배포 연동 사용하지 않음.** GitHub ↔ Vercel OAuth 불필요.

```
GitHub Actions (cron) → Python 실행 → Neon DB에 직접 INSERT → 끝
Vercel의 Next.js는 DB에서 SELECT해서 보여주기만 함 (SSR/ISR)
```

- 코드 수정 시에만 `vercel --prod` 수동 배포
- Vercel 무료 플랜으로 충분
- 복수 사이트 동시 운영 가능 (DB 테이블만 분리)

---

## 환경 변수 (.env)

```env
# KIS API (한국투자증권 - 한국/미국 주식 + 환율)
KIS_APP_KEY=your_app_key
KIS_APP_SECRET=your_app_secret
KIS_ACCOUNT_NO=12345678-01
KIS_HTS_ID=your_hts_id

# DART (금융감독원 공시)
DART_API_KEY=your_dart_key

# Claude API
ANTHROPIC_API_KEY=your_anthropic_key

# Neon PostgreSQL
NEON_DATABASE_URL=postgresql://user:pass@host/dbname

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_channel_id

# 보안
PUBLISH_SECRET=your_secret_key
```

---

## DB 스키마

```sql
CREATE TABLE stock_reports (
  id SERIAL PRIMARY KEY,
  report_date DATE NOT NULL,
  report_type VARCHAR(20) NOT NULL,      -- 'morning' or 'closing'
  title VARCHAR(500) NOT NULL,
  content TEXT NOT NULL,                  -- HTML 블로그 본문
  summary TEXT,                           -- 텔레그램 요약 (5줄)
  meta_description VARCHAR(300),          -- SEO 메타 디스크립션
  market_data JSONB,                      -- 지수 데이터
  top_gainers JSONB,                      -- 상승 TOP 15
  top_losers JSONB,                       -- 하락 TOP 15
  themes JSONB,                           -- 테마 분류 (뉴스링크 포함)
  disclosures JSONB,                      -- 공시 데이터
  supply_data JSONB,                      -- 수급 데이터
  news_links JSONB,                       -- 뉴스 링크 모음
  created_at TIMESTAMP DEFAULT NOW(),
  published_at TIMESTAMP,
  telegram_sent BOOLEAN DEFAULT FALSE,
  UNIQUE(report_date, report_type)
);

CREATE INDEX idx_stock_reports_date ON stock_reports(report_date DESC);
CREATE INDEX idx_stock_reports_type ON stock_reports(report_type);
```

---

## 디렉토리 구조

```
kr-stock-report/
├── python/
│   ├── collectors/
│   │   ├── kis_collector.py
│   │   ├── dart_collector.py
│   │   ├── krx_collector.py
│   │   └── news_crawler.py
│   ├── analyzers/
│   │   ├── rank_analyzer.py
│   │   ├── theme_analyzer.py
│   │   ├── disclosure_analyzer.py
│   │   └── supply_analyzer.py
│   ├── generators/
│   │   ├── blog_generator.py
│   │   └── telegram_generator.py
│   ├── publishers/
│   │   ├── db_publisher.py
│   │   └── telegram_publisher.py
│   ├── config/
│   │   ├── .env
│   │   └── settings.yaml
│   ├── main_morning.py
│   ├── main_closing.py
│   └── requirements.txt
├── src/                          # Next.js (TASK-3에서 구현)
│   ├── app/
│   ├── components/
│   └── lib/
├── .github/
│   └── workflows/
│       └── daily-report.yml      # (TASK-3에서 구현)
├── vercel.json
├── package.json
└── docs/
    ├── COMMON.md
    ├── TASK-1.md ~ TASK-5.md
```

---

## 법적 안전장치 (모든 코드에 적용)

### 데이터 사용 규칙
- yfinance, FinanceDataReader: **사용 금지** (상업적 사용 불가)
- KIS API: 시세 데이터 사용하되, 장 마감 후 확정된 종가/등락률만 사용
- 실시간 시세 절대 사용 금지
- 차트 이미지 사용 금지 — 숫자 텍스트만

### 뉴스 사용 규칙
- 뉴스 본문 복제 절대 불가 (저작권)
- 뉴스 제목 + URL 링크만 사용 (아웃링크 방식)
- 해외 통신사(Reuters 등) 원문 사용 불가 → 한국 언론사 번역기사 링크로 대체

### 투자자문업법
- 특정 종목 매수/매도 권유 절대 불가
- '올랐다'는 쓰되 '오를 것이다'는 절대 안 씀
- 모든 글 하단에 면책 문구 포함

### 면책 문구 (모든 블로그 글 하단에 포함)
```
⚠️ 본 콘텐츠는 공개된 시장 데이터 및 뉴스를 정리한 것으로, 특정 종목의 매수·매도를 권유하지 않습니다.
투자 판단의 최종 책임은 투자자 본인에게 있습니다.
본 블로그는 시세 조회 서비스가 아닌 뉴스 큐레이션 블로그입니다.
```

---

## 에러 처리 패턴 (모든 수집 모듈 공통)

```python
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def collect_with_fallback(primary_fn, backup_fn=None, name=""):
    """주 소스 실패 → 백업 소스 전환 → 둘 다 실패 → None 반환 + 로그"""
    try:
        data = primary_fn()
        if data:
            logger.info(f"[{name}] 주 소스 수집 성공")
            return data
    except Exception as e:
        logger.warning(f"[{name}] 주 소스 실패: {e}")

    if backup_fn:
        try:
            data = backup_fn()
            if data:
                logger.info(f"[{name}] 백업 소스 수집 성공")
                return data
        except Exception as e:
            logger.error(f"[{name}] 백업 소스도 실패: {e}")

    logger.error(f"[{name}] 모든 소스 실패 — 해당 섹션 스킵")
    return None
```
