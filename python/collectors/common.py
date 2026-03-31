import logging

logger = logging.getLogger(__name__)


def _is_supply_empty(data: dict) -> bool:
    """수급 데이터가 비어있는지 확인 (dict인데 모든 리스트가 비어있으면 빈 것)"""
    if not isinstance(data, dict):
        return not data
    list_values = [v for v in data.values() if isinstance(v, list)]
    if list_values and all(len(v) == 0 for v in list_values):
        return True
    return False


def collect_with_fallback(primary_fn, backup_fn=None, name=""):
    """주 소스 실패 → 백업 소스 전환 → 둘 다 실패 → None 반환 + 로그"""
    try:
        data = primary_fn()
        if data and not _is_supply_empty(data):
            logger.info(f"[{name}] 주 소스 수집 성공")
            return data
        else:
            logger.warning(f"[{name}] 주 소스 결과 비어있음 → 백업 시도")
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
