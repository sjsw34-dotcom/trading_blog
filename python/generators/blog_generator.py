"""Claude API 블로그 글 생성 모듈 — 아침 브리핑 / 마감 리포트

변경: JSON 감싸기 제거 → HTML 직접 출력 + 제목/메타 별도 경량 호출
등락 해설, 공시 요약을 블로그 생성 프롬프트에 합쳐 호출 횟수 축소
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "config" / ".env")

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-20250514"

DISCLAIMER = (
    '<div class="disclaimer">'
    "<p>⚠️ 본 콘텐츠는 공개된 시장 데이터 및 뉴스를 정리한 것으로, "
    "특정 종목의 매수·매도를 권유하지 않습니다. "
    "투자 판단의 최종 책임은 투자자 본인에게 있습니다. "
    "본 블로그는 시세 조회 서비스가 아닌 뉴스 큐레이션 블로그입니다.</p>"
    "</div>"
)

# ── 마감 리포트 프롬프트 ───────────────────────────

CLOSING_SYSTEM = """\
당신은 한국 주식시장 전문 뉴스 큐레이터입니다.
개인 투자자가 매일 읽고 싶어지는, 정보 밀도가 높은 장 마감 리포트를 HTML로 작성합니다.

## 글 톤
- 전문적이지만 읽기 쉽게. 딱딱한 보고서가 아닌, 증권가 선배가 후배에게 설명하듯.
- 팩트 기반 객관적 서술. '올랐다'는 쓰되 '오를 것이다'는 절대 안 씀.
- 투자 조언/추천 절대 금지.

## 필수 섹션 (이 순서대로, 빠짐없이)

### 1. 📊 시장 요약
- KOSPI, KOSDAQ 종가/등락률/거래량을 눈에 띄는 박스로
- 오늘 시장의 핵심 키워드 한 줄 요약

### 2. 🔥 상승 종목 TOP 15
- 테이블 형태: 순위 | 종목명(코드) | 종가 | 등락률 | 거래량
- 각 종목별 **상승 사유** 1~2줄 (뉴스 링크 포함)
- 같은 테마로 묶을 수 있는 종목은 묶어서 설명

### 3. 📉 하락 종목 TOP 15
- 같은 테이블 형태
- 각 종목별 **하락 사유** 1~2줄 (뉴스 링크 포함)

### 4. 🏷️ 오늘의 테마
- 테마별로 구분 (예: "원전 관련주", "AI 반도체", "건설/부동산")
- 각 테마: 이름 + 한줄 설명 + 해당 종목 리스트 + 대표 뉴스링크
- 테마가 왜 오늘 움직였는지 배경 설명

### 5. 📋 주요 공시 정리
- 카테고리별로 정리 (유상증자, 실적, 합병, 대주주변동 등)
- 각 공시: 기업명 + 제목 + 왜 중요한지 한줄 + DART 링크

### 6. 💰 외국인/기관 수급
- 외국인 순매수 TOP 5 / 순매도 TOP 5
- 기관 순매수 TOP 5 / 순매도 TOP 5
- 수급 흐름에서 읽을 수 있는 포인트 한줄

### 7. 📰 주요 뉴스 브리핑
- 국내 뉴스 핵심 5~10건 (제목 + 한줄 요약 + 링크)
- 해외 뉴스 핵심 5~10건 (제목 + 한줄 요약 + 링크)

### 8. 면책 문구

## HTML 작성 규칙
- 뉴스 링크: <a href="URL">제목(언론사)</a>
- 상승률: <span class="stock-up">+5.2%</span>
- 하락률: <span class="stock-down">-3.1%</span>
- 테이블은 <div class="table-wrapper"><table>...</table></div>로 감싸기
- 깔끔한 시맨틱 HTML. 인라인 스타일 최소화.
- 충분한 분량. 최소 3000자 이상.

## 중요: 출력 형식
- <article> 태그로 감싸진 HTML만 출력하세요.
- JSON으로 감싸지 마세요.
- 제목, 메타 설명 등 다른 텍스트 없이 HTML만.
"""

CLOSING_USER = """\
날짜: {today}

## 시장 데이터
{market_data}

## 상승 종목 TOP 15 (등락률 순위 데이터 + 관련 뉴스)
{rank_data}

## 하락 종목 TOP 15 (등락률 순위 데이터 + 관련 뉴스)
→ 위 rank_data의 losers 참고

## 테마 분류
{themes}

## 공시 원본 데이터 (카테고리별 정리 + 요약 작성 필요)
{disclosures}

## 수급 데이터
{supply}

## 국내 주요 뉴스 (제목+URL)
{main_news}

## 해외 뉴스 (제목+URL)
{world_news}

## 경제/정책 뉴스 (제목+URL)
{economy_news}

---

위 모든 데이터를 활용하여 장 마감 리포트를 작성해주세요.
- 상승/하락 종목의 사유는 관련 뉴스를 참고하여 직접 해설
- 공시 데이터는 개인투자자가 이해하기 쉽게 요약
- 뉴스 링크는 반드시 원본 URL을 그대로 사용
- 데이터가 비어있는 섹션도 "데이터 없음"으로 표시
- 면책 문구: {disclaimer}

<article> 태그로 감싸진 HTML만 출력하세요. 다른 텍스트 없이.
"""

# ── 제목/메타 추출 프롬프트 (경량) ──────────────────

TITLE_META_PROMPT = """\
아래 블로그 글의 제목과 SEO 메타 설명을 추출해주세요.

날짜: {today}
본문 첫 500자:
{content_preview}

JSON으로만 응답 (마크다운 코드블록 없이):
{{"title": "{today} 주식 시장 마감 리포트 — [오늘의 핵심 키워드]", "meta_description": "300자 이내 SEO 설명"}}
"""

MORNING_TITLE_META_PROMPT = """\
아래 블로그 글의 제목과 SEO 메타 설명을 추출해주세요.

날짜: {today}
본문 첫 500자:
{content_preview}

JSON으로만 응답 (마크다운 코드블록 없이):
{{"title": "{today} 미국장 마감 브리핑 — [핵심 키워드]", "meta_description": "300자 이내 SEO 설명"}}
"""

# ── 아침 브리핑 프롬프트 ───────────────────────────

MORNING_SYSTEM = """\
당신은 한국 주식시장 전문 뉴스 큐레이터입니다.
장 시작 전 읽어야 할 아침 브리핑을 HTML로 작성합니다.

## 글 톤
- 전문적이지만 읽기 쉽게. 증권가 선배가 후배에게 브리핑하듯.
- 팩트 기반 객관적 서술. 투자 조언/추천 절대 금지.

## 필수 섹션

### 1. 🇺🇸 전일 미국 시황
- 다우/나스닥/S&P500/필라델피아반도체 종가 및 등락률
- 왜 올랐는지/내렸는지 핵심 요인 2~3가지
- 주요 경제지표 발표 결과 (GDP, 고용, CPI 등)

### 2. 📈 미국 주요 종목 등락
- [상승] 주요 종목 10~15개: 종목명 +등락률% — 사유 한줄
- [하락] 주요 종목 10~15개: 종목명 -등락률% — 사유 한줄
- 같은 테마끼리 묶어서 설명 (AI, 양자컴퓨팅, 태양광 등)

### 3. 💱 환율/유가/금
- USD/KRW, WTI 유가, 금 가격, 국채 금리

### 4. 📰 오늘의 주요 뉴스
- 해외 뉴스 핵심 10건 (제목 + 한줄 요약 + 링크)
- 국내 뉴스 핵심 10건 (제목 + 한줄 요약 + 링크)

### 5. 🗓️ 오늘 한국장 주요 일정
- 신규상장, 공시 기한, 경제지표 발표 등

### 6. 면책 문구

## HTML 규칙
- 뉴스 링크: <a href="URL">제목(언론사)</a>
- 상승: <span class="stock-up">, 하락: <span class="stock-down">
- 충분한 분량. 최소 2000자 이상.

## 중요: 출력 형식
- <article> 태그로 감싸진 HTML만 출력하세요.
- JSON으로 감싸지 마세요.
"""

MORNING_USER = """\
날짜: {today}

## 미국 시장 데이터
{us_market}

## 해외 뉴스 (제목+URL)
{world_news}

## 국내 주요 뉴스 (제목+URL)
{main_news}

## 경제/정책 뉴스 (제목+URL)
{economy_news}

---

위 모든 데이터를 활용하여 아침 브리핑을 작성해주세요.
- 뉴스 링크는 반드시 원본 URL 그대로 사용
- 데이터가 비어있으면 "데이터 없음"으로 표시
- 면책 문구: {disclaimer}

<article> 태그로 감싸진 HTML만 출력하세요. 다른 텍스트 없이.
"""


class BlogGenerator:
    """Claude API로 블로그 글 생성

    호출 구조 (마감 리포트):
    1. 테마 분류 — ThemeAnalyzer에서 처리 (별도)
    2. HTML 본문 직접 생성 (1회, 등락 해설+공시 요약 합침)
    3. 제목+메타 추출 (1회, 경량 ~500토큰)
    """

    def __init__(self):
        self.client = anthropic.Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY", "")
        )

    def _call_claude(self, system: str, user_content: str, max_tokens: int = 4000) -> str:
        """Claude API 호출 → 텍스트 반환"""
        response = self.client.messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_content}],
        )
        return response.content[0].text.strip()

    def _call_claude_json(self, prompt: str, max_tokens: int = 500) -> dict:
        """Claude API 호출 → JSON 파싱 (경량 호출용)"""
        response = self.client.messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            raw = raw.rsplit("```", 1)[0]
        return json.loads(raw)

    def _extract_title_meta(self, content: str, today: str, report_type: str = "closing") -> dict:
        """HTML 본문에서 제목+메타 설명 추출 (경량 호출)"""
        content_preview = content[:500]
        template = TITLE_META_PROMPT if report_type == "closing" else MORNING_TITLE_META_PROMPT
        prompt = template.format(today=today, content_preview=content_preview)
        try:
            result = self._call_claude_json(prompt, max_tokens=500)
            logger.info(f"제목/메타 추출 완료: {result.get('title', '')[:50]}")
            return result
        except Exception as e:
            logger.error(f"제목/메타 추출 실패: {e}")
            fallback_title = (
                f"{today} 주식 시장 마감 리포트"
                if report_type == "closing"
                else f"{today} 미국장 마감 브리핑"
            )
            return {"title": fallback_title, "meta_description": ""}

    # ── 최종 통합 생성 ────────────────────────────────

    def generate_morning(
        self,
        us_market: dict,
        world_news: list[dict],
        main_news: list[dict],
        economy_news: list[dict] | None = None,
    ) -> dict:
        today = datetime.now().strftime("%Y년 %m월 %d일")
        user_content = MORNING_USER.format(
            today=today,
            us_market=json.dumps(us_market, ensure_ascii=False, indent=2, default=str),
            world_news=json.dumps(world_news[:30], ensure_ascii=False, indent=2),
            main_news=json.dumps(main_news[:20], ensure_ascii=False, indent=2),
            economy_news=json.dumps(economy_news[:15] if economy_news else [], ensure_ascii=False, indent=2),
            disclaimer=DISCLAIMER,
        )
        try:
            # 호출 1: HTML 본문 직접 생성
            html_content = self._call_claude(MORNING_SYSTEM, user_content, max_tokens=12000)
            logger.info(f"아침 브리핑 HTML 생성 완료 ({len(html_content)}자)")

            # 호출 2: 제목+메타 추출 (경량)
            title_meta = self._extract_title_meta(html_content, today, "morning")

            return {
                "title": title_meta.get("title", ""),
                "content": html_content,
                "meta_description": title_meta.get("meta_description", ""),
            }
        except Exception as e:
            logger.error(f"아침 브리핑 생성 실패: {e}")
            return {"title": "", "content": "", "meta_description": ""}

    def generate_closing(
        self,
        kr_market: dict,
        rank_data: dict,
        themes: dict,
        disclosures: dict,
        supply: dict,
        main_news: list[dict],
        world_news: list[dict] | None = None,
        economy_news: list[dict] | None = None,
    ) -> dict:
        today = datetime.now().strftime("%Y년 %m월 %d일")
        user_content = CLOSING_USER.format(
            today=today,
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
        try:
            # 호출 1: HTML 본문 직접 생성 (등락 해설+공시 요약 포함)
            html_content = self._call_claude(CLOSING_SYSTEM, user_content, max_tokens=12000)
            logger.info(f"마감 리포트 HTML 생성 완료 ({len(html_content)}자)")

            # 호출 2: 제목+메타 추출 (경량)
            title_meta = self._extract_title_meta(html_content, today, "closing")

            return {
                "title": title_meta.get("title", ""),
                "content": html_content,
                "meta_description": title_meta.get("meta_description", ""),
            }
        except Exception as e:
            logger.error(f"마감 리포트 생성 실패: {e}")
            return {"title": "", "content": "", "meta_description": ""}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    gen = BlogGenerator()
    print("BlogGenerator 초기화 완료")
    print(f"모델: {MODEL}")
