import logging

logger = logging.getLogger(__name__)


def collect_with_fallback(primary_fn, backup_fn=None, name=""):
    """주 소스 실패 → 백업 소스 전환 → 둘 다 실패 → None 반환 + 로그"""
    try:
        data = primary_fn()
        if data:
            logger.info(f"[{name}] 주 소스 수집 성공")
            return data
    except Exception as e:
        logger.warning(f"[{name}] 주 소스 실패: {e}")

    if backup_fn:
        try:
            data = backup_fn()
            if data:
                logger.info(f"[{name}] 백업 소스 수집 성공")
                return data
        except Exception as e:
            logger.error(f"[{name}] 백업 소스도 실패: {e}")

    logger.error(f"[{name}] 모든 소스 실패 — 해당 섹션 스킵")
    return None
