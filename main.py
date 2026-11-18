import asyncio
import os
from aiohttp import web
from aiogram import Bot, Dispatcher
from database import init_db
from handlers import router

try:
    from dotenv import load_dotenv
    load_dotenv("token.env")
except ImportError:
    pass

TOKEN = os.getenv("BOT_TOKEN")

# Заглушка для Render Web Service
async def health_check(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    if not TOKEN:
        print("❌ Ошибка: Не найден токен бота! Проверь переменные окружения.")
        return

    await init_db()
    await start_web_server()
    
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    
    await bot.delete_webhook(drop_pending_updates=True)
    print("🤖 Бот успешно запущен и готов к работе...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
