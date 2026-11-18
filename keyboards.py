from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def main_menu():
    kb = [
        [KeyboardButton(text="💸 Добавить запись"), KeyboardButton(text="💰 Баланс")],
        [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="📋 Мои категории")],
        [KeyboardButton(text="➕ Добавить категорию"), KeyboardButton(text="🗑 Удалить категорию")],
        [KeyboardButton(text="⚠️ Сбросить данные"), KeyboardButton(text="❓ Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def cancel_keyboard():
    kb = [
        [KeyboardButton(text="🔙 Назад"), KeyboardButton(text="🏠 Главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def category_type_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🟥 Расход", callback_data="type_expense")
    builder.button(text="🟩 Доход", callback_data="type_income")
    builder.button(text="🔙 Назад", callback_data="back_to_menu")
    builder.button(text="🏠 Главное меню", callback_data="go_main_menu")
    builder.adjust(2, 2)
    return builder.as_markup()

def make_categories_keyboard(categories):
    builder = InlineKeyboardBuilder()
    for cat in categories:
        icon = "🟥" if cat.type == "expense" else "🟩"
        builder.button(text=f"{icon} {cat.name}", callback_data=f"selcat_{cat.id}")
    builder.adjust(2)
    return builder.as_markup()

def after_transaction_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 К выбору категорий", callback_data="back_to_categories")
    builder.button(text="🏠 Главное меню", callback_data="go_main_menu")
    builder.adjust(1, 1)
    return builder.as_markup()

def categories_view_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 Главное меню", callback_data="go_main_menu")
    return builder.as_markup()

def make_delete_categories_keyboard(categories):
    builder = InlineKeyboardBuilder()
    for cat in categories:
        icon = "🟥" if cat.type == "expense" else "🟩"
        builder.button(text=f"❌ {icon} {cat.name}", callback_data=f"delcat_{cat.id}")
    builder.button(text="🔙 Назад", callback_data="back_to_menu")
    builder.button(text="🏠 Главное меню", callback_data="go_main_menu")
    builder.adjust(2)
    return builder.as_markup()

def welcome_inline_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📖 Инструкция", callback_data="show_instruction")
    builder.adjust(1)
    return builder.as_markup()
