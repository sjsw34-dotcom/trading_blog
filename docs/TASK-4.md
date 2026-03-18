# TASK-4: 텔레그램 봇 구현

> 먼저 `docs/COMMON.md`를 읽을 것. TASK-1~3이 완성된 상태에서 진행.

---

## 목표

`python/publishers/telegram_publisher.py` 구현 + 텔레그램 채널 설정 가이드.

---

## 1. telegram_publisher.py

### 기능
- 텔레그램 채널에 리포트 요약 메시지 자동 발송
- 성공/실패 시 알림 발송 (에러 시 에러 로그 포함)
- 마크다운 포맷 지원

### 구현

```python
import os
import logging
from telegram import Bot
from telegram.constants import ParseMode

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

async def send_message(text: str):
    """텔레그램 채널에 메시지 발송"""
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    try:
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=text,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )
        logger.info("텔레그램 발송 성공")
    except Exception as e:
        logger.error(f"텔레그램 발송 실패: {e}")

async def send_error_alert(error_msg: str):
    """에러 발생 시 텔레그램 알림"""
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    text = f"🚨 *주식 리포트 에러 발생*\n\n{error_msg}"
    try:
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=text,
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        logger.error(f"에러 알림 발송도 실패: {e}")
```

---

## 2. 메시지 포맷

### 아침 7시 브리핑
```
🇺🇸 3/18 미국장 마감
S&P500 5,638 (-0.7%) | 나스닥 17,844 (-1.2%)
테슬라 -2.1% | 엔비디아 +1.3%
USD/KRW 1,342원 | WTI $78.2

📌 트럼프, 중국산 반도체 추가관세 예고

전체 리포트 → https://사이트URL/report/2026-03-18
```

### 마감 리포트
```
📊 3/18 장 마감
KOSPI 2,847 (+1.2%) | KOSDAQ 892 (-0.3%)
🔥 상승1위 두산에너빌리티 +8.3% (원전 수출)
📉 하락1위 에코프로비엠 -4.2% (EU 보조금 축소)
외국인 +2,340억 | 기관 -1,200억

전체 리포트 → https://사이트URL/report/2026-03-18
```

### 에러 알림
```
🚨 *주식 리포트 에러 발생*

파이프라인: 마감 리포트
시간: 2026-03-18 15:50
에러: KIS API 인증 실패 — 토큰 만료
```

---

## 3. main 파이프라인에 통합

main_morning.py, main_closing.py의 마지막 단계에서:

```python
import asyncio

# 성공 시
asyncio.run(telegram_publisher.send_message(telegram_summary))

# 에러 시 (try-except 블록 내)
asyncio.run(telegram_publisher.send_error_alert(f"파이프라인: {pipeline_name}\n에러: {str(e)}"))
```

---

## 4. 텔레그램 채널 설정 가이드

### BotFather에서 봇 생성
1. 텔레그램에서 @BotFather 검색
2. `/newbot` 명령어
3. 봇 이름 설정 (예: KR Stock Daily Bot)
4. 봇 username 설정 (예: kr_stock_daily_bot)
5. 발급된 토큰을 TELEGRAM_BOT_TOKEN에 저장

### 채널 생성
1. 텔레그램에서 새 채널 생성
2. 채널 이름: "주식 일일 리포트" (또는 원하는 이름)
3. 공개 채널로 설정 (구독자 모집 위해)
4. 채널 설정 → 관리자 → 봇을 관리자로 추가
5. 채널 ID 확인: 채널에 아무 메시지 보낸 후 `https://api.telegram.org/bot{TOKEN}/getUpdates`로 chat_id 확인

### GitHub Secrets 설정
```
TELEGRAM_BOT_TOKEN: 봇 토큰
TELEGRAM_CHAT_ID: 채널 ID (보통 -100으로 시작)
```

---

## 완료 기준

- [ ] telegram_publisher.py: 메시지 발송 동작
- [ ] send_error_alert: 에러 알림 발송 동작
- [ ] main_morning.py에 텔레그램 발송 통합
- [ ] main_closing.py에 텔레그램 발송 통합
- [ ] 에러 발생 시 텔레그램 에러 알림 동작
- [ ] 텔레그램 설정 가이드 문서 포함
