"""공시 분류/포맷팅 모듈 — DART 공시 데이터를 블로그용으로 가공"""

import json
import logging

logger = logging.getLogger(__name__)

# 블로그 표시 우선순위 (높은 카테고리부터)
CATEGORY_PRIORITY = [
    "실적발표",
    "유상증자",
    "무상증자",
    "전환사채",
    "합병분할",
    "대주주변동",
    "권리락",
]


class DisclosureAnalyzer:
    """DART 공시 데이터를 블로그 출력용으로 포맷팅"""

    def analyze(self, disclosures: dict) -> dict:
        """
        dart_collector 출력을 블로그용으로 가공

        Args:
            disclosures: dart_collector.get_disclosures() 출력
                {"total_count": int, "categories": {카테고리: [공시목록]}}

        Returns:
            {
                "total_count": int,
                "summary": [{"category", "count", "items": [...]}],
                "highlights": [주요 공시 목록 (최대 10건)]
            }
        """
        if not disclosures or not disclosures.get("categories"):
            logger.warning("분석할 공시 데이터 없음")
            return {"total_count": 0, "summary": [], "highlights": []}

        categories = disclosures["categories"]
        total = disclosures.get("total_count", 0)

        # 카테고리별 정리 (우선순위 순)
        summary = []
        for cat in CATEGORY_PRIORITY:
            items = categories.get(cat, [])
            if items:
                summary.append({
                    "category": cat,
                    "count": len(items),
                    "items": items,
                })

        # 하이라이트: 각 카테고리 상위 항목 추출 (최대 10건)
        highlights = []
        for entry in summary:
            for item in entry["items"][:3]:
                highlights.append({
                    "category": entry["category"],
                    "corp_name": item["corp_name"],
                    "title": item["title"],
                    "url": item["url"],
                    "date": item.get("date", ""),
                })
                if len(highlights) >= 10:
                    break
            if len(highlights) >= 10:
                break

        logger.info(
            f"공시 분석 완료: {len(summary)}개 카테고리, "
            f"하이라이트 {len(highlights)}건"
        )
        return {
            "total_count": total,
            "summary": summary,
            "highlights": highlights,
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sample = {
        "total_count": 150,
        "categories": {
            "유상증자": [
                {"corp_name": "ABC기업", "title": "유상증자 결정", "date": "2026-03-18",
                 "url": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=12345"},
            ],
            "실적발표": [
                {"corp_name": "삼성전자", "title": "영업실적 공시", "date": "2026-03-18",
                 "url": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=67890"},
            ],
        },
    }
    analyzer = DisclosureAnalyzer()
    result = analyzer.analyze(sample)
    print(json.dumps(result, ensure_ascii=False, indent=2))
