# TASK-1: Python 데이터 수집 모듈 구현

> 먼저 `docs/COMMON.md`를 읽고 전체 프로젝트 컨텍스트를 파악한 후 이 Task를 진행할 것.

---

## 목표

`python/collectors/` 디렉토리에 4개 데이터 수집 모듈을 구현한다.

---

## 1. kis_collector.py — KIS API 시세 수집 (한국+미국+환율)

### 기능
- KIS API 인증 (접근토큰 발급/캐싱/갱신)
- 한국 주식: 전종목 당일 종가/등락률/거래량 조회
- 한국 주식: 거래량 순위 TOP 조회
- 미국 주식: S&P500, 나스닥, 다우 지수 종가/등락률 조회
- 미국 주식: 주요 개별종목 (AAPL, MSFT, GOOGL, AMZN, TSLA, NVDA, META) 종가/등락률
- 환율: USD/KRW 조회
- 투자자별 매매동향 (외국인/기관 순매수)

### KIS API 주요 엔드포인트

```
실전 base_url: https://openapi.koreainvestment.com:9443

인증:
  POST /oauth2/tokenP
  body: { grant_type: "client_credentials", appkey, appsecret }
  → access_token (24시간 유효)

공통 헤더:
  authorization: Bearer {token}
  appkey: {app_key}
  appsecret: {app_secret}
  tr_id: {거래ID}
  content-type: application/json; charset=utf-8

한국 현재가: GET /uapi/domestic-stock/v1/quotations/inquire-price
  tr_id: FHKST01010100
  params: FID_COND_MRKT_DIV_CODE=J, FID_INPUT_ISCD={종목코드}

한국 거래량순위: GET /uapi/domestic-stock/v1/quotations/volume-rank
  tr_id: FHPST01710000
  params: FID_COND_MRKT_DIV_CODE=J, FID_INPUT_ISCD=0000 등

미국 현재가: GET /uapi/overseas-price/v1/quotations/price
  tr_id: HHDFS00000300
  params: AUTH="", EXCD=NAS (또는 NYS), SYMB={티커}

미국 일봉: GET /uapi/overseas-price/v1/quotations/dailyprice
  tr_id: HHDFS76240000
```

### 토큰 캐싱
```python
TOKEN_FILE = "token_cache.json"
# 만료 1시간 전까지 유효하면 재사용
# 만료 임박하면 자동 갱신
```

### 출력 형식
```python
# 한국 시세
{
  "kospi": {"close": 2847.50, "change": 1.2, "volume": 450000000},
  "kosdaq": {"close": 892.30, "change": -0.3, "volume": 280000000},
  "stocks": [
    {"code": "005930", "name": "삼성전자", "close": 67500, "change_rate": 3.2, "volume": 15000000},
    ...
  ]
}

# 미국 시세
{
  "sp500": {"close": 5638.0, "change": -0.7},
  "nasdaq": {"close": 17844.0, "change": -1.2},
  "dow": {"close": 42150.0, "change": -0.3},
  "stocks": [
    {"ticker": "AAPL", "name": "Apple", "close": 252.82, "change_rate": -1.5},
    ...
  ],
  "usd_krw": 1342.5
}

# 수급 데이터
{
  "foreign_buy_top": [{"code": "005930", "name": "삼성전자", "net_buy": 150000000000}, ...],
  "foreign_sell_top": [...],
  "institution_buy_top": [...],
  "institution_sell_top": [...]
}
```

---

## 2. dart_collector.py — DART 공시 수집

### 기능
- 당일 전체 공시 목록 조회
- 공시 카테고리 자동 분류: 유상증자, 무상증자, 권리락, 전환사채(CB), 합병/분할, 대주주변동, 실적발표

### DART API

```
base_url: https://opendart.fss.or.kr/api

공시 목록: GET /list.json
  params: crtfc_key={DART_API_KEY}, bgn_de={시작일}, end_de={종료일}, page_count=100

주요사항보고: kind='B' 파라미터로 필터링
```

### 카테고리 분류 로직
```python
CATEGORY_KEYWORDS = {
    "유상증자": ["유상증자", "신주발행", "제3자배정"],
    "무상증자": ["무상증자", "주식배당"],
    "권리락": ["권리락", "신주인수권"],
    "전환사채": ["전환사채", "CB발행"],
    "합병분할": ["합병", "분할", "액면분할"],
    "대주주변동": ["대량보유", "지분변동", "최대주주"],
    "실적발표": ["영업실적", "매출액", "영업이익"],
}
```

### 출력 형식
```python
{
  "total_count": 45,
  "categories": {
    "유상증자": [{"corp_name": "OOO", "title": "유상증자 결정", "date": "2026-03-18", "url": "https://dart.fss.or.kr/..."}],
    "무상증자": [...],
    ...
  }
}
```

---

## 3. krx_collector.py — pykrx 시장 데이터 (백업)

### 기능
- KIS API 실패 시 백업으로 사용
- 전종목 당일 OHLCV + 등락률
- 투자자별 매매동향

### 주요 함수
```python
from pykrx import stock

# 전종목 당일 OHLCV
df = stock.get_market_ohlcv("20260318")

# 투자자별 매매동향
df = stock.get_market_trading_value_by_investor("20260318", "20260318", "KOSPI")
```

### 출력 형식
- kis_collector.py와 동일한 형식으로 변환하여 반환
- collect_with_fallback() 패턴 사용 (COMMON.md 참조)

---

## 4. news_crawler.py — 뉴스 제목+URL 크롤링

### 기능
- 종목별 뉴스 크롤링 (종목코드 입력 → 당일+최근 3일 뉴스 제목+URL 반환)
- 한국 주요 주식 뉴스 크롤링
- 미국/해외 뉴스 크롤링 (한국 언론사 번역기사)

### 크롤링 대상

```python
# 종목별 뉴스
url = f"https://finance.naver.com/item/news.naver?code={stock_code}"
# → 뉴스 제목, URL, 날짜, 언론사 추출

# 한국 주요 뉴스
url = "https://finance.naver.com/news/mainnews.naver"
# → 주요 헤드라인 제목 + URL

# 미국/해외 뉴스 (한국어)
url = "https://finance.naver.com/news/news_list.naver?mode=LSS3D&section_id=101&section_id2=258"
# → 해외증시 관련 한국어 뉴스 제목 + URL
```

### ⚠️ 크롤링 규칙
- requests + BeautifulSoup 사용
- User-Agent 헤더 필수 설정
- 요청 간 1초 딜레이 (서버 부하 방지)
- 뉴스 본문은 절대 크롤링하지 않음 — 제목 + URL만
- robots.txt 준수

### 출력 형식
```python
# 종목별 뉴스
{
  "005930": [
    {"title": "삼성전자, 1분기 실적 서프라이즈", "url": "https://...", "date": "2026-03-18", "press": "한국경제"},
    {"title": "반도체 업황 회복 신호", "url": "https://...", "date": "2026-03-17", "press": "매일경제"},
  ],
  ...
}

# 주요 뉴스
[
  {"title": "코스피 2,900 돌파", "url": "https://...", "date": "2026-03-18", "press": "연합뉴스"},
  ...
]

# 미국/해외 뉴스
[
  {"title": "트럼프, 중국산 반도체 추가 관세 예고", "url": "https://...", "date": "2026-03-18", "press": "연합뉴스"},
  {"title": "연준 파월 금리 인하 서두르지 않겠다", "url": "https://...", "date": "2026-03-18", "press": "한경"},
  ...
]
```

---

## 5. requirements.txt

```
requests>=2.31.0
beautifulsoup4>=4.12.0
pykrx>=1.0.45
psycopg2-binary>=2.9.9
anthropic>=0.40.0
python-telegram-bot>=20.0
python-dotenv>=1.0.0
pyyaml>=6.0
tenacity>=8.2.0
loguru>=0.7.0
```

---

## 6. config/settings.yaml

```yaml
system:
  timezone: "Asia/Seoul"

kis:
  base_url_real: "https://openapi.koreainvestment.com:9443"
  us_stocks:
    - {ticker: "AAPL", exchange: "NAS", name: "Apple"}
    - {ticker: "MSFT", exchange: "NAS", name: "Microsoft"}
    - {ticker: "GOOGL", exchange: "NAS", name: "Alphabet"}
    - {ticker: "AMZN", exchange: "NAS", name: "Amazon"}
    - {ticker: "TSLA", exchange: "NAS", name: "Tesla"}
    - {ticker: "NVDA", exchange: "NAS", name: "NVIDIA"}
    - {ticker: "META", exchange: "NAS", name: "Meta"}

crawling:
  delay_seconds: 1
  max_news_per_stock: 5
  news_days_range: 3
  user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

report:
  top_n_stocks: 15
  top_n_themes: 5
```

---

## 완료 기준

- [ ] `kis_collector.py`: KIS API 인증 + 한국 시세 + 미국 시세 + 환율 + 수급 조회 동작
- [ ] `dart_collector.py`: 당일 공시 조회 + 카테고리 분류 동작
- [ ] `krx_collector.py`: pykrx 백업 수집 동작
- [ ] `news_crawler.py`: 종목별/주요/해외 뉴스 제목+URL 크롤링 동작
- [ ] 각 모듈이 독립적으로 테스트 가능
- [ ] collect_with_fallback() 에러 처리 패턴 적용
- [ ] requirements.txt, settings.yaml 생성
