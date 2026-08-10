from rubka import Robot, filters
import sqlite3
import random
from datetime import datetime

# ========== تنظیمات ==========
TOKEN = "CBFGDH0RCEJALDLEWCWJVEGBOVCSLHLKRLRLWLFAGLFPJQBCVIICTQHLTOAHZJOI"
DB_NAME = "rubka_memory.db"

# ========== دیتابیس حافظه ==========
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS chat_memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        message TEXT,
        response TEXT,
        timestamp TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS learned_patterns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        keyword TEXT,
        response TEXT,
        count INTEGER DEFAULT 1,
        user_id TEXT
    )''')
    
    conn.commit()
    conn.close()
    print("✅ دیتابیس راه‌اندازی شد!")

def save_memory(user_id, message, response):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "INSERT INTO chat_memory (user_id, message, response, timestamp) VALUES (?, ?, ?, ?)",
        (user_id, message, response, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def learn_pattern(user_id, message, response):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    keywords = [w.lower() for w in message.split() if len(w) > 3]
    
    for keyword in keywords[:5]:
        c.execute(
            "SELECT id, count FROM learned_patterns WHERE keyword=? AND user_id=?",
            (keyword, user_id)
        )
        result = c.fetchone()
        
        if result:
            c.execute(
                "UPDATE learned_patterns SET count=count+1, response=? WHERE keyword=? AND user_id=?",
                (response, keyword, user_id)
            )
        else:
            c.execute(
                "INSERT INTO learned_patterns (keyword, response, count, user_id) VALUES (?, ?, 1, ?)",
                (keyword, response, user_id)
            )
    
    conn.commit()
    conn.close()

def get_learned_response(user_id, message):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    words = message.lower().split()
    best_response = None
    best_count = 0
    
    for word in words:
        if len(word) > 3:
            c.execute(
                "SELECT response, count FROM learned_patterns WHERE keyword=? AND user_id=? ORDER BY count DESC LIMIT 1",
                (word, user_id)
            )
            result = c.fetchone()
            if result and result[1] > best_count:
                best_response = result[0]
                best_count = result[1]
    
    conn.close()
    return best_response

def get_recent_history(user_id, limit=5):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "SELECT message, response FROM chat_memory WHERE user_id=? ORDER BY timestamp DESC LIMIT ?",
        (user_id, limit)
    )
    history = c.fetchall()
    conn.close()
    
    if history:
        context = "\n".join([f"👤: {msg}\n🤖: {resp}" for msg, resp in history[::-1]])
        return context
    return ""

# ========== تولید پاسخ هوشمند ==========
def generate_response(message_text, user_id):
    
    # ۱. بررسی الگوهای یادگرفته‌شده
    learned = get_learned_response(user_id, message_text)
    if learned:
        return learned
    
    msg_lower = message_text.lower()
    
    responses = {
        "سلام": [
            "سلام! خوشحالم که پیام دادی 😊 چطور می‌تونم کمک کنم؟",
            "سلام علیک! چه خبر؟ منتظر پیامت بودم!",
            "سلام! امیدوارم روز خوبی داشته باشی 🌹",
            "سلام دوست عزیز! چطور می‌تونم مفید باشم؟"
        ],
        "خوبی": [
            "عالی‌ام، ممنون! تو چطوری؟",
            "همیشه خوبم وقتی با تو حرف می‌زنم 😄",
            "فوقالعاده! امیدوارم تو هم خوب باشی.",
            "بهترین حالت رو دارم، ممنون که پرسیدی!"
        ],
        "ربات": [
            "بله، من یه ربات هوشمندم و دارم یاد می‌گیرم! 🤖",
            "من ربات روبیکا هستم با کتابخونه rubka ساخته شده.",
            "رباتم ولی با هر مکالمه باهوش‌تر می‌شوم! 🧠"
        ],
        "یادت میاد": [
            "بله! حافظه‌ی خوبی دارم. قبلاً با هم صحبت کردیم.",
            "یادم میاد! می‌خوای ادامه بدیم؟"
        ],
        "کمک": [
            "در خدمتم! هر سوالی داری بپرس 📝",
            "چطور می‌تونم کمکت کنم؟",
            "راهنما: هر چیزی که نیاز داری بپرس!"
        ],
        "خداحافظ": [
            "خداحافظ! خوشحال شدم ازت 👋",
            "به امید دیدار! همیشه منتظرتم.",
            "خدانگهدار! بازم بیا!"
        ],
        "عشق": [
            "❤️ چه احساس قشنگی!",
            "عشق زیباترین حس دنیاست ❤️",
            "چه حرف قشنگی! 😍"
        ],
        "متشکرم": [
            "خواهش می‌کنم! 🙏",
            "خوشحالم که مفید بودم!",
            "قابلی نداشت! 😊"
        ],
        "ربیکا": [
            "روبیكا بهترین پیام‌رسان ایرانی! 🇮🇷",
            "روبیكا رو دوست دارم! ❤️"
        ],
        "برنامه": [
            "برنامه‌نویسی یه هنره! چه زبانی کار می‌کنی؟ 💻",
            "برنامه‌نویسی عالیه! امیدوارم موفق باشی 🚀"
        ]
    }
    
    for keyword, reply_list in responses.items():
        if keyword in msg_lower:
            return random.choice(reply_list)
    
    history = get_recent_history(user_id, 3)
    if history:
        return f"جالب! بر اساس حرف‌هایی که قبلاً زدی:\n\n{history}\n\nحالا درباره‌ی '{message_text}' بیشتر توضیح بده تا بهتر یاد بگیرم 🧠"
    
    return f"ممنون از پیامت! 🧠 من در حال یادگیری هستم.\n\nدرباره‌ی '{message_text}' بیشتر توضیح می‌دی؟\nهرچه بیشتر صحبت کنیم، بهتر یاد می‌گیرم! 😊"

# ========== راه‌اندازی ربات ==========
bot = Robot(token=TOKEN)

# ========== هندلر پیام‌ها ==========
@bot.on_message(filters.text)
async def handle_messages(bot, message):
    """مدیریت پیام‌های متنی"""
    try:
        user_id = str(message.sender_id)
        user_message = message.text
        
        if not user_message:
            return
        
        # تولید پاسخ
        response = generate_response(user_message, user_id)
        
        # ارسال پاسخ
        await message.reply(response)
        
        # ذخیره در حافظه
        save_memory(user_id, user_message, response)
        learn_pattern(user_id, user_message, response)
        
        # نمایش در کنسول
        chat_type = "گروهی" if hasattr(message.chat, 'type') and message.chat.type == "group" else "خصوصی"
        print(f"📩 [{chat_type}] 👤 {user_id}: {user_message}")
        print(f"🤖 {response}\n")
        print("-" * 50)
        
    except Exception as e:
        print(f"❌ خطا در پردازش پیام: {e}")

# ========== هندلر دکمه‌ها ==========
@bot.on_callback_query()
async def handle_callback(bot, callback):
    """مدیریت کلیک روی دکمه‌ها"""
    try:
        data = callback.data
        user_id = str(callback.sender_id)
        
        await callback.answer(f"✅ دکمه‌ی '{data}' زده شد!")
        
        responses = {
            "help": "📖 **راهنمای ربات:**\n\n• هر سوالی دارید بپرسید\n• ربات از مکالمات یاد می‌گیرد\n• هرچه بیشتر صحبت کنید، بهتر پاسخ می‌دهد\n• از دکمه‌ها برای تعامل استفاده کنید",
            "about": f"🤖 **درباره‌ی من:**\n\nمن یک ربات هوشمند روبیکا هستم.\nبا کتابخونه‌ی `rubka` ساخته شده‌ام.\nهدفم یادگیری از مکالمات و کمک به شماست!\n\n📅 تاریخ فعال‌سازی: {datetime.now().strftime('%Y/%m/%d')}",
            "start": "🎯 **شروع مجدد!**\n\nاز الان می‌تونیم مکالمه رو شروع کنیم.\nهر چیزی که دوست داری بپرس! 😊",
            "learn": "🧠 **یادگیری فعال!**\n\nمن از هر مکالمه‌ای یاد می‌گیرم.\nهرچه بیشتر صحبت کنید، پاسخ‌های من دقیق‌تر می‌شود."
        }
        
        if data in responses:
            await callback.message.edit_text(responses[data])
            save_memory(user_id, f"دکمه: {data}", responses[data])
            
    except Exception as e:
        print(f"❌ خطا در پردازش دکمه: {e}")

# ========== اجرا ==========
if __name__ == "__main__":
    init_db()
    print("=" * 60)
    print("🤖 ربات روبیکا با قابلیت یادگیری روشن شد!")
    print(f"📚 دیتابیس: {DB_NAME}")
    print(f"🔑 توکن: {TOKEN[:10]}...")
    print("🔄 در حال دریافت پیام‌ها...")
    print("=" * 60)
    print()
    
    try:
        bot.run()
    except KeyboardInterrupt:
        print("\n👋 ربات خاموش شد!")
    except Exception as e:
        print(f"❌ خطا: {e}")
        import traceback
        traceback.print_exc()
