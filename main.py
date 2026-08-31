import os
import threading
from flask import Flask
import telebot
from telebot import types

# --- НАЛАШТУВАННЯ ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "8666795532:AAFICKdumXhvFSVm9GVzRNyZ2UJNMMq9EQg")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "8083694619")

bot = telebot.TeleBot(BOT_TOKEN)
user_data = {}

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER (Щоб Free Plan не вимикався) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running live!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# --- ЛОГІКА ТЕЛЕГРАМ БОТА ---
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("📅 Записатися на послугу"))
    bot.send_message(
        message.chat.id, 
        "Вітаємо у нашому сервісі! Оберіть потрібний розділ нижче:", 
        reply_markup=markup
    )

@bot.message_handler(func=lambda msg: msg.text == "📅 Записатися на послугу")
def start_booking(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("✂️ Чоловіча стрижка"), types.KeyboardButton("🧔 Оформлення бороди"))
    markup.add(types.KeyboardButton("❌ Скасувати"))
    bot.send_message(message.chat.id, "Оберіть послугу, яка вас цікавить:", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text in ["✂️ Чоловіча стрижка", "🧔 Оформлення бороди"])
def select_service(message):
    user_data[message.chat.id] = {"service": message.text}
    markup = types.ReplyKeyboardRemove()
    msg = bot.send_message(message.chat.id, "Як до вас звертатися? Напишіть ваше ім'я:", reply_markup=markup)
    bot.register_next_step_handler(msg, get_name)

def get_name(message):
    if message.text == "❌ Скасувати":
        return cancel(message)
    user_data[message.chat.id]["name"] = message.text
    msg = bot.send_message(message.chat.id, "Надішліть ваш номер телефону для зв'язку (наприклад, 0971234567):")
    bot.register_next_step_handler(msg, get_phone)

def get_phone(message):
    if message.text == "❌ Скасувати":
        return cancel(message)
        
    name = user_data[message.chat.id].get("name", "Не вказано")
    service = user_data[message.chat.id].get("service", "Не вказано")
    phone = message.text
    username = f"@{message.from_user.username}" if message.from_user.username else "немає"

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("📅 Записатися на послугу"))

    # Повідомлення клієнту
    bot.send_message(
        message.chat.id,
        f"Дякуємо, {name}! Заявку прийнято.\n\n📌 Послуга: {service}\n📞 Телефон: {phone}\n\nАдміністратор зв'яжеться з вами найближчим часом!",
        reply_markup=markup
    )

    # Сповіщення адміну (вам у приватні)
    admin_msg = (
        f"🚨 <b>НОВА ЗАЯВКА НА ЗАПИС!</b>\n\n"
        f"👤 <b>Ім'я:</b> {name}\n"
        f"📞 <b>Телефон:</b> {phone}\n"
        f"📌 <b>Послуга:</b> {service}\n"
        f"💬 <b>Telegram:</b> {username}"
    )
    try:
        bot.send_message(ADMIN_CHAT_ID, admin_msg, parse_mode="HTML")
    except Exception as e:
        print(f"Помилка відправки адміну: {e}")

@bot.message_handler(func=lambda msg: msg.text == "❌ Скасувати")
def cancel(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("📅 Записатися на послугу"))
    bot.send_message(message.chat.id, "Запис скасовано.", reply_markup=markup)

if __name__ == "__main__":
    # Запускаємо веб-сервер у фоновому потоці
    threading.Thread(target=run_web, daemon=True).start()
    print("Запуск бота...")
    bot.infinity_polling(skip_pending=True)
