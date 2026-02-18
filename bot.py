import sqlite3
import telebot
from telebot import types
import requests
import json
import os
from datetime import datetime
import random
import time
import threading
import string

# --- زانیارییە سەرەکییەکان ---
token = os.getenv("BOT_TOKEN") 
ADMIN_ID = 1621554170
CHANNEL = '@onestore6'
ADMINS = [1621554170]
PHONE_NUMBER = "076788"

bot = telebot.TeleBot(token)

# --- دروستکردنی داتابەیس و خشتەکان ---
def init_db():
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS users
                     (user_id INTEGER PRIMARY KEY, 
                      username TEXT,
                      first_name TEXT,
                      join_date TEXT,
                      points INTEGER DEFAULT 0,
                      invited_by INTEGER DEFAULT 0,
                      shares INTEGER DEFAULT 0,
                      spent_points INTEGER DEFAULT 0,
                      orders_count INTEGER DEFAULT 0,
                      today_messages INTEGER DEFAULT 0)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS admins
                     (admin_id INTEGER PRIMARY KEY)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS orders
                     (order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER,
                      service_type TEXT,
                      quantity INTEGER,
                      link TEXT,
                      status TEXT DEFAULT 'pending',
                      order_date TEXT,
                      api_order_id TEXT)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS settings
                     (key TEXT PRIMARY KEY, value TEXT)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS gift_codes
                     (code TEXT PRIMARY KEY,
                      points INTEGER,
                      used_by INTEGER DEFAULT 0,
                      is_used INTEGER DEFAULT 0)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS messages
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER,
                      message_text TEXT,
                      message_date TEXT)''')
    
    conn.commit()
    conn.close()

# --- فەنکشنەکانی بەڕێوەبردنی بەکارهێنەر ---
def get_user(user_id):
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def add_user(user_id, username, first_name, invited_by=0):
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    join_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''INSERT OR IGNORE INTO users 
                     (user_id, username, first_name, join_date, invited_by) 
                     VALUES (?, ?, ?, ?, ?)''',
                  (user_id, username, first_name, join_date, invited_by))
    conn.commit()
    conn.close()

def update_user_points(user_id, points):
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET points = points + ? WHERE user_id = ?", 
                  (points, user_id))
    conn.commit()
    conn.close()

def get_total_users():
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_today_users():
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT COUNT(*) FROM users WHERE DATE(join_date) = ?", (today,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_user_stats():
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute('''SELECT 
                     COUNT(*) as total_users,
                     SUM(points) as total_points,
                     SUM(orders_count) as total_orders,
                     SUM(spent_points) as total_spent
                     FROM users''')
    stats = cursor.fetchone()
    conn.close()
    return stats

# --- فەنکشنەکانی بەڕێوەبردنی ئەدمین ---
def is_admin(user_id):
    return user_id in ADMINS or user_id == ADMIN_ID

def add_admin(admin_id):
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO admins (admin_id) VALUES (?)", (admin_id,))
    conn.commit()
    conn.close()

def get_admins():
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT admin_id FROM admins")
    admins = [row[0] for row in cursor.fetchall()]
    conn.close()
    return admins

def remove_all_admins():
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM admins")
    conn.commit()
    conn.close()

# --- ڕێکخستنەکان ---
def get_setting(key):
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def set_setting(key, value):
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", 
                  (key, value))
    conn.commit()
    conn.close()

def check_subscription(user_id):
    try:
        chat_member = bot.get_chat_member(CHANNEL, user_id)
        return chat_member.status in ['member', 'administrator', 'creator']
    except:
        return False

# ناوی خزمەتگوزارییەکان بە کوردی
SERVICES = {
    'instagram': {
        'followers': [
            {'name': 'فۆڵۆوەرزی جێگیر', 'price': 1, 'service_id': 9650},
            {'name': 'فۆڵۆوەرزی ناجێگیر', 'price': 2, 'service_id': 9650},
            {'name': 'فۆڵۆوەرزی ڕاستەقینە', 'price': 0.5, 'service_id': 9650},
            {'name': 'ڵایک', 'price': 15, 'service_id': 9168},
            {'name': 'بینین (Views)', 'price': 25, 'service_id': 5132},
        ]
    },
    'telegram': {
        'members': [
            {'name': 'ئەندامی کەناڵ', 'price': 2.1, 'service_id': 8504},
            {'name': 'بینینی پۆست', 'price': 25, 'service_id': 10401},
        ]
    }
}

# --- دەستپێکی بۆت (/start) ---
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username or "بێ ناسناو"
    first_name = message.from_user.first_name or "بەکارهێنەر"
    
    if not check_subscription(user_id):
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("📢 جۆین بە لە کەناڵ", url=f"https://t.me/{CHANNEL[1:]}"))
        bot.send_message(message.chat.id,
                        f"""🚸 **ببوورە ئازیزم** 
🔰 **سەرەتا دەبێت لە کەناڵی بۆتەکە جۆین بیت**

📢 **کەناڵ:** {CHANNEL}

‼️ **جۆین بە و پاشان /start بنێرەوە**""",
                        reply_markup=keyboard)
        return
    
    if get_setting('bot_locked') == 'true' and not is_admin(user_id):
        bot.send_message(message.chat.id, "⏳ بۆتەکە لە ئێستادا لەژێر چاکسازیدایە، تکایە دواتر هەوڵ بدەرەوە")
        return
    
    invited_by = 0
    if len(message.text.split()) > 1:
        try:
            invited_by = int(message.text.split()[1])
        except:
            pass
    
    add_user(user_id, username, first_name, invited_by)
    
    if invited_by and invited_by != user_id:
        update_user_points(invited_by, 5)
        bot.send_message(invited_by, f"🎉 5 خاڵت وەرگرت! بەکارهێنەرێکی نوێ لە ڕێگەی لینکەکەتەوە هاتە ناو بۆت")
    
    user = get_user(user_id)
    points = user[4] if user else 0
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton(f"🎯 خاڵەکانت: {points}", callback_data="my_points")
    )
    keyboard.row(
        types.InlineKeyboardButton("🛒 خزمەتگوزارییەکان", callback_data="services"),
        types.InlineKeyboardButton("👤 هەژمار", callback_data="account")
    )
    keyboard.row(
        types.InlineKeyboardButton("💰 کۆکردنەوەی خاڵ", callback_data="earn_points"),
        types.InlineKeyboardButton("🎁 بەکارهێنانی کۆد", callback_data="use_gift")
    )
    keyboard.row(
        types.InlineKeyboardButton("🔄 کڕینی خاڵ", callback_data="buy_points"),
        types.InlineKeyboardButton("📊 داواکارییەکانم", callback_data="my_orders")
    )
    
    if is_admin(user_id):
        keyboard.row(types.InlineKeyboardButton("🎮 پانێڵی کۆنتڕۆڵ", callback_data="admin_panel"))
    
    welcome_text = f"""🎊 **بەخێرهاتی {first_name}!

🤖 بۆ بۆتی پێشکەوتووی زیادکردنی فۆڵۆوەرز**
────────────────
💎 **خاڵەکانت:** `{points}`
🆔 **ئایدی تۆ:** `{user_id}`
────────────────
یەکێک لە بژاردەکانی خوارەوە هەڵبژێرە:"""

    bot.send_message(message.chat.id, welcome_text, 
                    reply_markup=keyboard, parse_mode='Markdown')

# --- بەڕێوەبردنی کلیکەکان (Callbacks) ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    
    if call.data == "services":
        show_services(call)
    elif call.data == "account":
        show_account(call)
    elif call.data == "earn_points":
        show_earn_points(call)
    elif call.data == "use_gift":
        use_gift_code(call)
    elif call.data == "buy_points":
        show_buy_points(call)
    elif call.data == "my_points":
        show_my_points(call)
    elif call.data == "my_orders":
        show_my_orders(call)
    elif call.data == "admin_panel":
        admin_panel(call)
    elif call.data == "rshq_panel":
        show_rshq_panel(call)
    elif call.data == "add_points": # چارەسەری زیادکردنی خاڵ
        add_points_handler(call)
    elif call.data == "create_gift": # چارەسەری دروستکردنی کۆد
        create_gift_handler(call)
    elif call.data == "manage_admins":
        manage_admins(call)
    elif call.data == "statistics":
        show_statistics(call)
    elif call.data == "broadcast":
        show_broadcast(call)
    elif call.data == "lock_bot":
        lock_bot(call)
    elif call.data == "unlock_bot":
        unlock_bot(call)
    elif call.data == "add_admin":
        add_admin_handler(call)
    elif call.data == "delete_admins":
        delete_admins(call)
    elif call.data == "back_to_main":
        start(call.message)
    elif call.data == "back_to_admin":
        admin_panel(call)
    elif call.data.startswith("service_"):
        show_service_details(call)
    elif call.data.startswith("order_"):
        create_service_order(call)

# --- کرداری زیادکردنی خاڵ لەلایەن ئەدمینەوە ---
def add_points_handler(call):
    if not is_admin(call.from_user.id): return
    msg = bot.edit_message_text("👤 **ئایدی ئەو بەکارهێنەرە بنێرە کە دەتەوێت خاڵی بۆ زیاد بکەیت:**",
                               chat_id=call.message.chat.id, message_id=call.message.message_id)
    bot.register_next_step_handler(msg, process_add_points_id)

def process_add_points_id(message):
    try:
        target_id = int(message.text)
        msg = bot.send_message(message.chat.id, f"💎 **بڕی ئەو خاڵانە بنووسە کە دەتەوێت بۆ `{target_id}` زیاد بکرێت:**")
        bot.register_next_step_handler(msg, process_add_points_amount, target_id)
    except:
        bot.send_message(message.chat.id, "❌ تکایە ئایدی بە دروستی بنووسە.")

def process_add_points_amount(message, target_id):
    try:
        amount = int(message.text)
        update_user_points(target_id, amount)
        bot.send_message(message.chat.id, f"✅ سەرکەوتوو بوو! `{amount}` خاڵ بۆ `{target_id}` زیادکرا.")
        try:
            bot.send_message(target_id, f"🎁 **دیاری!** ئەدمین بڕی `{amount}` خاڵی خستە سەر هەژمارەکەت.")
        except: pass
    except:
        bot.send_message(message.chat.id, "❌ بڕی خاڵ دەبێت تەنها ژمارە بێت.")

# --- کرداری دروستکردنی کۆدی دیاری ---
def create_gift_handler(call):
    if not is_admin(call.from_user.id): return
    msg = bot.edit_message_text("💎 **بڕی خاڵ بۆ ئەم کۆدە بنووسە:**",
                               chat_id=call.message.chat.id, message_id=call.message.message_id)
    bot.register_next_step_handler(msg, process_create_gift_final)

def process_create_gift_final(message):
    try:
        amount = int(message.text)
        # دروستکردنی کۆدێکی ٨ پیتی
        code = "OS-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
        conn = sqlite3.connect('bot_data.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO gift_codes (code, points) VALUES (?, ?)", (code, amount))
        conn.commit()
        conn.close()
        
        bot.send_message(message.chat.id, f"✅ **کۆدی دیاری دروستکرا:**\n\n`{code}`\n💎 **بڕی خاڵ:** {amount}", parse_mode='Markdown')
    except:
        bot.send_message(message.chat.id, "❌ تەنها ژمارە بنووسە.")

# --- نیشاندانی خزمەتگوزارییەکان ---
def show_services(call):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton("📸 ئینستاگرام", callback_data="service_instagram"),
        types.InlineKeyboardButton("📱 تێلیگرام", callback_data="service_telegram")
    )
    keyboard.row(
        types.InlineKeyboardButton("🎵 تیک تۆک", callback_data="service_tiktok"),
        types.InlineKeyboardButton("📘 فەیسبووک", callback_data="service_facebook")
    )
    keyboard.row(
        types.InlineKeyboardButton("🐦 تویتەر", callback_data="service_twitter"),
        types.InlineKeyboardButton("📺 یوتیوب", callback_data="service_youtube")
    )
    keyboard.row(
        types.InlineKeyboardButton("🔙 گەڕانەوە", callback_data="back_to_main")
    )
    
    bot.edit_message_text("""🛒 **بەشی خزمەتگوزارییەکان**

ئەو سۆشیاڵ میدیایە هەڵبژێرە کە دەتەوێت خزمەتگوزاری بۆ داوا بکەیت:""", 
                         chat_id=call.message.chat.id,
                         message_id=call.message.message_id,
                         reply_markup=keyboard,
                         parse_mode='Markdown')

def show_service_details(call):
    service = call.data.replace("service_", "")
    
    if service == "instagram":
        services_list = SERVICES['instagram']['followers']
        text = "📸 **خزمەتگوزارییەکانی ئینستاگرام**\n\n"
    elif service == "telegram":
        services_list = SERVICES['telegram']['members']
        text = "📱 **خزمەتگوزارییەکانی تێلیگرام**\n\n"
    else:
        services_list = []
        text = f"**خزمەتگوزارییەکانی {service}**\n\n"
    
    keyboard = types.InlineKeyboardMarkup()
    
    for idx, service_item in enumerate(services_list):
        keyboard.row(
            types.InlineKeyboardButton(
                f"{service_item['name']} - {service_item['price']} خاڵ", 
                callback_data=f"order_{service}_{idx}"
            )
        )
    
    keyboard.row(types.InlineKeyboardButton("🔙 گەڕانەوە", callback_data="services"))
    
    bot.edit_message_text(text + "خزمەتگوزارییەک هەڵبژێرە:",
                         chat_id=call.message.chat.id,
                         message_id=call.message.message_id,
                         reply_markup=keyboard,
                         parse_mode='Markdown')

def create_service_order(call):
    data = call.data.replace("order_", "")
    service, index = data.split("_")
    index = int(index)
    
    if service == 'instagram':
        service_item = SERVICES['instagram']['followers'][index]
    else:
        service_item = SERVICES['telegram']['members'][index]
    
    msg = bot.edit_message_text(f"""🛒 **داواکردنی: {service_item['name']}**

💵 **نرخ:** {service_item['price']} خاڵ بۆ هەر 1000 دانە
────────────────
📥 **ئێستا لینکەکە بنێرە:**""",
                         chat_id=call.message.chat.id,
                         message_id=call.message.message_id,
                         parse_mode='Markdown')
    
    bot.register_next_step_handler(msg, process_order_link, service_item)

def process_order_link(message, service_item):
    link = message.text
    msg = bot.send_message(message.chat.id, f"📊 **بڕی داواکراو بنووسە:**")
    bot.register_next_step_handler(msg, process_order_quantity, service_item, link)

def process_order_quantity(message, service_item, link):
    user_id = message.from_user.id
    
    try:
        quantity = int(message.text)
        if quantity < 100:
            bot.send_message(message.chat.id, "❌ کەمترین بڕی داواکراو 100 دانەیە")
            return start(message)
    except:
        bot.send_message(message.chat.id, "❌ تکایە تەنها ژمارە بنووسە")
        return start(message)
    
    cost = (quantity / 1000) * service_item['price']
    cost = round(cost)
    
    user = get_user(user_id)
    if user[4] < cost:
        bot.send_message(message.chat.id, f"❌ خاڵەکانت بەش ناکات. پێویستت بە {cost} خاڵ هەیە")
        return start(message)
    
    update_user_points(user_id, -cost)
    
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    order_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''INSERT INTO orders 
                     (user_id, service_type, quantity, link, order_date) 
                     VALUES (?, ?, ?, ?, ?)''',
                  (user_id, service_item['name'], quantity, link, order_date))
    
    order_id = cursor.lastrowid
    
    cursor.execute("UPDATE users SET orders_count = orders_count + 1, spent_points = spent_points + ? WHERE user_id = ?",
                  (cost, user_id))
    
    conn.commit()
    conn.close()
    
    bot.send_message(message.chat.id, f"✅ **داواکاری تۆمارکرا!**\n📦 ژمارە: `{order_id}`\n📊 بڕ: {quantity}\n💎 تێچوو: {cost} خاڵ", parse_mode='Markdown')
    bot.send_message(ADMIN_ID, f"🆕 **داواکاری نوێ**\n🆔 `{user_id}`\n📦 {service_item['name']}\n🔗 {link}\n📊 بڕ: {quantity}")
    start(message)

# --- هەژمار و ئامارەکان ---
def show_account(call):
    user = get_user(call.from_user.id)
    if not user: return
    
    user_id, username, first_name, join_date, points, invited_by, shares, spent_points, orders_count, today_messages = user
    
    account_text = f"""👤 **زانیارییەکانی هەژمارەکەت**

🏷 **ناو:** {first_name}
🆔 **ئایدی:** `{user_id}`
────────────────
💎 **خاڵەکانت:** {points}
👥 **بانگهێشتەکان:** {shares}
💰 **خاڵی خەرجکراو:** {spent_points}
📦 **کۆی داواکارییەکان:** {orders_count}
────────────────
📅 **بەروار:** {join_date[:10]}"""

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("🔙 گەڕانەوە", callback_data="back_to_main"))
    bot.edit_message_text(account_text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=keyboard, parse_mode='Markdown')

def show_earn_points(call):
    user_id = call.from_user.id
    invite_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(types.InlineKeyboardButton("🔙 گەڕانەوە", callback_data="back_to_main"))
    
    bot.edit_message_text(f"💰 **کۆکردنەوەی خاڵ**\n\n🔗 لینکی بانگهێشتی تۆ:\n`{invite_link}`\n\nبۆ هەر کەسێک ٥ خاڵ وەردەگریت.", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=keyboard, parse_mode='Markdown')

def show_buy_points(call):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("🔙 گەڕانەوە", callback_data="back_to_main"))
    bot.edit_message_text("💳 **بۆ کڕینی خاڵ پەیوەندی بکە بە ئەدمین:** @FFJFF5", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=keyboard)

def show_my_points(call):
    user = get_user(call.from_user.id)
    points = user[4] if user else 0
    bot.answer_callback_query(call.id, f"🎯 خاڵەکانت: {points} خاڵ")

def show_my_orders(call):
    user_id = call.from_user.id
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY order_id DESC LIMIT 5", (user_id,))
    orders = cursor.fetchall()
    conn.close()
    
    text = "📦 **دواین 5 داواکاریت:**\n\n" if orders else "📭 هیچ داواکارییەکت نییە."
    for order in orders:
        text += f"🔹 #{order[0]} | {order[2]} | {order[3]} دانە | {order[5]}\n"
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("🔙 گەڕانەوە", callback_data="back_to_main"))
    bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=keyboard, parse_mode='Markdown')

# --- پانێڵی بەڕێوەبەر (Admin Panel) ---
@bot.message_handler(commands=['admin'])
def admin_command(message):
    if is_admin(message.from_user.id): admin_panel(message)

def admin_panel(call):
    m = call.message if isinstance(call, types.CallbackQuery) else call
    stats = get_user_stats()
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(types.InlineKeyboardButton("🔒 داخستن", callback_data="lock_bot"), types.InlineKeyboardButton("🔓 کردنەوە", callback_data="unlock_bot"))
    keyboard.row(types.InlineKeyboardButton("📊 ئامارەکان", callback_data="statistics"), types.InlineKeyboardButton("🎁 بەشی دیاری", callback_data="rshq_panel"))
    keyboard.row(types.InlineKeyboardButton("🔄 نوێکردنەوە", callback_data="admin_panel"))
    
    text = f"🎮 **پانێڵی ئەدمین**\n\n👥 میمبەر: {stats[0]}\n💎 خاڵ: {stats[1]}\n📦 داواکاری: {stats[2]}"
    if isinstance(call, types.CallbackQuery):
        bot.edit_message_text(text, chat_id=m.chat.id, message_id=m.message_id, reply_markup=keyboard)
    else:
        bot.send_message(m.chat.id, text, reply_markup=keyboard)

def show_rshq_panel(call):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(types.InlineKeyboardButton("➕ زیادکردنی خاڵ", callback_data="add_points"), types.InlineKeyboardButton("🎁 دروستکردنی کۆد", callback_data="create_gift"))
    keyboard.row(types.InlineKeyboardButton("🔙 گەڕانەوە", callback_data="back_to_admin"))
    bot.edit_message_text("🎮 **بەشی بەڕێوەبردنی خاڵەکان:**", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=keyboard)

def lock_bot(call):
    set_setting('bot_locked', 'true')
    bot.answer_callback_query(call.id, "بۆتەکە داخرا")
    admin_panel(call)

def unlock_bot(call):
    set_setting('bot_locked', 'false')
    bot.answer_callback_query(call.id, "بۆتەکە کرایەوە")
    admin_panel(call)

def show_statistics(call):
    stats = get_user_stats()
    bot.send_message(call.message.chat.id, f"📊 **ئاماری گشتی:**\n\nمیمبەر: {stats[0]}\nخاڵی گشتی: {stats[1]}\nداواکارییەکان: {stats[2]}")

def use_gift_code(call):
    msg = bot.edit_message_text("🎁 **کۆدی دیاری بنووسە:**", chat_id=call.message.chat.id, message_id=call.message.message_id)
    bot.register_next_step_handler(msg, process_gift_code)

def process_gift_code(message):
    code = message.text
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT points FROM gift_codes WHERE code = ? AND is_used = 0", (code,))
    gift = cursor.fetchone()
    if gift:
        update_user_points(message.from_user.id, gift[0])
        cursor.execute("UPDATE gift_codes SET is_used = 1, used_by = ? WHERE code = ?", (message.from_user.id, code))
        conn.commit()
        bot.send_message(message.chat.id, f"✅ پیرۆزە! `{gift[0]}` خاڵت وەرگرت.")
    else:
        bot.send_message(message.chat.id, "❌ کۆدەکە هەڵەیە یان بەکارهێنراوە.")
    conn.close()
    start(message)

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    if not message.text.startswith('/'): start(message)

# --- دەستپێکردنی کۆتایی ---
if __name__ == "__main__":
    init_db()
    print("🎯 بۆتەکە بە سەرکەوتوویی داگیرسا...")
    # بۆ چارەسەری ئێرۆری Conflict
    try:
        bot.delete_webhook()
        bot.infinity_polling(timeout=60, long_polling_timeout=30)
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(5)