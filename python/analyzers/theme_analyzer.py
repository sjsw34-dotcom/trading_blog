"""뉴스 기반 테마 자동 분류 모듈 — OpenAI API + 테마 사전 활용"""

import json
import logging
import os
from pathlib import Path

from openai import OpenAI
import yaml
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "config" / ".env")

logger = logging.getLogger(__name__)

_settings_path = Path(__file__).parent.parent / "config" / "settings.yaml"
with open(_settings_path, "r", encoding="utf-8") as f:
    SETTINGS = yaml.safe_load(f)

TOP_N_THEMES = SETTINGS["report"]["top_n_themes"]
MODEL = "gpt-4o"

THEME_PROMPT = """\
당신은 한국 주식시장 테마 분류 전문가입니다.

## 기존 테마 사전 (DB 누적 데이터)
아래는 지금까지 한국 주식시장에서 관찰된 테마 목록입니다.
오늘 상승 종목이 이 중 하나에 해당하면 "기존 테마 재부각"으로 분류하세요.
해당하는 테마가 없으면 새 테마를 만드세요.

{existing_themes}

## 최근 7일 주요 뉴스 흐름 (맥락 참고)
{recent_news}

## 오늘 상승 종목 + 관련 뉴스
{stock_data}

## 작업
1. 같은 이유(뉴스)로 상승한 종목끼리 묶어 테마를 만드세요.
2. 기존 테마에 해당하면 그 테마명을 그대로 사용하세요.
3. 기존 테마에 없는 새로운 움직임이면 새 테마명을 만드세요.
4. 각 테마별로 한 줄 설명 작성 (왜 오늘 움직였는지).
5. 기존 테마 재부각이면 "재부각" 표시, 새 테마면 "신규" 표시.
6. 투자 조언/추천 절대 금지. 팩트만.
7. '올랐다'는 쓰되 '오를 것이다'는 절대 안 씀.

JSON 형식으로만 응답 (마크다운 코드블록 없이):
{{"themes": [{{"name": "테마명", "description": "한줄설명", "is_new": false, "stocks": [{{"code": "종목코드", "name": "종목명", "change_rate": 5.2}}], "avg_change": 5.2, "news": [{{"title": "뉴스제목", "url": "URL", "press": "언론사"}}]}}]}}
"""


class ThemeAnalyzer:
    """뉴스 기반 테마 자동 분류 — OpenAI API + 테마 사전"""

    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY", "")
        )

    def _build_stock_text(self, gainers: list[dict]) -> str:
        lines = []
        for i, s in enumerate(gainers, 1):
            news_text = ""
            if s.get("news"):
                news_items = [
                    f"  - [{n['title']}]({n.get('url', '')}) ({n.get('press', '')})"
                    for n in s["news"][:3]
                ]
                news_text = "\n".join(news_items)
            else:
                news_text = "  - (관련 뉴스 없음)"
            lines.append(
                f"{i}. {s['name']}({s['code']}) +{s.get('change_rate', 0)}%\n{news_text}"
            )
        return "\n".join(lines)

    def _build_themes_text(self, existing_themes: list[dict]) -> str:
        if not existing_themes:
            return "(테마 사전 비어있음 — 모두 신규 테마로 분류)"
        lines = []
        for t in existing_themes:
            stocks_str = ", ".join(
                s.get("name", "") for s in (t.get("stocks") or [])[:5]
            )
            lines.append(
                f"- {t['name']} (중요도:{t.get('importance',3)}, "
                f"마지막:{t.get('last_active','?')}, "
                f"횟수:{t.get('hit_count',0)}) "
                f"종목: {stocks_str}"
            )
        return "\n".join(lines)

    def _build_recent_news_text(self, recent_news: list[dict]) -> str:
        if not recent_news:
            return "(최근 뉴스 없음)"
        lines = []
        for n in recent_news[:30]:
            lines.append(f"- [{n.get('date','')}] {n.get('title','')}")
        return "\n".join(lines)

    def analyze(
        self,
        gainers: list[dict],
        existing_themes: list[dict] | None = None,
        recent_news_context: list[dict] | None = None,
    ) -> dict:
        if not gainers:
            logger.warning("테마 분석할 상승 종목 없음")
            return {"themes": []}

        stock_text = self._build_stock_text(gainers)
        themes_text = self._build_themes_text(existing_themes or [])
        news_text = self._build_recent_news_text(recent_news_context or [])

        prompt = THEME_PROMPT.format(
            stock_data=stock_text,
            existing_themes=themes_text,
            recent_news=news_text,
        )

        try:
            response = self.client.chat.completions.create(
                model=MODEL,
                max_tokens=3000,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.choices[0].message.content.strip()

            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1]
                raw = raw.rsplit("```", 1)[0]

            result = json.loads(raw)
            themes = result.get("themes", [])
            themes.sort(key=lambda t: t.get("avg_change", 0), reverse=True)

            new_count = sum(1 for t in themes if t.get("is_new"))
            reappear_count = len(themes) - new_count
            logger.info(
                f"테마 분류 완료: {len(themes)}개 "
                f"(재부각 {reappear_count}, 신규 {new_count})"
            )
            return {"themes": themes[:TOP_N_THEMES]}

        except json.JSONDecodeError as e:
            logger.error(f"응답 JSON 파싱 실패: {e}")
            return {"themes": []}
        except Exception as e:
            logger.error(f"테마 분석 실패: {e}")
            return {"themes": []}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    analyzer = ThemeAnalyzer()
    print("ThemeAnalyzer 초기화 완료")
