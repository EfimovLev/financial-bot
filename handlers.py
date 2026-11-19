import os
import re
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, func, and_, delete

from database import async_session_maker, get_or_create_user, Category, Transaction, User
from keyboards import (
    main_menu,
    cancel_keyboard,
    cancel_feedback_kb,
    category_type_keyboard,
    make_categories_keyboard,
    after_transaction_keyboard,
    categories_view_keyboard,
    make_delete_categories_keyboard,
    welcome_inline_keyboard
)
from states import CategoryStates, TransactionStates, FeedbackStates

router = Router()
FEEDBACK_CHAT_ID = int(os.getenv("FEEDBACK_CHAT_ID", "0"))


@router.message(CommandStart())
async def cmd_start(message: Message):
    async with async_session_maker() as session:
        await get_or_create_user(session, message.from_user.id)

    await message.answer(
        "👋 Привет! Добро пожаловать в твой бот для учета личных финансов.",
        reply_markup=main_menu()
    )
    await message.answer(
        "Нажми на кнопку ниже, чтобы ознакомиться с инструкцией:",
        reply_markup=welcome_inline_keyboard()
    )


@router.message(F.text == "🏠 Главное меню")
async def text_main_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🏠 **Главное меню**\nВыберите нужное действие:",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )


@router.message(F.text == "🔙 Назад")
async def cancel_action(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Действие отменено.\n\n🏠 **Главное меню**:",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "go_main_menu")
async def callback_go_main_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🏠 Возврат в главное меню.")
    await callback.message.answer(
        "🏠 **Главное меню**\nВыберите действие:",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Действие отменено.")
    await callback.message.answer(
        "🏠 **Главное меню**:",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "show_instruction")
async def process_instruction_callback(callback: CallbackQuery):
    instruction_text = (
        "📖 **Инструкция по использованию бота:**\n\n"
        "1. **Добавление записи:** Нажми **«💸 Добавить запись»**, выбери категорию и введи сумму цифрами.\n"
        "2. **Управление категориями:** Просматривай список («📋 Мои категории»), добавляй новые («➕ Добавить категорию») или удаляй ненужные («🗑 Удалить категорию»).\n"
        "3. **Сброс данных:** Кнопка «⚠️ Сбросить данные» позволяет полностью обнулить баланс и историю.\n"
        "4. **Навигация:** Используй кнопки **«🔙 Назад»** и **«🏠 Главное меню»** для быстрого перемещения."
    )
    await callback.message.edit_text(instruction_text, parse_mode="Markdown")
    await callback.answer()


@router.message(F.text == "❓ Помощь")
async def cmd_help(message: Message):
    await message.answer(
        "📖 **Справка:**\n\n"
        "• Запись расходов/доходов происходит через кнопку **«💸 Добавить запись»**.\n"
        "• Категории можно создавать и удалять в соответствующих разделах меню.\n"
        "• Используй кнопку **🏠 Главное меню** для возврата к основным разделам.",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )


@router.message(F.text == "💰 Баланс")
async def show_balance(message: Message):
    async with async_session_maker() as session:
        user = await get_or_create_user(session, message.from_user.id)
        await message.answer(f"💳 Текущий баланс основного счета: **{user.balance:,.2f} руб.**", parse_mode="Markdown")


@router.message(F.text == "📋 Мои категории")
async def show_user_categories(message: Message):
    user_id = message.from_user.id
    async with async_session_maker() as session:
        stmt = select(Category).where(Category.user_id == user_id)
        res = await session.execute(stmt)
        categories = res.scalars().all()

    expenses = [c.name for c in categories if c.type == "expense"]
    incomes = [c.name for c in categories if c.type == "income"]

    text = "📋 **Ваши доступные категории:**\n\n"
    text += "🟥 **Расходы:**\n" + (", ".join(expenses) if expenses else "нет") + "\n\n"
    text += "🟩 **Доходы:**\n" + (", ".join(incomes) if incomes else "нет") + "\n\n"

    await message.answer(text, reply_markup=categories_view_keyboard(), parse_mode="Markdown")


@router.message(F.text == "💸 Добавить запись")
async def start_transaction(message: Message):
    user_id = message.from_user.id
    async with async_session_maker() as session:
        stmt = select(Category).where(Category.user_id == user_id)
        res = await session.execute(stmt)
        categories = res.scalars().all()

    if not categories:
        await message.answer("У вас пока нет категорий. Сначала добавьте их через кнопку «➕ Добавить категорию».")
        return

    await message.answer(
        "📂 Выберите категорию для транзакции:",
        reply_markup=make_categories_keyboard(categories)
    )


@router.callback_query(F.data.startswith("selcat_"))
async def category_selected(callback: CallbackQuery, state: FSMContext):
    cat_id = int(callback.data.split("_")[1])
    async with async_session_maker() as session:
        category = await session.get(Category, cat_id)
        if not category:
            await callback.answer("Категория не найдена!", show_alert=True)
            return

        await state.update_data(category_name=category.name, category_type=category.type)
        await state.set_state(TransactionStates.waiting_for_amount)

        await callback.message.edit_text(
            f"Вы выбрали категорию: **{category.name}**\n\n"
            f"💵 Введите сумму цифрами (например: `350` или `1500`):",
            parse_mode="Markdown"
        )
        await callback.answer()


@router.callback_query(F.data == "back_to_categories")
async def back_to_categories_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    async with async_session_maker() as session:
        stmt = select(Category).where(Category.user_id == user_id)
        res = await session.execute(stmt)
        categories = res.scalars().all()

    if not categories:
        await callback.message.edit_text("У вас пока нет категорий.")
        return

    await callback.message.edit_text(
        "📂 Выберите категорию для транзакции:",
        reply_markup=make_categories_keyboard(categories)
    )
    await callback.answer()


@router.message(TransactionStates.waiting_for_amount)
async def process_amount_input(message: Message, state: FSMContext):
    text_amount = message.text.replace(",", ".").strip()
    try:
        amount = float(text_amount)
        if amount <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректное положительное число или воспользуйтесь кнопкой отмены.")
        return

    data = await state.get_data()
    category_name = data["category_name"]
    t_type = data["category_type"]
    user_id = message.from_user.id

    async with async_session_maker() as session:
        user = await get_or_create_user(session, user_id)

        if t_type == "expense":
            user.balance -= amount
            sign_str = "-"
            type_label = "Расход 📉"
        else:
            user.balance += amount
            sign_str = "+"
            type_label = "Доход 📈"

        tx = Transaction(
            user_id=user_id,
            amount=amount,
            type=t_type,
            category=category_name
        )
        session.add(tx)
        await session.commit()
        current_balance = user.balance

    await state.clear()
    await message.answer(
        f"✅ Успешно записано:\n"
        f"• Тип: {type_label}\n"
        f"• Сумма: {sign_str}{amount:,.2f} руб.\n"
        f"• Категория: {category_name}\n\n"
        f"💳 Баланс: {current_balance:,.2f} руб.",
        reply_markup=after_transaction_keyboard(),
        parse_mode="Markdown"
    )


@router.message(F.text == "🗑 Удалить категорию")
async def start_delete_category(message: Message):
    user_id = message.from_user.id
    async with async_session_maker() as session:
        stmt = select(Category).where(Category.user_id == user_id)
        res = await session.execute(stmt)
        categories = res.scalars().all()

    if not categories:
        await message.answer("У вас нет категорий для удаления.")
        return

    await message.answer(
        "🗑 Выберите категорию, которую хотите **удалить**:",
        reply_markup=make_delete_categories_keyboard(categories),
        parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("delcat_"))
async def process_delete_category(callback: CallbackQuery):
    cat_id = int(callback.data.split("_")[1])
    async with async_session_maker() as session:
        category = await session.get(Category, cat_id)
        if not category:
            await callback.answer("Категория не найдена или уже удалена!", show_alert=True)
            return

        cat_name = category.name
        await session.delete(category)
        await session.commit()

    await callback.message.edit_text(
        f"🗑 Категория **'{cat_name}'** успешно удалена!",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(F.text == "⚠️ Сбросить данные")
async def reset_data_request(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, сбросить всё", callback_data="confirm_reset"),
         InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_reset")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="go_main_menu")]
    ])
    await message.answer(
        "⚠️ **Внимание!** Вы собираетесь сбросить все данные:\n"
        "• Баланс обнулится.\n"
        "• Все транзакции будут удалены.\n"
        "• Категории вернутся к стандартному набору.\n\n"
        "Вы уверены?",
        reply_markup=kb,
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "confirm_reset")
async def confirm_reset_data(callback: CallbackQuery):
    user_id = callback.from_user.id
    async with async_session_maker() as session:
        await session.execute(delete(Transaction).where(Transaction.user_id == user_id))
        await session.execute(delete(Category).where(Category.user_id == user_id))

        user = await session.get(User, user_id)
        if user:
            user.balance = 0.0

        defaults = [
            ("Продукты", "expense"), ("Транспорт", "expense"),
            ("Жилье", "expense"), ("Развлечения", "expense"), ("Кафе", "expense"),
            ("Зарплата", "income")
        ]
        for name, ctype in defaults:
            cat = Category(name=name, type=ctype, user_id=user_id)
            session.add(cat)

        await session.commit()

    await callback.message.edit_text(
        "🔄 Все данные успешно сброшены! Баланс обнулен, категории восстановлены до начальных.",
        parse_mode="Markdown"
    )
    await callback.message.answer(
        "🏠 **Главное меню**:",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "cancel_reset")
async def cancel_reset_data(callback: CallbackQuery):
    await callback.message.edit_text("❌ Сброс данных отменен.")
    await callback.message.answer(
        "🏠 **Главное меню**:",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(F.text == "➕ Добавить категорию")
async def start_add_category(message: Message, state: FSMContext):
    await state.set_state(CategoryStates.waiting_for_name)
    await message.answer("Введите название новой категории:", reply_markup=cancel_keyboard())


@router.message(CategoryStates.waiting_for_name)
async def category_received_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip().capitalize())
    await state.set_state(CategoryStates.waiting_for_type)
    await message.answer("Выберите тип категории:", reply_markup=category_type_keyboard())


@router.callback_query(CategoryStates.waiting_for_type, F.data.startswith("type_"))
async def category_received_type(callback: CallbackQuery, state: FSMContext):
    t_type = callback.data.split("_")[1]
    data = await state.get_data()
    cat_name = data["name"]
    user_id = callback.from_user.id

    async with async_session_maker() as session:
        stmt = select(Category).where(
            and_(Category.user_id == user_id, Category.name.ilike(cat_name), Category.type == t_type)
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            await callback.message.answer(f"⚠️ Категория '{cat_name}' уже существует!")
        else:
            new_cat = Category(name=cat_name, type=t_type, user_id=user_id)
            session.add(new_cat)
            await session.commit()
            type_label = "расход" if t_type == 'expense' else 'доход'
            await callback.message.answer(f"✅ Категория '{cat_name}' ({type_label}) успешно создана!")

    await state.clear()
    await callback.message.answer(
        "🏠 **Главное меню**:",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(F.text == "📊 Статистика")
async def show_stats_menu(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 За день", callback_data="stat_day"),
         InlineKeyboardButton(text="📆 За неделю", callback_data="stat_week")],
        [InlineKeyboardButton(text="🗓 За месяц", callback_data="stat_month"),
         InlineKeyboardButton(text="🏠 Главное меню", callback_data="go_main_menu")]
    ])
    await message.answer("Выберите период для формирования отчета:", reply_markup=kb)


@router.callback_query(F.data.startswith("stat_"))
async def get_statistics(callback: CallbackQuery):
    period = callback.data.split("_")[1]
    user_id = callback.from_user.id
    now = datetime.now()

    if period == "day":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        period_name = "сегодня"
    elif period == "week":
        start_date = now - timedelta(days=7)
        period_name = "последние 7 дней"
    elif period == "month":
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        period_name = "текущий месяц"
    else:
        return

    async with async_session_maker() as session:
        stmt = select(
            Transaction.type,
            func.sum(Transaction.amount)
        ).where(
            and_(Transaction.user_id == user_id, Transaction.date >= start_date)
        ).group_by(Transaction.type)

        res = await session.execute(stmt)
        totals = {row[0]: row[1] for row in res.all()}
        total_expense = totals.get("expense", 0.0)
        total_income = totals.get("income", 0.0)

        cat_stmt = select(
            Transaction.category,
            func.sum(Transaction.amount)
        ).where(
            and_(Transaction.user_id == user_id, Transaction.type == "expense", Transaction.date >= start_date)
        ).group_by(Transaction.category)

        cat_res = await session.execute(cat_stmt)
        categories_breakdown = cat_res.all()

    report = f"📊 **Статистика за {period_name}:**\n\n"
    report += f"📈 Доходы: **+{total_income:,.2f} руб.**\n"
    report += f"📉 Расходы: **-{total_expense:,.2f} руб.**\n\n"

    if categories_breakdown:
        report += "🟥 **Расходы по категориям:**\n"
        for cat_name, amount in categories_breakdown:
            percent = (amount / total_expense * 100) if total_expense > 0 else 0
            report += f"• {cat_name}: {amount:,.2f} руб. *({percent:.1f}%)*\n"
    else:
        report += "📭 За выбранный период расходов не зафиксировано."

    await callback.message.edit_text(report, parse_mode="Markdown")
    await callback.answer()


# 1. Нажатие на кнопку "💬 Обратная связь"
@router.message(F.text == "💬 Обратная связь")
async def ask_feedback(message: Message, state: FSMContext):
    await state.set_state(FeedbackStates.waiting_for_feedback)
    await message.answer(
        "✍️ Опиши проблему, баг или идею для улучшения одним сообщением.\n"
        "При необходимости можешь прикрепить скриншот.",
        reply_markup=cancel_feedback_kb
    )


# 2. Отмена отправки
@router.message(FeedbackStates.waiting_for_feedback, F.text == "❌ Отмена")
async def cancel_feedback(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отправка отменена.", reply_markup=main_menu())


# 3. Приём текста или фото и пересылка в группу
@router.message(FeedbackStates.waiting_for_feedback)
async def send_feedback_to_group(message: Message, state: FSMContext):
    user = message.from_user
    username = f"@{user.username}" if user.username else "нет username"

    header = (
        "🐞 <b>Новое обращение</b>\n"
        f"👤 <b>От:</b> {user.full_name} ({username})\n"
        f"🆔 <code>{user.id}</code>\n"
        "───────────────\n"
    )

    if FEEDBACK_CHAT_ID != 0:
        if message.text:
            await message.bot.send_message(
                chat_id=FEEDBACK_CHAT_ID,
                text=f"{header}{message.text}",
                parse_mode="HTML"
            )
        elif message.photo:
            caption = message.caption or "<i>Без текстового описания</i>"
            await message.bot.send_photo(
                chat_id=FEEDBACK_CHAT_ID,
                photo=message.photo[-1].file_id,
                caption=f"{header}{caption}",
                parse_mode="HTML"
            )
        else:
            await message.answer("Пожалуйста, отправь текст или скриншот с описанием.")
            return

    await state.clear()
    await message.answer(
        "✅ Спасибо! Сообщение передано команде разработки.",
        reply_markup=main_menu()
    )
