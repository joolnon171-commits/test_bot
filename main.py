# main.py

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from db import init_db, clear_cache
from handlers import register_handlers, AccessMiddleware, FSMTimeoutMiddleware

# --- НАСТРОЙКИ ---
BOT_TOKEN = "8400237965:AAFfWPtwnbCeU7qaun5Iy4jeIwC_bLDgdeE"

# --- НАСТРОЙКА ЛОГИРОВАНИЯ ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def main():
    logger.info("🚀 Запуск бота...")

    # 1. Очищаем кэш перед запуском
    logger.info("🧹 Очищаем кэш...")
    clear_cache()

    # 2. Инициализация БД
    logger.info("📦 Инициализация базы данных...")
    init_db()

    # 3. Инициализация бота
    logger.info("🤖 Инициализация бота...")
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # 4. Удаляем вебхук
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Webhook удален")
    except Exception as e:
        logger.warning(f"⚠️ Не удалось удалить webhook: {e}")

    # 5. Диспетчер
    dp = Dispatcher()

    # 6. Регистрация обработчиков
    register_handlers(dp)

    # 7. Middleware
    dp.message.middleware(AccessMiddleware(bot))
    dp.callback_query.middleware(AccessMiddleware(bot))
    dp.message.middleware(FSMTimeoutMiddleware())
    dp.callback_query.middleware(FSMTimeoutMiddleware())

    # 8. Запуск
    logger.info("✅ Бот запущен и ожидает сообщений...")
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Бот остановлен.")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback

        traceback.print_exc()