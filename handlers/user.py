import logging
from html import escape
from typing import Any

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from database import Database
from keyboards.inline import confirmation_keyboard, services_keyboard
from keyboards.reply import cancel_keyboard, contact_keyboard


logger = logging.getLogger(__name__)

SERVICES = {
    "consultation": "Консультация",
    "repair": "Ремонт",
    "other": "Другое",
}

CANCEL_TEXT = "❌ Отменить"


class LeadForm(StatesGroup):
    name = State()
    contact = State()
    comment = State()
    confirmation = State()


def _clean_text(message: Message, max_length: int) -> str | None:
    if not message.text:
        return None
    value = message.text.strip()
    if not value or len(value) > max_length:
        return None
    return value


def _confirmation_text(lead: dict[str, Any]) -> str:
    return (
        "<b>Проверьте заявку:</b>\n\n"
        f"<b>Услуга:</b> {escape(str(lead['service']))}\n"
        f"<b>Имя:</b> {escape(str(lead['name']))}\n"
        f"<b>Контакт:</b> {escape(str(lead['contact']))}\n"
        f"<b>Комментарий:</b> {escape(str(lead['comment']))}"
    )


def _admin_notification_text(lead: dict[str, Any]) -> str:
    username = f"@{escape(lead['username'])}" if lead.get("username") else "—"
    return (
        "<b>📩 Новая заявка</b>\n\n"
        f"<b>Услуга:</b> {escape(str(lead['service']))}\n"
        f"<b>Имя:</b> {escape(str(lead['name']))}\n"
        f"<b>Контакт:</b> {escape(str(lead['contact']))}\n"
        f"<b>Комментарий:</b> {escape(str(lead['comment']))}\n"
        f"<b>Telegram:</b> {username}\n"
        f"<b>Telegram ID:</b> {lead['telegram_user_id']}\n"
        f"<b>Дата и время (UTC):</b> {escape(str(lead['created_at']))}"
    )


def create_user_router(admin_id: int, database: Database) -> Router:
    router = Router(name="user")

    async def show_cancelled(message: Message, state: FSMContext) -> None:
        await state.clear()
        await message.answer("Заявка отменена.", reply_markup=ReplyKeyboardRemove())
        await message.answer(
            "Выберите услугу, чтобы создать новую заявку:",
            reply_markup=services_keyboard(),
        )

    @router.message(CommandStart())
    async def start(message: Message, state: FSMContext) -> None:
        await state.clear()
        await message.answer(
            "Здравствуйте! 👋\n"
            "Оставьте заявку, и мы свяжемся с вами.\n\n"
            "Выберите интересующую услугу:",
            reply_markup=services_keyboard(),
        )

    @router.message(Command("cancel"))
    async def cancel_command(message: Message, state: FSMContext) -> None:
        current_state = await state.get_state()
        if current_state:
            await show_cancelled(message, state)
        else:
            await message.answer(
                "Сейчас нет активной заявки. Выберите услугу:",
                reply_markup=services_keyboard(),
            )

    @router.message(
        StateFilter(
            LeadForm.name,
            LeadForm.contact,
            LeadForm.comment,
            LeadForm.confirmation,
        ),
        F.text == CANCEL_TEXT,
    )
    async def cancel_by_button(message: Message, state: FSMContext) -> None:
        await show_cancelled(message, state)

    @router.callback_query(F.data.startswith("service:"))
    async def choose_service(callback: CallbackQuery, state: FSMContext) -> None:
        service_key = callback.data.split(":", maxsplit=1)[1] if callback.data else ""
        service = SERVICES.get(service_key)
        if not service:
            await callback.answer("Неизвестная услуга.", show_alert=True)
            return

        await state.clear()
        await state.update_data(service=service)
        await state.set_state(LeadForm.name)
        await callback.answer()
        if callback.message:
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.answer(
                "Как вас зовут?",
                reply_markup=cancel_keyboard(),
            )

    @router.message(LeadForm.name)
    async def receive_name(message: Message, state: FSMContext) -> None:
        name = _clean_text(message, 100)
        if not name:
            await message.answer("Введите имя — от 1 до 100 символов.")
            return

        await state.update_data(name=name)
        await state.set_state(LeadForm.contact)
        await message.answer(
            "Укажите номер телефона или имя пользователя Telegram в формате @username.\n"
            "Также можно поделиться номером с помощью кнопки ниже:",
            reply_markup=contact_keyboard(),
        )

    @router.message(LeadForm.contact)
    async def receive_contact(message: Message, state: FSMContext) -> None:
        if message.contact:
            contact = message.contact.phone_number.strip()
        else:
            contact = _clean_text(message, 100)

        if not contact:
            await message.answer(
                "Укажите номер телефона, @username или нажмите «Поделиться номером телефона»."
            )
            return

        await state.update_data(contact=contact)
        await state.set_state(LeadForm.comment)
        await message.answer(
            "Кратко опишите, что вам требуется:",
            reply_markup=cancel_keyboard(),
        )

    @router.message(LeadForm.comment)
    async def receive_comment(message: Message, state: FSMContext) -> None:
        comment = _clean_text(message, 1000)
        if not comment:
            await message.answer("Введите описание — от 1 до 1000 символов.")
            return

        await state.update_data(comment=comment)
        data = await state.get_data()
        await state.set_state(LeadForm.confirmation)
        await message.answer(
            "Проверьте данные перед отправкой.",
            reply_markup=ReplyKeyboardRemove(),
        )
        await message.answer(
            _confirmation_text(data),
            reply_markup=confirmation_keyboard(),
        )

    @router.callback_query(LeadForm.confirmation, F.data == "lead:cancel")
    async def cancel_lead(callback: CallbackQuery, state: FSMContext) -> None:
        await callback.answer("Заявка отменена")
        if callback.message:
            await callback.message.edit_reply_markup(reply_markup=None)
            await show_cancelled(callback.message, state)
        else:
            await state.clear()

    @router.callback_query(LeadForm.confirmation, F.data == "lead:submit")
    async def submit_lead(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
        user = callback.from_user
        data = await state.get_data()
        required = ("service", "name", "contact", "comment")
        if any(not data.get(field) for field in required):
            await state.clear()
            await callback.answer(
                "Форма устарела. Создайте новую заявку.", show_alert=True
            )
            if callback.message:
                await callback.message.edit_reply_markup(reply_markup=None)
            return

        try:
            lead = database.add_lead(
                telegram_user_id=user.id,
                username=user.username,
                service=data["service"],
                name=data["name"],
                contact=data["contact"],
                comment=data["comment"],
            )
        except Exception:
            logger.exception("Не удалось сохранить заявку пользователя Telegram %s", user.id)
            await callback.answer(
                "Не удалось сохранить заявку. Попробуйте ещё раз.", show_alert=True
            )
            return

        await state.clear()
        await callback.answer("Заявка отправлена")
        if callback.message:
            await callback.message.edit_reply_markup(reply_markup=None)

        try:
            await bot.send_message(admin_id, _admin_notification_text(lead))
        except TelegramAPIError:
            logger.exception(
                "Заявка %s сохранена, но уведомление администратору не отправлено",
                lead["id"],
            )

        if callback.message:
            await callback.message.answer(
                "Спасибо! Ваша заявка успешно отправлена. Мы свяжемся с вами."
            )

    return router
