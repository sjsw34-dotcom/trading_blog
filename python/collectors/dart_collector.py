"""DART 공시 수집 모듈"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "config" / ".env")

logger = logging.getLogger(__name__)

BASE_URL = "https://opendart.fss.or.kr/api"

CATEGORY_KEYWORDS = {
    "유상증자": ["유상증자", "신주발행", "제3자배정"],
    "무상증자": ["무상증자", "주식배당"],
    "권리락": ["권리락", "신주인수권"],
    "전환사채": ["전환사채", "CB발행"],
    "합병분할": ["합병", "분할", "액면분할"],
    "대주주변동": ["대량보유", "지분변동", "최대주주"],
    "실적발표": ["영업실적", "매출액", "영업이익"],
}


class DARTCollector:
    """금융감독원 DART 공시 수집기"""

    def __init__(self):
        self.api_key = os.getenv("DART_API_KEY", "")

    def _classify(self, title: str) -> str:
        """공시 제목에서 카테고리 자동 분류"""
        for category, keywords in CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if kw in title:
                    return category
        return "기타"

    def get_disclosures(self, date: str | None = None) -> dict:
        """
        당일 전체 공시 목록 조회 + 카테고리 분류

        Args:
            date: 조회 날짜 (YYYYMMDD). None이면 오늘.

        Returns:
            {"total_count": int, "categories": {카테고리: [공시목록]}}
        """
        if date is None:
            date = datetime.now().strftime("%Y%m%d")

        all_items = []
        page = 1

        while True:
            try:
                resp = requests.get(
                    f"{BASE_URL}/list.json",
                    params={
                        "crtfc_key": self.api_key,
                        "bgn_de": date,
                        "end_de": date,
                        "page_count": 100,
                        "page_no": page,
                    },
                    timeout=15,
                )
                resp.raise_for_status()
                data = resp.json()

                if data.get("status") != "000":
                    logger.warning(f"DART API 오류: {data.get('message', '')}")
                    break

                items = data.get("list", [])
                if not items:
                    break

                all_items.extend(items)

                total_page = int(data.get("total_page", 1))
                if page >= total_page:
                    break
                page += 1

            except Exception as e:
                logger.error(f"DART 공시 조회 실패 (page {page}): {e}")
                break

        # 카테고리 분류
        categories: dict[str, list] = {}
        for item in all_items:
            title = item.get("report_nm", "")
            category = self._classify(title)
            if category == "기타":
                continue

            disclosure = {
                "corp_name": item.get("corp_name", ""),
                "title": title,
                "date": f"{date[:4]}-{date[4:6]}-{date[6:8]}",
                "url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={item.get('rcept_no', '')}",
            }
            categories.setdefault(category, []).append(disclosure)

        logger.info(
            f"DART 공시 수집 완료: 총 {len(all_items)}건, "
            f"분류 {sum(len(v) for v in categories.values())}건"
        )

        return {
            "total_count": len(all_items),
            "categories": categories,
        }

    def get_major_disclosures(self, date: str | None = None) -> dict:
        """주요사항보고만 필터링하여 조회"""
        if date is None:
            date = datetime.now().strftime("%Y%m%d")

        try:
            resp = requests.get(
                f"{BASE_URL}/list.json",
                params={
                    "crtfc_key": self.api_key,
                    "bgn_de": date,
                    "end_de": date,
                    "kind": "B",
                    "page_count": 100,
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") != "000":
                return {"total_count": 0, "items": []}

            items = []
            for item in data.get("list", []):
                items.append(
                    {
                        "corp_name": item.get("corp_name", ""),
                        "title": item.get("report_nm", ""),
                        "date": f"{date[:4]}-{date[4:6]}-{date[6:8]}",
                        "url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={item.get('rcept_no', '')}",
                        "category": self._classify(item.get("report_nm", "")),
                    }
                )

            return {"total_count": len(items), "items": items}

        except Exception as e:
            logger.error(f"DART 주요사항 조회 실패: {e}")
            return {"total_count": 0, "items": []}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    collector = DARTCollector()
    data = collector.get_disclosures()
    print(json.dumps(data, ensure_ascii=False, indent=2))
