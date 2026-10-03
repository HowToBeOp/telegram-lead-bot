from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def services_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Консультация", callback_data="service:consultation")],
            [InlineKeyboardButton(text="Ремонт", callback_data="service:repair")],
            [InlineKeyboardButton(text="Другое", callback_data="service:other")],
        ]
    )


def confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Отправить", callback_data="lead:submit"),
                InlineKeyboardButton(text="❌ Отменить", callback_data="lead:cancel"),
            ]
        ]
    )
