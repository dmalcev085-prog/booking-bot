import os
import sqlite3
import requests
from datetime import datetime, timedelta
from flask import Flask, request
import telebot
from telebot import types

# --- ОПТИМІЗОВАНО ОТРИМАННЯ ТОКЕНА ---
ENV_TOKEN = os.environ.get("BOT_TOKEN")
DEFAULT_TOKEN = "8666795532:AAFICKdumXhvFSVm9GVzRNyZ2UJNMMq9EQg"

BOT_TOKEN = ENV_TOKEN if (ENV_TOKEN and ENV_TOKEN.strip()) else DEFAULT_TOKEN
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "8083694619")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://booking-bot-6j3w.onrender.com")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

DB_NAME = "booking_system.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_name TEXT,
            service TEXT,
            master TEXT,
            date TEXT,
            time TEXT,
            contact TEXT,
            status TEXT DEFAULT 'ACTIVE',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

SERVICES = {
    "✂️ Чоловіча стрижка": {"price": "400 грн", "time": "45 хв"},
    "🧔 Оформлення бороди": {"price": "250 грн", "time": "30 хв"},
    "🔥 Комплекс (Стрижка + Борода)": {"price": "600 грн", "time": "60 хв"},
    "👶 Дитяча стрижка": {"price": "350 грн", "time": "40 хв"}
}

MASTERS = ["Олександр", "Дмитро", "Будь-який вільний"]
TIMES = ["10:00", "11:30", "13:00", "14:30", "16:00", "17:30", "19:00"]

user_sessions = {}

# --- ГНУЧКИЙ ВЕБХУК ДЛЯ TELEGRAM ---
@app.route('/', methods=['POST'])
def webhook():
    try:
        json_data = request.get_data().decode('utf-8')
        if json_data:
            update = telebot.types.Update.de_json(json_data)
            bot.process_new_updates([update])
        return 'OK', 200
    except Exception as e:
        print(f"Помилка в обробці оновлення: {e}")
        return 'OK', 200  # Завжди повертаємо 200 для Telegram

@app.route('/', methods=['GET'])
def index():
    return "Bot Server is Alive and Working!", 200

def main_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("📅 Онлайн-запис"),
        types.KeyboardButton("💰 Послуги та Прайс"),
        types.KeyboardButton("👤 Мій кабінет"),
        types.KeyboardButton("ℹ️ Контакти та Локація")
    )
    if str(user_id) == str(ADMIN_CHAT_ID):
        markup.add(types.KeyboardButton("👑 Адмін-панель"))
    return markup

# --- КОМАНДИ ---
@bot.message_handler(commands=['start', 'menu'])
def send_welcome(message):
    bot.clear_step_handler_by_chat_id(chat_id=message.chat.id)
    bot.send_message(
        message.chat.id,
        f"Вітаємо, <b>{message.from_user.first_name}</b>! 👋\n\nОберіть потрібну дію в меню нижче:",
        parse_mode="HTML",
        reply_markup=main_keyboard(message.chat.id)
    )

@bot.message_handler(func=lambda msg: msg.text == "💰 Послуги та Прайс")
def show_price(message):
    text = "<b>💵 Актуальний прайс-лист:</b>\n\n"
    for s_name, info in SERVICES.items():
        text += f"• <b>{s_name}</b>\n  Вартість: <code>{info['price']}</code> | Тривалість: {info['time']}\n\n"
    bot.send_message(message.chat.id, text, parse_mode="HTML")

@bot.message_handler(func=lambda msg: msg.text == "ℹ️ Контакти та Локація")
def show_contacts(message):
    text = (
        "<b>📍 Наші контакти:</b>\n\n"
        "🏠 <b>Адреса:</b> м. Київ, вул. Хрещатик, 1\n"
        "⏰ <b>Режим роботи:</b> Щодня з 09:00 до 21:00\n"
        "📞 <b>Телефон:</b> +380 67 123 4567\n"
    )
    bot.send_message(message.chat.id, text, parse_mode="HTML")

@bot.message_handler(func=lambda msg: msg.text == "👤 Мій кабінет")
def show_cabinet(message):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, service, master, date, time FROM appointments WHERE user_id = ? AND status = 'ACTIVE' ORDER BY id DESC", (message.chat.id,))
    apps = cursor.fetchall()
    conn.close()

    if not apps:
        bot.send_message(message.chat.id, "У вас немає активних записів.", reply_markup=main_keyboard(message.chat.id))
        return

    bot.send_message(message.chat.id, f"<b>👤 Ваші активні записи ({len(apps)}):</b>", parse_mode="HTML")
    for app_item in apps:
        app_id, service, master, date, time_slot = app_item
        text = f"📌 <b>{service}</b>\n👤 Майстер: {master}\n📅 {date} о {time_slot}"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("❌ Скасувати запис", callback_data=f"cancel_app_{app_id}"))
        bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("cancel_app_"))
def cancel_appointment_callback(call):
    app_id = call.data.split("_")[2]
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE appointments SET status = 'CANCELLED' WHERE id = ?", (app_id,))
    conn.commit()
    conn.close()
    bot.edit_message_text("❌ <b>Запис скасовано.</b>", call.message.chat.id, call.message.message_id, parse_mode="HTML")

@bot.message_handler(func=lambda msg: msg.text == "📅 Онлайн-запис")
def start_booking(message):
    user_sessions[message.chat.id] = {}
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    for s_name in SERVICES.keys():
        markup.add(types.KeyboardButton(s_name))
    markup.add(types.KeyboardButton("❌ Скасувати"))
    bot.send_message(message.chat.id, "<b>Крок 1/5:</b> Оберіть послугу:", parse_mode="HTML", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text in SERVICES.keys())
def step_select_master(message):
    if message.text == "❌ Скасувати":
        return cancel_flow(message)
    user_sessions[message.chat.id] = {"service": message.text}
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for master in MASTERS:
        markup.add(types.KeyboardButton(master))
    markup.add(types.KeyboardButton("❌ Скасувати"))
    bot.send_message(message.chat.id, "<b>Крок 2/5:</b> Оберіть майстра:", parse_mode="HTML", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text in MASTERS)
def step_select_date(message):
    if message.text == "❌ Скасувати":
        return cancel_flow(message)
    user_sessions[message.chat.id]["master"] = message.text
    today = datetime.now()
    dates = [
        ("Сьогодні", today.strftime("%Y-%m-%d")),
        ("Завтра", (today + timedelta(days=1)).strftime("%Y-%m-%d")),
        ((today + timedelta(days=2)).strftime("%d.%m"), (today + timedelta(days=2)).strftime("%Y-%m-%d"))
    ]
    markup = types.InlineKeyboardMarkup(row_width=2)
    for label, date_str in dates:
        markup.add(types.InlineKeyboardButton(f"📅 {label}", callback_data=f"select_date_{date_str}"))
    bot.send_message(message.chat.id, "<b>Крок 3/5:</b> Оберіть дату:", parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("select_date_"))
def step_select_time(call):
    date_str = call.data.split("_")[2]
    user_sessions[call.message.chat.id]["date"] = date_str
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    for t_slot in TIMES:
        markup.add(types.KeyboardButton(t_slot))
    markup.add(types.KeyboardButton("❌ Скасувати"))
    bot.send_message(call.message.chat.id, f"<b>Крок 4/5:</b> Обрано {date_str}.\nОберіть час:", parse_mode="HTML", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text in TIMES)
def step_get_contact(message):
    if message.text == "❌ Скасувати":
        return cancel_flow(message)
    user_sessions[message.chat.id]["time"] = message.text
    markup = types.ReplyKeyboardRemove()
    msg = bot.send_message(message.chat.id, "<b>Крок 5/5:</b> Напишіть ваше ім'я та номер телефону:", parse_mode="HTML", reply_markup=markup)
    bot.register_next_step_handler(msg, finish_booking)

def finish_booking(message):
    if message.text in ["/start", "/menu", "❌ Скасувати"]:
        return send_welcome(message)
    chat_id = message.chat.id
    contact = message.text
    session = user_sessions.get(chat_id, {})
    service = session.get("service", "Не вказано")
    master = session.get("master", "Не вказано")
    date = session.get("date", datetime.now().strftime("%Y-%m-%d"))
    booking_time = session.get("time", "Не вказано")
    username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO appointments (user_id, user_name, service, master, date, time, contact) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (chat_id, username, service, master, date, booking_time, contact))
    conn.commit()
    conn.close()

    bot.send_message(chat_id, f"🎉 <b>УСПІШНИЙ ЗАПИС!</b>\n\n📌 {service}\n👤 {master}\n📅 {date} о {booking_time}", parse_mode="HTML", reply_markup=main_keyboard(chat_id))

def cancel_flow(message):
    bot.clear_step_handler_by_chat_id(chat_id=message.chat.id)
    bot.send_message(message.chat.id, "Запис скасовано.", reply_markup=main_keyboard(message.chat.id))

# --- АВТОМАТИЧНЕ НАЛАШТУВАННЯ ВЕБХУКА ---
try:
    target_url = f"{RENDER_EXTERNAL_URL.rstrip('/')}/"
    res = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={target_url}")
    print(f"Webhook response: {res.json()}")
except Exception as err:
    print(f"Webhook setup error: {err}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)