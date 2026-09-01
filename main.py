import os
from flask import Flask, request
import telebot
from telebot import types

# Заміни на свій новий токен з BotFather
BOT_TOKEN = os.getenv("BOT_TOKEN", "8845140241:AAFykPP-lypxMkzrc_oxn4YbWtRb6UyGuPI")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "8083694619")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

SERVICES = {
    "✂️ Чоловіча стрижка": {"price": "400 грн", "time": "45 хв"},
    "🧔 Оформлення бороди": {"price": "250 грн", "time": "30 хв"},
    "🔥 Комплекс (Стрижка + Борода)": {"price": "600 грн", "time": "60 хв"},
    "👶 Дитяча стрижка": {"price": "350 грн", "time": "40 хв"}
}

# --- WEBHOOK ROUTES ---
@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == 'POST':
        json_str = request.get_data().decode('UTF-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return 'OK', 200
    return "Bot Server is Live!", 200

# --- BOT COMMANDS ---
@bot.message_handler(commands=['start', 'menu'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("📅 Онлайн-запис"),
        types.KeyboardButton("💰 Послуги та Прайс"),
        types.KeyboardButton("ℹ️ Контакти")
    )
    bot.send_message(
        message.chat.id,
        f"Вітаємо, <b>{message.from_user.first_name}</b>! 👋\nОберіть потрібний розділ у меню нижче:",
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.message_handler(func=lambda msg: msg.text == "💰 Послуги та Прайс")
def show_price(message):
    text = "<b>💵 Наш прайс-лист:</b>\n\n"
    for s_name, info in SERVICES.items():
        text += f"• <b>{s_name}</b> — {info['price']} ({info['time']})\n"
    bot.send_message(message.chat.id, text, parse_mode="HTML")

@bot.message_handler(func=lambda msg: msg.text == "ℹ️ Контакти")
def show_contacts(message):
    bot.send_message(message.chat.id, "📍 м. Київ, вул. Хрещатик, 1\n📞 +380 67 123 4567")

@bot.message_handler(func=lambda msg: True)
def echo_all(message):
    bot.send_message(message.chat.id, "Натисніть /start для відкриття меню.")

# --- LAUNCH ---
if __name__ == "__main__":
    bot.remove_webhook()
    
    # Реєстрація Webhook
    if RENDER_EXTERNAL_URL:
        webhook_url = RENDER_EXTERNAL_URL.rstrip('/') + '/'
        bot.set_webhook(url=webhook_url)
        print(f"Webhook set to: {webhook_url}")

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
