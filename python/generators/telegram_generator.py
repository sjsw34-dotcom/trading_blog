"""텔레그램 요약 생성 모듈 — 블로그 글을 5줄 이내로 압축"""

import json
import logging
import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "config" / ".env")

logger = logging.getLogger(__name__)

MODEL = "claude-haiku-4-5-20251001"

MORNING_TEMPLATE = """\
아래 아침 브리핑 데이터를 텔레그램 메시지로 5줄 이내 요약해주세요.

데이터:
{data}

형식 (이모지 사용, 마크다운 없이 순수 텍스트):
🇺🇸 {date} 미국장 마감
S&P500 [종가] ([등락%]) | 나스닥 [종가] ([등락%])
[주요 종목 2~3개 등락률]
[환율]

📌 [가장 중요한 이슈 한 줄]

전체 리포트 → {{blog_url}}

위 형식에 맞춰 응답만 해주세요. 다른 설명 없이 메시지만.
"""

CLOSING_TEMPLATE = """\
아래 마감 리포트 데이터를 텔레그램 메시지로 5줄 이내 요약해주세요.

데이터:
{data}

형식 (이모지 사용, 마크다운 없이 순수 텍스트):
📊 {date} 장 마감
KOSPI [종가] ([등락%]) | KOSDAQ [종가] ([등락%])
🔥 상승1위 [종목명] [등락%] ([사유])
📉 하락1위 [종목명] [등락%] ([사유])
외국인 [순매수금액] | 기관 [순매수금액]

전체 리포트 → {{blog_url}}

위 형식에 맞춰 응답만 해주세요. 다른 설명 없이 메시지만.
"""


class TelegramGenerator:
    """블로그 글을 텔레그램 요약으로 변환"""

    def __init__(self):
        self.client = anthropic.Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY", "")
        )

    def _call_claude(self, prompt: str) -> str:
        """Claude API 호출"""
        response = self.client.messages.create(
            model=MODEL,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()

    def generate_morning(
        self,
        us_market: dict,
        world_news: list[dict],
        date_str: str,
    ) -> str:
        """
        아침 브리핑 텔레그램 요약 생성

        Args:
            us_market: 미국 시장 데이터
            world_news: 해외 뉴스 리스트
            date_str: 날짜 문자열 (예: "3/18")

        Returns:
            텔레그램 메시지 문자열 ({blog_url} 플레이스홀더 포함)
        """
        data = {
            "us_market": us_market,
            "world_news": world_news[:5],
        }
        prompt = MORNING_TEMPLATE.format(
            data=json.dumps(data, ensure_ascii=False, indent=2, default=str),
            date=date_str,
        )
        try:
            result = self._call_claude(prompt)
            logger.info("아침 텔레그램 요약 생성 완료")
            return result
        except Exception as e:
            logger.error(f"아침 텔레그램 요약 생성 실패: {e}")
            return f"🇺🇸 {date_str} 미국장 마감\n요약 생성 실패\n\n전체 리포트 → {{blog_url}}"

    def generate_closing(
        self,
        kr_market: dict,
        rank_data: dict,
        supply: dict,
        date_str: str,
    ) -> str:
        """
        마감 리포트 텔레그램 요약 생성

        Args:
            kr_market: 한국 시장 데이터
            rank_data: 상승/하락 TOP 데이터
            supply: 수급 데이터
            date_str: 날짜 문자열 (예: "3/18")

        Returns:
            텔레그램 메시지 문자열 ({blog_url} 플레이스홀더 포함)
        """
        data = {
            "kr_market": kr_market,
            "top_gainer": rank_data.get("gainers", [{}])[0] if rank_data.get("gainers") else {},
            "top_loser": rank_data.get("losers", [{}])[0] if rank_data.get("losers") else {},
            "supply_summary": supply.get("summary", {}),
        }
        prompt = CLOSING_TEMPLATE.format(
            data=json.dumps(data, ensure_ascii=False, indent=2, default=str),
            date=date_str,
        )
        try:
            result = self._call_claude(prompt)
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
