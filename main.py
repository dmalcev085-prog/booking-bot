import os
import threading
from flask import Flask
import telebot
from telebot import types

BOT_TOKEN = os.getenv("BOT_TOKEN", "8666795532:AAFICKdumXhvFSVm9GVzRNyZ2UJNMMq9EQg")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "8083694619")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# Сховище даних сесій клієнтів
user_data = {}
user_appointments = {}  # Тимчасова база записів {chat_id: [записи]}

# База даних послуг та майстрів
SERVICES = {
    "✂️ Чоловіча стрижка": {"price": "400 грн", "time": "45 хв"},
    "🧔 Оформлення бороди": {"price": "250 грн", "time": "30 хв"},
    "🔥 Комплекс (Стрижка + Борода)": {"price": "600 грн", "time": "60 хв"},
    "👶 Дитяча стрижка": {"price": "350 грн", "time": "40 хв"}
}

MASTERS = ["Олександр", "Дмитро", "Будь-який вільний"]
TIMES = ["10:00", "12:00", "14:00", "16:00", "18:00"]

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER ---
@app.route('/')
def home():
    return "Pro Max Bot is active!"

def start_bot():
    bot.infinity_polling(skip_pending=True)

# --- МЕНЮ ТА ГОЛОВНА ЛОГІКА ---
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("📅 Онлайн-запис"),
        types.KeyboardButton("💰 Послуги та Прайс"),
        types.KeyboardButton("👤 Мій кабінет"),
        types.KeyboardButton("ℹ️ Контакти та Локація")
    )
    return markup

@bot.message_handler(commands=['start', 'menu'])
def send_welcome(message):
    bot.send_message(
        message.chat.id,
        f"Вітаємо, <b>{message.from_user.first_name}</b>! 👋\n\nЛаскаво просимо до нашого сервісу. Оберіть потрібний розділ у меню нижче:",
        parse_mode="HTML",
        reply_markup=main_keyboard()
    )

# --- 1. ПОСЛУГИ ТА ПРАЙС ---
@bot.message_handler(func=lambda msg: msg.text == "💰 Послуги та Прайс")
def show_price(message):
    text = "<b>💵 Наш прайс-лист та послуги:</b>\n\n"
    for s_name, info in SERVICES.items():
        text += f"• <b>{s_name}</b>\n  Вартість: {info['price']} | Тривалість: {info['time']}\n\n"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📅 Записатися зараз", callback_data="start_booking_inline"))
    bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=markup)

# --- 2. КОНТАКТИ ТА ЛОКАЦІЯ ---
@bot.message_handler(func=lambda msg: msg.text == "ℹ️ Контакти та Локація")
def show_contacts(message):
    text = (
        "<b>📍 Наші контакти:</b>\n\n"
        "🏠 <b>Адреса:</b> м. Київ, вул. Хрещатик, 1\n"
        "⏰ <b>Графік роботи:</b> Пн-Сб з 09:00 до 20:00\n"
        "📞 <b>Телефон:</b> +380 67 123 4567\n"
        "💬 <b>Telegram:</b> @admin_booking\n"
    )
    bot.send_message(message.chat.id, text, parse_mode="HTML")

# --- 3. ОСОБИСТИЙ КАБІНЕТ ---
@bot.message_handler(func=lambda msg: msg.text == "👤 Мій кабінет")
def show_cabinet(message):
    apps = user_appointments.get(message.chat.id, [])
    if not apps:
        bot.send_message(message.chat.id, "У вас немає активних записів.")
        return
    
    text = "<b>👤 Ваші активні записи:</b>\n\n"
    for i, app_item in enumerate(apps, 1):
        text += (
            f"<b>Запис №{i}</b>\n"
            f"📌 Послуга: {app_item['service']}\n"
            f"👤 Майстер: {app_item['master']}\n"
            f"🕒 Час: {app_item['time']}\n\n"
        )
    bot.send_message(message.chat.id, text, parse_mode="HTML")

# --- 4. ОНЛАЙН-ЗАПИС (ПОКРОКОВИЙ СЦЕНАРІЙ) ---
@bot.message_handler(func=lambda msg: msg.text == "📅 Онлайн-запис")
@bot.callback_query_handler(func=lambda call: call.data == "start_booking_inline")
def start_booking(item):
    chat_id = item.message.chat.id if isinstance(item, types.CallbackQuery) else item.chat.id
    user_data[chat_id] = {}
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    for s_name in SERVICES.keys():
        markup.add(types.KeyboardButton(s_name))
    markup.add(types.KeyboardButton("❌ Скасувати"))
    
    bot.send_message(chat_id, "Крок 1/4: Оберіть необхідну послугу:", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text in SERVICES.keys())
def step_select_master(message):
    user_data[message.chat.id]["service"] = message.text
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for master in MASTERS:
        markup.add(types.KeyboardButton(master))
    markup.add(types.KeyboardButton("❌ Скасувати"))
    
    bot.send_message(message.chat.id, "Крок 2/4: Оберіть майстра:", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text in MASTERS)
def step_select_time(message):
    user_data[message.chat.id]["master"] = message.text
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    for t_slot in TIMES:
        markup.add(types.KeyboardButton(t_slot))
    markup.add(types.KeyboardButton("❌ Скасувати"))
    
    bot.send_message(message.chat.id, "Крок 3/4: Оберіть зручний час на сьогодні:", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text in TIMES)
def step_get_name(message):
    user_data[message.chat.id]["time"] = message.text
    
    markup = types.ReplyKeyboardRemove()
    msg = bot.send_message(message.chat.id, "Крок 4/4: Введіть ваше ім'я та номер телефону для зв'язку (наприклад, Олексій 0971234567):", reply_markup=markup)
    bot.register_next_step_handler(msg, step_finish_booking)

def step_finish_booking(message):
    if message.text == "❌ Скасувати":
        return cancel(message)
        
    chat_id = message.chat.id
    contact_info = message.text
    service = user_data.get(chat_id, {}).get("service", "Не вказано")
    master = user_data.get(chat_id, {}).get("master", "Не вказано")
    booking_time = user_data.get(chat_id, {}).get("time", "Не вказано")
    username = f"@{message.from_user.username}" if message.from_user.username else "немає"

    appointment = {"service": service, "master": master, "time": booking_time, "contact": contact_info}
    if chat_id not in user_appointments:
        user_appointments[chat_id] = []
    user_appointments[chat_id].append(appointment)

    # Підтвердження клієнту
    success_text = (
        f"🎉 <b>Вітаємо! Ви успішно записані!</b>\n\n"
        f"📌 <b>Послуга:</b> {service}\n"
        f"👤 <b>Майстер:</b> {master}\n"
        f"🕒 <b>Час:</b> {booking_time}\n"
        f"📞 <b>Контакт:</b> {contact_info}\n\n"
        f"Чекаємо на вас!"
    )
    bot.send_message(chat_id, success_text, parse_mode="HTML", reply_markup=main_keyboard())

    # Сповіщення адміністратору
    admin_msg = (
        f"🚨 <b>НОВИЙ PRO MAX ЗАПИС!</b>\n\n"
        f"📌 <b>Послуга:</b> {service}\n"
        f"👤 <b>Майстер:</b> {master}\n"
        f"🕒 <b>Час:</b> {booking_time}\n"
        f"📞 <b>Клієнт:</b> {contact_info}\n"
        f"💬 <b>Telegram:</b> {username}"
    )
    try:
        bot.send_message(ADMIN_CHAT_ID, admin_msg, parse_mode="HTML")
    except Exception as e:
        print(f"Помилка надсилання адміну: {e}")

@bot.message_handler(func=lambda msg: msg.text == "❌ Скасувати")
def cancel(message):
    bot.send_message(message.chat.id, "Запис скасовано.", reply_markup=main_keyboard())

if __name__ == "__main__":
    threading.Thread(target=start_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
