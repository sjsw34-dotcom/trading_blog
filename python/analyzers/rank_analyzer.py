"""등락률 순위 분석 모듈 — 상승/하락 TOP 15 + 뉴스 매칭"""

import json
import logging
import re
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_settings_path = Path(__file__).parent.parent / "config" / "settings.yaml"
with open(_settings_path, "r", encoding="utf-8") as f:
    SETTINGS = yaml.safe_load(f)

TOP_N = SETTINGS["report"]["top_n_stocks"]

# 필터링 패턴: 스팩, 우선주, 리츠, ETF/ETN
EXCLUDE_PATTERNS = re.compile(
    r"스팩|SPAC|우$|우B$|우C$|리츠|REIT|ETF|ETN|인버스|레버리지|선물"
)


class RankAnalyzer:
    """전종목 등락률 기준 상승/하락 TOP 15 추출 + 뉴스 매칭"""

    def _should_exclude(self, name: str) -> bool:
        """스팩, 우선주, 리츠, ETF/ETN 필터링"""
        return bool(EXCLUDE_PATTERNS.search(name))

    def analyze(
        self,
        stocks: list[dict],
        stock_news: dict[str, list[dict]] | None = None,
    ) -> dict:
        """
        등락률 기준 상승/하락 TOP N 추출

        Args:
            stocks: 전종목 시세 리스트
                [{"code", "name", "close", "change_rate", "volume"}, ...]
            stock_news: 종목코드→뉴스 리스트 매핑 (news_crawler 출력)

        Returns:
            {"gainers": [...], "losers": [...]}
        """
        if not stocks:
            logger.warning("분석할 종목 데이터 없음")
            return {"gainers": [], "losers": []}

        stock_news = stock_news or {}

        # 필터링
        filtered = [s for s in stocks if not self._should_exclude(s.get("name", ""))]
        logger.info(f"필터링 후 종목 수: {len(filtered)}/{len(stocks)}")

        # 상승 TOP N
        by_gain = sorted(filtered, key=lambda x: x.get("change_rate", 0), reverse=True)
        gainers = []
        for s in by_gain[:TOP_N]:
            entry = {
                "code": s["code"],
                "name": s.get("name", ""),
                "close": s.get("close", 0),
                "change_rate": s.get("change_rate", 0),
                "volume": s.get("volume", 0),
                "news": stock_news.get(s["code"], []),
            }
            gainers.append(entry)

        # 하락 TOP N
        by_loss = sorted(filtered, key=lambda x: x.get("change_rate", 0))
        losers = []
        for s in by_loss[:TOP_N]:
            entry = {
                "code": s["code"],
                "name": s.get("name", ""),
                "close": s.get("close", 0),
                "change_rate": s.get("change_rate", 0),
                "volume": s.get("volume", 0),
                "news": stock_news.get(s["code"], []),
            }
            losers.append(entry)

        logger.info(
            f"등락률 분석 완료: 상승 {len(gainers)}건, 하락 {len(losers)}건"
        )
        return {"gainers": gainers, "losers": losers}

    def get_stock_codes(self, rank_data: dict) -> list[str]:
        """분석 결과에서 종목코드 리스트 추출 (뉴스 크롤링용)"""
        codes = []
        for s in rank_data.get("gainers", []):
            codes.append(s["code"])
        for s in rank_data.get("losers", []):
            codes.append(s["code"])
        return list(dict.fromkeys(codes))  # 중복 제거, 순서 유지


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # 테스트용 더미 데이터
    sample_stocks = [
        {"code": "005930", "name": "삼성전자", "close": 72000, "change_rate": 2.1, "volume": 10000000},
        {"code": "034020", "name": "두산에너빌리티", "close": 21500, "change_rate": 8.3, "volume": 5000000},
        {"code": "247540", "name": "에코프로비엠", "close": 152000, "change_rate": -4.2, "volume": 3000000},
        {"code": "999999", "name": "테스트스팩1호", "close": 2100, "change_rate": 30.0, "volume": 100},
    ]
    analyzer = RankAnalyzer()
    result = analyzer.analyze(sample_stocks)
    print(json.dumps(result, ensure_ascii=False, indent=2))
