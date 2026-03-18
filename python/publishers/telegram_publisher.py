"""텔레그램 봇 발송 모듈 — python-telegram-bot (async)"""

import logging
import os
from datetime import datetime
from pathlib import Path

from telegram import Bot
from telegram.constants import ParseMode
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "config" / ".env")

logger = logging.getLogger(__name__)


class TelegramPublisher:
    """텔레그램 채널 메시지 발송 (async)"""

    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    def _bot(self) -> Bot:
        return Bot(token=self.bot_token)

    async def send_message(self, text: str, blog_url: str = "") -> bool:
        """
        텔레그램 채널에 메시지 발송

        Args:
            text: 발송할 메시지 ({blog_url} 플레이스홀더 자동 치환)
            blog_url: 블로그 글 URL

        Returns:
            성공 여부
        """
        if not self.bot_token or not self.chat_id:
            logger.error("텔레그램 봇 토큰 또는 채팅 ID 미설정")
            return False

        text = text.replace("{blog_url}", blog_url)

        bot = self._bot()
        try:
            await bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
            )
            logger.info("텔레그램 발송 성공")
            return True
        except Exception as e:
            logger.error(f"텔레그램 발송 실패: {e}")
            return False

    async def send_error_alert(
        self, pipeline_name: str, error_msg: str
    ) -> bool:
        """
        에러 발생 시 텔레그램 알림

        Args:
            pipeline_name: 파이프라인 이름 (예: "아침 브리핑", "마감 리포트")
            error_msg: 에러 메시지

        Returns:
            성공 여부
        """
        if not self.bot_token or not self.chat_id:
            logger.error("텔레그램 봇 토큰 또는 채팅 ID 미설정 — 에러 알림 불가")
            return False

        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        text = (
            f"🚨 *주식 리포트 에러 발생*\n\n"
            f"파이프라인: {pipeline_name}\n"
            f"시간: {now}\n"
            f"에러: {error_msg}"
        )

        bot = self._bot()
        try:
            await bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN,
            )
            logger.info("에러 알림 발송 성공")
            return True
        except Exception as e:
            logger.error(f"에러 알림 발송도 실패: {e}")
            return False


if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)
    pub = TelegramPublisher()
    print(f"Bot token set: {bool(pub.bot_token)}")
    print(f"Chat ID set: {bool(pub.chat_id)}")
