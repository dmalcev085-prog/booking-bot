import os
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)

logging.basicConfig(level=logging.INFO)

SERVICE, NAME, PHONE = range(3)

BOT_TOKEN = os.getenv("BOT_TOKEN", "8666795532:AAFICKdumXhvFSVm9GVzRNyZ2UJNMMq9EQg")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "ТВІЙ_TELEGRAM_ID")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_keyboard = [["📅 Записатися на послугу"], ["ℹ️ Про нас / Контакти"]]
    await update.message.reply_text(
        "Вітаємо у нашому сервісі! Оберіть потрібний розділ нижче:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True),
    )

async def start_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    services_keyboard = [["✂️ Чоловіча стрижка"], ["🧔 Оформлення бороди"], ["❌ Скасувати"]]
    await update.message.reply_text(
        "Оберіть послугу, яка вас цікавить:",
        reply_markup=ReplyKeyboardMarkup(services_keyboard, resize_keyboard=True),
    )
    return SERVICE

async def select_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "❌ Скасувати":
        return await cancel(update, context)
        
    context.user_data["service"] = text
    await update.message.reply_text(
        "Як до вас звертатися? Напишіть ваше ім'я:",
        reply_markup=ReplyKeyboardRemove(),
    )
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text(
        "Надішліть ваш номер телефону для зв'язку (наприклад, 0971234567):"
    )
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["phone"] = update.message.text
    
    user_name = context.user_data["name"]
    user_phone = context.user_data["phone"]
    service = context.user_data["service"]
    username = f"@{update.effective_user.username}" if update.effective_user.username else "немає"

    await update.message.reply_text(
        f"Дякуємо, {user_name}! Заявку прийнято.\n\n"
        f"📌 Послуга: {service}\n"
        f"📞 Телефон: {user_phone}\n\n"
        f"Адміністратор зв'яжеться з вами найближчим часом!",
        reply_markup=ReplyKeyboardMarkup([["📅 Записатися на послугу"]], resize_keyboard=True)
    )

    admin_message = (
        f"🚨 <b>НОВА ЗАЯВКА НА ЗАПИС!</b>\n\n"
        f"👤 <b>Ім'я:</b> {user_name}\n"
        f"📞 <b>Телефон:</b> {user_phone}\n"
        f"📌 <b>Послуга:</b> {service}\n"
        f"💬 <b>Telegram:</b> {username}"
    )
    
    try:
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=admin_message,
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Помилка відправки адміну: {e}")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Запис скасовано.",
        reply_markup=ReplyKeyboardMarkup([["📅 Записатися на послугу"]], resize_keyboard=True)
    )
    return ConversationHandler.END

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    booking_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📅 Записатися на послугу$"), start_booking)],
        states={
            SERVICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_service)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
        },
        fallbacks=[MessageHandler(filters.Regex("^❌ Скасувати$"), cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(booking_handler)

    print("Запуск бота...")
    app.run_polling()

