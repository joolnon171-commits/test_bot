# main.py

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
logger = logging.getLogger(__name__)
from db import init_db
from handlers import register_handlers, AccessMiddleware, FSMTimeoutMiddleware

# --- НАСТРОЙКИ ---
BOT_TOKEN = "8400237965:AAFfWPtwnbCeU7qaun5Iy4jeIwC_bLDgdeE"

# --- НАСТРОЙКА ЛОГИРОВАНИЯ ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def main():
    # Инициализация БД
    init_db()

    # Инициализация бота с таймаутом и удалением вебхука
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # Удаляем вебхук ПЕРЕД созданием диспетчера
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook удален успешно")
    except Exception as e:
        logger.warning(f"Не удалось удалить webhook: {e}")

    dp = Dispatcher()

    # Регистрация всех обработчиков
    register_handlers(dp)

    # Подключение middleware
    dp.message.middleware(AccessMiddleware(bot))
    dp.callback_query.middleware(AccessMiddleware(bot))
    dp.message.middleware(FSMTimeoutMiddleware())
    dp.callback_query.middleware(FSMTimeoutMiddleware())

    # Запуск поллинга с явным указанием параметров
    logger.info("Бот запущен и ожидает сообщений...")
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nБот остановлен.")
    except Exception as e:
        print(f"Критическая ошибка: {e}")