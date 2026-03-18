"""테마 사전 초기 시드 데이터 입력 스크립트
참고자료의 테마 스케줄 데이터를 stock_themes 테이블에 INSERT
"""

import logging
from publishers.db_publisher import DBPublisher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── 테마 시드 데이터 ──────────────────────────────
# 주신 참고자료에서 추출한 주요 테마 + 관련 종목 + 키워드

SEED_THEMES = [
    {
        "name": "희토류",
        "description": "미-중, 일-중 분쟁용 테마. 바닥권일때 모아가면 늘 수익줌",
        "stocks": [
            {"code": "", "name": "유니온머티리얼"}, {"code": "", "name": "유니온"},
            {"code": "", "name": "노바텍"}, {"code": "", "name": "EG"},
            {"code": "", "name": "성안머티리얼스"}, {"code": "", "name": "현대비앤지스틸"},
            {"code": "", "name": "쎄노텍"}, {"code": "", "name": "고려아연"},
        ],
        "keywords": ["희토류", "중국 수출 규제", "핵심광물", "MP머티리얼스"],
        "importance": 4,
    },
    {
        "name": "원전 관련주",
        "description": "AI시대에 원전은 피할수 없음. 체코 원전 수출 이후 지속",
        "stocks": [
            {"code": "", "name": "두산에너빌리티"}, {"code": "", "name": "한전기술"},
            {"code": "", "name": "보성파워텍"}, {"code": "", "name": "우리기술"},
            {"code": "", "name": "우진"}, {"code": "", "name": "한전산업"},
            {"code": "", "name": "일진파워"}, {"code": "", "name": "태웅"},
        ],
        "keywords": ["원전", "SMR", "핵발전", "원자력", "체코 원전"],
        "importance": 5,
    },
    {
        "name": "로봇(산업/협동/휴머노이드)",
        "description": "휴머노이드 현실화 가능성에 미래가 밝음. 노란봉투법 수혜",
        "stocks": [
            {"code": "", "name": "레인보우로보틱스"}, {"code": "", "name": "두산로보틱스"},
            {"code": "", "name": "엔젤로보틱스"}, {"code": "", "name": "뉴로메카"},
            {"code": "", "name": "휴림로봇"}, {"code": "", "name": "현대무벡스"},
            {"code": "", "name": "계양전기"}, {"code": "", "name": "에스피지"},
        ],
        "keywords": ["로봇", "휴머노이드", "아틀라스", "보스턴다이내믹스", "테슬라 옵티머스", "피지컬AI"],
        "importance": 5,
    },
    {
        "name": "AI 반도체/HBM",
        "description": "AI시대에 반도체 수요 급증. 삼성전자·SK하이닉스 핵심",
        "stocks": [
            {"code": "", "name": "삼성전자"}, {"code": "", "name": "SK하이닉스"},
            {"code": "", "name": "한미반도체"}, {"code": "", "name": "피에스케이"},
            {"code": "", "name": "리노공업"}, {"code": "", "name": "이수페타시스"},
        ],
        "keywords": ["HBM", "반도체", "엔비디아", "AI칩", "필라델피아반도체"],
        "importance": 5,
    },
    {
        "name": "2차전지",
        "description": "중국 경쟁으로 힘들지만 휴머노이드·ESS로 제2의 전성기 가능",
        "stocks": [
            {"code": "", "name": "에코프로"}, {"code": "", "name": "에코프로비엠"},
            {"code": "", "name": "LG에너지솔루션"}, {"code": "", "name": "삼성SDI"},
            {"code": "", "name": "엔켐"}, {"code": "", "name": "포스코퓨처엠"},
        ],
        "keywords": ["2차전지", "배터리", "리튬", "ESS", "전기차 배터리"],
        "importance": 4,
    },
    {
        "name": "전기차",
        "description": "보조금 정책에 따라 왔다갔다. 테슬라 영향 큼",
        "stocks": [
            {"code": "", "name": "LG에너지솔루션"}, {"code": "", "name": "삼성SDI"},
            {"code": "", "name": "현대차"}, {"code": "", "name": "기아"},
            {"code": "", "name": "한온시스템"}, {"code": "", "name": "HL만도"},
        ],
        "keywords": ["전기차", "EV", "테슬라", "보조금", "충전"],
        "importance": 4,
    },
    {
        "name": "자율주행",
        "description": "미국·중국 주도, 현대차 포티투닷/모셔널 기대감",
        "stocks": [
            {"code": "", "name": "현대오토에버"}, {"code": "", "name": "넥스트칩"},
            {"code": "", "name": "아우토크립트"}, {"code": "", "name": "슈어소프트테크"},
            {"code": "", "name": "에스오에스랩"}, {"code": "", "name": "퓨런티어"},
        ],
        "keywords": ["자율주행", "로보택시", "FSD", "포티투닷", "모셔널"],
        "importance": 4,
    },
    {
        "name": "우주항공/스페이스X",
        "description": "스페이스X 상장 기대감. 누리호 발사 일정도 영향",
        "stocks": [
            {"code": "", "name": "켄코아에어로스페이스"}, {"code": "", "name": "쎄트렉아이"},
            {"code": "", "name": "나라스페이스테크놀로지"}, {"code": "", "name": "이노스페이스"},
            {"code": "", "name": "스피어"}, {"code": "", "name": "루미르"},
        ],
        "keywords": ["우주항공", "스페이스X", "누리호", "위성", "IPO 스페이스"],
        "importance": 5,
    },
    {
        "name": "방위산업/K방산",
        "description": "중립국 이미지+북한 대응 무기 수준으로 글로벌 K방산 부각",
        "stocks": [
            {"code": "", "name": "한화에어로스페이스"}, {"code": "", "name": "한화시스템"},
            {"code": "", "name": "현대로템"}, {"code": "", "name": "LIG넥스원"},
            {"code": "", "name": "한국항공우주"}, {"code": "", "name": "풍산"},
        ],
        "keywords": ["방산", "K방산", "무기 수출", "한화에어로", "현대로템", "K2전차"],
        "importance": 5,
    },
    {
        "name": "전력 설비",
        "description": "AI 데이터센터 전력 수요 급증. 인류가 멸망까지 꾸준함",
        "stocks": [
            {"code": "", "name": "LS ELECTRIC"}, {"code": "", "name": "HD현대일렉트릭"},
            {"code": "", "name": "효성중공업"}, {"code": "", "name": "일진전기"},
            {"code": "", "name": "산일전기"}, {"code": "", "name": "대한전선"},
        ],
        "keywords": ["전력", "변압기", "전선", "데이터센터 전력", "전력기기"],
        "importance": 5,
    },
    {
        "name": "스테이블코인",
        "description": "대통령이 밀고 있음. 원화 스테이블코인 제도화 기대",
        "stocks": [
            {"code": "", "name": "헥토파이낸셜"}, {"code": "", "name": "다날"},
            {"code": "", "name": "NHN KCP"}, {"code": "", "name": "한컴위드"},
            {"code": "", "name": "위메이드"}, {"code": "", "name": "카카오페이"},
        ],
        "keywords": ["스테이블코인", "원화 스테이블", "디지털자산", "STO", "토큰증권"],
        "importance": 4,
    },
    {
        "name": "가상화폐/비트코인",
        "description": "비트코인 가격에 연동. 스테이블코인에 위협받는 중",
        "stocks": [
            {"code": "", "name": "우리기술투자"}, {"code": "", "name": "한화투자증권"},
            {"code": "", "name": "다날"}, {"code": "", "name": "위지트"},
            {"code": "", "name": "티사이언티픽"}, {"code": "", "name": "비트맥스"},
        ],
        "keywords": ["비트코인", "가상화폐", "암호화폐", "업비트", "빗썸"],
        "importance": 3,
    },
    {
        "name": "바이오/제약",
        "description": "금리인하 호재. 알테오젠·삼천당제약 등 플랫폼 기업 주목",
        "stocks": [
            {"code": "", "name": "알테오젠"}, {"code": "", "name": "삼천당제약"},
            {"code": "", "name": "한미약품"}, {"code": "", "name": "셀트리온"},
            {"code": "", "name": "바이넥스"}, {"code": "", "name": "한올바이오파마"},
        ],
        "keywords": ["바이오", "제약", "신약", "기술이전", "JP모건 헬스케어"],
        "importance": 4,
    },
    {
        "name": "비만치료제",
        "description": "한국산 비만치료제 기대. 글로벌 시장 급성장",
        "stocks": [
            {"code": "", "name": "펩트론"}, {"code": "", "name": "지투지바이오"},
            {"code": "", "name": "인벤티지랩"}, {"code": "", "name": "디앤디파마텍"},
            {"code": "", "name": "올릭스"}, {"code": "", "name": "나이벡"},
        ],
        "keywords": ["비만치료", "위고비", "GLP-1", "비만약", "오젬픽"],
        "importance": 4,
    },
    {
        "name": "K뷰티/화장품",
        "description": "K엔터 최대 수혜. 독자적으로 세계 탑급",
        "stocks": [
            {"code": "", "name": "코스메카코리아"}, {"code": "", "name": "에이피알"},
            {"code": "", "name": "아모레퍼시픽"}, {"code": "", "name": "달바글로벌"},
            {"code": "", "name": "클래시스"}, {"code": "", "name": "케어젠"},
        ],
        "keywords": ["화장품", "K뷰티", "틱톡", "미용", "뷰티"],
        "importance": 4,
    },
    {
        "name": "엔터테인먼트/한한령",
        "description": "한한령 해제 기대감. 중국 시장 진출 가능성",
        "stocks": [
            {"code": "", "name": "에스엠"}, {"code": "", "name": "하이브"},
            {"code": "", "name": "JYP Ent."}, {"code": "", "name": "와이지엔터테인먼트"},
            {"code": "", "name": "키이스트"}, {"code": "", "name": "스튜디오드래곤"},
        ],
        "keywords": ["엔터", "한한령", "K팝", "BTS", "블랙핑크", "한류"],
        "importance": 4,
    },
    {
        "name": "양자암호/양자컴퓨팅",
        "description": "최근 뜨거운 테마. 정부 투자 + 글로벌 경쟁",
        "stocks": [
            {"code": "", "name": "아이씨티케이"}, {"code": "", "name": "아이윈플러스"},
            {"code": "", "name": "한국첨단소재"}, {"code": "", "name": "포톤"},
            {"code": "", "name": "라닉스"}, {"code": "", "name": "엑스게이트"},
        ],
        "keywords": ["양자", "양자컴퓨팅", "양자암호", "아이온큐", "큐비트"],
        "importance": 4,
    },
    {
        "name": "우크라이나 재건/모듈러주택",
        "description": "종전 기대감에 따라 움직임. 건설기계 포함",
        "stocks": [
            {"code": "", "name": "에스와이"}, {"code": "", "name": "금강공업"},
            {"code": "", "name": "덕신이피씨"}, {"code": "", "name": "엔알비"},
            {"code": "", "name": "HD현대건설기계"}, {"code": "", "name": "POSCO홀딩스"},
        ],
        "keywords": ["우크라이나", "종전", "재건", "모듈러", "휴전"],
        "importance": 4,
    },
    {
        "name": "남북경협",
        "description": "북미 대화 재개 시 움직임. 현재는 김정은 발언에 좌우",
        "stocks": [
            {"code": "", "name": "코데즈컴바인"}, {"code": "", "name": "좋은사람들"},
            {"code": "", "name": "인디에프"}, {"code": "", "name": "형지엘리트"},
            {"code": "", "name": "제이에스티나"}, {"code": "", "name": "현대건설"},
        ],
        "keywords": ["남북", "경협", "개성공단", "북미", "김정은"],
        "importance": 3,
    },
    {
        "name": "태양광/우주태양광",
        "description": "머스크 우주 태양광 비전 + 중국 제재 반사이익",
        "stocks": [
            {"code": "", "name": "한화솔루션"}, {"code": "", "name": "HD현대에너지솔루션"},
            {"code": "", "name": "OCI홀딩스"}, {"code": "", "name": "대주전자재료"},
            {"code": "", "name": "유니테스트"}, {"code": "", "name": "파루"},
        ],
        "keywords": ["태양광", "솔라", "페로브스카이트", "우주태양광"],
        "importance": 4,
    },
    {
        "name": "조선/K-조선",
        "description": "글로벌 수주 호황 + 미국 마스가 프로젝트",
        "stocks": [
            {"code": "", "name": "HD한국조선해양"}, {"code": "", "name": "한화오션"},
            {"code": "", "name": "삼성중공업"}, {"code": "", "name": "HD현대미포"},
            {"code": "", "name": "한화엔진"}, {"code": "", "name": "한국카본"},
        ],
        "keywords": ["조선", "LNG선", "마스가", "군함", "잠수함"],
        "importance": 5,
    },
    {
        "name": "건설/부동산",
        "description": "주택공급 정책 기대. 노란봉투법 리스크 있음",
        "stocks": [
            {"code": "", "name": "현대건설"}, {"code": "", "name": "대우건설"},
            {"code": "", "name": "GS건설"}, {"code": "", "name": "DL이앤씨"},
            {"code": "", "name": "HDC현대산업개발"}, {"code": "", "name": "삼성물산"},
        ],
        "keywords": ["건설", "부동산", "재건축", "주택공급", "PF"],
        "importance": 3,
    },
    {
        "name": "게임",
        "description": "한한령 해제로 중국 진출 가능. 신작 모멘텀",
        "stocks": [
            {"code": "", "name": "크래프톤"}, {"code": "", "name": "넷마블"},
            {"code": "", "name": "엔씨소프트"}, {"code": "", "name": "펄어비스"},
            {"code": "", "name": "위메이드"}, {"code": "", "name": "카카오게임즈"},
        ],
        "keywords": ["게임", "신작", "출시", "모바일게임"],
        "importance": 3,
    },
    {
        "name": "리튬",
        "description": "2차전지 원자재. 가격 반등 시 더 강하게 움직임",
        "stocks": [
            {"code": "", "name": "에코프로"}, {"code": "", "name": "하이드로리튬"},
            {"code": "", "name": "강원에너지"}, {"code": "", "name": "POSCO홀딩스"},
            {"code": "", "name": "미래나노텍"}, {"code": "", "name": "포스코퓨처엠"},
        ],
        "keywords": ["리튬", "탄산리튬", "수산화리튬", "리튬 가격"],
        "importance": 4,
    },
]

# ── 테마 스케줄 시드 데이터 ────────────────────────

SEED_SCHEDULES = [
    {"date": None, "text": "2026년 빗썸 IPO", "themes": ["가상화폐/비트코인"], "stocks": ["비덴트", "위지트", "티사이언티픽"], "importance": 4},
    {"date": None, "text": "2026년 2분기 업비트 상장", "themes": ["가상화폐/비트코인", "스테이블코인"], "stocks": ["우리기술투자", "한화투자증권", "DSC인베스트먼트", "바른손"], "importance": 5},
    {"date": None, "text": "2026년 3분기 마켓컬리 상장", "themes": [], "stocks": ["DSC인베스트먼트", "미래에셋벤처투자", "흥국에프엔비"], "importance": 3},
    {"date": None, "text": "2026년 리벨리온 상장", "themes": ["AI 반도체/HBM"], "stocks": ["SV인베스트먼트", "미래에셋벤처투자", "DB하이텍"], "importance": 4},
    {"date": None, "text": "2026년 토스 미국 상장", "themes": [], "stocks": ["한국전자인증", "한글과컴퓨터", "위지트"], "importance": 3},
    {"date": None, "text": "2026년 하반기 무신사 상장", "themes": ["K뷰티/화장품"], "stocks": ["DSC인베스트먼트", "LB인베스트먼트"], "importance": 3},
    {"date": None, "text": "2026년 스페이스X IPO (6월 추진)", "themes": ["우주항공/스페이스X"], "stocks": ["미래에셋벤처투자", "미래에셋증권", "켄코아에어로스페이스"], "importance": 5},
]


def main():
    db = DBPublisher()

    # 테마 사전 시드
    logger.info(f"=== 테마 사전 시드 입력 시작: {len(SEED_THEMES)}개 ===")
    for t in SEED_THEMES:
        db.upsert_theme({
            "name": t["name"],
            "description": t["description"],
            "stocks": t["stocks"],
            "keywords": t["keywords"],
            "importance": t["importance"],
            "status": "active",
        })

    # 테마 스케줄 시드
    logger.info(f"=== 테마 스케줄 시드 입력: {len(SEED_SCHEDULES)}개 ===")
    for s in SEED_SCHEDULES:
        db.save_schedule(s)

    # 확인
    themes = db.get_active_themes()
    logger.info(f"DB 테마 사전: {len(themes)}개 등록됨")
    for t in themes[:5]:
        logger.info(f"  {t['name']} (중요도:{t['importance']}, 횟수:{t['hit_count']})")

    schedules = db.get_upcoming_schedules(days=365)
    logger.info(f"DB 테마 스케줄: {len(schedules)}개 등록됨")


if __name__ == "__main__":
    main()
