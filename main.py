import asyncio
import os
from aiogram import Bot, Dispatcher
from database import init_db
from handlers import router

# Пытаемся подгрузить токен из файла token.env, если он есть локально
try:
    from dotenv import load_dotenv
    load_dotenv("token.env")
except ImportError:
    pass

TOKEN = os.getenv("BOT_TOKEN")

async def main():
    if not TOKEN:
        print("❌ Ошибка: Не найден токен бота! Проверь файл token.env или переменные окружения.")
        return

    await init_db()
    
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    
    dp.include_router(router)
    
    await bot.delete_webhook(drop_pending_updates=True)
    print("🤖 Бот успешно запущен и готов к работе...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
