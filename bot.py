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

token = os.getenv("BOT_TOKEN") 
ADMIN_ID = 7598650992
CHANNEL = '@onestore6'
ADMINS = [7598650992]
token = os.getenv("BOT_TOKEN")
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
    'instagram': {
        'followers': [
            {'name': 'متابعين ثابتين', 'price': 1, 'service_id': 9650},
            {'name': 'متابعين غير ثابتين', 'price': 2, 'service_id': 9650},
            {'name': 'متابعين حقيقيين', 'price': 0.5, 'service_id': 9650},
            {'name': 'لايكات', 'price': 15, 'service_id': 9168},
            {'name': 'مشاهدات', 'price': 25, 'service_id': 5132},
        ]
    },
    'telegram': {
        'members': [
            {'name': 'أعضاء قنوات', 'price': 2.1, 'service_id': 8504},
            {'name': 'مشاهدات بوست', 'price': 25, 'service_id': 10401},
        ]
    }
}

def create_order(user_id, service_type, quantity, link):
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    price = quantity * SERVICES['instagram']['followers'][0]['price']
    
    user = get_user(user_id)
    if user[4] < price:
        return False, "رصيدك غير كافي"
    
    update_user_points(user_id, -price)
    
    order_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''INSERT INTO orders 
                     (user_id, service_type, quantity, link, order_date) 
                     VALUES (?, ?, ?, ?, ?)''',
                  (user_id, service_type, quantity, link, order_date))
    
    order_id = cursor.lastrowid
    
    cursor.execute("UPDATE users SET orders_count = orders_count + 1, spent_points = spent_points + ? WHERE user_id = ?",
                  (price, user_id))
    
    conn.commit()
    conn.close()
    
    return True, order_id

def broadcast_message(message_text, message_type='text'):
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    success = 0
    failed = 0
    
    for user_id in users:
        try:
            if message_type == 'text':
                bot.send_message(user_id, message_text)
            success += 1
        except:
            failed += 1
        time.sleep(0.1)
    
    return success, failed

def create_gift_code(points):
    code = f"GIFT{random.randint(1000, 9999)}"
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO gift_codes (code, points) VALUES (?, ?)", (code, points))
    conn.commit()
    conn.close()
    return code

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username or "بلا معرف"
    first_name = message.from_user.first_name or "مستخدم"
    
    if not check_subscription(user_id):
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("📢 اشترك في القناة", url=f"https://t.me/{CHANNEL[1:]}"))
        bot.send_message(message.chat.id,
                        f"""🚸 **عذراً عزيزي** 
🔰 **عليك الاشتراك بقناة البوت أولاً**

📢 **القناة:** {CHANNEL}

‼️ **اشترك ثم ارسل /start**""",
                        reply_markup=keyboard)
        return
    
    if get_setting('bot_locked') == 'true' and not is_admin(user_id):
        bot.send_message(message.chat.id, "⏳ البوت يخضع للتحديث حاليًا، الرجاء المحاولة لاحقًا")
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
        bot.send_message(invited_by, f"🎉 حصلت على 5 نقاط! مستخدم جديد انضم عبر رابطك")
    
    user = get_user(user_id)
    points = user[4] if user else 0
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton(f"🎯 نقاطك: {points}", callback_data="my_points")
    )
    keyboard.row(
        types.InlineKeyboardButton("🛒 الخدمات", callback_data="services"),
        types.InlineKeyboardButton("👤 الحساب", callback_data="account")
    )
    keyboard.row(
        types.InlineKeyboardButton("💰 التجميع", callback_data="earn_points"),
        types.InlineKeyboardButton("🎁 استخدام كود", callback_data="use_gift")
    )
    keyboard.row(
        types.InlineKeyboardButton("🔄 شحن نقاط", callback_data="buy_points"),
        types.InlineKeyboardButton("📊 طلباتي", callback_data="my_orders")
    )
    
    if is_admin(user_id):
        keyboard.row(types.InlineKeyboardButton("🎮 لوحة التحكم", callback_data="admin_panel"))
    
    welcome_text = f"""🎊 **مرحباً بك {first_name}!

🤖 في بوت الرشق المتطور**
────────────────
💎 **نقاطك:** `{points}`
🆔 **ايديك:** `{user_id}`
────────────────
اختر من الأوامر أدناه:"""

    bot.send_message(message.chat.id, welcome_text, 
                    reply_markup=keyboard, parse_mode='Markdown')

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
        back_to_main(call)
    elif call.data == "back_to_admin":
        back_to_admin(call)
    elif call.data.startswith("service_"):
        show_service_details(call)
    elif call.data.startswith("order_"):
        create_service_order(call)

def show_services(call):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton("📸 إنستغرام", callback_data="service_instagram"),
        types.InlineKeyboardButton("📱 تيليجرام", callback_data="service_telegram")
    )
    keyboard.row(
        types.InlineKeyboardButton("🎵 تيك توك", callback_data="service_tiktok"),
        types.InlineKeyboardButton("📘 فيسبوك", callback_data="service_facebook")
    )
    keyboard.row(
        types.InlineKeyboardButton("🐦 تويتر", callback_data="service_twitter"),
        types.InlineKeyboardButton("📺 يوتيوب", callback_data="service_youtube")
    )
    keyboard.row(
        types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")
    )
    
    bot.edit_message_text("""🛒 **قسم الخدمات**

اختر المنصة التي تريد الرشق عليها:""", 
                         chat_id=call.message.chat.id,
                         message_id=call.message.message_id,
                         reply_markup=keyboard,
                         parse_mode='Markdown')

def show_service_details(call):
    service = call.data.replace("service_", "")
    
    if service == "instagram":
        services_list = SERVICES['instagram']['followers']
        text = "📸 **خدمات إنستغرام**\n\n"
    else:
        services_list = []
        text = f"**خدمات {service}**\n\n"
    
    keyboard = types.InlineKeyboardMarkup()
    
    for idx, service_item in enumerate(services_list[:30]):
        keyboard.row(
            types.InlineKeyboardButton(
                f"{service_item['name']} - {service_item['price']} نقطة", 
                callback_data=f"order_{service}_{idx}"
            )
        )
    
    keyboard.row(types.InlineKeyboardButton("🔙 رجوع", callback_data="services"))
    
    bot.edit_message_text(text + "اختر الخدمة المطلوبة:",
                         chat_id=call.message.chat.id,
                         message_id=call.message.message_id,
                         reply_markup=keyboard,
                         parse_mode='Markdown')

def create_service_order(call):
    data = call.data.replace("order_", "")
    service, index = data.split("_")
    index = int(index)
    
    service_item = SERVICES['instagram']['followers'][index]
    
    msg = bot.edit_message_text(f"""🛒 **طلب خدمة: {service_item['name']}**

💵 **السعر:** {service_item['price']} نقطة لكل 1000
────────────────
📥 **أرسل الرابط الآن:**""",
                         chat_id=call.message.chat.id,
                         message_id=call.message.message_id,
                         parse_mode='Markdown')
    
    bot.register_next_step_handler(msg, process_order_link, service_item)

def process_order_link(message, service_item):
    user_id = message.from_user.id
    link = message.text
    
    msg = bot.send_message(message.chat.id, f"📊 **أدخل الكمية المطلوبة:**")
    bot.register_next_step_handler(msg, process_order_quantity, service_item, link)

def process_order_quantity(message, service_item, link):
    user_id = message.from_user.id
    
    try:
        quantity = int(message.text)
        if quantity < 100:
            bot.send_message(message.chat.id, "❌ الحد الأدنى للطلب هو 100")
            return start(message)
    except:
        bot.send_message(message.chat.id, "❌ الرجاء إدخال رقم صحيح")
        return start(message)
    
    cost = (quantity / 1000) * service_item['price']
    cost = round(cost)
    
    user = get_user(user_id)
    if user[4] < cost:
        bot.send_message(message.chat.id, f"❌ رصيدك غير كافي. تحتاج {cost} نقطة")
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
    
    bot.send_message(message.chat.id, f"""✅ **تم استلام طلبك بنجاح!**

📦 **رقم الطلب:** `{order_id}`
🎯 **الخدمة:** {service_item['name']}
🔗 **الرابط:** {link}
📊 **الكمية:** {quantity}
💎 **التكلفة:** {cost} نقطة
⏳ **الحالة:** قيد المعالجة

سيتم البدء في التنفيذ خلال دقائق ⏰""", parse_mode='Markdown')
    
    user = get_user(user_id)
    admin_msg = f"""🆕 **طلب جديد**

👤 **المستخدم:** {user[2]} (@{user[1]})
🆔 **ايدي:** `{user_id}`
📦 **الطلب:** {service_item['name']}
🔗 **الرابط:** {link}
📊 **الكمية:** {quantity}
💎 **التكلفة:** {cost} نقطة"""

    bot.send_message(ADMIN_ID, admin_msg, parse_mode='Markdown')
    
    start(message)

def show_account(call):
    user = get_user(call.from_user.id)
    if not user:
        return
    
    user_id, username, first_name, join_date, points, invited_by, shares, spent_points, orders_count, today_messages = user
    
    account_text = f"""👤 **معلومات حسابك**

🏷 **الاسم:** {first_name}
📧 **المعرف:** @{username if username else 'بلا معرف'}
🆔 **ايدي:** `{user_id}`
────────────────
💎 **النقاط:** {points}
👥 **المشاركات:** {shares}
💰 **النقاط المصروفة:** {spent_points}
📦 **الطلبات:** {orders_count}
────────────────
📅 **تاريخ الانضمام:** {join_date[:10]}"""

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"))
    
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
        types.InlineKeyboardButton("🔗 رابط الدعوة", callback_data="invite_link"),
        types.InlineKeyboardButton("📲 تسليم حسابات", callback_data="submit_accounts")
    )
    keyboard.row(
        types.InlineKeyboardButton("🔄 تبديل نقاط", callback_data="exchange_points"),
        types.InlineKeyboardButton("💰 شراء نقاط", callback_data="buy_points")
    )
    keyboard.row(
        types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")
    )
    
    bot.edit_message_text(f"""💰 **قسم تجميع النقاط**

🎯 **طرق الحصول على النقاط:**

1. **مشاركة رابط الدعوة** 🫂
   - تحصل على 5 نقاط لكل صديق
   - رابطك: `{invite_link}`

2. **تسليم حسابات للمطور** 📲
   - من 100 إلى 400 نقطة حسب الدولة

3. **شراء نقاط مباشرة** 💳
   - أسعار تنافسية

4. **تبديل نقاط تمويل** 🔄
   - 2000 نقطة تمويل = 500 نقطة رشق""",
                         chat_id=call.message.chat.id,
                         message_id=call.message.message_id,
                         reply_markup=keyboard,
                         parse_mode='Markdown')

def show_buy_points(call):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton("💳 شحن برصيد", callback_data="charge_balance"),
        types.InlineKeyboardButton("🎫 كارت شحن", callback_data="charge_card")
    )
    keyboard.row(
        types.InlineKeyboardButton("🔙 رجوع", callback_data="earn_points")
    )
    
    bot.edit_message_text("""💳 **قسم شحن النقاط**

💎 **أسعار النقاط:**
- 1$ = 1000 نقطة
- 5$ = 5000 نقطة  
- 10$ = 11000 نقطة

📞 **للتواصل:** @FFJFF5

💰 **طرق الدفع المتاحة:**
- سبأفون، يمن موبايل، كريمي
- سوا، موبايلي، راجحي
- زين كاش، آسيا، رايزر
- باي بال، USDT، وغيرها""",
                         chat_id=call.message.chat.id,
                         message_id=call.message.message_id,
                         reply_markup=keyboard,
                         parse_mode='Markdown')

def show_my_points(call):
    user = get_user(call.from_user.id)
    points = user[4] if user else 0
    
    bot.answer_callback_query(call.id, f"🎯 نقاطك الحالية: {points} نقطة")

def show_my_orders(call):
    user_id = call.from_user.id
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY order_id DESC LIMIT 5", (user_id,))
    orders = cursor.fetchall()
    conn.close()
    
    if not orders:
        text = "📭 **لا توجد طلبات سابقة**"
    else:
        text = "📦 **آخر 5 طلبات**\n\n"
        for order in orders:
            text += f"**الطلب #{order[0]}**\n"
            text += f"الخدمة: {order[2]}\n"
            text += f"الكمية: {order[3]}\n"
            text += f"الحالة: {order[5]}\n"
            text += f"التاريخ: {order[6][:10]}\n"
            text += "────────────────\n"
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"))
    
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
        user_id = call.from_user.id
    else:
        message = call
        user_id = call.from_user.id
    
    if not is_admin(user_id):
        return
    
    total_users = get_total_users()
    today_users = get_today_users()
    stats = get_user_stats()
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton("🔒 قفل البوت", callback_data="lock_bot"),
        types.InlineKeyboardButton("🔓 فتح البوت", callback_data="unlock_bot")
    )
    keyboard.row(
        types.InlineKeyboardButton("👥 إدارة الإدمن", callback_data="manage_admins"),
        types.InlineKeyboardButton("📊 الإحصائيات", callback_data="statistics")
    )
    keyboard.row(
        types.InlineKeyboardButton("📢 قسم الإذاعة", callback_data="broadcast"),
        types.InlineKeyboardButton("🎁 قسم الرشق", callback_data="rshq_panel")
    )
    keyboard.row(
        types.InlineKeyboardButton("🔄 تحديث", callback_data="admin_panel")
    )
    
    text = f"""🎮 **لوحة تحكم المسؤول**

👥 **إجمالي المستخدمين:** {total_users}
📈 **المستخدمين اليوم:** {today_users}
💎 **إجمالي النقاط:** {stats[1]}
📦 **إجمالي الطلبات:** {stats[2]}
💰 **النقاط المصروفة:** {stats[3]}
⚙️ **حالة البوت:** {'مفتوح ✅' if get_setting('bot_locked') != 'true' else 'مقفل 🔒'}

اختر الإجراء المناسب:"""
    
    if isinstance(call, types.CallbackQuery):
        bot.edit_message_text(text, chat_id=message.chat.id, message_id=message.message_id,
                            reply_markup=keyboard, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, text, reply_markup=keyboard, parse_mode='Markdown')

def show_rshq_panel(call):
    if not is_admin(call.from_user.id):
        return
    
    try:
        response = requests.get(f"https://yemenfollow.com/api/v2?key={API_TOKEN}&action=balance")
        balance_data = response.json()
        balance = balance_data.get('balance', 0)
        currency = balance_data.get('currency', '')
    except:
        balance = 0
        currency = ''
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton("➕ إضافة نقاط", callback_data="add_points"),
        types.InlineKeyboardButton("🎁 صنع كود هدية", callback_data="create_gift")
    )
    keyboard.row(
        types.InlineKeyboardButton("✅ فتح الرشق", callback_data="enable_rshq"),
        types.InlineKeyboardButton("❌ غلق الرشق", callback_data="disable_rshq")
    )
    keyboard.row(
        types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_admin")
    )
    
    bot.edit_message_text(f"""🎮 **قسم إدارة الرشق**

💰 **رصيد الموقع:** {balance} {currency}
⚙️ **حالة الاستقبال:** {'مفتوح ✅' if get_setting('rshq_enabled') != 'false' else 'مغلق ❌'}

اختر الإجراء المناسب:""",
                         chat_id=call.message.chat.id,
                         message_id=call.message.message_id,
                         reply_markup=keyboard,
                         parse_mode='Markdown')

def manage_admins(call):
    if not is_admin(call.from_user.id):
        return
    
    admins_list = get_admins()
    admins_text = "\n".join([f"• `{admin_id}`" for admin_id in admins_list[:5]])
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton("➕ رفع أدمن", callback_data="add_admin"),
        types.InlineKeyboardButton("🗑 حذف الأدمن", callback_data="delete_admins")
    )
    keyboard.row(
        types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_admin")
    )
    
    bot.edit_message_text(f"""👥 **إدارة الإدمن**

آخر 5 أدمن:
{admins_text}""",
                         chat_id=call.message.chat.id,
                         message_id=call.message.message_id,
                         reply_markup=keyboard,
                         parse_mode='Markdown')

def add_admin_handler(call):
    if not is_admin(call.from_user.id):
        return
    
    msg = bot.edit_message_text("👤 **أرسل ايدي المستخدم لرفعه أدمن:**",
                               chat_id=call.message.chat.id,
                               message_id=call.message.message_id)
    bot.register_next_step_handler(msg, process_add_admin)

def process_add_admin(message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        new_admin_id = int(message.text)
        add_admin(new_admin_id)
        bot.send_message(message.chat.id, f"✅ تم رفع المستخدم `{new_admin_id}` كأدمن")
        
        try:
            bot.send_message(new_admin_id, "🎉 تم ترقيتك إلى أدمن في البوت!\nاستخدم /admin للوصول إلى لوحة التحكم")
        except:
            pass
            
    except ValueError:
        bot.send_message(message.chat.id, "❌ الرجاء إدخال ايدي صحيح")
    
    admin_panel(message)

def delete_admins(call):
    if not is_admin(call.from_user.id):
        return
    
    remove_all_admins()
    bot.answer_callback_query(call.id, "✅ تم حذف جميع الأدمنية")
    admin_panel(call.message)

def show_statistics(call):
    if not is_admin(call.from_user.id):
        return
    
    total_users = get_total_users()
    today_users = get_today_users()
    stats = get_user_stats()
    
    bot.edit_message_text(f"""📊 **الإحصائيات الشاملة**

👥 **إجمالي المستخدمين:** {total_users}
📈 **المستخدمين اليوم:** {today_users}
💎 **إجمالي النقاط:** {stats[1]}
📦 **إجمالي الطلبات:** {stats[2]}
💰 **النقاط المصروفة:** {stats[3]}
⚙️ **حالة البوت:** {'مفتوح ✅' if get_setting('bot_locked') != 'true' else 'مقفل 🔒'}""",
                         chat_id=call.message.chat.id,
                         message_id=call.message.message_id,
                         parse_mode='Markdown')

def show_broadcast(call):
    if not is_admin(call.from_user.id):
        return
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton("📝 رسالة نصية", callback_data="broadcast_text"),
        types.InlineKeyboardButton("🖼 صورة", callback_data="broadcast_photo")
    )
    keyboard.row(
        types.InlineKeyboardButton("📹 ميديا", callback_data="broadcast_media"),
        types.InlineKeyboardButton("🔗 توجيه", callback_data="broadcast_forward")
    )
    keyboard.row(
        types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_admin")
    )
    
    bot.edit_message_text("""📢 **قسم الإذاعة**

اختر نوع الإذاعة:""",
                         chat_id=call.message.chat.id,
                         message_id=call.message.message_id,
                         reply_markup=keyboard)

def lock_bot(call):
    if not is_admin(call.from_user.id):
        return
    
    set_setting('bot_locked', 'true')
    bot.answer_callback_query(call.id, "تم قفل البوت بنجاح ✅")
    admin_panel(call)

def unlock_bot(call):
    if not is_admin(call.from_user.id):
        return
    
    set_setting('bot_locked', 'false')
    bot.answer_callback_query(call.id, "تم فتح البوت بنجاح ✅")
    admin_panel(call)

def use_gift_code(call):
    msg = bot.edit_message_text("🎁 **أدخل كود الهدية:**",
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
        
        bot.send_message(message.chat.id, f"🎉 مبروك! حصلت على {points} نقطة من الكود {code}")
        
        bot.send_message(ADMIN_ID, f"🎁 مستخدم استخدم كود هدية\nالمستخدم: {user_id}\nالكود: {code}\nالنقاط: {points}")
    else:
        bot.send_message(message.chat.id, "❌ كود الهدية غير صالح أو مستخدم مسبقاً")
    
    conn.commit()
    conn.close()
    start(message)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_main")
def back_to_main(call):
    start(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_admin")
def back_to_admin(call):
    admin_panel(call)

@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = """🆘 **دليل استخدام البوت**

🤖 **بوت رشق EgyCodes**
────────────────
📖 **طريقة الاستخدام:**

1. **تجميع النقاط 💰**
   - مشاركة رابط الدعوة
   - تسليم حسابات
   - شراء نقاط مباشرة

2. **الرشق 🎯**  
   - اختر الخدمة المطلوبة
   - حدد الكمية
   - أرسل الرابط

3. **إدارة الحساب 👤**
   - تتبع نقاطك
   - مراجعة الطلبات
   - استخدام أكواد الهدايا

📞 **الدعم:** @FFJFF5
📢 **القناة:** @EgyCodes"""

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
    print("🎯 بدأ تشغيل بوت الرشق...")
    init_db()
    
    if not get_setting('bot_locked'):
        set_setting('bot_locked', 'false')
    if not get_setting('rshq_enabled'):
        set_setting('rshq_enabled', 'true')
    if not get_setting('notifications'):
        set_setting('notifications', 'on')
    
    for admin_id in ADMINS:
        add_admin(admin_id)
    
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"خطأ: {e}")
        time.sleep(5)