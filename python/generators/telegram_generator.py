"""텔레그램 요약 생성 모듈 — OpenAI API"""

import json
import logging
import os
from pathlib import Path

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "config" / ".env")

logger = logging.getLogger(__name__)

MODEL = "gpt-4o-mini"

MORNING_TEMPLATE = """\
아래 데이터로 텔레그램 아침 브리핑을 작성하세요.

데이터:
{data}

형식 (마크다운 없이 순수 텍스트, 이모지 사용):

🇺🇸 {date} 미국장 마감

📈 지수
S&P500 [종가] ([등락%]) | 나스닥 [종가] ([등락%]) | 다우 [종가] ([등락%])

🔥 주요 상승 (5개)
[종목명] [등락%] — [한줄 사유]
...

📉 주요 하락 (5개)
[종목명] [등락%] — [한줄 사유]
...

💱 환율·원자재
USD/KRW [환율] | WTI [가격] | 금 [가격]

📌 오늘의 핵심 (2~3줄)
- [미국장 핵심 이슈 1]
- [한국장에 미칠 영향]

📰 주요 뉴스 (3건)
· [뉴스 제목 — 한줄 요약]
...

전체 리포트 → {{blog_url}}

위 형식대로만 출력하세요. 다른 설명 없이.
"""

CLOSING_TEMPLATE = """\
아래 데이터로 텔레그램 마감 리포트를 작성하세요.

데이터:
{data}

형식 (마크다운 없이 순수 텍스트, 이모지 사용):

📊 {date} 장 마감

📈 지수
KOSPI [종가] ([등락%]) | KOSDAQ [종가] ([등락%])
거래대금 [금액] | 외국인 [순매수/순매도 금액] | 기관 [순매수/순매도 금액]

🔥 상승 TOP 5
1. [종목명] [등락%] — [한줄 사유]
2. ...

📉 하락 TOP 5
1. [종목명] [등락%] — [한줄 사유]
2. ...

🏷️ 오늘의 테마
· [테마명]: [대장주] 외 N종목 — [한줄 배경]
...

📌 오늘의 핵심 (2~3줄)
- [시장을 움직인 가장 큰 요인]
- [내일 주목할 포인트]

전체 리포트 → {{blog_url}}

위 형식대로만 출력하세요. 다른 설명 없이.
"""


class TelegramGenerator:
    """블로그 글을 텔레그램 요약으로 변환"""

    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY", "")
        )

    def _call_llm(self, prompt: str) -> str:
        """OpenAI API 호출"""
        response = self.client.chat.completions.create(
            model=MODEL,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()

    def generate_morning(
        self,
        us_market: dict,
        world_news: list[dict],
        date_str: str,
    ) -> str:
        data = {
            "us_market": us_market,
            "world_news": world_news[:10],
        }
        prompt = MORNING_TEMPLATE.format(
            data=json.dumps(data, ensure_ascii=False, indent=2, default=str),
            date=date_str,
        )
        try:
            result = self._call_llm(prompt)
            logger.info("아침 텔레그램 요약 생성 완료")
            return result
        except Exception as e:
            logger.error(f"아침 텔레그램 요약 생성 실패: {e}")
            return f"🇺🇸 {date_str} 미국장 마감\n요약 생성 실패\n\n전체 리포트 → {{blog_url}}"

    def generate_closing(
        self,
        kr_market: dict,
        rank_data: dict,
        date_str: str,
        themes: dict | None = None,
    ) -> str:
        gainers = rank_data.get("gainers", [])
        losers = rank_data.get("losers", [])
        data = {
            "kr_market": kr_market,
            "top_gainers": gainers[:5],
            "top_losers": losers[:5],
            "themes": themes.get("themes", [])[:3] if themes else [],
        }
        prompt = CLOSING_TEMPLATE.format(
            data=json.dumps(data, ensure_ascii=False, indent=2, default=str),
            date=date_str,
        )
        try:
            result = self._call_llm(prompt)
            logger.info("마감 텔레그램 요약 생성 완료")
            return result
        except Exception as e:
            logger.error(f"마감 텔레그램 요약 생성 실패: {e}")
            return f"📊 {date_str} 장 마감\n요약 생성 실패\n\n전체 리포트 → {{blog_url}}"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    gen = TelegramGenerator()
    print("TelegramGenerator 초기화 완료")
    print(f"모델: {MODEL}")
