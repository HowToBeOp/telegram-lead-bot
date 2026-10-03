import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_id: int


def load_config() -> Config:
    load_dotenv()

    bot_token = os.getenv("BOT_TOKEN", "").strip()
    admin_id_value = os.getenv("ADMIN_ID", "").strip()

    if not bot_token:
        raise RuntimeError("BOT_TOKEN не задан. Добавьте его в файл .env.")

    try:
        admin_id = int(admin_id_value)
    except ValueError as error:
        raise RuntimeError("ADMIN_ID должен быть числовым Telegram ID.") from error

    if admin_id <= 0:
        raise RuntimeError("ADMIN_ID должен быть положительным целым числом.")

    return Config(bot_token=bot_token, admin_id=admin_id)
