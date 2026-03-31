"""pykrx + 네이버 금융 기반 시장 데이터 백업 수집 모듈"""

import json
import logging
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from pykrx import stock

logger = logging.getLogger(__name__)

NAVER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}


class KRXCollector:
    """pykrx + 네이버 금융 백업 수집기"""

    # ── 한국 시장 데이터 (pykrx) ─────────────────────

    def get_kr_market_data(self, date: str | None = None) -> dict:
        if date is None:
            date = datetime.now().strftime("%Y%m%d")

        try:
            kospi_df = stock.get_index_ohlcv(date, date, "1001")
            kospi = None
            if not kospi_df.empty:
                row = kospi_df.iloc[-1]
                kospi = {
                    "close": float(row["종가"]),
                    "change": float(row.get("등락률", 0)),
                    "volume": int(row.get("거래량", 0)),
                }

            kosdaq_df = stock.get_index_ohlcv(date, date, "2001")
            kosdaq = None
            if not kosdaq_df.empty:
                row = kosdaq_df.iloc[-1]
                kosdaq = {
                    "close": float(row["종가"]),
                    "change": float(row.get("등락률", 0)),
                    "volume": int(row.get("거래량", 0)),
                }

            stocks = []
            for market in ("KOSPI", "KOSDAQ"):
                ohlcv = stock.get_market_ohlcv(date, market=market)
                if ohlcv.empty:
                    continue
                for code in ohlcv.index:
                    row = ohlcv.loc[code]
                    vol = int(row.get("거래량", 0))
                    if vol == 0:
                        continue
                    name = stock.get_market_ticker_name(code)
                    stocks.append({
                        "code": code,
                        "name": name or "",
                        "close": int(row["종가"]),
                        "change_rate": float(row.get("등락률", 0)),
                        "volume": vol,
                        "market": market,
                    })

            logger.info(f"pykrx 한국 시장 데이터 수집 완료: {len(stocks)}종목")
            return {"kospi": kospi, "kosdaq": kosdaq, "stocks": stocks}

        except Exception as e:
            logger.error(f"pykrx 한국 시장 데이터 수집 실패: {e}")
            return {"kospi": None, "kosdaq": None, "stocks": []}

    def get_all_stock_prices(self, date: str | None = None) -> list[dict]:
        """전체 종목 시세만 가져오기 (인덱스 조회 없이)"""
        if date is None:
            date = datetime.now().strftime("%Y%m%d")
        try:
            stocks = []
            for market in ("KOSPI", "KOSDAQ"):
                ohlcv = stock.get_market_ohlcv(date, market=market)
                if ohlcv.empty:
                    continue
                for code in ohlcv.index:
                    row = ohlcv.loc[code]
                    vol = int(row.get("거래량", 0))
                    if vol == 0:
                        continue
                    name = stock.get_market_ticker_name(code)
                    stocks.append({
                        "code": code,
                        "name": name or "",
                        "close": int(row["종가"]),
                        "change_rate": float(row.get("등락률", 0)),
                        "volume": vol,
                        "market": market,
                    })
            logger.info(f"pykrx 전체 종목 시세 수집: {len(stocks)}종목")
            return stocks
        except Exception as e:
            logger.error(f"pykrx 전체 종목 시세 수집 실패: {e}")
            return []

    # ── 투자자별 매매동향 (네이버 금융 크롤링) ──────────

    def _parse_naver_deal_rank(self, investor_code: str, deal_type: str) -> list[dict]:
        """
        네이버 금융 투자자별 매매 순위 파싱

        Args:
            investor_code: "9000" (외국인), "1000" (금융투자=기관)
            deal_type: "buy" (순매수), "sell" (순매도)

        Returns:
            [{"code": "005930", "name": "삼성전자", "net_buy": 382}, ...]
        """
        # sosok=01: KOSPI
        url = (
            f"https://finance.naver.com/sise/sise_deal_rank_iframe.naver"
            f"?sosok=01&investor_gubun={investor_code}&type={deal_type}"
        )
        try:
            r = requests.get(url, headers=NAVER_HEADERS, timeout=10)
            r.encoding = "euc-kr"
            soup = BeautifulSoup(r.text, "html.parser")

            tables = soup.find_all("table")
            if not tables:
                return []

            results = []
            table = tables[0]
            rows = table.find_all("tr")

            for row in rows:
                cols = row.find_all("td")
                if len(cols) < 4:
                    continue

                link = cols[0].find("a")
                if not link or "href" not in link.attrs:
                    continue

                href = link["href"]
                code = href.split("code=")[-1] if "code=" in href else ""
                if not code:
                    continue

                name = link.text.strip()
                try:
                    # 순매수/순매도 수량 (만주 단위 아님, 건수)
                    net_val = int(cols[1].text.strip().replace(",", ""))
                except (ValueError, IndexError):
                    net_val = 0

                if deal_type == "sell":
                    net_val = -abs(net_val)

                results.append({
                    "code": code,
                    "name": name,
                    "net_buy": net_val,
                })

            return results[:10]

        except Exception as e:
            logger.error(f"네이버 금융 수급 크롤링 실패 [{investor_code}/{deal_type}]: {e}")
            return []

    def get_investor_trading(self, date: str | None = None) -> dict:
        """
        투자자별 순매수/순매도 상위 종목 (네이버 금융)
        외국인: 9000, 기관(금융투자): 1000
        """
        result = {
            "foreign_buy_top": [],
            "foreign_sell_top": [],
            "institution_buy_top": [],
            "institution_sell_top": [],
        }

        # 외국인 순매수
        foreign_buy = self._parse_naver_deal_rank("9000", "buy")
        if foreign_buy:
            result["foreign_buy_top"] = foreign_buy
            logger.info(f"네이버 외국인 순매수 {len(foreign_buy)}건 수집")

        # 외국인 순매도
        foreign_sell = self._parse_naver_deal_rank("9000", "sell")
        if foreign_sell:
            result["foreign_sell_top"] = foreign_sell
            logger.info(f"네이버 외국인 순매도 {len(foreign_sell)}건 수집")

        # 기관 순매수 (금융투자: 1000)
        inst_buy = self._parse_naver_deal_rank("1000", "buy")
        if inst_buy:
            result["institution_buy_top"] = inst_buy
            logger.info(f"네이버 기관 순매수 {len(inst_buy)}건 수집")

        # 기관 순매도
        inst_sell = self._parse_naver_deal_rank("1000", "sell")
        if inst_sell:
            result["institution_sell_top"] = inst_sell
            logger.info(f"네이버 기관 순매도 {len(inst_sell)}건 수집")

        total = sum(len(v) for v in result.values())
        if total == 0:
            logger.warning("네이버 금융 수급 데이터 전체 0건")
        else:
            logger.info(f"네이버 금융 수급 수집 완료: 총 {total}건")

        return result

    # ── 통합 ─────────────────────────────────────

    def collect_all(self) -> dict:
        logger.info("pykrx/네이버 데이터 수집 시작")
        kr = self.get_kr_market_data()
        supply = self.get_investor_trading()
        logger.info("pykrx/네이버 데이터 수집 완료")
        return {"kr_market": kr, "us_market": {}, "supply": supply}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    collector = KRXCollector()
    supply = collector.get_investor_trading()
    print(json.dumps(supply, ensure_ascii=False, indent=2, default=str))
