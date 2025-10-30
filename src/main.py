import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from .config import settings
from .handlers import build_router


async def main() -> None:
	logging.basicConfig(level=logging.INFO)

	bot = Bot(
		token=settings.bot_token,
		default=DefaultBotProperties(parse_mode=ParseMode.HTML),
	)
	dp = Dispatcher()
	dp.include_router(build_router())

	await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
	asyncio.run(main())
