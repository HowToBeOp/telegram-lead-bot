import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeChat

from config import load_config
from database import Database
from handlers.admin import create_admin_router
from handlers.user import create_user_router


async def set_bot_commands(bot: Bot, admin_id: int) -> None:
    user_commands = [BotCommand(command="start", description="Оставить заявку")]
    admin_commands = [
        *user_commands,
        BotCommand(command="admin", description="Статистика заявок"),
        BotCommand(command="leads", description="Последние заявки"),
    ]

    await bot.set_my_commands(user_commands)
    await bot.set_my_commands(
        admin_commands,
        scope=BotCommandScopeChat(chat_id=admin_id),
    )


async def main() -> None:
    config = load_config()
    database = Database("leads.db")
    database.initialize()

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher()
    dispatcher.include_router(create_admin_router(config.admin_id, database))
    dispatcher.include_router(create_user_router(config.admin_id, database))

    try:
        await bot.delete_webhook(drop_pending_updates=False)
        await set_bot_commands(bot, config.admin_id)
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")
