import os
import sqlite3
import csv
import io
import requests
from datetime import datetime, timedelta
from flask import Flask, request
import telebot
from telebot import types
from telebot.apihelper import ApiTelegramException

# --- 1. НАЛАШТУВАННЯ ТА ТОКЕНИ ---
RAW_TOKEN = os.environ.get("BOT_TOKEN")
DEFAULT_TOKEN = "8666795532:AAFICKdumXhvFSVm9GVzRNyZ2UJNMMq9EQg"

BOT_TOKEN = RAW_TOKEN.strip() if (RAW_TOKEN and isinstance(RAW_TOKEN, str) and RAW_TOKEN.strip()) else DEFAULT_TOKEN
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "8083694619")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://booking-bot-6j3w.onrender.com")

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
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
            price TEXT,
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

def parse_price(price_str):
    if isinstance(price_str, (int, float)):
        return int(price_str)
    import re
    numbers = re.findall(r'\d+', str(price_str))
    return int(numbers[0]) if numbers else 0

MASTERS = ["Олександр", "Дмитро", "Будь-який вільний"]
TIMES = ["10:00", "11:30", "13:00", "14:30", "16:00", "17:30", "19:00"]

user_sessions = {}

def safe_send_message(chat_id, text, **kwargs):
    try:
        return bot.send_message(chat_id, text, **kwargs)
    except ApiTelegramException as e:
        print(f"Помилка надсилання в чат {chat_id}: {e}")
        return None
    except Exception as e:
        print(f"Загальна помилка надсилання: {e}")
        return None

@app.route('/', methods=['POST'])
def webhook():
    try:
        json_string = request.get_data().decode('utf-8')
        if json_string:
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
    except Exception as e:
        print(f"Помилка обробки вебхуку: {e}")
    return 'OK', 200

@app.route('/', methods=['GET'])
def index():
    return "✅ Barber Booking Bot Server is Running smoothly!", 200

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

def admin_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("📋 Активні записи"),
        types.KeyboardButton("💵 Доходи та Фінанси"),
        types.KeyboardButton("📊 Статистика"),
        types.KeyboardButton("📥 Експорт таблиці (CSV)"),
        types.KeyboardButton("🔙 Назад в головне меню")
    )
    return markup

@bot.message_handler(commands=['start', 'menu'])
def send_welcome(message):
    bot.clear_step_handler_by_chat_id(chat_id=message.chat.id)
    if message.chat.id in user_sessions:
        del user_sessions[message.chat.id]
    safe_send_message(
        message.chat.id,
        f"Вітаємо, <b>{message.from_user.first_name}</b>! 👋\n\nОберіть потрібну дію в меню нижче:",
        parse_mode="HTML",
        reply_markup=main_keyboard(message.chat.id)
    )

# --- УНІВЕРСАЛЬНИЙ ОБРОБНИК КНОПКИ СКАСУВАТИ ---
@bot.message_handler(func=lambda msg: msg.text == "❌ Скасувати")
def global_cancel_handler(message):
    bot.clear_step_handler_by_chat_id(chat_id=message.chat.id)
    if message.chat.id in user_sessions:
        del user_sessions[message.chat.id]
    safe_send_message(
        message.chat.id,
        "❌ Дюю скасовано. Повертаємось до головного меню:",
        parse_mode="HTML",
        reply_markup=main_keyboard(message.chat.id)
    )

# --- АДМІН-ПАНЕЛЬ ТА ФІНАНСИ ---
@bot.message_handler(func=lambda msg: msg.text == "👑 Адмін-панель")
def show_admin_panel(message):
    if str(message.chat.id) != str(ADMIN_CHAT_ID):
        return
    safe_send_message(
        message.chat.id,
        "<b>👑 Панель Адміністратора</b>\n\nОберіть розділ керування:",
        parse_mode="HTML",
        reply_markup=admin_keyboard()
    )

@bot.message_handler(func=lambda msg: msg.text == "📋 Активні записи")
def admin_show_appointments(message):
    if str(message.chat.id) != str(ADMIN_CHAT_ID):
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_name, service, price, master, date, time, contact FROM appointments WHERE status = 'ACTIVE' ORDER BY date ASC, time ASC")
    apps = cursor.fetchall()
    conn.close()

    if not apps:
        safe_send_message(message.chat.id, "Зараз немає активних записів.", reply_markup=admin_keyboard())
        return

    safe_send_message(message.chat.id, f"<b>📋 Всього активних записів: {len(apps)}</b>\n", parse_mode="HTML")
    for app_item in apps:
        app_id, user_name, service, price, master, date, time_slot, contact = app_item
        text = (
            f"🆔 <b>Запис #{app_id}</b>\n"
            f"👤 <b>Клієнт:</b> {user_name}\n"
            f"📞 <b>Контакт:</b> {contact}\n"
            f"📌 <b>Послуга:</b> {service} ({price})\n"
            f"💈 <b>Майстер:</b> {master}\n"
            f"📅 <b>Дата/Час:</b> {date} о {time_slot}"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("❌ Скасувати цей запис", callback_data=f"cancel_app_{app_id}"))
        safe_send_message(message.chat.id, text, parse_mode="HTML", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text == "💵 Доходи та Фінанси")
def admin_show_revenue(message):
    if str(message.chat.id) != str(ADMIN_CHAT_ID):
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT price, status FROM appointments")
    rows = cursor.fetchall()
    conn.close()

    total_revenue = 0
    active_revenue = 0

    for row in rows:
        p_val = parse_price(row[0])
        total_revenue += p_val
        if row[1] == 'ACTIVE':
            active_revenue += p_val

    text = (
        "<b>💰 Фінансовий звіт перукарні:</b>\n\n"
        f"🟢 <b>Потенційний дохід (активні записи):</b> <code>{active_revenue} грн</code>\n"
        f"📈 <b>Загальний обіг (включно зі скасованими):</b> <code>{total_revenue} грн</code>\n"
    )
    safe_send_message(message.chat.id, text, parse_mode="HTML", reply_markup=admin_keyboard())

@bot.message_handler(func=lambda msg: msg.text == "📊 Статистика")
def admin_show_stats(message):
    if str(message.chat.id) != str(ADMIN_CHAT_ID):
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM appointments")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM appointments WHERE status = 'ACTIVE'")
    active = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM appointments WHERE status = 'CANCELLED'")
    cancelled = cursor.fetchone()[0]
    conn.close()

    text = (
        "<b>📊 Статистика закладу:</b>\n\n"
        f"🔹 <b>Всього бронювань:</b> {total}\n"
        f"✅ <b>Активні:</b> {active}\n"
        f"❌ <b>Скасовані:</b> {cancelled}\n"
    )
    safe_send_message(message.chat.id, text, parse_mode="HTML", reply_markup=admin_keyboard())

@bot.message_handler(func=lambda msg: msg.text == "📥 Експорт таблиці (CSV)")
def admin_export_csv(message):
    if str(message.chat.id) != str(ADMIN_CHAT_ID):
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_name, service, price, master, date, time, contact, status, created_at FROM appointments")
    rows = cursor.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(["ID", "Клієнт", "Послуга", "Ціна", "Майстер", "Дата", "Час", "Контакт", "Статус", "Створено"])
    
    for row in rows:
        writer.writerow(row)

    output.seek(0)
    file_bytes = io.BytesIO(output.getvalue().encode('utf-8-sig'))
    file_bytes.name = "barber_booking_report.csv"

    bot.send_document(
        message.chat.id, 
        file_bytes, 
        caption="📊 <b>Таблиця з усіма записами та фінансами.</b> Відкривається у Excel чи Google Таблицях.",
        parse_mode="HTML",
        reply_markup=admin_keyboard()
    )

@bot.message_handler(func=lambda msg: msg.text == "🔙 Назад в головне меню")
def back_to_main_menu(message):
    send_welcome(message)

# --- КЛІЄНТСЬКА ЧАСТИНА ---
@bot.message_handler(func=lambda msg: msg.text == "💰 Послуги та Прайс")
def show_price(message):
    text = "<b>💵 Актуальний прайс-лист:</b>\n\n"
    for s_name, info in SERVICES.items():
        text += f"• <b>{s_name}</b>\n  Вартість: <code>{info['price']}</code> | Тривалість: {info['time']}\n\n"
    safe_send_message(message.chat.id, text, parse_mode="HTML")

@bot.message_handler(func=lambda msg: msg.text == "ℹ️ Контакти та Локація")
def show_contacts(message):
    text = (
        "<b>📍 Наші контакти:</b>\n\n"
        "🏠 <b>Адреса:</b> м. Київ, вул. Хрещатик, 1\n"
        "⏰ <b>Режим роботи:</b> Щодня з 09:00 до 21:00\n"
        "📞 <b>Телефон:</b> +380 67 123 4567\n"
    )
    safe_send_message(message.chat.id, text, parse_mode="HTML")

@bot.message_handler(func=lambda msg: msg.text == "👤 Мій кабінет")
def show_cabinet(message):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, service, master, date, time FROM appointments WHERE user_id = ? AND status = 'ACTIVE' ORDER BY id DESC", (message.chat.id,))
    apps = cursor.fetchall()
    conn.close()

    if not apps:
        safe_send_message(message.chat.id, "У вас немає активних записів.", reply_markup=main_keyboard(message.chat.id))
        return

    safe_send_message(message.chat.id, f"<b>👤 Ваші активні записи ({len(apps)}):</b>", parse_mode="HTML")
    for app_item in apps:
        app_id, service, master, date, time_slot = app_item
        text = f"📌 <b>{service}</b>\n👤 Майстер: {master}\n📅 {date} о {time_slot}"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("❌ Скасувати запис", callback_data=f"cancel_app_{app_id}"))
        safe_send_message(message.chat.id, text, parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("cancel_app_"))
def cancel_appointment_callback(call):
    try:
        app_id = call.data.split("_")[2]
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE appointments SET status = 'CANCELLED' WHERE id = ?", (app_id,))
        conn.commit()
        conn.close()

        bot.answer_callback_query(call.id, text="Запис успішно скасовано!")
        bot.edit_message_text(
            "❌ <b>Цей запис було скасовано.</b>", 
            call.message.chat.id, 
            call.message.message_id, 
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Помилка скасування: {e}")
        bot.answer_callback_query(call.id, text="Помилка при скасуванні.", show_alert=True)

@bot.message_handler(func=lambda msg: msg.text == "📅 Онлайн-запис")
def start_booking(message):
    user_sessions[message.chat.id] = {}
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    for s_name in SERVICES.keys():
        markup.add(types.KeyboardButton(s_name))
    markup.add(types.KeyboardButton("❌ Скасувати"))
    safe_send_message(message.chat.id, "<b>Крок 1/5:</b> Оберіть послугу:", parse_mode="HTML", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text in SERVICES.keys())
def step_select_master(message):
    service_name = message.text
    service_price = SERVICES[service_name]["price"]
    user_sessions[message.chat.id] = {"service": service_name, "price": service_price}
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for master in MASTERS:
        markup.add(types.KeyboardButton(master))
    markup.add(types.KeyboardButton("❌ Скасувати"))
    safe_send_message(message.chat.id, "<b>Крок 2/5:</b> Оберіть майстра:", parse_mode="HTML", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text in MASTERS)
def step_select_date(message):
    if message.chat.id not in user_sessions:
        user_sessions[message.chat.id] = {}
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
    safe_send_message(message.chat.id, "<b>Крок 3/5:</b> Оберіть дату:", parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("select_date_"))
def step_select_time(call):
    try:
        bot.answer_callback_query(call.id)
        date_str = call.data.split("_")[2]
        if call.message.chat.id not in user_sessions:
            user_sessions[call.message.chat.id] = {}
        user_sessions[call.message.chat.id]["date"] = date_str
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
        for t_slot in TIMES:
            markup.add(types.KeyboardButton(t_slot))
        markup.add(types.KeyboardButton("❌ Скасувати"))
        safe_send_message(call.message.chat.id, f"<b>Крок 4/5:</b> Обрано дату {date_str}.\nТепер оберіть час:", parse_mode="HTML", reply_markup=markup)
    except Exception as e:
        print(f"Помилка вибору часу: {e}")

@bot.message_handler(func=lambda msg: msg.text in TIMES)
def step_get_contact(message):
    if message.chat.id not in user_sessions:
        user_sessions[message.chat.id] = {}
    user_sessions[message.chat.id]["time"] = message.text
    markup = types.ReplyKeyboardRemove()
    msg = safe_send_message(message.chat.id, "<b>Крок 5/5:</b> Напишіть ваше ім'я та номер телефону:", parse_mode="HTML", reply_markup=markup)
    if msg:
        bot.register_next_step_handler(msg, finish_booking)

def finish_booking(message):
    if message.text in ["/start", "/menu", "❌ Скасувати"]:
        return send_welcome(message)
    chat_id = message.chat.id
    contact = message.text
    session = user_sessions.get(chat_id, {})
    service = session.get("service", "Не вказано")
    price = session.get("price", "0 грн")
    master = session.get("master", "Не вказано")
    date = session.get("date", datetime.now().strftime("%Y-%m-%d"))
    booking_time = session.get("time", "Не вказано")
    username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO appointments (user_id, user_name, service, price, master, date, time, contact) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                   (chat_id, username, service, str(price), master, date, booking_time, contact))
    conn.commit()
    conn.close()

    if chat_id in user_sessions:
        del user_sessions[chat_id]

    safe_send_message(chat_id, f"🎉 <b>УСПІШНИЙ ЗАПИС!</b>\n\n📌 {service} ({price})\n👤 Майстер: {master}\n📅 Дата: {date} о {booking_time}", parse_mode="HTML", reply_markup=main_keyboard(chat_id))

    if ADMIN_CHAT_ID:
        admin_msg = f"⚡️ <b>НОВИЙ ЗАПИС!</b>\n📌 {service} — <code>{price}</code>\n👤 Майстер: {master}\n📅 {date} о {booking_time}\n📞 {contact}\n💬 Клієнт: {username}"
        safe_send_message(ADMIN_CHAT_ID, admin_msg, parse_mode="HTML")

def setup_webhook():
    try:
        target_url = f"{RENDER_EXTERNAL_URL.rstrip('/')}/"
        res = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={target_url}")
        print(f"Webhook setup result: {res.json()}")
    except Exception as err:
        print(f"Webhook setup error: {err}")

setup_webhook()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)