# main.py
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from db import init_db
from handlers import register_handlers, AccessMiddleware, FSMTimeoutMiddleware

# --- НАСТРОЙКИ ---
BOT_TOKEN = "8400237965:AAFfWPtwnbCeU7qaun5Iy4jeIwC_bLDgdeE"  # Ваш токен

# --- НАСТРОЙКА ЛОГИРОВАНИЯ ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- ЗАПУСК ---
async def main():
    # Инициализация БД
    init_db()

    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # Регистрация всех обработчиков
    register_handlers(dp)

    # Подключение middleware
    dp.message.middleware(AccessMiddleware(bot))
    dp.callback_query.middleware(AccessMiddleware(bot))
    dp.message.middleware(FSMTimeoutMiddleware())
    dp.callback_query.middleware(FSMTimeoutMiddleware())

    # Удаление вебхука и запуск поллинга
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен.")