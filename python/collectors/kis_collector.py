"""KIS API 시세 수집 모듈 (한국+미국+환율+수급)"""

import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "config" / ".env")

logger = logging.getLogger(__name__)

# 설정 로드
_settings_path = Path(__file__).parent.parent / "config" / "settings.yaml"
with open(_settings_path, "r", encoding="utf-8") as f:
    SETTINGS = yaml.safe_load(f)

BASE_URL = SETTINGS["kis"]["base_url_real"]
US_STOCKS = SETTINGS["kis"]["us_stocks"]

TOKEN_FILE = Path(__file__).parent.parent / "config" / "token_cache.json"


class KISCollector:
    """한국투자증권 KIS API 수집기"""

    def __init__(self):
        self.app_key = os.getenv("KIS_APP_KEY", "")
        self.app_secret = os.getenv("KIS_APP_SECRET", "")
        self.account_no = os.getenv("KIS_ACCOUNT_NO", "")
        self.hts_id = os.getenv("KIS_HTS_ID", "")
        self._token = None
        self._token_expires = None

    # ── 인증 ──────────────────────────────────────────

    def _get_token(self) -> str:
        """접근토큰 발급/캐싱/갱신"""
        # 메모리 캐시 확인
        if self._token and self._token_expires and datetime.now() < self._token_expires:
            return self._token

        # 파일 캐시 확인
        if TOKEN_FILE.exists():
            try:
                cache = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
                expires = datetime.fromisoformat(cache["expires_at"])
                if datetime.now() < expires - timedelta(hours=1):
                    self._token = cache["access_token"]
                    self._token_expires = expires
                    logger.info("토큰 파일 캐시 사용")
                    return self._token
            except Exception:
                pass

        # 신규 발급
        url = f"{BASE_URL}/oauth2/tokenP"
        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
        }
        resp = requests.post(url, json=body, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        self._token = data["access_token"]
        expires_in = int(data.get("expires_in", 86400))
        self._token_expires = datetime.now() + timedelta(seconds=expires_in)

        # 파일 캐시 저장
        TOKEN_FILE.write_text(
            json.dumps(
                {
                    "access_token": self._token,
                    "expires_at": self._token_expires.isoformat(),
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        logger.info("새 토큰 발급 완료")
        return self._token

    def _headers(self, tr_id: str) -> dict:
        """공통 요청 헤더"""
        return {
            "authorization": f"Bearer {self._get_token()}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id,
            "content-type": "application/json; charset=utf-8",
        }

    def _get(self, path: str, tr_id: str, params: dict) -> dict | None:
        """GET 요청 공통 래퍼"""
        url = f"{BASE_URL}{path}"
        try:
            resp = requests.get(
                url, headers=self._headers(tr_id), params=params, timeout=15
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("rt_cd") != "0":
                logger.warning(f"KIS API 오류: {data.get('msg1', '')}")
                return None
            return data
        except Exception as e:
            logger.error(f"KIS API 요청 실패 [{path}]: {e}")
            return None

    # ── 한국 시세 ─────────────────────────────────────

    def get_kr_index(self, index_code: str) -> dict | None:
        """한국 지수 조회 (KOSPI: 0001, KOSDAQ: 1001)"""
        data = self._get(
            "/uapi/domestic-stock/v1/quotations/inquire-index-price",
            "FHPUP02100000",
            {"FID_COND_MRKT_DIV_CODE": "U", "FID_INPUT_ISCD": index_code},
        )
        if not data or "output" not in data:
            return None
        o = data["output"]
        return {
            "close": float(o.get("bstp_nmix_prpr", 0)),
            "change": float(o.get("bstp_nmix_prdy_ctrt", 0)),
            "volume": int(o.get("acml_vol", 0)),
        }

    def get_kr_stock_price(self, stock_code: str) -> dict | None:
        """한국 개별종목 현재가(종가) 조회"""
        data = self._get(
            "/uapi/domestic-stock/v1/quotations/inquire-price",
            "FHKST01010100",
            {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": stock_code},
        )
        if not data or "output" not in data:
            return None
        o = data["output"]
        return {
            "code": stock_code,
            "name": o.get("hts_kor_isnm", ""),
            "close": int(o.get("stck_prpr", 0)),
            "change_rate": float(o.get("prdy_ctrt", 0)),
            "volume": int(o.get("acml_vol", 0)),
        }

    def get_kr_volume_rank(self, top_n: int = 15) -> list[dict]:
        """한국 거래량 순위 TOP N"""
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_COND_SCR_DIV_CODE": "20171",
            "FID_INPUT_ISCD": "0000",
            "FID_DIV_CLS_CODE": "0",
            "FID_BLNG_CLS_CODE": "0",
            "FID_TRGT_CLS_CODE": "111111111",
            "FID_TRGT_EXLS_CLS_CODE": "000000",
            "FID_INPUT_PRICE_1": "0",
            "FID_INPUT_PRICE_2": "0",
            "FID_VOL_CNT": "0",
            "FID_INPUT_DATE_1": "",
        }
        data = self._get(
            "/uapi/domestic-stock/v1/quotations/volume-rank",
            "FHPST01710000",
            params,
        )
        if not data or "output" not in data:
            return []

        result = []
        for item in data["output"][:top_n]:
            result.append(
                {
                    "code": item.get("mksc_shrn_iscd", ""),
                    "name": item.get("hts_kor_isnm", ""),
                    "close": int(item.get("stck_prpr", 0)),
                    "change_rate": float(item.get("prdy_ctrt", 0)),
                    "volume": int(item.get("acml_vol", 0)),
                }
            )
        return result

    def get_kr_fluctuation_rank(self, top_n: int = 30, direction: str = "up") -> list[dict]:
        """한국 등락률 순위 (상승/하락)

        Args:
            top_n: 상위 N개
            direction: "up" (상승) 또는 "down" (하락)
        """
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_COND_SCR_DIV_CODE": "20170",
            "FID_INPUT_ISCD": "0000",
            "FID_DIV_CLS_CODE": "0" if direction == "up" else "1",
            "FID_BLNG_CLS_CODE": "0",
            "FID_TRGT_CLS_CODE": "111111111",
            "FID_TRGT_EXLS_CLS_CODE": "000000",
            "FID_INPUT_PRICE_1": "0",
            "FID_INPUT_PRICE_2": "0",
            "FID_VOL_CNT": "0",
            "FID_INPUT_DATE_1": "",
            "FID_RANK_SORT_CLS_CODE": "1" if direction == "down" else "0",
            "FID_INPUT_CNT_1": "0",
            "FID_PRC_CLS_CODE": "0",
            "FID_RSFL_RATE1": "",
            "FID_RSFL_RATE2": "",
        }
        data = self._get(
            "/uapi/domestic-stock/v1/ranking/fluctuation",
            "FHPST01700000",
            params,
        )
        if not data or "output" not in data:
            return []

        result = []
        for item in data["output"][:top_n * 2]:  # 필터링 여유분 확보
            code = item.get("stck_shrn_iscd", "") or item.get("mksc_shrn_iscd", "")
            change_rate = float(item.get("prdy_ctrt", 0))
            # 하락 조회 시 change_rate < 0인 것만 (KIS API가 양수도 섞어 반환)
            if direction == "down" and change_rate >= 0:
                continue
            result.append(
                {
                    "code": code,
                    "name": item.get("hts_kor_isnm", ""),
                    "close": int(item.get("stck_prpr", 0)),
                    "change_rate": change_rate,
                    "volume": int(item.get("acml_vol", 0)),
                }
            )
            if len(result) >= top_n:
                break

        if direction == "down" and not result:
            logger.warning("하락 종목 필터 결과 0건 — KIS API 응답에 음수 등락률 없음")
        return result

    def get_kr_market_data(self) -> dict:
        """한국 시장 전체 데이터 수집 (지수 + 등락률 상위/하위 + 거래량 상위)"""
        kospi = self.get_kr_index("0001")
        kosdaq = self.get_kr_index("1001")
        time.sleep(0.2)

        # 등락률 상위 30 + 하위 30 + 거래량 상위 15 합쳐서 전달
        gainers = self.get_kr_fluctuation_rank(30, "up")
        time.sleep(0.2)
        losers = self.get_kr_fluctuation_rank(30, "down")
        time.sleep(0.2)
        volume_top = self.get_kr_volume_rank(SETTINGS["report"]["top_n_stocks"])

        # 중복 제거 후 합침 (하위 호환용 stocks 필드 유지)
        seen = set()
        stocks = []
        for s in gainers + losers + volume_top:
            if s["code"] and s["code"] not in seen:
                seen.add(s["code"])
                stocks.append(s)

        return {
            "kospi": kospi,
            "kosdaq": kosdaq,
            "stocks": stocks,
            "gainers": gainers,
            "losers": losers,
        }

    # ── 미국 시세 ─────────────────────────────────────

    def get_us_stock_price(self, ticker: str, exchange: str) -> dict | None:
        """미국 개별종목 현재가(종가) 조회"""
        data = self._get(
            "/uapi/overseas-price/v1/quotations/price",
            "HHDFS00000300",
            {"AUTH": "", "EXCD": exchange, "SYMB": ticker},
        )
        if not data or "output" not in data:
            return None
        o = data["output"]
        close = float(o.get("last") or 0)
        prev_close = float(o.get("base") or 0)
        if not close:
            return None
        change_rate = ((close - prev_close) / prev_close * 100) if prev_close else 0
        return {
            "ticker": ticker,
            "close": close,
            "change_rate": round(change_rate, 2),
        }

    def get_us_index(self, symbol: str, exchange: str) -> dict | None:
        """미국 지수 조회 (S&P500, 나스닥, 다우)

        해외지수 기간별시세 API(FHKST03030100) 사용.
        DOW는 KIS 지수 API 미지원 → DIA ETF(AMS) 가격 × 100 으로 근사.
        """
        today = datetime.now().strftime("%Y%m%d")
        yesterday = (datetime.now() - timedelta(days=4)).strftime("%Y%m%d")

        data = self._get(
            "/uapi/overseas-price/v1/quotations/inquire-daily-chartprice",
            "FHKST03030100",
            {
                "FID_COND_MRKT_DIV_CODE": "N",
                "FID_INPUT_ISCD": symbol,
                "FID_INPUT_DATE_1": yesterday,
                "FID_INPUT_DATE_2": today,
                "FID_PERIOD_DIV_CODE": "D",
            },
        )
        if not data or "output1" not in data:
            return None
        o = data["output1"]
        close = float(o.get("ovrs_nmix_prpr") or 0)
        change = float(o.get("prdy_ctrt") or 0)
        if not close:
            # DOW 등 지수 API 미지원 시 ETF 폴백
            if symbol == "DJI":
                return self._get_dow_from_etf()
            return None
        return {"close": close, "change": change}

    def _get_dow_from_etf(self) -> dict | None:
        """DIA ETF 가격으로 다우지수 근사 (DIA ≈ DOW / 100)"""
        price = self.get_us_stock_price("DIA", "AMS")
        if not price:
            return None
        return {
            "close": round(price["close"] * 100, 2),
            "change": price["change_rate"],
        }

    def get_usd_krw(self) -> float | None:
        """USD/KRW 환율 조회 (해외지수 기간별시세 API)"""
        today = datetime.now().strftime("%Y%m%d")
        yesterday = (datetime.now() - timedelta(days=4)).strftime("%Y%m%d")
        data = self._get(
            "/uapi/overseas-price/v1/quotations/inquire-daily-chartprice",
            "FHKST03030100",
            {
                "FID_COND_MRKT_DIV_CODE": "X",
                "FID_INPUT_ISCD": "FX@KRW",
                "FID_INPUT_DATE_1": yesterday,
                "FID_INPUT_DATE_2": today,
                "FID_PERIOD_DIV_CODE": "D",
            },
        )
        if not data or "output1" not in data:
            return None
        return float(data["output1"].get("ovrs_nmix_prpr") or 0) or None

    def get_us_market_data(self) -> dict:
        """미국 시장 전체 데이터 수집"""
        indices = {
            "sp500": ("SPX", "N"),
            "nasdaq": ("COMP", "N"),
            "dow": ("DJI", "N"),
        }
        result = {}
        for key, (symbol, excd) in indices.items():
            result[key] = self.get_us_index(symbol, excd)
            time.sleep(0.2)

        stocks = []
        for s in US_STOCKS:
            price = self.get_us_stock_price(s["ticker"], s["exchange"])
            if price:
                price["name"] = s["name"]
                stocks.append(price)
            time.sleep(0.2)

        result["stocks"] = stocks
        result["usd_krw"] = self.get_usd_krw()
        return result

    # ── 수급 (투자자별 매매동향) ──────────────────────

    def get_investor_trading(self) -> dict:
        """투자자별 매매동향 (외국인/기관 순매수 상위)"""
        today = datetime.now().strftime("%Y%m%d")
        result = {
            "foreign_buy_top": [],
            "foreign_sell_top": [],
            "institution_buy_top": [],
            "institution_sell_top": [],
        }

        # 외국인 순매수
        for cls_code, key in [("1", "foreign_buy_top"), ("2", "foreign_sell_top")]:
            data = self._get(
                "/uapi/domestic-stock/v1/quotations/inquire-investor",
                "FHPTJ04400000",
                {
                    "FID_COND_MRKT_DIV_CODE": "V",
                    "FID_COND_SCR_DIV_CODE": "16449",
                    "FID_INPUT_ISCD": "0000",
                    "FID_DIV_CLS_CODE": cls_code,
                    "FID_INPUT_DATE_1": today,
                    "FID_INPUT_DATE_2": today,
                    "FID_RANK_SORT_CLS_CODE": "0",
                },
            )
            if data and "output" in data:
                for item in data["output"][:10]:
                    result[key].append(
                        {
                            "code": item.get("mksc_shrn_iscd", ""),
                            "name": item.get("hts_kor_isnm", ""),
                            "net_buy": int(item.get("ntby_qty", 0)),
                        }
                    )
            time.sleep(0.2)

        # 기관 순매수
        for cls_code, key in [("3", "institution_buy_top"), ("4", "institution_sell_top")]:
            data = self._get(
                "/uapi/domestic-stock/v1/quotations/inquire-investor",
                "FHPTJ04400000",
                {
                    "FID_COND_MRKT_DIV_CODE": "V",
                    "FID_COND_SCR_DIV_CODE": "16449",
                    "FID_INPUT_ISCD": "0000",
                    "FID_DIV_CLS_CODE": cls_code,
                    "FID_INPUT_DATE_1": today,
                    "FID_INPUT_DATE_2": today,
                    "FID_RANK_SORT_CLS_CODE": "0",
                },
            )
            if data and "output" in data:
                for item in data["output"][:10]:
                    result[key].append(
                        {
                            "code": item.get("mksc_shrn_iscd", ""),
                            "name": item.get("hts_kor_isnm", ""),
                            "net_buy": int(item.get("ntby_qty", 0)),
                        }
                    )
            time.sleep(0.2)

        return result

    # ── 통합 수집 ─────────────────────────────────────

    def collect_all(self) -> dict:
        """전체 데이터 수집 (KR/수급은 KRX 백업 자동 전환)"""
        from .common import collect_with_fallback
        from .krx_collector import KRXCollector

        logger.info("KIS 데이터 수집 시작")
        krx = KRXCollector()
        kr = collect_with_fallback(self.get_kr_market_data, krx.get_kr_market_data, "KR시장")
        supply = collect_with_fallback(self.get_investor_trading, krx.get_investor_trading, "수급")
        us = self.get_us_market_data()  # 미국은 KIS만 가능, 백업 없음
        logger.info("KIS 데이터 수집 완료")
        return {"kr_market": kr, "us_market": us, "supply": supply}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    collector = KISCollector()
    data = collector.collect_all()
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))
