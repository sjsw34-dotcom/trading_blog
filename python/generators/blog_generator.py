"""OpenAI API 블로그 글 생성 모듈 — 아침 브리핑 / 마감 리포트

OpenAI GPT-4o 기반. 등락 해설+공시+테마를 통합 생성.
"""

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "config" / ".env")

logger = logging.getLogger(__name__)

MODEL = "gpt-4o"

DISCLAIMER = (
    '<div class="disclaimer">'
    "<p>본 콘텐츠는 공개된 시장 데이터 및 뉴스를 정리한 것으로, "
    "특정 종목의 매수·매도를 권유하지 않습니다. "
    "투자 판단의 최종 책임은 투자자 본인에게 있습니다.</p>"
    "</div>"
)

# ── 마감 리포트 프롬프트 ───────────────────────────

CLOSING_SYSTEM = """\
당신은 증권사 리서치센터 소속 10년차 수석 애널리스트입니다.
매일 장 마감 후 개인 투자자에게 배포하는 데일리 마감 리포트를 HTML로 작성합니다.

## ★★★ 최우선 원칙: 데이터 날조 절대 금지 ★★★
- 제공된 데이터에 없는 종목을 절대 추가하지 마세요.
- 종가, 등락률, 거래량 등 숫자를 절대 지어내지 마세요.
- 데이터에 없는 종목의 등락률을 "N/A"로 표시하는 것도 금지입니다 — 아예 넣지 마세요.
- "수혜 예상", "경쟁력 강화", "성장 기대" 같은 근거 없는 일반론을 사유로 쓰지 마세요.
- 모든 종목명, 숫자, 링크는 반드시 제공된 데이터에서 가져와야 합니다.
- 이 원칙을 어기면 리포트 전체가 실패입니다.

## 글 톤 & 원칙
- 증권사 데일리 브리핑 톤. 전문적이되 읽기 쉽게.
- 팩트 기반 객관적 서술. '올랐다'는 쓰되 '오를 것이다'는 절대 쓰지 않음.
- 투자 조언, 매수·매도 추천 절대 금지.
- 자연스럽고 유려한 한국어. 번역체·기계적 표현 금지.
- 오류 메시지, "데이터 없음", "정보 부족" 등 시스템 문구 절대 노출 금지.
  데이터가 부족하면 해당 내용을 자연스럽게 생략.

## 필수 섹션 (순서 반드시 지킬 것)

### 1. 📊 시장 개관
- KOSPI, KOSDAQ 종가·등락률·거래대금을 한눈에 보이도록 정리
- 오늘 시장을 관통하는 핵심 키워드 1~2개로 한 줄 요약
- 장중 흐름: 시초가 → 장중 고저 → 마감 흐름을 2~3줄로 서술

### 2. 🔥 상승 종목 TOP 15
- 반드시 데이터에 포함된 상승 종목 15개를 1위부터 15위까지 빠짐없이 전부 테이블에 표시할 것.
- 테이블 컬럼: 순위 | 종목명(코드) | 종가 | 등락률 | 거래량
- 테이블 아래에 종목별 상승 사유를 각 2~3줄로 해설
  (관련 뉴스가 있으면 뉴스 링크 포함, 없으면 업종·테마 맥락에서 추론하여 설명)
- 같은 테마로 묶을 수 있는 종목은 묶어서 "왜 이 종목군이 함께 올랐는지" 설명

### 3. 📉 하락 종목 TOP 15
- 반드시 데이터에 포함된 하락 종목을 빠짐없이 전부 테이블에 표시할 것.
- 동일한 테이블 형태
- 종목별 하락 사유를 각 2~3줄로 해설
- 하락 배경: 실적 우려, 수급 이탈, 업종 전반 약세 등 맥락 설명

### 4. 🏷️ 오늘의 테마 — 종목군 심층 분석
★ 이 섹션이 이 리포트의 핵심입니다. 단순 나열이 아닌 깊이 있는 분석을 합니다. ★
- "테마 DB 참고 데이터"에서 오늘 관심이 집중된 테마와 종목별 소속 테마를 참고하여 더 풍부하게 분석하세요.
- 같은 테마에 속한 종목들이 함께 움직인 경우, 해당 테마의 배경과 맥락을 깊이 있게 설명하세요.
- 단, 매매 전략/시그널/기술적 지표 관련 내용은 절대 언급하지 마세요.
각 테마별로 아래 구조를 반드시 따를 것:

**[테마명]** — 한 줄 요약

**왜 움직였나:**
- 촉발 뉴스, 정책, 글로벌 이벤트 등 배경을 5줄 이상으로 자세히 설명
- 이 테마의 최근 1~2주 흐름과 오늘의 차이점
- 향후 이 테마의 관전 포인트 (다음 촉매가 될 이벤트)

**대장주:** 테마 내 등락률 1위 종목 (데이터에서 확인). 왜 이 종목이 대장인지 설명.

**종목군 (동반 상승):**
- 테마 분류 결과의 stocks + companion_stocks 모두 사용하세요.
- companion_stocks는 같은 테마에 속하면서 당일 실제로 상승한 종목입니다 (Trading DB 기반).
- ★ 등락률이 제공된 종목만 넣을 것. 등락률 "N/A" 종목 절대 금지. ★
- 테이블: 종목명 | 등락률 | 비고(오늘 이 종목이 움직인 구체적 이유)
- 비고란 금지 표현: "수혜 예상", "경쟁력 강화", "성장 기대", "회복 기대" 등 근거 없는 일반론
- 대장주와 종목군을 합쳐 최소 3종목 이상 보여야 "테마군"으로서 의미가 있음

**관련 뉴스:** 2~3건 (제공된 뉴스 데이터에서 링크 포함)

### 5. 📋 주요 공시
- 카테고리별 정리 (유상증자, 실적, 합병, 대주주변동 등)
- 각 공시: 기업명 + 제목 + 투자자 관점에서 왜 중요한지 1~2줄 해설

### 6. 📰 뉴스 심층 분석
- 오늘 시장을 움직인 핵심 이슈 3~5건을 **각각 5~8줄로 심층 분석**
  (단순 제목+요약이 아님. 배경→경과→시장 반응→향후 관전 포인트까지 서술)
- 국내 뉴스 주요 10건 (제목 + 한줄 요약 + 링크)
- 해외 뉴스 주요 10건 (제목 + 한줄 요약 + 링크)

### 7. 🗓️ 향후 주요 일정
- 이번 주 남은 일정 + 다음 주 주요 일정
- 테이블: 날짜 | 이벤트 | 관련 섹터/종목 | 시장 영향 예상
- 최소 8~10건. FOMC, 고용지표, GDP, 기업 실적 발표, IPO, 옵션 만기 등

### 8. 면책 문구

### 9. 📌 오늘의 시장 한줄평
- 오늘 시장을 한 문장으로 요약하는 마무리 멘트

## HTML 작성 규칙
- 뉴스 링크: <a href="URL">제목(언론사)</a>
- 상승률: <span class="stock-up">+5.2%</span>
- 하락률: <span class="stock-down">-3.1%</span>
- 테이블: <div class="table-wrapper"><table>...</table></div>
- 깔끔한 시맨틱 HTML. 인라인 스타일 사용 금지.
- 충분한 분량: 최소 8000자 이상.
- 블로그 독자가 "이 글 하나로 오늘 시장을 전부 파악했다"고 느낄 수 있을 만큼 풍부하게.

## 출력 형식
- <article> 태그로 감싸진 순수 HTML만 출력.
- <article> 태그 앞에 어떤 텍스트나 문자도 넣지 마세요.
- 마크다운 코드블록(```)으로 감싸지 마세요.
"""

CLOSING_USER = """\
날짜: {today}

## 시장 데이터 (KOSPI/KOSDAQ 지수, 전체 종목 데이터)
{market_data}

## 상승 종목 TOP 15 (등락률 순, 각 종목별 관련 뉴스 포함)
아래 15개 종목을 테이블에 빠짐없이 전부 표시하세요.
{gainers_data}

## 하락 종목 (등락률 순, 각 종목별 관련 뉴스 포함)
아래 종목을 테이블에 빠짐없이 전부 표시하세요.
{losers_data}

## 테마 분류 결과 (AI 분석)
아래 테마를 기반으로 분석하세요.
각 테마의 stocks는 상승 TOP에서 분류된 종목이고, companion_stocks는 같은 테마에 속하면서 당일 실제 상승한 동반 종목입니다.
★ 대장주(등락률 1위) + 종목군(나머지 stocks + companion_stocks)을 함께 보여줘야 테마군입니다. ★
{themes}

## 테마 DB 참고 데이터 (자동매매 시스템)
아래 데이터를 테마 분석 및 종목 해설의 보조 자료로 활용하세요.
매매 전략이나 시그널/지표 관련 내용은 절대 언급하지 마세요.
테마 분류, 관련 종목 그룹핑, 업종 맥락 파악에만 참고하세요.

### 오늘 관심이 집중된 테마 (시장 데이터 기반)
{signal_themes}

### 상승 종목별 소속 테마
{gainer_theme_matches}

### 하락 종목별 소속 테마
{loser_theme_matches}

## 공시 데이터
{disclosures}

## 국내 주요 뉴스
{main_news}

## 해외 뉴스
{world_news}

## 경제/정책 뉴스
{economy_news}

---

작성 시 반드시 지킬 사항 (하나라도 어기면 실패):
1. 상승 TOP 15 테이블: 위 gainers 데이터의 종목 15개를 1위부터 15위까지 빠짐없이 전부
2. 하락 TOP 테이블: 위 losers 데이터의 종목 전부 빠짐없이
3. 각 종목별 상승/하락 사유를 2~3줄씩 해설 (뉴스 링크 포함)
4. ★ 데이터 날조 금지: 위 데이터에 없는 종목을 테이블에 추가 금지. 등락률 N/A 금지. 근거 없는 사유("수혜 예상" 등) 금지.
5. 테마 종목군: 테마 분류의 stocks + companion_stocks에 있는 종목 활용. 등락률이 제공된 종목만.
6. 뉴스 심층 분석: 3~5건을 각 5줄 이상으로 깊이 있게
7. 향후 일정: 최소 8건 이상 테이블로
8. 전체 분량: 8000자 이상
9. <article> 태그 앞에 어떤 문자도 넣지 말 것
10. 면책 문구: {disclaimer}

<article> 태그로 감싸진 HTML만 출력하세요.
"""

# ── 제목/메타 추출 프롬프트 ──────────────────

TITLE_META_PROMPT = """\
아래 블로그 글의 제목과 SEO 메타 설명을 작성해주세요.

날짜: {today}
본문 첫 500자:
{content_preview}

규칙:
- 제목: "{today} 주식 시장 마감 리포트 — [오늘의 핵심 테마/키워드]" 형태
- 메타 설명: 300자 이내, 검색 유입을 위한 핵심 키워드 포함

JSON으로만 응답 (마크다운 코드블록 없이):
{{"title": "...", "meta_description": "..."}}
"""

MORNING_TITLE_META_PROMPT = """\
아래 블로그 글의 제목과 SEO 메타 설명을 작성해주세요.

날짜: {today}
본문 첫 500자:
{content_preview}

규칙:
- 제목: "{today} 미국장 마감 브리핑 — [핵심 키워드]" 형태
- 메타 설명: 300자 이내

JSON으로만 응답 (마크다운 코드블록 없이):
{{"title": "...", "meta_description": "..."}}
"""

# ── 아침 브리핑 프롬프트 ───────────────────────────

MORNING_SYSTEM = """\
당신은 증권사 리서치센터 소속 10년차 수석 애널리스트입니다.
매일 아침 한국장 시작 전 배포하는 모닝 브리핑을 HTML로 작성합니다.

## 글 톤 & 원칙
- 증권사 모닝 브리핑 톤. 전문적이되 읽기 쉽게.
- 팩트 기반 객관적 서술. 투자 조언·추천 절대 금지.
- 자연스럽고 유려한 한국어.
- 오류 메시지, 시스템 문구 절대 노출 금지.

## 필수 섹션

### 1. 🇺🇸 전일 미국 시황
- 다우/나스닥/S&P500 종가·등락률 테이블
- 왜 올랐는지/내렸는지 핵심 요인 2~3가지를 자세히 서술 (각 3줄 이상)
- 주요 경제지표 발표 결과

### 2. 📈 미국 주요 종목 등락
- 상승 주요 종목 10~15개: 종목명 +등락률% — 사유 (테이블)
- 하락 주요 종목 10~15개: 종목명 -등락률% — 사유 (테이블)
- 같은 테마끼리 묶어서 배경 설명

### 3. 💱 환율·원자재·채권
- USD/KRW, WTI, 금, 미국채 10년물 금리 등

### 4. 📰 뉴스 심층 분석
- 한국장에 영향을 줄 핵심 이슈 3~5건을 **각 5줄 이상 심층 분석**
- 해외 뉴스 10건 (제목 + 한줄 요약 + 링크)
- 국내 뉴스 10건 (제목 + 한줄 요약 + 링크)

### 5. 🗓️ 오늘·이번주 주요 일정
- 국내외 주요 이벤트 테이블: 날짜 | 이벤트 | 관련 섹터 | 예상 영향
- 최소 8건 이상

### 6. 면책 문구

## HTML 규칙
- 상승: <span class="stock-up">, 하락: <span class="stock-down">
- 테이블: <div class="table-wrapper"><table>...</table></div>
- 최소 4000자 이상
- 오류 메시지 노출 금지

## 출력 형식
- <article> 태그로 감싸진 순수 HTML만 출력.
"""

MORNING_USER = """\
날짜: {today}

## 미국 시장 데이터
{us_market}

## 해외 뉴스
{world_news}

## 국내 주요 뉴스
{main_news}

## 경제/정책 뉴스
{economy_news}

---

작성 시 반드시 지킬 사항:
1. 미국 종목 상승/하락 각 10개 이상 테이블로 빠짐없이
2. 핵심 이슈 3~5건은 각 5줄 이상 심층 분석
3. 오늘·이번주 일정 8건 이상 테이블로
4. 전체 분량 4000자 이상
5. 면책 문구: {disclaimer}

<article> 태그로 감싸진 HTML만 출력하세요.
"""


class ContentValidationError(Exception):
    """블로그 콘텐츠 품질 검증 실패"""
    pass


class BlogGenerator:
    """OpenAI API로 블로그 글 생성"""

    # 콘텐츠 최소 길이 (자)
    MIN_CLOSING_LENGTH = 8000
    MIN_MORNING_LENGTH = 3000
    # 최대 재시도 횟수
    MAX_RETRIES = 2

    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY", "")
        )

    @staticmethod
    def _clean_html(raw: str) -> str:
        """GPT 출력에서 순수 HTML만 추출 — 불필요한 문자/코드블록 제거"""
        text = raw.strip()
        # 마크다운 코드블록 제거
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            text = text.rsplit("```", 1)[0]
        # <article> 태그 앞뒤 잡문자 제거
        match = re.search(r"<article[\s>]", text, re.IGNORECASE)
        if match:
            text = text[match.start():]
        else:
            logger.warning("GPT 출력에 <article> 태그 없음 — 원본 그대로 사용")
        # </article> 뒤 잡문자 제거
        match_end = re.search(r"</article>", text, re.IGNORECASE)
        if match_end:
            text = text[:match_end.end()]
        return text.strip()

    @staticmethod
    def _validate_content(html: str, report_type: str) -> list[str]:
        """생성된 HTML 콘텐츠 품질 검증. 문제 목록 반환 (빈 리스트 = 통과)"""
        issues = []

        # 1. 빈 콘텐츠 체크
        if not html or len(html.strip()) < 100:
            issues.append("콘텐츠가 비어있거나 너무 짧음")
            return issues  # 이후 검증 무의미

        # 2. 최소 길이 체크
        min_len = (
            BlogGenerator.MIN_CLOSING_LENGTH
            if report_type == "closing"
            else BlogGenerator.MIN_MORNING_LENGTH
        )
        if len(html) < min_len:
            issues.append(f"콘텐츠 길이 부족: {len(html)}자 (최소 {min_len}자)")

        # 3. 필수 HTML 요소 체크
        if not re.search(r"<table[\s>]", html, re.IGNORECASE):
            issues.append("테이블(<table>) 없음")

        # 4. 시스템 오류 메시지 노출 체크
        error_patterns = [
            r"데이터\s*(가|를|이)?\s*(없|부족|실패)",
            r"오류.*발생",
            r"API.*에러",
            r"정보.*부족",
            r"Error|Exception|Traceback",
        ]
        for pat in error_patterns:
            if re.search(pat, html, re.IGNORECASE):
                issues.append(f"시스템 오류 메시지 노출 의심: '{pat}'")
                break

        # 5. 마감 리포트 전용 체크
        if report_type == "closing":
            if not re.search(r"(상승|🔥|TOP\s*15)", html, re.IGNORECASE):
                issues.append("상승 종목 섹션 누락 의심")
            if not re.search(r"(하락|📉)", html, re.IGNORECASE):
                issues.append("하락 종목 섹션 누락 의심")
            if not re.search(r"(테마|🏷)", html, re.IGNORECASE):
                issues.append("테마 분석 섹션 누락 의심")

        return issues

    def _call_llm(self, system: str, user_content: str, max_tokens: int = 16000) -> str:
        """OpenAI API 호출 → 정제된 HTML 반환"""
        response = self.client.chat.completions.create(
            model=MODEL,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
        )
        raw = response.choices[0].message.content.strip()
        return self._clean_html(raw)

    def _call_llm_json(self, prompt: str, max_tokens: int = 500) -> dict:
        """OpenAI API 호출 → JSON 파싱"""
        response = self.client.chat.completions.create(
            model=MODEL,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            raw = raw.rsplit("```", 1)[0]
        return json.loads(raw)

    def _extract_title_meta(self, content: str, today: str, report_type: str = "closing") -> dict:
        """HTML 본문에서 제목+메타 설명 추출"""
        content_preview = content[:500]
        template = TITLE_META_PROMPT if report_type == "closing" else MORNING_TITLE_META_PROMPT
        prompt = template.format(today=today, content_preview=content_preview)
        try:
            result = self._call_llm_json(prompt, max_tokens=500)
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

    def _format_stocks_for_prompt(self, stocks: list[dict], label: str) -> str:
        """종목 리스트를 프롬프트용 텍스트로 변환 (번호 매겨서 빠짐없이)"""
        if not stocks:
            return f"(오늘 {label} 종목 데이터 없음)"
        lines = []
        for i, s in enumerate(stocks, 1):
            news_str = ""
            if s.get("news"):
                news_items = [f"    [{n['title']}]({n.get('url','')}) ({n.get('press','')})" for n in s["news"][:3]]
                news_str = "\n".join(news_items)
            lines.append(
                f"  {i}위. {s['name']}({s['code']}) | 종가 {s.get('close',0):,}원 | "
                f"등락률 {s.get('change_rate',0):+.2f}% | 거래량 {s.get('volume',0):,}"
            )
            if news_str:
                lines.append(f"    관련뉴스:\n{news_str}")
        return "\n".join(lines)

    # ── 마감 리포트 ────────────────────────────────

    @staticmethod
    def _format_trading_theme_data(trading_data: dict) -> tuple[str, str, str]:
        """Trading DB 테마 데이터를 프롬프트용 텍스트로 변환"""
        # 시그널 테마
        signal_themes = trading_data.get("signal_themes", [])
        if signal_themes:
            lines = []
            for t in signal_themes:
                stock_names = ", ".join(s["name"] for s in t["stocks"][:5])
                lines.append(f"- {t['theme']} ({t['signal_count']}종목 집중): {stock_names}")
            signal_text = "\n".join(lines)
        else:
            signal_text = "(데이터 없음)"

        # 상승 종목 테마 매칭
        gainer_themes = trading_data.get("gainer_themes", {})
        if gainer_themes:
            lines = []
            for code, themes in gainer_themes.items():
                lines.append(f"- {code}: {', '.join(themes[:3])}")
            gainer_text = "\n".join(lines)
        else:
            gainer_text = "(매칭 데이터 없음)"

        # 하락 종목 테마 매칭
        loser_themes = trading_data.get("loser_themes", {})
        if loser_themes:
            lines = []
            for code, themes in loser_themes.items():
                lines.append(f"- {code}: {', '.join(themes[:3])}")
            loser_text = "\n".join(lines)
        else:
            loser_text = "(매칭 데이터 없음)"

        return signal_text, gainer_text, loser_text

    def generate_closing(
        self,
        kr_market: dict,
        rank_data: dict,
        themes: dict,
        disclosures: dict,
        main_news: list[dict],
        world_news: list[dict] | None = None,
        economy_news: list[dict] | None = None,
        trading_theme_data: dict | None = None,
    ) -> dict:
        today = datetime.now().strftime("%Y년 %m월 %d일")

        gainers = rank_data.get("gainers", [])
        losers = rank_data.get("losers", [])
        if len(gainers) < 5:
            logger.warning(f"상승 종목 데이터 부족: {len(gainers)}개 (최소 5개 권장)")
        if len(losers) < 5:
            logger.warning(f"하락 종목 데이터 부족: {len(losers)}개 (최소 5개 권장)")

        gainers_text = self._format_stocks_for_prompt(gainers, "상승")
        losers_text = self._format_stocks_for_prompt(losers, "하락")

        signal_text, gainer_match_text, loser_match_text = self._format_trading_theme_data(
            trading_theme_data or {}
        )

        user_content = CLOSING_USER.format(
            today=today,
            market_data=json.dumps(kr_market, ensure_ascii=False, indent=2, default=str),
            gainers_data=gainers_text,
            losers_data=losers_text,
            themes=json.dumps(themes, ensure_ascii=False, indent=2),
            disclosures=json.dumps(disclosures, ensure_ascii=False, indent=2),
            main_news=json.dumps(main_news[:20], ensure_ascii=False, indent=2),
            world_news=json.dumps(world_news[:20] if world_news else [], ensure_ascii=False, indent=2),
            economy_news=json.dumps(economy_news[:15] if economy_news else [], ensure_ascii=False, indent=2),
            signal_themes=signal_text,
            gainer_theme_matches=gainer_match_text,
            loser_theme_matches=loser_match_text,
            disclaimer=DISCLAIMER,
        )

        last_error = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                html_content = self._call_llm(CLOSING_SYSTEM, user_content, max_tokens=16000)
                logger.info(f"마감 리포트 HTML 생성 완료 ({len(html_content)}자, 시도 {attempt}/{self.MAX_RETRIES})")

                # 콘텐츠 검증
                issues = self._validate_content(html_content, "closing")
                if issues:
                    issues_str = ", ".join(issues)
                    logger.warning(f"콘텐츠 검증 경고 (시도 {attempt}): {issues_str}")
                    # 빈 콘텐츠면 재시도, 그 외 경고만 남기고 진행
                    if any("비어있" in i or "길이 부족" in i for i in issues):
                        if attempt < self.MAX_RETRIES:
                            logger.info("콘텐츠 품질 미달 — 재생성 시도")
                            continue
                        else:
                            raise ContentValidationError(f"최종 검증 실패: {issues_str}")

                title_meta = self._extract_title_meta(html_content, today, "closing")

                return {
                    "title": title_meta.get("title", ""),
                    "content": html_content,
                    "meta_description": title_meta.get("meta_description", ""),
                }
            except ContentValidationError:
                raise
            except Exception as e:
                last_error = e
                logger.error(f"마감 리포트 생성 실패 (시도 {attempt}): {e}")
                if attempt < self.MAX_RETRIES:
                    continue

        raise RuntimeError(f"마감 리포트 생성 {self.MAX_RETRIES}회 실패: {last_error}")

    # ── 아침 브리핑 ────────────────────────────────

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

        last_error = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                html_content = self._call_llm(MORNING_SYSTEM, user_content, max_tokens=16000)
                logger.info(f"아침 브리핑 HTML 생성 완료 ({len(html_content)}자, 시도 {attempt}/{self.MAX_RETRIES})")

                # 콘텐츠 검증
                issues = self._validate_content(html_content, "morning")
                if issues:
                    issues_str = ", ".join(issues)
                    logger.warning(f"콘텐츠 검증 경고 (시도 {attempt}): {issues_str}")
                    if any("비어있" in i or "길이 부족" in i for i in issues):
                        if attempt < self.MAX_RETRIES:
                            logger.info("콘텐츠 품질 미달 — 재생성 시도")
                            continue
                        else:
                            raise ContentValidationError(f"최종 검증 실패: {issues_str}")

                title_meta = self._extract_title_meta(html_content, today, "morning")

                return {
                    "title": title_meta.get("title", ""),
                    "content": html_content,
                    "meta_description": title_meta.get("meta_description", ""),
                }
            except ContentValidationError:
                raise
            except Exception as e:
                last_error = e
                logger.error(f"아침 브리핑 생성 실패 (시도 {attempt}): {e}")
                if attempt < self.MAX_RETRIES:
                    continue

        raise RuntimeError(f"아침 브리핑 생성 {self.MAX_RETRIES}회 실패: {last_error}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    gen = BlogGenerator()
    print("BlogGenerator 초기화 완료")
    print(f"모델: {MODEL}")
