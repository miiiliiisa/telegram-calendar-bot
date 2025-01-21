from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters

# States for conversation handler
CHOOSING, BIRTHDATE, PROCESSING, DATE_RANGE = range(4)

def calculate_constant(birthdate: str) -> int:
    digits_sum = sum(int(digit) for digit in birthdate if digit.isdigit())
    while digits_sum > 22:
        digits_sum -= 22
    return digits_sum

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_keyboard = [
        ["Рассчитать сегодняшний день", "Рассчитать на месяц вперед", "Выбрать промежуток дат для расчета"]
    ]
    await update.message.reply_text(
        "Привет! Я бот для расчета по дате. Выберите действие:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return CHOOSING

async def choose_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_choice = update.message.text
    context.user_data['choice'] = user_choice

    await update.message.reply_text("Введите вашу дату рождения в формате ДД.ММ.ГГГГ:")
    return BIRTHDATE

async def get_birthdate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        birthdate = update.message.text
        context.user_data['constant'] = calculate_constant(birthdate)

        if context.user_data['choice'] == "Выбрать промежуток дат для расчета":
            await update.message.reply_text("Введите дату в формате ДД.ММ.ГГГГ-ДД.ММ.ГГГГ:")
            return DATE_RANGE
        elif context.user_data['choice'] == "Рассчитать сегодняшний день":
            result = calculate_single_day(context.user_data['constant'])
            await update.message.reply_text(f"Результат для сегодняшней даты: {result}")
        else:
            result_list = calculate_month(context.user_data['constant'])
            await update.message.reply_text("Результаты на месяц вперед:\n" + "\n".join(result_list))

        await update.message.reply_text("Рассчитать еще раз?", reply_markup=ReplyKeyboardMarkup([["Да"]], one_time_keyboard=True, resize_keyboard=True))
        return CHOOSING
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите дату в формате ДД.ММ.ГГГГ.")
        return BIRTHDATE

async def get_date_range(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        date_range = update.message.text
        start_date_str, end_date_str = date_range.split("-")
        start_date = datetime.strptime(start_date_str.strip(), "%d.%m.%Y")
        end_date = datetime.strptime(end_date_str.strip(), "%d.%m.%Y")

        if start_date > end_date:
            await update.message.reply_text("Начальная дата не может быть позже конечной. Попробуйте снова.")
            return DATE_RANGE

        constant = context.user_data['constant']
        results = calculate_date_range(start_date, end_date, constant)
        await update.message.reply_text("Результаты для выбранного промежутка:\n" + "\n".join(results))

        await update.message.reply_text("Рассчитать еще раз?", reply_markup=ReplyKeyboardMarkup([["Да"]], one_time_keyboard=True, resize_keyboard=True))
        return CHOOSING
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите даты в формате ДД.ММ.ГГГГ-ДД.ММ.ГГГГ.")
        return DATE_RANGE

def calculate_single_day(constant: int) -> int:
    today = datetime.now()
    return calculate_result(today, constant)

def calculate_month(constant: int) -> list:
    results = []
    today = datetime.now()
    for i in range(30):
        current_date = today + timedelta(days=i)
        result = calculate_result(current_date, constant)
        results.append(f"{current_date.strftime('%d.%m.%Y')}: {result}")
    return results

def calculate_date_range(start_date: datetime, end_date: datetime, constant: int) -> list:
    results = []
    current_date = start_date
    while current_date <= end_date:
        result = calculate_result(current_date, constant)
        results.append(f"{current_date.strftime('%d.%m.%Y')}: {result}")
        current_date += timedelta(days=1)
    return results

def calculate_result(date: datetime, constant: int) -> int:
    digits_sum = sum(int(digit) for digit in date.strftime('%d%m%Y'))
    result = digits_sum + constant
    if result > 22:
        result -= 22
    return result

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Процесс отменён. Если нужно, просто начните заново, введя /start.")
    return ConversationHandler.END

import os
from dotenv import load_dotenv

def main():
    # Загружаем переменные из .env файла
    load_dotenv()
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not telegram_bot_token:
        raise ValueError("Токен бота не найден. Убедитесь, что файл .env создан и содержит токен.")

    application = ApplicationBuilder().token(telegram_bot_token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_action)],
            BIRTHDATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_birthdate)],
            DATE_RANGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_date_range)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    application.run_polling()

if __name__ == "__main__":
    main()
