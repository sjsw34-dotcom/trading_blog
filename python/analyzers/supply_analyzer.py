"""수급 분석 모듈 — 외국인/기관 매매동향 정리"""

import json
import logging

logger = logging.getLogger(__name__)


class SupplyAnalyzer:
    """투자자별 매매동향 데이터를 블로그용으로 정리"""

    def analyze(self, supply_data: dict) -> dict:
        """
        kis_collector/krx_collector의 수급 데이터를 정리

        Args:
            supply_data: get_investor_trading() 출력
                {
                    "foreign_buy_top": [...],
                    "foreign_sell_top": [...],
                    "institution_buy_top": [...],
                    "institution_sell_top": [...],
                }

        Returns:
            {
                "foreign": {"buy_top": [...], "sell_top": [...]},
                "institution": {"buy_top": [...], "sell_top": [...]},
                "summary": {"foreign_net": str, "institution_net": str},
            }
        """
        if not supply_data:
            logger.warning("분석할 수급 데이터 없음")
            return {
                "foreign": {"buy_top": [], "sell_top": []},
                "institution": {"buy_top": [], "sell_top": []},
                "summary": {"foreign_net": "데이터 없음", "institution_net": "데이터 없음"},
            }

        foreign_buy = supply_data.get("foreign_buy_top", [])[:10]
        foreign_sell = supply_data.get("foreign_sell_top", [])[:10]
        inst_buy = supply_data.get("institution_buy_top", [])[:10]
        inst_sell = supply_data.get("institution_sell_top", [])[:10]

        # 순매수 요약 텍스트
        foreign_summary = self._make_summary("외국인", foreign_buy, foreign_sell)
        inst_summary = self._make_summary("기관", inst_buy, inst_sell)

        logger.info(
            f"수급 분석 완료: 외국인 매수 {len(foreign_buy)}건/매도 {len(foreign_sell)}건, "
            f"기관 매수 {len(inst_buy)}건/매도 {len(inst_sell)}건"
        )

        return {
            "foreign": {"buy_top": foreign_buy, "sell_top": foreign_sell},
            "institution": {"buy_top": inst_buy, "sell_top": inst_sell},
            "summary": {
                "foreign_net": foreign_summary,
                "institution_net": inst_summary,
            },
        }

    def _make_summary(
        self, investor_type: str, buy_list: list[dict], sell_list: list[dict]
    ) -> str:
        """순매수 요약 텍스트 생성"""
        if not buy_list and not sell_list:
            return f"{investor_type} 데이터 없음"

        parts = []
        if buy_list:
            top = buy_list[0]
            parts.append(f"순매수 1위 {top.get('name', '')}({top.get('net_buy', 0):,}주)")
        if sell_list:
            top = sell_list[0]
            parts.append(f"순매도 1위 {top.get('name', '')}({abs(top.get('net_buy', 0)):,}주)")

        return f"{investor_type}: {', '.join(parts)}"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sample = {
        "foreign_buy_top": [
            {"code": "005930", "name": "삼성전자", "net_buy": 500000},
            {"code": "000660", "name": "SK하이닉스", "net_buy": 300000},
        ],
        "foreign_sell_top": [
            {"code": "247540", "name": "에코프로비엠", "net_buy": -200000},
        ],
        "institution_buy_top": [
            {"code": "005930", "name": "삼성전자", "net_buy": 100000},
        ],
        "institution_sell_top": [
            {"code": "035420", "name": "NAVER", "net_buy": -150000},
        ],
    }
    analyzer = SupplyAnalyzer()
    result = analyzer.analyze(sample)
    print(json.dumps(result, ensure_ascii=False, indent=2))
