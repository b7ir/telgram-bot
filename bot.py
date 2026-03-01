import sqlite3
import telebot
from telebot import types
import requests
import json
import os
from datetime import datetime
import random
import string
import time
import threading

# وەرگرتنی توکن لە ڕێگەی Variable کانی Railway
token = os.getenv("BOT_TOKEN") 
ADMIN_ID = 1621554170
CHANNEL = '@onestore6'
ADMINS = [1621554170]
PHONE_NUMBER = "076788"

bot = telebot.TeleBot(token)

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

SERVICES = {
    'tg_members': [
        {'name': '👥 ئەندام کەناڵ و گروپ تێلیگرام گەرەنتی (60) ڕۆژ 👥', 'price': 1500},
        {'name': '👤 ئەندامی تێلیگرام جێگیر (30) ڕۆژ 👤', 'price': 1200},
        {'name': '👤 ئەندامی تێلیگرام جێگیر (90) ڕۆژ 👤', 'price': 1800},
        {'name': '👤 ئەندامی تێلیگرام عەرەب گەرەنتی (30) ڕۆژ 👤', 'price': 2500},
        {'name': '👤 ئەندام کەناڵ و گروپ تێلیگرام گەرەنتی (180) ڕۆژ 👤', 'price': 3000},
        {'name': '👤 ئەندام ئۆنلاین کەناڵ و گروپ گەرەنتی (30) ڕۆژ 👤', 'price': 3500},
    ],
    'tg_views': [
        {'name': '👁 بینەری پۆستی کەناڵ تێلیگرام', 'price': 100},
        {'name': '👁 بینەری کەناڵ تێلیگرام (1) پۆست', 'price': 150},
        {'name': '👁 بینەری کەناڵ تێلیگرام (5) پۆست', 'price': 500},
        {'name': '👁 بینەری کەناڵ تێلیگرام (10) پۆست', 'price': 1000},
        {'name': '👁 بینەری کەناڵ تێلیگرام (15) پۆست', 'price': 1500},
        {'name': '👁 بینەری کەناڵ تێلیگرام (20) پۆست', 'price': 2000},
        {'name': '👁 بینەری کەناڵ تێلیگرام (30) پۆست', 'price': 3000},
        {'name': '👁 بینەری کەناڵ تێلیگرام (50) پۆست', 'price': 4500},
        {'name': '👁 بینەری ستۆری تێلیگرام 👀', 'price': 800},
        {'name': '✨ بووست کەناڵ کردنەوەی ستۆری گەرەنتی (1) ڕۆژ', 'price': 4000},
        {'name': '🤩 بووست کەناڵ کردنەوەی ستۆری گەرەنتی (1) ڕۆژ', 'price': 4000},
        {'name': '✨ بووست کەناڵ کردنەوەی ستۆری گەرەنتی (30) ڕۆژ', 'price': 25000},
    ],
    'tg_reactions': [
        {'name': 'ریاکشن پۆست جۆر ( 👍 😍 ❤️ 🔥 )', 'price': 300},
        {'name': 'ریاکشن پۆست جۆر ( ❤️ 🔥 👍 🎉 )', 'price': 300},
        {'name': 'ریاکشن پۆست جۆر ( 👎 🤩 😢 💩 )', 'price': 300},
        {'name': 'ریاکشن پۆست جۆر ( ❤️ 💯 🎉 🏆 )', 'price': 300},
        {'name': 'ریاکشن پۆست جۆر ( 🍓 🎄 🦄 🕊 )', 'price': 300},
        {'name': 'ریاکشن پۆست جۆر ( 💔 💋 )', 'price': 300},
        {'name': 'ریاکشن پۆست جۆر ( 👏 🤣 )', 'price': 300},
        {'name': 'ریاکشن پۆست جۆر ( 👎 💔 )', 'price': 300},
        {'name': 'ریاکشن پۆست جۆر ( 😱 😢 )', 'price': 300},
        {'name': 'ریاکشن پۆست جۆر ( 💔 )', 'price': 200},
        {'name': 'ریاکشن پۆست جۆر ( 😈 )', 'price': 200},
        {'name': 'ریاکشن پۆست جۆر ( ❤️ )', 'price': 200},
        {'name': 'ریاکشن پۆست جۆر ( 🔥 )', 'price': 200},
        {'name': 'ریاکشن پۆست جۆر ( 🤣 )', 'price': 200},
        {'name': 'ریاکشن پۆست جۆر ( 👍 )', 'price': 200},
        {'name': 'ریاکشن پۆست جۆر ( 👏 )', 'price': 200},
        {'name': 'ریاکشن پۆست جۆر ( 🏆 )', 'price': 200},
        {'name': 'ریاکشن پۆست جۆر ( 👻 )', 'price': 200},
        {'name': 'ریاکشن پۆست جۆر ( 😭 )', 'price': 200},
        {'name': 'ریاکشن پۆست جۆر ( 😱 )', 'price': 200},
        {'name': 'ریاکشن پۆست جۆر ( 💯 )', 'price': 200},
        {'name': 'ریاکشن پۆست جۆر ( 🥰 )', 'price': 200},
        {'name': 'ریاکشن پۆست جۆر ( 🍓 )', 'price': 200},
        {'name': 'ریاکشن پۆست جۆر ( 💋 )', 'price': 200},
        {'name': 'ریاکشن پۆست جۆر ( 🙈 )', 'price': 200},
        {'name': 'ریاکشن پۆست جۆر ( 😘 )', 'price': 200},
        {'name': 'ریاکشن پۆست جۆر ( 💅 )', 'price': 200},
        {'name': 'ریاکشن پۆست جۆر ( 😡 )', 'price': 200},
        {'name': 'ریاکشن پۆست جۆر ( 🫡 )', 'price': 200},
        {'name': 'ریاکشن پۆست جۆر ( ❤️‍🔥 )', 'price': 200},
    ],
    'youtube': [
        {'name': '👤 سەبسکرایبی یوتیوب لە ڕێگەی ڕیکلامەوە 👤', 'price': 8000},
        {'name': '👤 سەبسکرایبی یوتیوب ڕاستەقینە 👤', 'price': 6000},
        {'name': '👍 ڵایکی پۆست یوتیوب زۆر خێرا 👍', 'price': 1500},
        {'name': '👍 ڵایکی پۆست یوتیوب هەرزان 👍', 'price': 800},
        {'name': '👍 ڵایکی پۆست یوتیوب بە گەرەنتی 👍', 'price': 2000},
        {'name': '🇸🇦 کۆمێنتی یوتیوب هەڕەمەکی عەرەب', 'price': 3500},
        {'name': '↪️ شەێری پۆست یوتیوب', 'price': 1200},
        {'name': '👁 بینەری پۆست یوتیوب گەرەنتی هەتاهەتای 👁', 'price': 3500},
        {'name': '👁 بینەری پۆست یوتیوب ڕاستەقینە 👁', 'price': 4500},
        {'name': '👁 بینەری لایف یوتیوب ڕاستەقینە 👀', 'price': 5000},
    ],
    'snapchat': [
        {'name': '👻 فۆڵۆوەرەکانی سناپچات ڕاستەقینە 👻', 'price': 7000},
        {'name': '👻 فۆڵۆوەرەکانی سناپچات ڕووسیا 👻', 'price': 4000},
        {'name': '👻 فۆڵۆوەرەکانی سناپچات بەنگلادیش 👻', 'price': 3500},
        {'name': '👻 فۆڵۆوەرەکانی سناپچات عەرەبی 👻', 'price': 6000},
        {'name': '👻 فۆڵۆوەرەکانی سناپچات پاکستانی 👻', 'price': 4000},
        {'name': '👻 فۆڵۆوەرەکانی سناپچات تورکی 👻', 'price': 4500},
        {'name': '👻 فۆڵۆوەرەکانی سناپچات کوالێتی بەرز 👻', 'price': 5500},
        {'name': '❤️ ڵایکەکانی سناپچات عەرەبی ❤️', 'price': 2500},
        {'name': '💕 ڵایکەکانی سناپچات عەرەبی 💕', 'price': 2500},
        {'name': '👁 بینەری ڤیدیۆی سپۆتلایت سناپچات دوبەی', 'price': 1500},
        {'name': '👁 بینەری ڤیدیۆی سپۆتلایت سناپچات عومان', 'price': 1500},
        {'name': '👁 بینەری ڤیدیۆی سپۆتلایت سناپچات قەتەر', 'price': 1500},
        {'name': '👁 بینەری ڤیدیۆی سپۆتلایت سناپچات کوێت', 'price': 1500},
        {'name': '👁 بینەری ڤیدیۆی سپۆتلایت سناپچات عێراق', 'price': 1500},
    ],
    'tiktok': [
        {'name': '👤 فۆڵۆوەرەکانی تیک تۆک کوالێتی مامناوەند', 'price': 2000},
        {'name': '👤 فۆڵۆوەرەکانی تیک تۆک کوالێتی بەرز', 'price': 2500},
        {'name': '👤 فۆڵۆوەرەکانی تیک تۆک ڕاستەقینەی ئینگلیزی', 'price': 4000},
        {'name': '👤 فۆڵۆوەرەکانی تیک تۆک هەرزان', 'price': 1000},
        {'name': '👤 فۆڵۆوەرەکانی تیک تۆک زۆر بەرز و خێرا', 'price': 3000},
        {'name': '❤️ ڵایک پۆست تیک تۆک جێگیر', 'price': 2000},
        {'name': '❤️ ڵایک پۆست تیک تۆک کوالێتی بەرز', 'price': 2200},
        {'name': '❤️ ڵایک پۆست تیک تۆک زۆر هەرزان', 'price': 1200},
        {'name': '💥 ڵایک + بینەر پۆست تیک تۆک', 'price': 2000},
        {'name': '🔰 سەیڤی پۆست تیک تۆک', 'price': 1000},
        {'name': '🔰 سەیڤی پۆست تیک تۆک هەرزان', 'price': 800},
        {'name': '🔄 شەێری پۆست تیک تۆک خێرایە', 'price': 1500},
        {'name': '🔄 شەێری پۆست تیک تۆک هەرزان', 'price': 900},
        {'name': '🔴 کۆمێنتی پۆستی تیک تۆک ئیمۆجی', 'price': 2000},
        {'name': '🟢 کۆمێنتی پۆستی تیک تۆک ئیمۆجی', 'price': 2000},
        {'name': '👁 بینەری پۆست تیک تۆک', 'price': 200},
        {'name': '👁 بینەری پۆست تیک تۆک کوالێتی باش', 'price': 400},
        {'name': '📽 بینەری لایف تیک تۆک (15) خولەک', 'price': 3000},
        {'name': '📽 بینەری لایف تیک تۆک (30) خولەک', 'price': 5000},
        {'name': '📽 بینەری لایف تیک تۆک (60) خولەک', 'price': 9000},
        {'name': '🔥 ڵایکی لایف تیک تۆک زۆر هەرزان', 'price': 1000},
        {'name': '💎 خاڵ چاڵێنجەکانی لایف تیک تۆک', 'price': 5000}
    ],
    'instagram': [
        {'name': '👥 فۆڵۆوەرزی ئینستاگرام جێگیر', 'price': 2000},
        {'name': '❤️ ڵایکی ئینستاگرام خێرا', 'price': 1000}
    ],
    'facebook': [
        {'name': '👥 فۆڵۆوەرزی پەیجی فەیسبووک', 'price': 2500},
        {'name': '👍 ڵایکی پۆستی فەیسبووک', 'price': 1500}
    ],
    'twitter': [
        {'name': '👥 فۆڵۆوەرزی تویتەر', 'price': 4000}
    ],
    'whatsapp': [
        {'name': '📞 خزمەتگوزاری واتسئەپ', 'price': 3000}
    ],
    'threads': [
        {'name': '👥 فۆڵۆوەرزی ثریدز', 'price': 2000}
    ],
    'pinterest': [
        {'name': '👥 فۆڵۆوەرزی پینتەرست', 'price': 2000}
    ],
    'free': [
        {'name': '🎁 ١٠ بینەری پۆستی تێلیگرام', 'price': 0},
        {'name': '🎁 ١٠ ڵایکی تیک تۆک', 'price': 0}
    ],
    'cheap': [
        {'name': '📉 فۆڵۆوەرزی هەرزان (ناجێگیر)', 'price': 800}
    ]
}

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

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    
    if call.data == "services":
        show_services(call)
    elif call.data == "service_telegram":
        show_telegram_menu(call)
    elif call.data == "tg_members":
        show_service_details(call, "tg_members")
    elif call.data == "tg_views":
        show_service_details(call, "tg_views")
    elif call.data == "tg_reactions":
        show_service_details(call, "tg_reactions")
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
    elif call.data == "add_points":
        add_points_handler(call)
    elif call.data == "create_gift":
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
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception as e:
            print(f"کێشە لە سڕینەوەی نامە: {e}")
        start(call.message)
    elif call.data == "back_to_admin":
        admin_panel(call)
    elif call.data == "back_to_services":
        show_services(call)
    elif call.data.startswith("service_"):
        show_service_details(call)
    elif call.data.startswith("order_"):
        create_service_order(call)

def show_services(call):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(types.InlineKeyboardButton("🔹 خزمەتگوزاری بێ بەرامبەر 🔹", callback_data="service_free"))
    keyboard.row(
        types.InlineKeyboardButton("📱 تێلیگرام", callback_data="service_telegram"),
        types.InlineKeyboardButton("📸 ئینستاگرام", callback_data="service_instagram")
    )
    keyboard.row(
        types.InlineKeyboardButton("📽 یوتیوب", callback_data="service_youtube"),
        types.InlineKeyboardButton("🎵 تیک تۆک", callback_data="service_tiktok")
    )
    keyboard.row(
        types.InlineKeyboardButton("📞 واتسئەپ", callback_data="service_whatsapp"),
        types.InlineKeyboardButton("📘 فەیسبووک", callback_data="service_facebook")
    )
    keyboard.row(
        types.InlineKeyboardButton("👻 سناپچات", callback_data="service_snapchat"),
        types.InlineKeyboardButton("🐦 تویتەر", callback_data="service_twitter")
    )
    keyboard.row(
        types.InlineKeyboardButton("🧵 ثریدز", callback_data="service_threads"),
        types.InlineKeyboardButton("📌 پینتەرست", callback_data="service_pinterest")
    )
    keyboard.row(types.InlineKeyboardButton("🔹 هەرزانترین خزمەتگوزاری 🔹", callback_data="service_cheap"))
    keyboard.row(
        types.InlineKeyboardButton("گەڕانەوە ⬅️", callback_data="back_to_main")
    )
    
    bot.edit_message_text("""- **لیستی بەشەکان دانەیەکی هەڵبژێرە** 📦""", 
                         chat_id=call.message.chat.id,
                         message_id=call.message.message_id,
                         reply_markup=keyboard,
                         parse_mode='Markdown')

def show_telegram_menu(call):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(types.InlineKeyboardButton("👥 ئەندامانی تێلیگرام", callback_data="tg_members"))
    keyboard.row(types.InlineKeyboardButton("👁 بینەری پۆست و ستۆری", callback_data="tg_views"))
    keyboard.row(types.InlineKeyboardButton("🎭 ریاکشن (کاردانەوە)", callback_data="tg_reactions"))
    keyboard.row(types.InlineKeyboardButton("گەڕانەوە ⬅️", callback_data="back_to_services"))
    
    bot.edit_message_text("📂 **بەشی تێلیگرام یەکێک هەڵبژێرە:**", 
                         chat_id=call.message.chat.id, 
                         message_id=call.message.message_id, 
                         reply_markup=keyboard)

def show_service_details(call, manual_key=None):
    if manual_key:
        service_key = manual_key
    else:
        service_key = call.data.replace("service_", "")
    
    services_list = SERVICES.get(service_key, [])
    
    if not services_list:
        bot.answer_callback_query(call.id, "هیچ خزمەتگوزارییەک لەم بەشەدا نییە!")
        return

    text = f"- **ئەوەی دەتەوێت لە خوارەوە هەڵبژێرە** 🛒"
    
    keyboard = types.InlineKeyboardMarkup()
    
    for idx, service_item in enumerate(services_list):
        keyboard.row(
            types.InlineKeyboardButton(
                f"{service_item['name']}", 
                callback_data=f"order_{service_key}_{idx}"
            )
        )
    
    back_target = "back_to_services"
    if service_key.startswith("tg_"):
        back_target = "service_telegram"
        
    keyboard.row(types.InlineKeyboardButton("گەڕانەوە ⬅️", callback_data=back_target))
    keyboard.row(types.InlineKeyboardButton("🏠 پەرەی سەرەکی", callback_data="back_to_main"))
    
    bot.edit_message_text(text,
                         chat_id=call.message.chat.id,
                         message_id=call.message.message_id,
                         reply_markup=keyboard,
                         parse_mode='Markdown')

def create_service_order(call):
    data = call.data.replace("order_", "").split("_")
    
    if len(data) == 3:
        service_key = f"{data[0]}_{data[1]}"
        index = int(data[2])
    else:
        service_key = data[0]
        index = int(data[1])
    
    service_item = SERVICES[service_key][index]
    
    msg = bot.edit_message_text(f"""💰 **نرخ: {service_item['price']} خاڵ (بۆ هەر 1k)**
📉 **کەمترین بڕ: 50**
📈 **زۆرترین بڕ: 50000**

🔢 **تکایە ژمارەی ئەو بڕەی دەتەوێت بنێرە:** 👇""",
                         chat_id=call.message.chat.id,
                         message_id=call.message.message_id,
                         parse_mode='Markdown')
    
    bot.register_next_step_handler(msg, process_order_quantity, service_item)

def process_order_quantity(message, service_item):
    try:
        quantity = int(message.text)
        if quantity < 50:
            bot.send_message(message.chat.id, "❌ کەمترین بڕ ٥٠ دانەیە")
            return
    except:
        bot.send_message(message.chat.id, "❌ تکایە تەنها ژمارە بنووسە")
        return

    msg = bot.send_message(message.chat.id, "🔗 **ئێستا لینکی پۆست یان پڕۆفایڵ بنێرە:**")
    bot.register_next_step_handler(msg, process_order_link_final, service_item, quantity)

def process_order_link_final(message, service_item, quantity):
    user_id = message.from_user.id
    link = message.text
    
    cost = (quantity / 1000) * service_item['price']
    cost = round(cost)
    
    user = get_user(user_id)
    if not user or user[4] < cost:
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
    
    bot.send_message(message.chat.id, f"""✅ **داواکارییەکەت بە سەرکەوتوویی تۆمارکرا!**

📦 **ژمارەی داواکاری:** `{order_id}`
🎯 **خزمەتگوزاری:** {service_item['name']}
🔗 **لینک:** {link}
📊 **بڕ:** {quantity}
💎 **تێچوو:** {cost} خاڵ
⏳ **بارودۆخ:** چاوەڕوانکردن""", parse_mode='Markdown')
    
    user = get_user(user_id)
    admin_msg = f"""🆕 **داواکارییەکی نوێ**

👤 **بەکارهێنەر:** {user[2]} (@{user[1]})
🆔 **ئایدی:** `{user_id}`
📦 **داواکاری:** {service_item['name']}
🔗 **لینک:** {link}
📊 **بڕ:** {quantity}
💎 **تێچوو:** {cost} خاڵ"""

    bot.send_message(ADMIN_ID, admin_msg, parse_mode='Markdown')
    start(message)

def show_account(call):
    user = get_user(call.from_user.id)
    if not user:
        return
    
    user_id, username, first_name, join_date, points, invited_by, shares, spent_points, orders_count, today_messages = user
    
    account_text = f"""👤 **زانیارییەکانی هەژمارەکەت**

🏷 **ناو:** {first_name}
📧 **یوزەرنییم:** @{username if username else 'بێ ناسناو'}
🆔 **ئایدی:** `{user_id}`
────────────────
💎 **خاڵەکانت:** {points}
👥 **بانگهێشتەکان:** {shares}
💰 **خاڵی خەرجکراو:** {spent_points}
📦 **کۆی داواکارییەکان:** {orders_count}
────────────────
📅 **بەرواری بەشداریکردن:** {join_date[:10]}"""

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("گەڕانەوە ⬅️", callback_data="back_to_main"))
    
    bot.edit_message_text(account_text,
                         chat_id=call.message.chat.id,
                         message_id=call.message.message_id,
                         reply_markup=keyboard,
                         parse_mode='Markdown')

def show_earn_points(call):
    user_id = call.from_user.id
    invite_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton("🔗 لینکی بانگهێشت", callback_data="invite_link"),
        types.InlineKeyboardButton("📲 ڕادەستکردنی ئەکاونت", callback_data="submit_accounts")
    )
    keyboard.row(
        types.InlineKeyboardButton("🔄 گۆڕینەوەی خاڵ", callback_data="exchange_points"),
        types.InlineKeyboardButton("💰 کڕینی خاڵ", callback_data="buy_points")
    )
    keyboard.row(
        types.InlineKeyboardButton("گەڕانەوە ⬅️", callback_data="back_to_main")
    )
    
    bot.edit_message_text(f"""💰 **بەشی کۆکردنەوەی خاڵ**

🎯 **ڕێگاکانی بەدەستهێنانی خاڵ:**

1. **بڵاوکردنەوەی لینکی بانگهێشت** 🫂
   - بۆ هەر هاوڕێیەک 5 خاڵ وەردەگریت
   - لینکی تۆ: `{invite_link}`

2. **ڕادەستکردنی ئەکاونت بە گەشەپێدەر** 📲
   - لە 100 بۆ 400 خاڵ بەپێی وڵاتی ئەکاونتەکە

3. **کڕینی خاڵ بە شێوەی ڕاستەوخۆ** 💳
   - بە نرخێکی گونجاو

4. **گۆڕینەوەی خاڵی فاست فۆڵۆوەر یان هتد** 🔄
   - 2000 خاڵی فاست = 500 خاڵی بۆت""",
                         chat_id=call.message.chat.id,
                         message_id=call.message.message_id,
                         reply_markup=keyboard,
                         parse_mode='Markdown')

def show_buy_points(call):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton("💳 کڕین بە ڕەسید", callback_data="charge_balance"),
        types.InlineKeyboardButton("🎫 کارتی بارگاوی کردن", callback_data="charge_card")
    )
    keyboard.row(
        types.InlineKeyboardButton("گەڕانەوە ⬅️", callback_data="back_to_main")
    )
    
    bot.edit_message_text("""💳 **بەشی کڕینی خاڵ**

💎 **نرخی خاڵەکان:**
- 1$ = 1000 خاڵ
- 5$ = 5000 خاڵ  
- 10$ = 11000 خاڵ

📞 **بۆ کڕین پەیوەندی بکە بە:** @BradostZangana

💰 **ڕێگاکانی پارەدان:**
- ئاسیاواڵێت، فاست پەی
- زەین کاش، کۆڕەک، ئاسیا
- باینانس (USDT)، پەیپاڵ""",
                         chat_id=call.message.chat.id,
                         message_id=call.message.message_id,
                         reply_markup=keyboard,
                         parse_mode='Markdown')

def show_my_points(call):
    user = get_user(call.from_user.id)
    points = user[4] if user else 0
    bot.answer_callback_query(call.id, f"🎯 خاڵەکانت لە ئێستادا: {points} خاڵە")

def show_my_orders(call):
    user_id = call.from_user.id
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY order_id DESC LIMIT 5", (user_id,))
    orders = cursor.fetchall()
    conn.close()
    
    if not orders:
        text = "📭 **هیچ داواکارییەکی پێشووت نییە**"
    else:
        text = "📦 **دواین 5 داواکاریت**\n\n"
        for order in orders:
            text += f"**داواکاری #{order[0]}**\n"
            text += f"خزمەتگوزاری: {order[2]}\n"
            text += f"بڕ: {order[3]}\n"
            text += f"بارودۆخ: {order[5]}\n"
            text += f"بەروار: {order[6][:10]}\n"
            text += "────────────────\n"
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("گەڕانەوە ⬅️", callback_data="back_to_main"))
    
    bot.edit_message_text(text,
                         chat_id=call.message.chat.id,
                         message_id=call.message.message_id,
                         reply_markup=keyboard,
                         parse_mode='Markdown')

@bot.message_handler(commands=['admin'])
def admin_command(message):
    if not is_admin(message.from_user.id):
        return
    admin_panel(message)

def admin_panel(call):
    if isinstance(call, types.CallbackQuery):
        message = call.message
        u_id = call.from_user.id
    else:
        message = call
        u_id = call.from_user.id
    
    if not is_admin(u_id):
        return
    
    total_users = get_total_users()
    today_users = get_today_users()
    stats = get_user_stats()
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton("🔒 داخستنی بۆت", callback_data="lock_bot"),
        types.InlineKeyboardButton("🔓 کردنەوەی بۆت", callback_data="unlock_bot")
    )
    keyboard.row(
        types.InlineKeyboardButton("👥 بەڕێوەبردنی ئەدمین", callback_data="manage_admins"),
        types.InlineKeyboardButton("📊 ئامارەکان", callback_data="statistics")
    )
    keyboard.row(
        types.InlineKeyboardButton("📢 بەشی ڕاگەیاندن", callback_data="broadcast"),
        types.InlineKeyboardButton("🎁 بەشی دیاری", callback_data="rshq_panel")
    )
    keyboard.row(
        types.InlineKeyboardButton("گەڕانەوە ⬅️", callback_data="back_to_main"),
        types.InlineKeyboardButton("🔄 نوێکردنەوە", callback_data="admin_panel")
    )
    
    text = f"""🎮 **پانێڵی بەڕێوەبەری بۆت**

👥 **کۆی بەکارهێنەران:** {total_users}
📈 **بەکارهێنەرانی ئەمڕۆ:** {today_users}
💎 **کۆی خاڵەکان:** {stats[1]}
📦 **کۆی داواکارییەکان:** {stats[2]}
💰 **خاڵی خەرجکراو:** {stats[3]}
⚙️ **بارودۆخی بۆت:** {'کراوەیە ✅' if get_setting('bot_locked') != 'true' else 'داخراوە 🔒'}

کردارێک هەڵبژێرە:"""
    
    if isinstance(call, types.CallbackQuery):
        bot.edit_message_text(text, chat_id=message.chat.id, message_id=message.message_id,
                            reply_markup=keyboard, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, text, reply_markup=keyboard, parse_mode='Markdown')

def show_rshq_panel(call):
    if not is_admin(call.from_user.id):
        return
    
    balance = 0
    currency = "$"
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton("➕ زیادکردنی خاڵ", callback_data="add_points"),
        types.InlineKeyboardButton("🎁 دروستکردنی کۆدی دیاری", callback_data="create_gift")
    )
    keyboard.row(
        types.InlineKeyboardButton("✅ کردنەوەی ڕەشق", callback_data="enable_rshq"),
        types.InlineKeyboardButton("❌ داخستنی ڕەشق", callback_data="disable_rshq")
    )
    keyboard.row(
        types.InlineKeyboardButton("گەڕانەوە ⬅️", callback_data="back_to_admin")
    )
    keyboard.row(types.InlineKeyboardButton("🏠 پەرەی سەرەکی", callback_data="back_to_main"))
    
    bot.edit_message_text(f"""🎮 **بەشی بەڕێوەبردنی خزمەتگوزارییەکان**

💰 **ڕەسیدی ماڵپەڕ:** {balance} {currency}
⚙️ **بارودۆخی وەرگرتن:** {'کراوەیە ✅' if get_setting('rshq_enabled') != 'false' else 'داخراوە ❌'}

کردارێک هەڵبژێرە:""",
                         chat_id=call.message.chat.id,
                         message_id=call.message.message_id,
                         reply_markup=keyboard,
                         parse_mode='Markdown')

def add_points_handler(call):
    if not is_admin(call.from_user.id): return
    msg = bot.edit_message_text("👤 **ئایدی ئەو کەسە بنێرە کە دەتەوێت خاڵی بۆ زیاد بکەیت:**",
                               chat_id=call.message.chat.id, message_id=call.message.message_id)
    bot.register_next_step_handler(msg, process_add_points_id)

def process_add_points_id(message):
    try:
        target_id = int(message.text)
        msg = bot.send_message(message.chat.id, f"💎 **بڕی ئەو خاڵە بنێرە کە دەتەوێت بۆ `{target_id}` زیاد بکرێت:**")
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
        bot.send_message(message.chat.id, "❌ بڕی خاڵ دەبێت تەنها ژمارە بنووسە.")

def create_gift_handler(call):
    if not is_admin(call.from_user.id): return
    msg = bot.edit_message_text("💎 **بڕی خاڵ بۆ ئەم کۆدە بنووسە:**",
                               chat_id=call.message.chat.id, message_id=call.message.message_id)
    bot.register_next_step_handler(msg, process_create_gift_final)

def process_create_gift_final(message):
    try:
        amount = int(message.text)
        code = "GIFT-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        conn = sqlite3.connect('bot_data.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO gift_codes (code, points) VALUES (?, ?)", (code, amount))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, f"✅ **کۆدی دیاری دروستکرا:**\n\n`{code}`\n💎 **بڕی خاڵ:** {amount}", parse_mode='Markdown')
    except:
        bot.send_message(message.chat.id, "❌ تەنها ژمارە بنووسە.")

def manage_admins(call):
    if not is_admin(call.from_user.id):
        return
    
    admins_list = get_admins()
    admins_text = "\n".join([f"• `{admin_id}`" for admin_id in admins_list[:5]])
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton("➕ زیادکردنی ئەدمین", callback_data="add_admin"),
        types.InlineKeyboardButton("🗑 سڕینەوەی ئەدمینەکان", callback_data="delete_admins")
    )
    keyboard.row(
        types.InlineKeyboardButton("گەڕانەوە ⬅️", callback_data="back_to_admin"),
        types.InlineKeyboardButton("🏠 پەرەی سەرەکی", callback_data="back_to_main")
    )
    
    bot.edit_message_text(f"""👥 **بەڕێوەبردنی ئەدمینەکان**

دواین 5 ئەدمین:
{admins_text}""",
                         chat_id=call.message.chat.id,
                         message_id=call.message.message_id,
                         reply_markup=keyboard,
                         parse_mode='Markdown')

def add_admin_handler(call):
    if not is_admin(call.from_user.id):
        return
    
    msg = bot.edit_message_text("👤 **ئایدی ئەو کەسە بنێرە کە دەتەوێت بیکەیت بە ئەدمین:**",
                               chat_id=call.message.chat.id,
                               message_id=call.message.message_id)
    bot.register_next_step_handler(msg, process_add_admin)

def process_add_admin(message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        new_admin_id = int(message.text)
        add_admin(new_admin_id)
        bot.send_message(message.chat.id, f"✅ بەکارهێنەری `{new_admin_id}` کرا بە ئەدمین")
        
        try:
            bot.send_message(new_admin_id, "🎉 تۆ کرایت بە ئەدمین لە ناو بۆت!\nفەرمانی /admin بەکاربهێنە بۆ بینینی پانێڵ")
        except:
            pass
            
    except ValueError:
        bot.send_message(message.chat.id, "❌ تکایە تەنها ئایدی بە ژمارە بنووسە")
    
    admin_panel(message)

def delete_admins(call):
    if not is_admin(call.from_user.id):
        return
    
    remove_all_admins()
    bot.answer_callback_query(call.id, "✅ هەموو ئەدمینەکان سڕانەوە")
    admin_panel(call.message)

def show_statistics(call):
    if not is_admin(call.from_user.id):
        return
    
    total_users = get_total_users()
    today_users = get_today_users()
    stats = get_user_stats()
    
    bot.edit_message_text(f"""📊 **ئاماری گشتی**

👥 **کۆی بەکارهێنەران:** {total_users}
📈 **بەکارهێنەرانی ئەمڕۆ:** {today_users}
💎 **کۆی خاڵەکان:** {stats[1]}
📦 **کۆی داواکارییەکان:** {stats[2]}
💰 **خاڵی خەرجکراو:** {stats[3]}
⚙️ **بارودۆخی بۆت:** {'کراوەیە ✅' if get_setting('bot_locked') != 'true' else 'داخراوە 🔒'}""",
                         chat_id=call.message.chat.id,
                         message_id=call.message.message_id,
                         parse_mode='Markdown')

def show_broadcast(call):
    if not is_admin(call.from_user.id):
        return
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton("📝 نامەی دەقی", callback_data="broadcast_text"),
        types.InlineKeyboardButton("🖼 وێنە", callback_data="broadcast_photo")
    )
    keyboard.row(
        types.InlineKeyboardButton("📹 میدیا", callback_data="broadcast_media"),
        types.InlineKeyboardButton("🔗 فۆروەرد", callback_data="broadcast_forward")
    )
    keyboard.row(
        types.InlineKeyboardButton("🏠 پەرەی سەرەکی", callback_data="back_to_main"),
        types.InlineKeyboardButton("گەڕانەوە ⬅️", callback_data="back_to_admin")
    )
    
    bot.edit_message_text("""📢 **بەشی ناردنی نامە بۆ هەمووان**

جۆری ناردنەکە هەڵبژێرە:""",
                         chat_id=call.message.chat.id,
                         message_id=call.message.message_id,
                         reply_markup=keyboard)

def lock_bot(call):
    if not is_admin(call.from_user.id):
        return
    
    set_setting('bot_locked', 'true')
    bot.answer_callback_query(call.id, "بۆتەکە داخرا ✅")
    admin_panel(call)

def unlock_bot(call):
    if not is_admin(call.from_user.id):
        return
    
    set_setting('bot_locked', 'false')
    bot.answer_callback_query(call.id, "بۆتەکە کرایەوە ✅")
    admin_panel(call)

def use_gift_code(call):
    msg = bot.edit_message_text("🎁 **کۆدی دیاری بنووسە:**",
                               chat_id=call.message.chat.id,
                               message_id=call.message.message_id)
    bot.register_next_step_handler(msg, process_gift_code)

def process_gift_code(message):
    user_id = message.from_user.id
    code = message.text
    
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM gift_codes WHERE code = ? AND is_used = 0", (code,))
    gift = cursor.fetchone()
    
    if gift:
        points = gift[1]
        update_user_points(user_id, points)
        cursor.execute("UPDATE gift_codes SET is_used = 1, used_by = ? WHERE code = ?", 
                      (user_id, code))
        
        bot.send_message(message.chat.id, f"🎉 پیرۆزە! {points} خاڵت وەرگرت لە ڕێگەی کۆدی {code}")
        
        bot.send_message(ADMIN_ID, f"🎁 بەکارهێنەرێک کۆدی بەکارهێنا\nبەکارهێنەر: {user_id}\nکۆد: {code}\nخاڵ: {points}")
    else:
        bot.send_message(message.chat.id, "❌ کۆدەکە هەڵەیە یان پێشتر بەکارهاتووە")
    
    conn.commit()
    conn.close()
    start(message)

@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = """🆘 **ڕێبەری بەکارهێنانی بۆت**

🤖 **بۆتی زیادکردنی فۆڵۆوەرز**
────────────────
📖 **شێوازی کارکردن:**

1. **کۆکردنەوەی خاڵ 💰**
   - بڵاوکردنەوەی لینکی بانگهێشت
   - کڕینی خاڵ بە شێوەی ڕاستەوخۆ

2. **داواکردن 🎯**  
   - جۆری خزمەتگوزاری هەڵبژێرە
   - لینک بنێرە

3. **بەڕێوەبردنی هەژمار 👤**
   - بینینی خاڵەکان
   - بەکارهێنانی کۆدی دیاری

📞 **پشتیوانی:** @BradostZangana
📢 **کەناڵ:** @onestore6"""

    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET today_messages = today_messages + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    
    if get_setting('notifications') == 'on' and not is_admin(user_id):
        try:
            bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
        except:
            pass
    
    if message.text and not message.text.startswith('/'):
        start(message)

if __name__ == "__main__":
    init_db()
    print("🎯 بۆتەکە دەستی بە کارکردن کرد...")
    
    if not get_setting('bot_locked'):
        set_setting('bot_locked', 'false')
    if not get_setting('rshq_enabled'):
        set_setting('rshq_enabled', 'true')
    if not get_setting('notifications'):
        set_setting('notifications', 'on')
    
    for a_id in ADMINS:
        add_admin(a_id)
    
    # چارەسەری ئیرۆری Conflict و Unauthorized
    while True:
        try:
            bot.remove_webhook(drop_pending_updates=True)
            bot.infinity_polling(timeout=60, long_polling_timeout=30)
        except Exception as e:
            print(f"Error occurred: {e}")
            time.sleep(5)