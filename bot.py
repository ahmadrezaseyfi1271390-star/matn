from rubka import Robot, filters, InlineBuilder
import sqlite3
import json
import requests
import asyncio
from datetime import datetime

# ========== تنظیمات ==========
TOKEN = "CBFGDH0RCEJALDLEWCWJVEGBOVCSLHLKRLRLWLFAGLFPJQBCVIICTQHLTOAHZJOI"
MASTER_DB = "master_robot.db"

# ========== دیتابیس ربات مادر ==========
def init_master_db():
    conn = sqlite3.connect(MASTER_DB)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS robots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT UNIQUE,
        bot_token TEXT,
        bot_name TEXT,
        bot_username TEXT,
        registered_at TEXT,
        is_active INTEGER DEFAULT 1
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS trainings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        bot_token TEXT,
        question TEXT,
        answer TEXT,
        created_at TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS buttons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        bot_token TEXT,
        button_text TEXT,
        button_data TEXT,
        created_at TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        first_seen TEXT,
        last_seen TEXT,
        state TEXT DEFAULT 'idle',
        temp_data TEXT
    )''')
    
    conn.commit()
    conn.close()
    print("✅ دیتابیس ربات مادر راه‌اندازی شد!")

# ========== توابع کمکی ==========
def get_user_state(user_id):
    conn = sqlite3.connect(MASTER_DB)
    c = conn.cursor()
    c.execute("SELECT state, temp_data FROM users WHERE user_id=?", (user_id,))
    result = c.fetchone()
    conn.close()
    if result:
        return result[0], json.loads(result[1]) if result[1] else {}
    return "idle", {}

def set_user_state(user_id, state, temp_data=None):
    conn = sqlite3.connect(MASTER_DB)
    c = conn.cursor()
    now = datetime.now().isoformat()
    
    c.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if c.fetchone():
        c.execute(
            "UPDATE users SET state=?, temp_data=?, last_seen=? WHERE user_id=?",
            (state, json.dumps(temp_data or {}), now, user_id)
        )
    else:
        c.execute(
            "INSERT INTO users (user_id, first_seen, last_seen, state, temp_data) VALUES (?, ?, ?, ?, ?)",
            (user_id, now, now, state, json.dumps(temp_data or {}))
        )
    
    conn.commit()
    conn.close()

def register_robot(user_id, bot_token):
    conn = sqlite3.connect(MASTER_DB)
    c = conn.cursor()
    
    try:
        response = requests.get(f"https://api.rubika.ir/bot/{bot_token}/getMe", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                bot_info = data.get("result", {})
                bot_name = bot_info.get("name", "نامشخص")
                bot_username = bot_info.get("username", "نامشخص")
                
                c.execute(
                    "INSERT OR REPLACE INTO robots (user_id, bot_token, bot_name, bot_username, registered_at, is_active) VALUES (?, ?, ?, ?, ?, 1)",
                    (user_id, bot_token, bot_name, bot_username, datetime.now().isoformat())
                )
                conn.commit()
                conn.close()
                return True, bot_name, bot_username
    except Exception as e:
        print(f"خطا در دریافت اطلاعات ربات: {e}")
    
    conn.close()
    return False, None, None

def save_training(user_id, bot_token, question, answer):
    conn = sqlite3.connect(MASTER_DB)
    c = conn.cursor()
    c.execute(
        "INSERT INTO trainings (user_id, bot_token, question, answer, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, bot_token, question, answer, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def get_trainings_by_token(bot_token):
    conn = sqlite3.connect(MASTER_DB)
    c = conn.cursor()
    c.execute("SELECT question, answer FROM trainings WHERE bot_token=?", (bot_token,))
    results = c.fetchall()
    conn.close()
    return results

def save_button(user_id, bot_token, button_text, button_data):
    conn = sqlite3.connect(MASTER_DB)
    c = conn.cursor()
    c.execute(
        "INSERT INTO buttons (user_id, bot_token, button_text, button_data, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, bot_token, button_text, button_data, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def get_buttons_by_token(bot_token):
    conn = sqlite3.connect(MASTER_DB)
    c = conn.cursor()
    c.execute("SELECT button_text, button_data FROM buttons WHERE bot_token=?", (bot_token,))
    results = c.fetchall()
    conn.close()
    return results

def get_robot_by_user(user_id):
    conn = sqlite3.connect(MASTER_DB)
    c = conn.cursor()
    c.execute("SELECT bot_token, bot_name, bot_username FROM robots WHERE user_id=? AND is_active=1", (user_id,))
    result = c.fetchone()
    conn.close()
    return result

def delete_robot_data(user_id):
    conn = sqlite3.connect(MASTER_DB)
    c = conn.cursor()
    c.execute("DELETE FROM trainings WHERE user_id=?", (user_id,))
    c.execute("DELETE FROM buttons WHERE user_id=?", (user_id,))
    c.execute("UPDATE robots SET is_active=0 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def update_robot_token(user_id, new_token):
    conn = sqlite3.connect(MASTER_DB)
    c = conn.cursor()
    c.execute("UPDATE robots SET bot_token=?, is_active=1, registered_at=? WHERE user_id=?", 
              (new_token, datetime.now().isoformat(), user_id))
    conn.commit()
    conn.close()

def get_all_robots():
    conn = sqlite3.connect(MASTER_DB)
    c = conn.cursor()
    c.execute("SELECT user_id, bot_token, bot_name, bot_username FROM robots WHERE is_active=1")
    results = c.fetchall()
    conn.close()
    return results

# ========== ارسال به ربات زیردست ==========
async def send_to_sub_robot(bot_token, chat_id, text, reply_to=None):
    """ارسال پیام به ربات زیردست از طریق API"""
    try:
        url = f"https://api.rubika.ir/bot/{bot_token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text
        }
        if reply_to:
            data["reply_to_message_id"] = reply_to
        
        response = requests.post(url, json=data, timeout=10)
        return response.json()
    except Exception as e:
        print(f"خطا در ارسال به ربات زیردست: {e}")
        return None

async def add_button_to_sub_robot(bot_token, chat_id, button_text, button_data):
    """اضافه کردن دکمه به ربات زیردست"""
    try:
        url = f"https://api.rubika.ir/bot/{bot_token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": f"🔘 دکمه جدید: {button_text}",
            "inline_keyboard": [
                [{"text": button_text, "callback_data": button_data}]
            ]
        }
        response = requests.post(url, json=data, timeout=10)
        return response.json()
    except Exception as e:
        print(f"خطا در اضافه کردن دکمه: {e}")
        return None

# ========== ربات مادر ==========
bot = Robot(token=TOKEN)

# ========== منوی اصلی ==========
def get_main_keyboard():
    return InlineBuilder([
        [{"text": "🤖 ثبت توکن ربات", "callback_data": "register"}],
        [{"text": "📚 آموزش ربات", "callback_data": "train"}],
        [{"text": "🔘 ساخت دکمه ربات", "callback_data": "make_button"}],
        [{"text": "✏️ ویرایش توکن", "callback_data": "edit_token"}],
        [{"text": "📊 وضعیت ربات", "callback_data": "status"}],
        [{"text": "📋 لیست ربات‌ها", "callback_data": "list_robots"}]
    ])

# ========== پیام خوش‌آمدگویی ==========
@bot.on_message(filters.is_private & filters.text)
async def handle_start(bot_obj, message):
    try:
        user_id = str(message.sender_id)
        text = message.text
        
        if text == "/start":
            set_user_state(user_id, "idle")
            
            welcome_text = f"""🎉 **به ربات مادر خوش آمدی!** 

👤 **شناسه شما:** `{user_id}`

🤖 **این ربات به شما کمک می‌کند تا ربات‌های خود را مدیریت کنید.**

📋 **راهنما:**
• برای ثبت ربات جدید، روی دکمه «ثبت توکن ربات» کلیک کنید
• برای آموزش دادن به ربات، گزینه «آموزش ربات» را انتخاب کنید
• برای ساخت دکمه، گزینه «ساخت دکمه ربات» را بزنید

⚡ **قبل از استفاده، توکن ربات خود را ثبت کنید!**

💡 **ساختار توکن روبیکا:** حروف بزرگ و اعداد

⏰ **زمان فعلی:** {datetime.now().strftime('%H:%M:%S')}
"""
            
            await message.reply(
                welcome_text,
                inline_keyboard=get_main_keyboard()
            )
            
            print(f"👤 کاربر جدید: {user_id}")
        else:
            # اگر پیام معمولی بود، وضعیت را چک کن
            await handle_states(bot_obj, message)
        
    except Exception as e:
        print(f"خطا در start: {e}")
        await message.reply("❌ خطا در پردازش پیام!")

# ========== مدیریت دکمه‌های شیشه‌ای ==========
@bot.on_callback_query()
async def handle_callbacks(bot_obj, callback):
    try:
        user_id = str(callback.sender_id)
        data = callback.data
        
        await callback.answer("✅ در حال پردازش...")
        
        # ===== ثبت توکن =====
        if data == "register":
            state, temp = get_user_state(user_id)
            if state == "waiting_for_token":
                await callback.message.edit_text("❌ شما در حال ثبت توکن هستید! لطفاً توکن را ارسال کنید.")
                return
            
            set_user_state(user_id, "waiting_for_token", {"action": "register"})
            await callback.message.edit_text(
                "🤖 **لطفاً توکن ربات خود را وارد کنید:**\n\n"
                "📌 توکن را از ربات‌ساز روبیکا دریافت کنید.\n"
                "⚠️ توکن باید معتبر باشد.\n\n"
                "✏️ توکن را ارسال کنید:"
            )
        
        # ===== آموزش ربات =====
        elif data == "train":
            robot_info = get_robot_by_user(user_id)
            if not robot_info:
                await callback.message.edit_text(
                    "❌ **شما هنوز رباتی ثبت نکرده‌اید!**\n\n"
                    "لطفاً ابتدا روی دکمه «ثبت توکن ربات» کلیک کنید."
                )
                return
            
            set_user_state(user_id, "waiting_for_training_question", {
                "action": "train",
                "bot_token": robot_info[0]
            })
            await callback.message.edit_text(
                f"📚 **آموزش ربات {robot_info[1]}**\n\n"
                "مرحله ۱: **متن سوال را وارد کنید.**\n\n"
                "📝 سوالی که کاربر می‌پرسد را بنویسید:"
            )
        
        # ===== ساخت دکمه =====
        elif data == "make_button":
            robot_info = get_robot_by_user(user_id)
            if not robot_info:
                await callback.message.edit_text(
                    "❌ **شما هنوز رباتی ثبت نکرده‌اید!**\n\n"
                    "لطفاً ابتدا روی دکمه «ثبت توکن ربات» کلیک کنید."
                )
                return
            
            set_user_state(user_id, "waiting_for_button_text", {
                "action": "button",
                "bot_token": robot_info[0]
            })
            await callback.message.edit_text(
                f"🔘 **ساخت دکمه برای ربات {robot_info[1]}**\n\n"
                "مرحله ۱: **متن دکمه را وارد کنید.**\n\n"
                "✏️ متنی که روی دکمه نمایش داده می‌شود:"
            )
        
        # ===== ویرایش توکن =====
        elif data == "edit_token":
            robot_info = get_robot_by_user(user_id)
            if not robot_info:
                await callback.message.edit_text(
                    "❌ **شما هنوز رباتی ثبت نکرده‌اید!**\n\n"
                    "لطفاً ابتدا روی دکمه «ثبت توکن ربات» کلیک کنید."
                )
                return
            
            set_user_state(user_id, "waiting_for_new_token", {
                "action": "edit_token"
            })
            await callback.message.edit_text(
                f"✏️ **ویرایش توکن ربات**\n\n"
                f"توکن فعلی: `{robot_info[0]}`\n\n"
                "⚠️ **توجه:** با تغییر توکن، تمام آموزش‌ها و دکمه‌های قبلی حذف می‌شوند!\n\n"
                "📌 توکن جدید را وارد کنید:"
            )
        
        # ===== وضعیت =====
        elif data == "status":
            robot_info = get_robot_by_user(user_id)
            if not robot_info:
                await callback.message.edit_text(
                    "📊 **وضعیت:**\n\n"
                    "❌ شما هنوز رباتی ثبت نکرده‌اید!\n\n"
                    "برای ثبت ربات، روی دکمه «ثبت توکن ربات» کلیک کنید."
                )
                return
            
            trainings = get_trainings_by_token(robot_info[0])
            buttons = get_buttons_by_token(robot_info[0])
            
            status_text = f"""📊 **وضعیت ربات شما**

🤖 **نام:** {robot_info[1]}
👤 **یوزرنیم:** @{robot_info[2]}
🔑 **توکن:** `{robot_info[0][:10]}...`

📚 **تعداد آموزش‌ها:** {len(trainings)}
🔘 **تعداد دکمه‌ها:** {len(buttons)}

📅 **تاریخ ثبت:** {datetime.now().strftime('%Y/%m/%d %H:%M')}

---
💡 برای مدیریت بیشتر از منوی اصلی استفاده کنید.
"""
            await callback.message.edit_text(
                status_text,
                inline_keyboard=get_main_keyboard()
            )
        
        # ===== لیست ربات‌ها =====
        elif data == "list_robots":
            robots = get_all_robots()
            if not robots:
                await callback.message.edit_text(
                    "📋 **لیست ربات‌ها:**\n\n"
                    "❌ هیچ رباتی ثبت نشده است!"
                )
                return
            
            text = "📋 **لیست ربات‌های ثبت شده:**\n\n"
            for idx, (uid, token, name, username) in enumerate(robots, 1):
                text += f"{idx}. 🤖 **{name}**\n"
                text += f"   👤 @{username}\n"
                text += f"   🆔 {uid[:10]}...\n"
                text += f"   🔑 {token[:10]}...\n\n"
            
            await callback.message.edit_text(
                text,
                inline_keyboard=get_main_keyboard()
            )
        
    except Exception as e:
        print(f"خطا در callback: {e}")
        await callback.message.reply("❌ خطا در پردازش!")

# ========== مدیریت پیام‌های متنی (States) ==========
@bot.on_message(filters.is_private & filters.text)
async def handle_states(bot_obj, message):
    try:
        user_id = str(message.sender_id)
        text = message.text
        
        if text == "/start":
            return
        
        state, temp_data = get_user_state(user_id)
        
        # ===== ثبت توکن =====
        if state == "waiting_for_token":
            bot_token = text.strip()
            
            if len(bot_token) < 30:
                await message.reply(
                    "❌ **توکن نامعتبر!**\n\n"
                    "توکن باید حداقل ۳۰ کاراکتر داشته باشد.\n"
                    "لطفاً توکن معتبر ارسال کنید:"
                )
                return
            
            success, bot_name, bot_username = register_robot(user_id, bot_token)
            
            if success:
                set_user_state(user_id, "idle")
                await message.reply(
                    f"✅ **ربات با موفقیت ثبت شد!**\n\n"
                    f"🤖 **نام:** {bot_name}\n"
                    f"👤 **یوزرنیم:** @{bot_username}\n"
                    f"🔑 **توکن:** `{bot_token[:10]}...`\n\n"
                    "حالا می‌توانید از منوی اصلی استفاده کنید.",
                    inline_keyboard=get_main_keyboard()
                )
            else:
                await message.reply(
                    "❌ **خطا در ثبت ربات!**\n\n"
                    "توکن معتبر نیست یا ربات فعال نمی‌باشد.\n"
                    "لطفاً دوباره تلاش کنید:"
                )
        
        # ===== آموزش ربات (سوال) =====
        elif state == "waiting_for_training_question":
            question = text.strip()
            
            if len(question) < 3:
                await message.reply(
                    "❌ **سوال کوتاه است!**\n\n"
                    "لطفاً سوال را کامل‌تر وارد کنید (حداقل ۳ کاراکتر):"
                )
                return
            
            set_user_state(user_id, "waiting_for_training_answer", {
                "action": "train_answer",
                "bot_token": temp_data.get("bot_token"),
                "question": question
            })
            
            await message.reply(
                f"📚 **مرحله ۲: پاسخ سوال**\n\n"
                f"📝 **سوال:** {question}\n\n"
                "✏️ **پاسخ مورد نظر را وارد کنید:**"
            )
        
        # ===== آموزش ربات (جواب) =====
        elif state == "waiting_for_training_answer":
            answer = text.strip()
            bot_token = temp_data.get("bot_token")
            question = temp_data.get("question")
            
            if len(answer) < 3:
                await message.reply(
                    "❌ **پاسخ کوتاه است!**\n\n"
                    "لطفاً پاسخ را کامل‌تر وارد کنید (حداقل ۳ کاراکتر):"
                )
                return
            
            save_training(user_id, bot_token, question, answer)
            
            try:
                result = await send_to_sub_robot(bot_token, user_id, answer)
                if result and result.get("ok"):
                    await message.reply(
                        f"✅ **آموزش با موفقیت ذخیره شد!**\n\n"
                        f"📝 **سوال:** {question}\n"
                        f"💬 **پاسخ:** {answer}\n\n"
                        "🔔 پاسخ به ربات شما ارسال شد."
                    )
                else:
                    await message.reply(
                        f"✅ **آموزش ذخیره شد!**\n\n"
                        f"📝 **سوال:** {question}\n"
                        f"💬 **پاسخ:** {answer}\n\n"
                        "⚠️ اما ارسال به ربات با خطا مواجه شد."
                    )
            except Exception as e:
                await message.reply(
                    f"✅ **آموزش ذخیره شد!**\n\n"
                    f"📝 **سوال:** {question}\n"
                    f"💬 **پاسخ:** {answer}\n\n"
                    f"❌ خطا در ارسال: {e}"
                )
            
            set_user_state(user_id, "idle")
            await message.reply(
                "📋 **منوی اصلی:**",
                inline_keyboard=get_main_keyboard()
            )
        
        # ===== ساخت دکمه (متن دکمه) =====
        elif state == "waiting_for_button_text":
            button_text = text.strip()
            
            if len(button_text) < 2:
                await message.reply(
                    "❌ **متن دکمه کوتاه است!**\n\n"
                    "لطفاً متن دکمه را کامل‌تر وارد کنید (حداقل ۲ کاراکتر):"
                )
                return
            
            set_user_state(user_id, "waiting_for_button_data", {
                "action": "button_data",
                "bot_token": temp_data.get("bot_token"),
                "button_text": button_text
            })
            
            await message.reply(
                f"🔘 **مرحله ۲: داده دکمه**\n\n"
                f"📝 **متن دکمه:** {button_text}\n\n"
                "✏️ **داده (data) دکمه را وارد کنید:**\n"
                "(این داده زمانی که کاربر روی دکمه کلیک می‌کند به ربات ارسال می‌شود)"
            )
        
        # ===== ساخت دکمه (داده دکمه) =====
        elif state == "waiting_for_button_data":
            button_data = text.strip()
            bot_token = temp_data.get("bot_token")
            button_text = temp_data.get("button_text")
            
            if len(button_data) < 2:
                await message.reply(
                    "❌ **داده دکمه کوتاه است!**\n\n"
                    "لطفاً داده دکمه را کامل‌تر وارد کنید (حداقل ۲ کاراکتر):"
                )
                return
            
            save_button(user_id, bot_token, button_text, button_data)
            
            try:
                result = await add_button_to_sub_robot(bot_token, user_id, button_text, button_data)
                if result and result.get("ok"):
                    await message.reply(
                        f"✅ **دکمه با موفقیت ساخته شد!**\n\n"
                        f"🔘 **متن:** {button_text}\n"
                        f"📊 **داده:** `{button_data}`\n\n"
                        "🔔 دکمه به ربات شما اضافه شد."
                    )
                else:
                    await message.reply(
                        f"✅ **دکمه ذخیره شد!**\n\n"
                        f"🔘 **متن:** {button_text}\n"
                        f"📊 **داده:** `{button_data}`\n\n"
                        "⚠️ اما اضافه شدن به ربات با خطا مواجه شد."
                    )
            except Exception as e:
                await message.reply(
                    f"✅ **دکمه ذخیره شد!**\n\n"
                    f"🔘 **متن:** {button_text}\n"
                    f"📊 **داده:** `{button_data}`\n\n"
                    f"❌ خطا: {e}"
                )
            
            set_user_state(user_id, "idle")
            await message.reply(
                "📋 **منوی اصلی:**",
                inline_keyboard=get_main_keyboard()
            )
        
        # ===== ویرایش توکن =====
        elif state == "waiting_for_new_token":
            new_token = text.strip()
            
            if len(new_token) < 30:
                await message.reply(
                    "❌ **توکن نامعتبر!**\n\n"
                    "توکن باید حداقل ۳۰ کاراکتر داشته باشد.\n"
                    "لطفاً توکن معتبر ارسال کنید:"
                )
                return
            
            try:
                response = requests.get(f"https://api.rubika.ir/bot/{new_token}/getMe", timeout=10)
                if response.status_code == 200 and response.json().get("ok"):
                    delete_robot_data(user_id)
                    update_robot_token(user_id, new_token)
                    
                    bot_info = response.json().get("result", {})
                    bot_name = bot_info.get("name", "نامشخص")
                    bot_username = bot_info.get("username", "نامشخص")
                    
                    set_user_state(user_id, "idle")
                    await message.reply(
                        f"✅ **توکن با موفقیت ویرایش شد!**\n\n"
                        f"🤖 **نام:** {bot_name}\n"
                        f"👤 **یوزرنیم:** @{bot_username}\n"
                        f"🔑 **توکن جدید:** `{new_token[:10]}...`\n\n"
                        "⚠️ تمام آموزش‌ها و دکمه‌های قبلی حذف شدند.\n\n"
                        "حالا می‌توانید از منوی اصلی استفاده کنید.",
                        inline_keyboard=get_main_keyboard()
                    )
                else:
                    await message.reply(
                        "❌ **توکن نامعتبر!**\n\n"
                        "لطفاً توکن معتبر ارسال کنید:"
                    )
            except Exception as e:
                await message.reply(
                    f"❌ **خطا در اعتبارسنجی توکن!**\n\n"
                    f"خطا: {e}\n\n"
                    "لطفاً دوباره تلاش کنید:"
                )
        
        else:
            # اگر کاربر در حالت خاصی نبود
            await message.reply(
                "🤖 **سلام!**\n\n"
                "لطفاً از دکمه‌های منوی اصلی استفاده کنید.\n"
                "اگر تازه وارد شده‌اید، روی «ثبت توکن ربات» کلیک کنید.",
                inline_keyboard=get_main_keyboard()
            )
        
    except Exception as e:
        print(f"خطا در handle_states: {e}")
        await message.reply("❌ خطا در پردازش!")

# ========== اجرا ==========
if __name__ == "__main__":
    init_master_db()
    print("=" * 70)
    print("🤖 ربات مادر روبیکا با قابلیت مدیریت ربات‌ها روشن شد!")
    print(f"🔑 توکن ربات مادر: {TOKEN[:10]}...")
    print("📚 دیتابیس: " + MASTER_DB)
    print("=" * 70)
    print()
    print("💡 راهنما:")
    print("  1. کاربران توکن ربات خود را ثبت می‌کنند")
    print("  2. ربات مادر آموزش‌ها و دکمه‌ها را مدیریت می‌کند")
    print("  3. هر کاربر می‌تواند چندین ربات داشته باشد")
    print("=" * 70)
    print()
    
    try:
        bot.run()
    except KeyboardInterrupt:
        print("\n👋 ربات خاموش شد!")
    except Exception as e:
        print(f"❌ خطا: {e}")
        import traceback
        traceback.print_exc()
