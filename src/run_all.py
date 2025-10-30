import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
import uvicorn

from .config import settings
from .handlers import build_router
from .admin.app import app as admin_app


async def start_bot():
	logging.basicConfig(level=logging.INFO)
	bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
	dp = Dispatcher()
	dp.include_router(build_router())
	await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


async def start_admin():
	config = uvicorn.Config(admin_app, host="192.168.1.59", port=8001, log_level="info", reload=False)
	server = uvicorn.Server(config)
	await server.serve()


async def main():
	task_bot = asyncio.create_task(start_bot())
	task_admin = asyncio.create_task(start_admin())
	await asyncio.gather(task_bot, task_admin)


if __name__ == "__main__":
	asyncio.run(main())
