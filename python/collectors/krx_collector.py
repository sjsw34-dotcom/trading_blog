"""pykrx 기반 시장 데이터 백업 수집 모듈"""

import json
import logging
from datetime import datetime

from pykrx import stock

logger = logging.getLogger(__name__)


class KRXCollector:
    """pykrx 백업 수집기 — KIS API 실패 시 사용"""

    def get_kr_market_data(self, date: str | None = None) -> dict:
        """
        전종목 당일 OHLCV + 등락률 → KIS 형식으로 변환

        Args:
            date: 조회 날짜 (YYYYMMDD). None이면 오늘.
        """
        if date is None:
            date = datetime.now().strftime("%Y%m%d")

        try:
            # KOSPI 지수
            kospi_df = stock.get_index_ohlcv(date, date, "1001")
            kospi = None
            if not kospi_df.empty:
                row = kospi_df.iloc[-1]
                kospi = {
                    "close": float(row["종가"]),
                    "change": float(row.get("등락률", 0)),
                    "volume": int(row.get("거래량", 0)),
                }

            # KOSDAQ 지수
            kosdaq_df = stock.get_index_ohlcv(date, date, "2001")
            kosdaq = None
            if not kosdaq_df.empty:
                row = kosdaq_df.iloc[-1]
                kosdaq = {
                    "close": float(row["종가"]),
                    "change": float(row.get("등락률", 0)),
                    "volume": int(row.get("거래량", 0)),
                }

            # 전종목 OHLCV (KOSPI + KOSDAQ)
            stocks = []
            for market in ("KOSPI", "KOSDAQ"):
                ohlcv = stock.get_market_ohlcv(date, market=market)
                if ohlcv.empty:
                    continue
                for code in ohlcv.index:
                    row = ohlcv.loc[code]
                    vol = int(row.get("거래량", 0))
                    if vol == 0:
                        continue  # 거래 없는 종목 제외
                    name = stock.get_market_ticker_name(code)
                    stocks.append(
                        {
                            "code": code,
                            "name": name or "",
                            "close": int(row["종가"]),
                            "change_rate": float(row.get("등락률", 0)),
                            "volume": vol,
                            "market": market,
                        }
                    )

            logger.info(f"pykrx 한국 시장 데이터 수집 완료: {len(stocks)}종목")
            return {"kospi": kospi, "kosdaq": kosdaq, "stocks": stocks}

        except Exception as e:
            logger.error(f"pykrx 한국 시장 데이터 수집 실패: {e}")
            return {"kospi": None, "kosdaq": None, "stocks": []}

    def get_investor_trading(self, date: str | None = None) -> dict:
        """
        투자자별 매매동향 (외국인/기관)

        Args:
            date: 조회 날짜 (YYYYMMDD). None이면 오늘.
        """
        if date is None:
            date = datetime.now().strftime("%Y%m%d")

        result = {
            "foreign_buy_top": [],
            "foreign_sell_top": [],
            "institution_buy_top": [],
            "institution_sell_top": [],
        }

        try:
            # 외국인 매매동향
            foreign_df = stock.get_market_net_purchases_of_equities(
                date, date, "KOSPI", "외국인"
            )
            if not foreign_df.empty:
                # 순매수 상위
                buy_sorted = foreign_df.sort_values("순매수거래량", ascending=False)
                for code in buy_sorted.index[:10]:
                    row = buy_sorted.loc[code]
                    name = stock.get_market_ticker_name(code)
                    result["foreign_buy_top"].append(
                        {
                            "code": code,
                            "name": name or "",
                            "net_buy": int(row["순매수거래량"]),
                        }
                    )
                # 순매도 상위
                sell_sorted = foreign_df.sort_values("순매수거래량", ascending=True)
                for code in sell_sorted.index[:10]:
                    row = sell_sorted.loc[code]
                    name = stock.get_market_ticker_name(code)
                    result["foreign_sell_top"].append(
                        {
                            "code": code,
                            "name": name or "",
                            "net_buy": int(row["순매수거래량"]),
                        }
                    )

            # 기관 매매동향
            inst_df = stock.get_market_net_purchases_of_equities(
                date, date, "KOSPI", "기관합계"
            )
            if not inst_df.empty:
                buy_sorted = inst_df.sort_values("순매수거래량", ascending=False)
                for code in buy_sorted.index[:10]:
                    row = buy_sorted.loc[code]
                    name = stock.get_market_ticker_name(code)
                    result["institution_buy_top"].append(
                        {
                            "code": code,
                            "name": name or "",
                            "net_buy": int(row["순매수거래량"]),
                        }
                    )
                sell_sorted = inst_df.sort_values("순매수거래량", ascending=True)
                for code in sell_sorted.index[:10]:
                    row = sell_sorted.loc[code]
                    name = stock.get_market_ticker_name(code)
                    result["institution_sell_top"].append(
                        {
                            "code": code,
                            "name": name or "",
                            "net_buy": int(row["순매수거래량"]),
                        }
                    )

            logger.info("pykrx 투자자별 매매동향 수집 완료")

        except Exception as e:
            logger.error(f"pykrx 투자자별 매매동향 수집 실패: {e}")

        return result


    def collect_all(self) -> dict:
        """전체 데이터 수집 (KISCollector와 인터페이스 일관성)"""
        logger.info("pykrx 데이터 수집 시작")
        kr = self.get_kr_market_data()
        supply = self.get_investor_trading()
        logger.info("pykrx 데이터 수집 완료")
        return {"kr_market": kr, "us_market": {}, "supply": supply}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    collector = KRXCollector()
    market = collector.get_kr_market_data()
    print(json.dumps(market, ensure_ascii=False, indent=2, default=str))
    supply = collector.get_investor_trading()
    print(json.dumps(supply, ensure_ascii=False, indent=2, default=str))
