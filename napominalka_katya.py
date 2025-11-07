import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types, Router
from aiogram.filters import Command
from aiogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Настройки
BOT_TOKEN = "8073865785:AAGXkyGh5x1xK8J6s-mAcXfiy6BVWWrhbuc"

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# Словарь для хранения chat_id пользователей, которые запустили бота
active_chats = set()


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    chat_id = message.chat.id
    active_chats.add(chat_id)

    welcome_text = (
        "🤖 Бот-напоминание активирован!\n\n"
        "Я буду напоминать тебе по понедельникам и четвергам:\n"
        '"Не забудь про футболку где написано "Миша Кочев лучший", ее нужно носить 4 дня подряд!"\n\n'
    )

    await message.answer(welcome_text)
    logger.info(f"Пользователь {chat_id} подписался на напоминания")


@router.message(Command("stop"))
async def cmd_stop(message: Message):
    """Обработчик команды /stop"""
    chat_id = message.chat.id
    if chat_id in active_chats:
        active_chats.remove(chat_id)
        await message.answer("❌ Напоминания отключены. Используй /start чтобы снова включить.")
        logger.info(f"Пользователь {chat_id} отписался от напоминаний")
    else:
        await message.answer("ℹ️ Ты и так не подписан на напоминания. Используй /start чтобы подписаться.")


@router.message(Command("status"))
async def cmd_status(message: Message):
    """Обработчик команды /status"""
    chat_id = message.chat.id
    if chat_id in active_chats:
        status_text = "✅ Ты подписан на напоминания\nСледующее сообщение придет в понедельник или четверг в 9:00"
    else:
        status_text = "❌ Ты не подписан на напоминания\nИспользуй /start чтобы подписаться"

    await message.answer(status_text)


@router.message(Command("test"))
async def cmd_test(message: Message):
    """Тестовая команда для проверки отправки сообщения"""
    await send_reminder_to_all()
    await message.answer("✅ Тестовое напоминание отправлено всем подписчикам")


async def send_reminder_to_all():
    """Отправка напоминания всем подписанным пользователям"""
    if not active_chats:
        logger.info("Нет активных подписчиков для отправки напоминания")
        return

    message_text = 'Не забудь про футболку где написано "Миша Кочев лучший", ее нужно носить 4 дня подряд!'
    successful_sends = 0
    failed_sends = 0

    for chat_id in list(active_chats):  # Используем list для копирования, т.к. set может измениться
        try:
            await bot.send_message(chat_id=chat_id, text=message_text)
            successful_sends += 1
            logger.debug(f"Напоминание отправлено пользователю {chat_id}")
        except Exception as e:
            failed_sends += 1
            logger.error(f"Ошибка отправки пользователю {chat_id}: {e}")
            # Если пользователь заблокировал бота или чат не существует, удаляем из активных
            if "chat not found" in str(e).lower() or "bot was blocked" in str(e).lower():
                active_chats.discard(chat_id)
                logger.info(f"Пользователь {chat_id} удален из активных подписчиков")

    logger.info(f"Напоминания отправлены. Успешно: {successful_sends}, Ошибок: {failed_sends}")


async def scheduled_reminder():
    """Функция для планировщика - отправка напоминания по расписанию"""
    logger.info("Запуск плановой отправки напоминаний")
    await send_reminder_to_all()


def setup_scheduler():
    """Настройка планировщика"""
    scheduler = AsyncIOScheduler()

    # Настраиваем отправку по понедельникам и четвергам в 9:00 утра
    scheduler.add_job(
        scheduled_reminder,
        trigger=CronTrigger(
            day_of_week='mon,thu',
            hour=9,
            minute=0,
            timezone='Europe/Moscow'  # Укажите вашу временную зону
        ),
        id='weekly_reminder',
        replace_existing=True
    )

    return scheduler


async def on_startup():
    """Действия при запуске бота"""
    logger.info("Бот запущен и готов к работе!")
    logger.info(f"Активных подписчиков: {len(active_chats)}")


async def on_shutdown():
    """Действия при остановке бота"""
    logger.info("Бот останавливается...")
    await bot.session.close()


async def main():
    """Основная функция"""
    # Настройка планировщика
    scheduler = setup_scheduler()
    scheduler.start()

    # Запуск бота
    try:
        await on_startup()
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при работе бота: {e}")
    finally:
        await on_shutdown()
        scheduler.shutdown()


if __name__ == "__main__":
    # Укажите ваш токен бота здесь
    BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

    # Запуск приложения
    asyncio.run(main())