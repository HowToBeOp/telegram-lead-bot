from html import escape
from typing import Any

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from database import Database


def _short_lead(lead: dict[str, Any]) -> str:
    username = f"@{escape(lead['username'])}" if lead.get("username") else "—"
    comment = str(lead["comment"])
    if len(comment) > 300:
        comment = comment[:297] + "..."
    return (
        f"<b>#{lead['id']} · {escape(str(lead['service']))}</b>\n"
        f"Имя: {escape(str(lead['name']))}\n"
        f"Контакт: {escape(str(lead['contact']))}\n"
        f"Telegram: {username} (ID: {lead['telegram_user_id']})\n"
        f"Комментарий: {escape(comment)}\n"
        f"Дата и время (UTC): {escape(str(lead['created_at']))}"
    )


async def _send_lead_blocks(message: Message, heading: str, leads: list[dict[str, Any]]) -> None:
    if not leads:
        await message.answer(f"<b>{heading}</b>\n\nЗаявок пока нет.")
        return

    chunks: list[str] = []
    current = f"<b>{heading}</b>\n\n"
    for lead in leads:
        block = _short_lead(lead)
        addition = block if current.endswith("\n\n") else f"\n\n{block}"
        if len(current) + len(addition) > 3900:
            chunks.append(current)
            current = block
        else:
            current += addition
    chunks.append(current)

    for chunk in chunks:
        await message.answer(chunk)


def create_admin_router(admin_id: int, database: Database) -> Router:
    router = Router(name="admin")

    def is_admin(message: Message) -> bool:
        return bool(message.from_user and message.from_user.id == admin_id)

    @router.message(Command("admin"))
    async def admin_dashboard(message: Message) -> None:
        if not is_admin(message):
            await message.answer("Эта команда доступна только администратору.")
            return

        total = database.count_leads()
        today = database.count_leads_today()
        leads = database.get_recent_leads(5)
        await message.answer(
            "<b>Статистика заявок</b>\n\n"
            f"Всего заявок: <b>{total}</b>\n"
            f"Заявок сегодня: <b>{today}</b>"
        )
        await _send_lead_blocks(message, "Последние 5 заявок", leads)

    @router.message(Command("leads"))
    async def recent_leads(message: Message) -> None:
        if not is_admin(message):
            await message.answer("Эта команда доступна только администратору.")
            return

        await _send_lead_blocks(
            message, "Последние 10 заявок", database.get_recent_leads(10)
        )

    return router
