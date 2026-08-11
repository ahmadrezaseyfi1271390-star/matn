import asyncio
import json
import os
import hashlib
import random
import string

from rubka import Robot
from rubka.context import Message
from rubka.keypad import ChatKeypadBuilder


# =========================================================
# تنظیمات ربات مادر
# =========================================================

MOTHER_TOKEN = "CBFHDH0GNRJXCUWLGMDAALCISLAKUVPNZFGEZULWRBGAUZYMRTNCENCKFJNRMSDK"

CREATOR = "@reza_127_s"

DATA_FILE = "bots.json"

# محدودیت‌ها برای اکانت ساده
FREE_BOT_LIMIT = 1
FREE_BUTTON_LIMIT = 3
FREE_QUESTION_LIMIT = 5

# محدودیت‌ها برای اکانت ویژه
VIP_BOT_LIMIT = 5
VIP_BUTTON_LIMIT = 999999
VIP_QUESTION_LIMIT = 999999

# کد مخفی برای ساخت کد یکبار مصرف
SECRET_CODE = "1271390"


# =========================================================
# دیتابیس ساده JSON
# =========================================================

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"users": {}, "vip_users": [], "temp_codes": {}}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"users": {}, "vip_users": [], "temp_codes": {}}


def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(
            DATA,
            f,
            ensure_ascii=False,
            indent=2
        )


DATA = load_data()

# بارگذاری کاربران ویژه از دیتابیس
VIP_USERS = set(DATA.get("vip_users", []))


# =========================================================
# وضعیت موقت کاربران
# =========================================================

states = {}


# =========================================================
# ربات‌های فعال
# =========================================================

child_bots = {}

child_tasks = {}


# =========================================================
# گرفتن شناسه کاربر
# =========================================================

def get_user_id(message):

    value = getattr(message, "sender_id", None)

    if value:
        return str(value)

    value = getattr(message, "chat_id", None)

    if value:
        return str(value)

    return None


# =========================================================
# اطلاعات کاربر
# =========================================================

def get_user_data(uid):

    if uid not in DATA["users"]:

        DATA["users"][uid] = {
            "bots": {},
            "start_message": "👋 سلام! به ربات من خوش آمدی."
        }

        save_data()

    return DATA["users"][uid]


# =========================================================
# بررسی وضعیت ویژه بودن کاربر
# =========================================================

def is_vip(uid):
    return uid in VIP_USERS


# =========================================================
# دریافت محدودیت‌های کاربر
# =========================================================

def get_user_limits(uid):
    if is_vip(uid):
        return {
            "bot_limit": VIP_BOT_LIMIT,
            "button_limit": VIP_BUTTON_LIMIT,
            "question_limit": VIP_QUESTION_LIMIT,
            "is_vip": True
        }
    else:
        return {
            "bot_limit": FREE_BOT_LIMIT,
            "button_limit": FREE_BUTTON_LIMIT,
            "question_limit": FREE_QUESTION_LIMIT,
            "is_vip": False
        }


# =========================================================
# ساخت ID برای توکن
# =========================================================

def make_token_id(token):

    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()[:16]


# =========================================================
# ساخت کد یکبار مصرف
# =========================================================

def generate_temp_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


# =========================================================
# فرمت‌دهی متن با تگ‌ها (مخفی)
# =========================================================

def format_text(text):
    # کج (ایتالیک)
    text = text.replace('کج', '__')
    
    # اسپویلر
    text = text.replace('اسپویلر', '||')
    
    # برجسته (پررنگ)
    text = text.replace('برجسته', '**')
    
    # خطدار
    text = text.replace('خطدار', '~~')
    
    # کپی
    text = text.replace('کپی', '`')
    
    # کپی کد
    text = text.replace('کپی کد', '```')
    
    return text


# =========================================================
# کیبورد اصلی (منوی ربات‌ها)
# =========================================================

def main_keypad(uid):

    builder = ChatKeypadBuilder()
    
    user_data = get_user_data(uid)
    bots = user_data["bots"]
    
    # دکمه افزودن ربات
    row1 = builder.row(
        builder.button(
            id="add_bot",
            text="➕ افزودن ربات"
        )
    )
    
    # دکمه‌های ربات‌ها
    if bots:
        rows = []
        for tid, bot_data in bots.items():
            rows.append(
                builder.row(
                    builder.button(
                        id=f"bot_{tid}",
                        text=f"🤖 {bot_data.get('name', 'ربات')}"
                    )
                )
            )
        
        # اضافه کردن دکمه اکانت ویژه در انتها
        rows.append(
            builder.row(
                builder.button(
                    id="menu_vip",
                    text="⭐ اکانت ویژه"
                )
            )
        )
        
        # ساخت کیبورد با همه ردیف‌ها
        keypad = builder.build()
        # چون نمی‌تونیم مستقیم به builder ردیف اضافه کنیم، از روش دیگه استفاده می‌کنیم
        # بهتره کیبورد رو به صورت دستی بسازیم
        
        # برگرداندن کیبورد با استفاده از متد build با لیست ردیف‌ها
        return builder.build()
    
    # اگر رباتی نیست
    keypad = (
        builder
        .row(
            builder.button(
                id="add_bot",
                text="➕ افزودن ربات"
            )
        )
        .row(
            builder.button(
                id="menu_vip",
                text="⭐ اکانت ویژه"
            )
        )
        .build()
    )
    
    return keypad


# =========================================================
# ساخت کیبورد اصلی به صورت دستی
# =========================================================

def build_main_keypad(uid):
    builder = ChatKeypadBuilder()
    user_data = get_user_data(uid)
    bots = user_data["bots"]
    
    # ردیف اول: افزودن ربات
    builder.row(
        builder.button(
            id="add_bot",
            text="➕ افزودن ربات"
        )
    )
    
    # ردیف‌های ربات‌ها
    for tid, bot_data in bots.items():
        builder.row(
            builder.button(
                id=f"bot_{tid}",
                text=f"🤖 {bot_data.get('name', 'ربات')}"
            )
        )
    
    # ردیف آخر: اکانت ویژه
    builder.row(
        builder.button(
            id="menu_vip",
            text="⭐ اکانت ویژه"
        )
    )
    
    return builder.build()


# =========================================================
# کیبورد مدیریت ربات (منوی دوم)
# =========================================================

def bot_manager_keypad(bot_name):

    builder = ChatKeypadBuilder()

    keypad = (
        builder
        .row(
            builder.button(
                id="menu_buttons",
                text="🔘 دکمه‌ها"
            ),
            builder.button(
                id="menu_trainings",
                text="📚 آموزش‌ها"
            )
        )
        .row(
            builder.button(
                id="edit_start",
                text="✏️ پیام استارت"
            ),
            builder.button(
                id="delete_bot",
                text="🗑 حذف ربات"
            )
        )
        .row(
            builder.button(
                id="back_to_main",
                text="🔙 بازگشت"
            )
        )
        .build()
    )

    return keypad


# =========================================================
# کیبورد منوی دکمه‌ها
# =========================================================

def buttons_menu_keypad():

    builder = ChatKeypadBuilder()

    keypad = (
        builder
        .row(
            builder.button(
                id="make_button",
                text="➕ ساخت دکمه"
            ),
            builder.button(
                id="edit_buttons",
                text="✏️ ویرایش دکمه"
            )
        )
        .row(
            builder.button(
                id="delete_buttons",
                text="🗑 حذف دکمه"
            ),
            builder.button(
                id="back_to_bot_manager",
                text="🔙 بازگشت"
            )
        )
        .build()
    )

    return keypad


# =========================================================
# کیبورد منوی آموزش‌ها
# =========================================================

def trainings_menu_keypad():

    builder = ChatKeypadBuilder()

    keypad = (
        builder
        .row(
            builder.button(
                id="training",
                text="➕ آموزش جدید"
            ),
            builder.button(
                id="edit_training",
                text="✏️ ویرایش آموزش"
            )
        )
        .row(
            builder.button(
                id="delete_training",
                text="🗑 حذف آموزش"
            ),
            builder.button(
                id="back_to_bot_manager",
                text="🔙 بازگشت"
            )
        )
        .build()
    )

    return keypad


# =========================================================
# کیبورد ربات فرزند
# =========================================================

def child_keyboard(buttons):

    builder = ChatKeypadBuilder()

    if not buttons:
        return builder.build()

    for i in range(0, len(buttons), 2):

        row = []

        for button in buttons[i:i + 2]:

            row.append(
                builder.button(
                    id=button["id"],
                    text=button["text"]
                )
            )

        builder.row(*row)

    return builder.build()


# =========================================================
# پیدا کردن اطلاعات ربات
# =========================================================

def find_bot_data(token_id):

    for uid in DATA["users"]:

        bots = DATA["users"][uid]["bots"]

        if token_id in bots:
            return bots[token_id]

    return None


# =========================================================
# پیدا کردن ربات با ID
# =========================================================

def find_bot_by_id(uid, bot_id):
    user_data = get_user_data(uid)
    return user_data["bots"].get(bot_id)


# =========================================================
# فعال کردن ربات فرزند
# =========================================================

async def activate_bot(uid, bot_name, token):

    token = token.strip()
    bot_name = bot_name.strip()

    if not token:
        return False, None, "توکن خالی است."

    if not bot_name:
        return False, None, "اسم ربات خالی است."

    if token == "/start":
        return False, None, "این توکن نیست."

    # بررسی محدودیت تعداد ربات‌ها
    user_data = get_user_data(uid)
    limits = get_user_limits(uid)
    
    current_bots_count = len(user_data["bots"])
    
    if current_bots_count >= limits["bot_limit"]:
        if limits["is_vip"]:
            return False, None, f"شما به حداکثر تعداد ربات‌ها رسیده‌اید (حداکثر {limits['bot_limit']} ربات)."
        else:
            return False, None, f"شما به حداکثر تعداد ربات‌ها رسیده‌اید (حداکثر {limits['bot_limit']} ربات).\nبرای ارتقا به اکانت ویژه، از منوی اکانت ویژه استفاده کنید."

    try:

        bot = Robot(token)

        # بررسی توکن
        me = await bot.get_me()

        if not me:
            return False, None, "توکن معتبر نیست."

        tid = make_token_id(token)

        user_data = get_user_data(uid)

        # اگر قبلاً وجود داشت، اطلاعاتش حفظ شود
        old_data = user_data["bots"].get(
            tid,
            {}
        )

        user_data["bots"][tid] = {

            "token": token,

            "name": bot_name,

            "questions": old_data.get(
                "questions",
                {}
            ),

            "buttons": old_data.get(
                "buttons",
                []
            )
        }

        save_data()

        child_bots[tid] = bot

        return True, tid, "OK"

    except Exception as e:

        print(
            "TOKEN ERROR:",
            type(e).__name__,
            str(e)
        )

        return (
            False,
            None,
            "توکن نامعتبر است یا ربات قابل دسترسی نیست."
        )


# =========================================================
# ربات مادر
# =========================================================

mother = Robot(MOTHER_TOKEN)


# =========================================================
# /start ربات مادر
# =========================================================

@mother.on_message(commands=["start"])
async def mother_start(bot: Robot, message: Message):

    uid = get_user_id(message)

    if not uid:
        return

    user_data = get_user_data(uid)

    states.pop(uid, None)

    await message.reply_keypad(
        "🤖 ربات مادر فعال است.\n\n"
        f"👨‍💻 سازنده: {CREATOR}\n\n"
        "برای شروع یک ربات جدید اضافه کن:",
        build_main_keypad(uid)
    )


# =========================================================
# بازگشت به منوی اصلی
# =========================================================

@mother.on_callback("back_to_main")
async def back_to_main(bot: Robot, message: Message):

    uid = get_user_id(message)

    if not uid:
        return

    states.pop(uid, None)

    await message.reply_keypad(
        "🤖 منوی اصلی:\n\n"
        f"👨‍💻 سازنده: {CREATOR}",
        build_main_keypad(uid)
    )


# =========================================================
# بازگشت به منوی مدیریت ربات
# =========================================================

@mother.on_callback("back_to_bot_manager")
async def back_to_bot_manager(bot: Robot, message: Message):

    uid = get_user_id(message)

    if not uid:
        return

    state_data = states.get(uid)
    
    if not state_data or "bot_id" not in state_data:
        await back_to_main(bot, message)
        return
    
    bot_id = state_data["bot_id"]
    bot_data = find_bot_by_id(uid, bot_id)
    
    if not bot_data:
        await back_to_main(bot, message)
        return
    
    states.pop(uid, None)
    
    await message.reply_keypad(
        f"🤖 **مدیریت ربات: {bot_data.get('name', 'ربات')}**\n\n"
        f"تعداد دکمه‌ها: {len(bot_data.get('buttons', []))}\n"
        f"تعداد آموزش‌ها: {len(bot_data.get('questions', {}))}",
        bot_manager_keypad(bot_data.get('name', 'ربات'))
    )


# =========================================================
# انتخاب ربات از منوی اصلی
# =========================================================

@mother.on_callback()
async def handle_bot_selection(bot: Robot, message: Message):

    uid = get_user_id(message)

    if not uid:
        return

    try:
        button_id = message.aux_data.button_id
    except Exception:
        return

    if not button_id or not button_id.startswith("bot_"):
        return

    bot_id = button_id.replace("bot_", "")
    bot_data = find_bot_by_id(uid, bot_id)
    
    if not bot_data:
        await message.reply("❌ ربات پیدا نشد.")
        return
    
    states[uid] = {
        "state": "bot_manager",
        "bot_id": bot_id
    }
    
    await message.reply_keypad(
        f"🤖 **مدیریت ربات: {bot_data.get('name', 'ربات')}**\n\n"
        f"تعداد دکمه‌ها: {len(bot_data.get('buttons', []))}\n"
        f"تعداد آموزش‌ها: {len(bot_data.get('questions', {}))}",
        bot_manager_keypad(bot_data.get('name', 'ربات'))
    )


# =========================================================
# افزودن ربات
# =========================================================

@mother.on_callback("add_bot")
async def add_bot(bot: Robot, message: Message):

    uid = get_user_id(message)

    if not uid:
        return

    # بررسی محدودیت تعداد ربات‌ها
    user_data = get_user_data(uid)
    limits = get_user_limits(uid)
    
    current_bots_count = len(user_data["bots"])
    
    if current_bots_count >= limits["bot_limit"]:
        if limits["is_vip"]:
            await message.reply(
                f"❌ شما به حداکثر تعداد ربات‌ها رسیده‌اید (حداکثر {limits['bot_limit']} ربات)."
            )
        else:
            await message.reply(
                f"❌ شما به حداکثر تعداد ربات‌ها رسیده‌اید (حداکثر {limits['bot_limit']} ربات).\n"
                "برای ارتقا به اکانت ویژه، از منوی اکانت ویژه استفاده کنید."
            )
        return

    states[uid] = {
        "state": "waiting_bot_name"
    }

    await message.reply(
        "🤖 **افزودن ربات جدید**\n\n"
        "لطفاً یک اسم برای ربات انتخاب کن:\n\n"
        "مثال:\n"
        "ربات فروشگاه"
    )


# =========================================================
# منوی اکانت ویژه
# =========================================================

@mother.on_callback("menu_vip")
async def menu_vip(bot: Robot, message: Message):

    uid = get_user_id(message)

    if not uid:
        return

    if is_vip(uid):
        await message.reply(
            "⭐ **اکانت ویژه**\n\n"
            "✅ شما کاربر ویژه هستید!\n\n"
            "🎯 امکانات ویژه:\n"
            f"• تعداد ربات‌ها: {VIP_BOT_LIMIT} عدد\n"
            "• تعداد دکمه‌ها: نامحدود\n"
            "• تعداد آموزش‌ها: نامحدود\n\n"
            "🙏 از اعتماد شما سپاسگزاریم!"
        )
        return

    await message.reply(
        "⭐ **ارتقا به اکانت ویژه**\n\n"
        "کد یکبار مصرف خود را وارد کنید.\n\n"
        "اگر کد ندارید، با سازنده ربات تماس بگیرید."
    )
    
    states[uid] = {
        "state": "waiting_vip_code"
    }


# =========================================================
# منوی دکمه‌ها
# =========================================================

@mother.on_callback("menu_buttons")
async def menu_buttons(bot: Robot, message: Message):

    uid = get_user_id(message)

    if not uid:
        return

    state_data = states.get(uid)
    
    if not state_data or "bot_id" not in state_data:
        await message.reply("❌ لطفاً ابتدا یک ربات را انتخاب کنید.")
        return
    
    bot_id = state_data["bot_id"]
    bot_data = find_bot_by_id(uid, bot_id)

    if not bot_data:
        await message.reply("❌ ربات پیدا نشد.")
        return

    await message.reply_keypad(
        "🔘 **مدیریت دکمه‌ها**\n\n"
        f"تعداد دکمه‌ها: {len(bot_data['buttons'])}",
        buttons_menu_keypad()
    )


# =========================================================
# منوی آموزش‌ها
# =========================================================

@mother.on_callback("menu_trainings")
async def menu_trainings(bot: Robot, message: Message):

    uid = get_user_id(message)

    if not uid:
        return

    state_data = states.get(uid)
    
    if not state_data or "bot_id" not in state_data:
        await message.reply("❌ لطفاً ابتدا یک ربات را انتخاب کنید.")
        return
    
    bot_id = state_data["bot_id"]
    bot_data = find_bot_by_id(uid, bot_id)

    if not bot_data:
        await message.reply("❌ ربات پیدا نشد.")
        return

    await message.reply_keypad(
        "📚 **مدیریت آموزش‌ها**\n\n"
        f"تعداد آموزش‌ها: {len(bot_data['questions'])}",
        trainings_menu_keypad()
    )


# =========================================================
# ویرایش پیام استارت
# =========================================================

@mother.on_callback("edit_start")
async def edit_start(bot: Robot, message: Message):

    uid = get_user_id(message)

    if not uid:
        return

    state_data = states.get(uid)
    
    if not state_data or "bot_id" not in state_data:
        await message.reply("❌ لطفاً ابتدا یک ربات را انتخاب کنید.")
        return
    
    bot_id = state_data["bot_id"]
    user_data = get_user_data(uid)
    current_start = user_data.get("start_message", "👋 سلام! به ربات من خوش آمدی.")

    states[uid] = {
        "state": "waiting_edit_start",
        "bot_id": bot_id
    }

    await message.reply(
        f"✏️ **ویرایش پیام استارت**\n\n"
        f"پیام فعلی:\n{current_start}\n\n"
        "پیام جدید را ارسال کنید."
    )


# =========================================================
# ساخت دکمه
# =========================================================

@mother.on_callback("make_button")
async def make_button(bot: Robot, message: Message):

    uid = get_user_id(message)

    if not uid:
        return

    state_data = states.get(uid)
    
    if not state_data or "bot_id" not in state_data:
        await message.reply("❌ لطفاً ابتدا یک ربات را انتخاب کنید.")
        return
    
    bot_id = state_data["bot_id"]
    bot_data = find_bot_by_id(uid, bot_id)

    if not bot_data:

        await message.reply(
            "❌ ربات پیدا نشد."
        )

        return

    # بررسی محدودیت تعداد دکمه‌ها
    limits = get_user_limits(uid)
    current_buttons = len(bot_data["buttons"])
    
    if current_buttons >= limits["button_limit"]:
        if limits["is_vip"]:
            await message.reply(
                f"❌ شما به حداکثر تعداد دکمه‌ها رسیده‌اید (حداکثر {limits['button_limit']} دکمه)."
            )
        else:
            await message.reply(
                f"❌ شما به حداکثر تعداد دکمه‌ها رسیده‌اید (حداکثر {limits['button_limit']} دکمه).\n"
                "برای ارتقا به اکانت ویژه، از منوی اکانت ویژه استفاده کنید."
            )
        return

    states[uid] = {
        "state": "waiting_button_text",
        "bot_id": bot_id
    }

    await message.reply(
        "🔘 **ساخت دکمه جدید**\n\n"
        "متن دکمه را بفرست.\n\n"
        "مثال:\n"
        "📞 ارتباط با ما"
    )


# =========================================================
# ویرایش دکمه‌ها
# =========================================================

@mother.on_callback("edit_buttons")
async def edit_buttons(bot: Robot, message: Message):

    uid = get_user_id(message)

    if not uid:
        return

    state_data = states.get(uid)
    
    if not state_data or "bot_id" not in state_data:
        await message.reply("❌ لطفاً ابتدا یک ربات را انتخاب کنید.")
        return
    
    bot_id = state_data["bot_id"]
    bot_data = find_bot_by_id(uid, bot_id)

    if not bot_data:

        await message.reply(
            "❌ ربات پیدا نشد."
        )

        return

    if not bot_data["buttons"]:

        await message.reply(
            "❌ هیچ دکمه‌ای برای ویرایش وجود ندارد."
        )

        return

    states[uid] = {
        "state": "waiting_edit_button",
        "bot_id": bot_id
    }

    # نمایش لیست دکمه‌ها
    buttons_list = ""
    for i, btn in enumerate(bot_data["buttons"], 1):
        buttons_list += f"{i}. {btn['text']}\n"

    await message.reply(
        f"✏️ **ویرایش دکمه**\n\n"
        f"دکمه‌های موجود:\n{buttons_list}\n"
        "شماره دکمه‌ای که می‌خواهید ویرایش کنید را بفرستید."
    )


# =========================================================
# حذف دکمه‌ها
# =========================================================

@mother.on_callback("delete_buttons")
async def delete_buttons(bot: Robot, message: Message):

    uid = get_user_id(message)

    if not uid:
        return

    state_data = states.get(uid)
    
    if not state_data or "bot_id" not in state_data:
        await message.reply("❌ لطفاً ابتدا یک ربات را انتخاب کنید.")
        return
    
    bot_id = state_data["bot_id"]
    bot_data = find_bot_by_id(uid, bot_id)

    if not bot_data:

        await message.reply(
            "❌ ربات پیدا نشد."
        )

        return

    if not bot_data["buttons"]:

        await message.reply(
            "❌ هیچ دکمه‌ای برای حذف وجود ندارد."
        )

        return

    states[uid] = {
        "state": "waiting_delete_button",
        "bot_id": bot_id
    }

    # نمایش لیست دکمه‌ها
    buttons_list = ""
    for i, btn in enumerate(bot_data["buttons"], 1):
        buttons_list += f"{i}. {btn['text']}\n"

    await message.reply(
        f"🗑 **حذف دکمه**\n\n"
        f"دکمه‌های موجود:\n{buttons_list}\n"
        "شماره دکمه‌ای که می‌خواهید حذف کنید را بفرستید.\n"
        "برای حذف همه دکمه‌ها، عدد 0 را بفرستید."
    )


# =========================================================
# حذف ربات
# =========================================================

@mother.on_callback("delete_bot")
async def delete_bot(bot: Robot, message: Message):

    uid = get_user_id(message)

    if not uid:
        return

    state_data = states.get(uid)
    
    if not state_data or "bot_id" not in state_data:
        await message.reply("❌ لطفاً ابتدا یک ربات را انتخاب کنید.")
        return
    
    bot_id = state_data["bot_id"]
    user_data = get_user_data(uid)
    
    if bot_id not in user_data["bots"]:
        await message.reply("❌ ربات پیدا نشد.")
        return

    # حذف ربات
    del user_data["bots"][bot_id]
    save_data()
    
    # حذف ربات از لیست فعال
    if bot_id in child_bots:
        del child_bots[bot_id]
    if bot_id in child_tasks:
        del child_tasks[bot_id]
    
    states.pop(uid, None)
    
    await message.reply_keypad(
        f"✅ ربات با موفقیت حذف شد!",
        build_main_keypad(uid)
    )


# =========================================================
# آموزش جدید
# =========================================================

@mother.on_callback("training")
async def training(bot: Robot, message: Message):

    uid = get_user_id(message)

    if not uid:
        return

    state_data = states.get(uid)
    
    if not state_data or "bot_id" not in state_data:
        await message.reply("❌ لطفاً ابتدا یک ربات را انتخاب کنید.")
        return
    
    bot_id = state_data["bot_id"]
    bot_data = find_bot_by_id(uid, bot_id)

    if not bot_data:

        await message.reply(
            "❌ ربات پیدا نشد."
        )

        return

    # بررسی محدودیت تعداد آموزش‌ها
    limits = get_user_limits(uid)
    current_questions = len(bot_data["questions"])
    
    if current_questions >= limits["question_limit"]:
        if limits["is_vip"]:
            await message.reply(
                f"❌ شما به حداکثر تعداد آموزش‌ها رسیده‌اید (حداکثر {limits['question_limit']} آموزش)."
            )
        else:
            await message.reply(
                f"❌ شما به حداکثر تعداد آموزش‌ها رسیده‌اید (حداکثر {limits['question_limit']} آموزش).\n"
                "برای ارتقا به اکانت ویژه، از منوی اکانت ویژه استفاده کنید."
            )
        return

    states[uid] = {
        "state": "waiting_question",
        "bot_id": bot_id
    }

    await message.reply(
        "📚 **آموزش جدید**\n\n"
        "سؤال یا متنی که می‌خواهی ربات یاد بگیرد را ارسال کن.\n\n"
        "مثال:\n"
        "سلام"
    )


# =========================================================
# ویرایش آموزش‌ها
# =========================================================

@mother.on_callback("edit_training")
async def edit_training(bot: Robot, message: Message):

    uid = get_user_id(message)

    if not uid:
        return

    state_data = states.get(uid)
    
    if not state_data or "bot_id" not in state_data:
        await message.reply("❌ لطفاً ابتدا یک ربات را انتخاب کنید.")
        return
    
    bot_id = state_data["bot_id"]
    bot_data = find_bot_by_id(uid, bot_id)

    if not bot_data:

        await message.reply(
            "❌ ربات پیدا نشد."
        )

        return

    if not bot_data["questions"]:

        await message.reply(
            "❌ هیچ آموزشی برای ویرایش وجود ندارد."
        )

        return

    states[uid] = {
        "state": "waiting_edit_training",
        "bot_id": bot_id
    }

    # نمایش لیست آموزش‌ها
    questions_list = ""
    for i, (q, a) in enumerate(bot_data["questions"].items(), 1):
        questions_list += f"{i}. {q}\n"

    await message.reply(
        f"✏️ **ویرایش آموزش**\n\n"
        f"آموزش‌های موجود:\n{questions_list}\n"
        "شماره آموزشی که می‌خواهید ویرایش کنید را بفرستید."
    )


# =========================================================
# حذف آموزش‌ها
# =========================================================

@mother.on_callback("delete_training")
async def delete_training(bot: Robot, message: Message):

    uid = get_user_id(message)

    if not uid:
        return

    state_data = states.get(uid)
    
    if not state_data or "bot_id" not in state_data:
        await message.reply("❌ لطفاً ابتدا یک ربات را انتخاب کنید.")
        return
    
    bot_id = state_data["bot_id"]
    bot_data = find_bot_by_id(uid, bot_id)

    if not bot_data:

        await message.reply(
            "❌ ربات پیدا نشد."
        )

        return

    if not bot_data["questions"]:

        await message.reply(
            "❌ هیچ آموزشی برای حذف وجود ندارد."
        )

        return

    states[uid] = {
        "state": "waiting_delete_training",
        "bot_id": bot_id
    }

    # نمایش لیست آموزش‌ها
    questions_list = ""
    for i, (q, a) in enumerate(bot_data["questions"].items(), 1):
        questions_list += f"{i}. {q}\n"

    await message.reply(
        f"🗑 **حذف آموزش**\n\n"
        f"آموزش‌های موجود:\n{questions_list}\n"
        "شماره آموزشی که می‌خواهید حذف کنید را بفرستید.\n"
        "برای حذف همه آموزش‌ها، عدد 0 را بفرستید."
    )


# =========================================================
# دریافت پیام‌های ربات مادر
# =========================================================

@mother.on_message()
async def mother_messages(bot: Robot, message: Message):

    uid = get_user_id(message)

    if not uid:
        return

    text = getattr(message, "text", None)

    if not text:
        return

    text = str(text).strip()

    # =====================================================
    # خیلی مهم:
    # دستورات را وارد سیستم توکن/آموزش نکن
    # =====================================================

    if text.startswith("/"):
        return

    state_data = states.get(uid)

    # =====================================================
    # بررسی کد مخفی (فقط سازنده می‌دونه)
    # =====================================================
    
    if text == SECRET_CODE:
        # تولید کد یکبار مصرف
        temp_code = generate_temp_code()
        
        # ذخیره کد در دیتابیس
        if "temp_codes" not in DATA:
            DATA["temp_codes"] = {}
        
        DATA["temp_codes"][temp_code] = uid
        save_data()
        
        await message.reply(
            f"🔐 **کد یکبار مصرف شما:**\n\n"
            f"`{temp_code}`\n\n"
            f"این کد را در منوی اکانت ویژه وارد کنید."
        )
        
        # پاک کردن state اگر وجود دارد
        if uid in states:
            states.pop(uid)
        
        return


    # =====================================================
    # دریافت کد یکبار مصرف (منوی اکانت ویژه)
    # =====================================================
    
    if state_data and state_data.get("state") == "waiting_vip_code":
        
        if text in DATA.get("temp_codes", {}):
            user_id = DATA["temp_codes"][text]
            
            if user_id == uid:
                # ارتقا به اکانت ویژه
                VIP_USERS.add(uid)
                DATA["vip_users"] = list(VIP_USERS)
                
                # حذف کد یکبار مصرف
                del DATA["temp_codes"][text]
                save_data()
                
                states.pop(uid, None)
                
                await message.reply_keypad(
                    "🎉 **تبریک! شما به اکانت ویژه ارتقا یافتید!** ⭐\n\n"
                    "امکانات جدید شما:\n"
                    f"• تعداد ربات‌ها: {VIP_BOT_LIMIT} عدد\n"
                    "• تعداد دکمه‌ها: نامحدود\n"
                    "• تعداد آموزش‌ها: نامحدود\n\n"
                    "از منوی اصلی استفاده کنید:",
                    build_main_keypad(uid)
                )
                
                return
            else:
                await message.reply(
                    "❌ این کد یکبار مصرف متعلق به شما نیست!"
                )
                return
        else:
            await message.reply(
                "❌ کد یکبار مصرف نامعتبر است!\n\n"
                "لطفاً کد صحیح را وارد کنید."
            )
            return

    if not state_data:
        return

    state = state_data.get("state")


    # =====================================================
    # دریافت اسم ربات
    # =====================================================

    if state == "waiting_bot_name":

        bot_name = text

        if not bot_name:

            await message.reply(
                "❌ اسم ربات نمی‌تواند خالی باشد."
            )

            return

        states[uid] = {
            "state": "waiting_token",
            "bot_name": bot_name
        }

        await message.reply(
            "✅ اسم ربات ثبت شد.\n\n"
            f"🤖 {bot_name}\n\n"
            "حالا توکن ربات را ارسال کن.\n\n"
            "⚠️ فقط توکن رباتی که خودت ساخته‌ای را ارسال کن."
        )

        return


    # =====================================================
    # دریافت توکن
    # =====================================================

    if state == "waiting_token":

        token = text
        bot_name = state_data.get("bot_name", "ربات")

        if not token:

            await message.reply(
                "❌ توکن خالی است."
            )

            return

        await message.reply(
            "⏳ در حال بررسی توکن..."
        )

        ok, tid, error = await activate_bot(
            uid,
            bot_name,
            token
        )

        if not ok:

            await message.reply(
                "❌ فعال‌سازی انجام نشد.\n\n"
                f"{error}"
            )

            return

        states.pop(uid, None)

        # ذخیره bot_id در state برای مدیریت بعدی
        states[uid] = {
            "state": "bot_manager",
            "bot_id": tid
        }

        await message.reply_keypad(
            f"✅ ربات '{bot_name}' با موفقیت فعال شد! 🎉\n\n"
            f"👨‍💻 سازنده: {CREATOR}\n\n"
            "از منوی مدیریت ربات استفاده کن:",
            bot_manager_keypad(bot_name)
        )

        # اجرای ربات
        await start_child_bot(tid)

        return


    # =====================================================
    # ویرایش پیام استارت
    # =====================================================

    if state == "waiting_edit_start":

        bot_id = state_data["bot_id"]
        user_data = get_user_data(uid)
        user_data["start_message"] = format_text(text)
        save_data()
        
        states[uid] = {
            "state": "bot_manager",
            "bot_id": bot_id
        }
        
        bot_data = find_bot_by_id(uid, bot_id)

        await message.reply_keypad(
            "✅ پیام استارت با موفقیت ویرایش شد!\n\n"
            f"پیام جدید:\n{format_text(text)}\n\n"
            "از منوی مدیریت ربات استفاده کن:",
            bot_manager_keypad(bot_data.get('name', 'ربات'))
        )

        return


    # =====================================================
    # دریافت متن دکمه
    # =====================================================

    if state == "waiting_button_text":

        button_text = text
        bot_id = state_data["bot_id"]

        if not button_text:

            await message.reply(
                "❌ متن دکمه نمی‌تواند خالی باشد."
            )

            return

        states[uid] = {
            "state": "waiting_button_response",
            "bot_id": bot_id,
            "button_text": button_text
        }

        await message.reply(
            "✅ متن دکمه دریافت شد.\n\n"
            f"🔘 {button_text}\n\n"
            "حالا جوابی که باید با زدن این دکمه ارسال شود را بفرست."
        )

        return


    # =====================================================
    # پاسخ دکمه
    # =====================================================

    if state == "waiting_button_response":

        response = text
        bot_id = state_data["bot_id"]

        user_data = get_user_data(uid)

        bot_data = user_data["bots"].get(bot_id)

        if not bot_data:

            states.pop(uid, None)

            await message.reply(
                "❌ ربات پیدا نشد."
            )

            return

        button_text = state_data["button_text"]

        number = len(
            bot_data["buttons"]
        ) + 1

        new_button = {

            "id": f"user_button_{number}",

            "text": button_text,

            "response": response
        }

        bot_data["buttons"].append(
            new_button
        )

        save_data()

        states[uid] = {
            "state": "bot_manager",
            "bot_id": bot_id
        }

        await message.reply_keypad(
            "✅ دکمه با موفقیت ساخته شد! 🎉\n\n"
            f"🔘 متن دکمه:\n{button_text}\n\n"
            "از منوی مدیریت ربات استفاده کن:",
            bot_manager_keypad(bot_data.get('name', 'ربات'))
        )

        # تلاش برای ارسال کیبورد جدید
        child = child_bots.get(bot_id)

        if child:

            try:

                keypad = child_keyboard(
                    bot_data["buttons"]
                )

                await child.send_message(
                    chat_id=uid,
                    text="🔘 دکمه جدید برای ربات فعال شد.",
                    chat_keypad=keypad,
                    chat_keypad_type="New"
                )

            except Exception as e:

                print(
                    "KEYPAD UPDATE ERROR:",
                    e
                )

        return


    # =====================================================
    # دریافت سؤال آموزشی
    # =====================================================

    if state == "waiting_question":

        question = text
        bot_id = state_data["bot_id"]

        if not question:

            await message.reply(
                "❌ سؤال خالی است."
            )

            return

        states[uid] = {

            "state": "waiting_answer",
            "bot_id": bot_id,
            "question": question
        }

        await message.reply(
            "✅ سؤال دریافت شد.\n\n"
            f"❓ {question}\n\n"
            "حالا جواب این سؤال را ارسال کن."
        )

        return


    # =====================================================
    # دریافت جواب آموزشی
    # =====================================================

    if state == "waiting_answer":

        answer = text
        bot_id = state_data["bot_id"]
        question = state_data["question"]

        user_data = get_user_data(uid)

        bot_data = user_data["bots"].get(bot_id)

        if not bot_data:

            states.pop(uid, None)

            await message.reply(
                "❌ ربات پیدا نشد."
            )

            return

        bot_data["questions"][question] = answer

        save_data()

        states[uid] = {
            "state": "bot_manager",
            "bot_id": bot_id
        }

        await message.reply_keypad(
            "🧠 آموزش با موفقیت ذخیره شد! ✅\n\n"
            f"❓ سؤال:\n{question}\n\n"
            "از منوی مدیریت ربات استفاده کن:",
            bot_manager_keypad(bot_data.get('name', 'ربات'))
        )

        return


    # =====================================================
    # ویرایش دکمه
    # =====================================================

    if state == "waiting_edit_button":

        bot_id = state_data["bot_id"]
        user_data = get_user_data(uid)
        bot_data = user_data["bots"].get(bot_id)

        if not bot_data:
            states.pop(uid, None)
            await message.reply("❌ ربات پیدا نشد.")
            return

        try:
            index = int(text) - 1
            if 0 <= index < len(bot_data["buttons"]):
                button = bot_data["buttons"][index]
                
                states[uid] = {
                    "state": "waiting_edit_button_text",
                    "bot_id": bot_id,
                    "button_index": index
                }
                
                await message.reply(
                    f"✏️ **ویرایش دکمه**\n\n"
                    f"متن فعلی: {button['text']}\n"
                    f"پاسخ فعلی: {button['response']}\n\n"
                    "متن جدید دکمه را بفرستید:"
                )
            else:
                await message.reply("❌ شماره وارد شده معتبر نیست.")
        except ValueError:
            await message.reply("❌ لطفاً یک شماره معتبر بفرستید.")

        return


    # =====================================================
    # ویرایش متن دکمه
    # =====================================================

    if state == "waiting_edit_button_text":

        new_text = text
        bot_id = state_data["bot_id"]
        index = state_data["button_index"]
        user_data = get_user_data(uid)
        bot_data = user_data["bots"].get(bot_id)

        if not bot_data:
            states.pop(uid, None)
            await message.reply("❌ ربات پیدا نشد.")
            return

        if 0 <= index < len(bot_data["buttons"]):
            bot_data["buttons"][index]["text"] = new_text
            save_data()
            
            states[uid] = {
                "state": "waiting_edit_button_response",
                "bot_id": bot_id,
                "button_index": index
            }
            
            await message.reply(
                f"✅ متن دکمه ویرایش شد.\n\n"
                f"متن جدید: {new_text}\n\n"
                "حالا پاسخ جدید دکمه را بفرستید:"
            )
        else:
            await message.reply("❌ خطا در ویرایش دکمه.")

        return


    # =====================================================
    # ویرایش پاسخ دکمه
    # =====================================================

    if state == "waiting_edit_button_response":

        new_response = text
        bot_id = state_data["bot_id"]
        index = state_data["button_index"]
        user_data = get_user_data(uid)
        bot_data = user_data["bots"].get(bot_id)

        if not bot_data:
            states.pop(uid, None)
            await message.reply("❌ ربات پیدا نشد.")
            return

        if 0 <= index < len(bot_data["buttons"]):
            bot_data["buttons"][index]["response"] = new_response
            save_data()
            
            states[uid] = {
                "state": "bot_manager",
                "bot_id": bot_id
            }
            
            await message.reply_keypad(
                "✅ دکمه با موفقیت ویرایش شد! 🎉\n\n"
                f"📝 دکمه: {bot_data['buttons'][index]['text']}\n"
                f"💬 پاسخ: {new_response}\n\n"
                "از منوی مدیریت ربات استفاده کن:",
                bot_manager_keypad(bot_data.get('name', 'ربات'))
            )
            
            # به‌روزرسانی کیبورد ربات فرزند
            child = child_bots.get(bot_id)
            if child:
                try:
                    keypad = child_keyboard(bot_data["buttons"])
                    await child.send_message(
                        chat_id=uid,
                        text="🔄 کیبورد به‌روزرسانی شد.",
                        chat_keypad=keypad,
                        chat_keypad_type="New"
                    )
                except Exception as e:
                    print("KEYPAD UPDATE ERROR:", e)
        else:
            await message.reply("❌ خطا در ویرایش دکمه.")

        return


    # =====================================================
    # حذف دکمه
    # =====================================================

    if state == "waiting_delete_button":

        bot_id = state_data["bot_id"]
        user_data = get_user_data(uid)
        bot_data = user_data["bots"].get(bot_id)

        if not bot_data:
            states.pop(uid, None)
            await message.reply("❌ ربات پیدا نشد.")
            return

        if text == "0":
            bot_data["buttons"] = []
            save_data()
            states[uid] = {
                "state": "bot_manager",
                "bot_id": bot_id
            }
            await message.reply_keypad(
                "✅ همه دکمه‌ها حذف شدند.",
                bot_manager_keypad(bot_data.get('name', 'ربات'))
            )
            
            # به‌روزرسانی کیبورد ربات فرزند
            child = child_bots.get(bot_id)
            if child:
                try:
                    keypad = child_keyboard([])
                    await child.send_message(
                        chat_id=uid,
                        text="🗑 همه دکمه‌ها حذف شدند.",
                        chat_keypad=keypad,
                        chat_keypad_type="New"
                    )
                except Exception as e:
                    print("KEYPAD UPDATE ERROR:", e)
            return

        try:
            index = int(text) - 1
            if 0 <= index < len(bot_data["buttons"]):
                deleted_button = bot_data["buttons"].pop(index)
                save_data()
                states[uid] = {
                    "state": "bot_manager",
                    "bot_id": bot_id
                }
                await message.reply_keypad(
                    f"✅ دکمه '{deleted_button['text']}' حذف شد.",
                    bot_manager_keypad(bot_data.get('name', 'ربات'))
                )
                
                # به‌روزرسانی کیبورد ربات فرزند
                child = child_bots.get(bot_id)
                if child:
                    try:
                        keypad = child_keyboard(bot_data["buttons"])
                        await child.send_message(
                            chat_id=uid,
                            text="🔄 کیبورد به‌روزرسانی شد.",
                            chat_keypad=keypad,
                            chat_keypad_type="New"
                        )
                    except Exception as e:
                        print("KEYPAD UPDATE ERROR:", e)
            else:
                await message.reply("❌ شماره وارد شده معتبر نیست. لطفاً شماره صحیح را بفرستید.")
        except ValueError:
            await message.reply("❌ لطفاً یک شماره معتبر یا 0 برای حذف همه بفرستید.")

        return


    # =====================================================
    # ویرایش آموزش
    # =====================================================

    if state == "waiting_edit_training":

        bot_id = state_data["bot_id"]
        user_data = get_user_data(uid)
        bot_data = user_data["bots"].get(bot_id)

        if not bot_data:
            states.pop(uid, None)
            await message.reply("❌ ربات پیدا نشد.")
            return

        try:
            index = int(text) - 1
            questions_list = list(bot_data["questions"].keys())
            if 0 <= index < len(questions_list):
                question = questions_list[index]
                
                states[uid] = {
                    "state": "waiting_edit_training_question",
                    "bot_id": bot_id,
                    "old_question": question
                }
                
                await message.reply(
                    f"✏️ **ویرایش آموزش**\n\n"
                    f"سؤال فعلی: {question}\n"
                    f"پاسخ فعلی: {bot_data['questions'][question]}\n\n"
                    "سؤال جدید را بفرستید:"
                )
            else:
                await message.reply("❌ شماره وارد شده معتبر نیست.")
        except ValueError:
            await message.reply("❌ لطفاً یک شماره معتبر بفرستید.")

        return


    # =====================================================
    # ویرایش سؤال آموزش
    # =====================================================

    if state == "waiting_edit_training_question":

        new_question = text
        bot_id = state_data["bot_id"]
        old_question = state_data["old_question"]
        user_data = get_user_data(uid)
        bot_data = user_data["bots"].get(bot_id)

        if not bot_data:
            states.pop(uid, None)
            await message.reply("❌ ربات پیدا نشد.")
            return

        if old_question in bot_data["questions"]:
            answer = bot_data["questions"][old_question]
            
            # حذف سؤال قدیمی
            del bot_data["questions"][old_question]
            
            # اضافه کردن سؤال جدید با پاسخ قبلی
            bot_data["questions"][new_question] = answer
            save_data()
            
            states[uid] = {
                "state": "waiting_edit_training_answer",
                "bot_id": bot_id,
                "new_question": new_question
            }
            
            await message.reply(
                f"✅ سؤال ویرایش شد.\n\n"
                f"سؤال جدید: {new_question}\n\n"
                "حالا پاسخ جدید را بفرستید:"
            )
        else:
            await message.reply("❌ خطا در ویرایش آموزش.")

        return


    # =====================================================
    # ویرایش پاسخ آموزش
    # =====================================================

    if state == "waiting_edit_training_answer":

        new_answer = text
        bot_id = state_data["bot_id"]
        new_question = state_data["new_question"]
        user_data = get_user_data(uid)
        bot_data = user_data["bots"].get(bot_id)

        if not bot_data:
            states.pop(uid, None)
            await message.reply("❌ ربات پیدا نشد.")
            return

        bot_data["questions"][new_question] = new_answer
        save_data()
        
        states[uid] = {
            "state": "bot_manager",
            "bot_id": bot_id
        }

        await message.reply_keypad(
            "✅ آموزش با موفقیت ویرایش شد! 🎉\n\n"
            f"❓ سؤال: {new_question}\n"
            f"💬 پاسخ: {new_answer}\n\n"
            "از منوی مدیریت ربات استفاده کن:",
            bot_manager_keypad(bot_data.get('name', 'ربات'))
        )

        return


    # =====================================================
    # حذف آموزش
    # =====================================================

    if state == "waiting_delete_training":

        bot_id = state_data["bot_id"]
        user_data = get_user_data(uid)
        bot_data = user_data["bots"].get(bot_id)

        if not bot_data:
            states.pop(uid, None)
            await message.reply("❌ ربات پیدا نشد.")
            return

        if text == "0":
            bot_data["questions"] = {}
            save_data()
            states[uid] = {
                "state": "bot_manager",
                "bot_id": bot_id
            }
            await message.reply_keypad(
                "✅ همه آموزش‌ها حذف شدند.",
                bot_manager_keypad(bot_data.get('name', 'ربات'))
            )
            return

        try:
            index = int(text) - 1
            questions_list = list(bot_data["questions"].keys())
            if 0 <= index < len(questions_list):
                deleted_question = questions_list[index]
                del bot_data["questions"][deleted_question]
                save_data()
                states[uid] = {
                    "state": "bot_manager",
                    "bot_id": bot_id
                }
                await message.reply_keypad(
                    f"✅ آموزش '{deleted_question}' حذف شد.",
                    bot_manager_keypad(bot_data.get('name', 'ربات'))
                )
            else:
                await message.reply("❌ شماره وارد شده معتبر نیست. لطفاً شماره صحیح را بفرستید.")
        except ValueError:
            await message.reply("❌ لطفاً یک شماره معتبر یا 0 برای حذف همه بفرستید.")

        return


# =========================================================
# اجرای ربات فرزند
# =========================================================

async def start_child_bot(tid):

    # اگر قبلاً در حال اجراست
    if tid in child_tasks:

        task = child_tasks[tid]

        if not task.done():
            return

    bot = child_bots.get(tid)

    if not bot:
        return

    async def runner():

        # -------------------------------
        # /start
        # -------------------------------

        @bot.on_message(commands=["start"])
        async def child_start(
            child_bot: Robot,
            message: Message
        ):

            data = find_bot_data(tid)

            if not data:
                return

            keypad = child_keyboard(
                data["buttons"]
            )

            # پیدا کردن کاربر و ارسال پیام استارت شخصی‌سازی شده
            uid = get_user_id(message)
            start_message = "👋 سلام! به ربات من خوش آمدی."
            
            if uid:
                user_data = get_user_data(uid)
                start_message = user_data.get("start_message", "👋 سلام! به ربات من خوش آمدی.")
                # فرمت‌دهی پیام (مخفی)
                start_message = format_text(start_message)

            await message.reply_keypad(
                start_message,
                keypad
            )


        # -------------------------------
        # دکمه‌ها
        # -------------------------------

        @bot.on_callback()
        async def child_callback(
            child_bot: Robot,
            message: Message
        ):

            data = find_bot_data(tid)

            if not data:
                return

            try:

                button_id = (
                    message
                    .aux_data
                    .button_id
                )

            except Exception:

                button_id = None

            if not button_id:
                return

            for button in data["buttons"]:

                if button["id"] == button_id:

                    await message.reply(
                        format_text(button["response"])
                    )

                    return


        # -------------------------------
        # پیام‌های عادی - پاسخ به سوالات
        # -------------------------------

        @bot.on_message()
        async def child_messages(
            child_bot: Robot,
            message: Message
        ):

            text = getattr(
                message,
                "text",
                None
            )

            if not text:
                return

            text = str(text).strip()

            # دستورات
            if text.startswith("/"):
                return

            data = find_bot_data(tid)

            if not data:
                return

            questions = data["questions"]

            # سؤال آموزش‌داده‌شده
            if text in questions:

                await message.reply(
                    format_text(questions[text])
                )

                return


        # -------------------------------
        # اجرای ربات
        # -------------------------------

        try:

            print(
                f"CHILD BOT STARTED: {tid}"
            )

            await bot.run()

        except Exception as e:

            print(
                f"CHILD BOT ERROR [{tid}]:",
                e
            )


    task = asyncio.create_task(
        runner()
    )

    child_tasks[tid] = task


# =========================================================
# فعال‌سازی ربات‌های ذخیره‌شده
# =========================================================

async def restore_child_bots():

    for uid in DATA["users"]:

        bots = DATA["users"][uid]["bots"]

        for tid in bots:

            bot_data = bots[tid]

            token = bot_data.get(
                "token"
            )

            if not token:
                continue

            try:

                bot = Robot(token)

                await bot.get_me()

                child_bots[tid] = bot

                await start_child_bot(
                    tid
                )

                print(
                    f"RESTORED BOT: {tid}"
                )

            except Exception as e:

                print(
                    f"RESTORE ERROR [{tid}]:",
                    e
                )


# =========================================================
# اجرای اصلی
# =========================================================

async def main():

    print(
        "================================"
    )

    print(
        " RUBKA BOT BUILDER"
    )

    print(
        " Creator:",
        CREATOR
    )

    print(
        "================================"
    )

    # ربات‌های قبلی
    await restore_child_bots()

    print(
        "Starting mother bot..."
    )

    # اجرای مادر
    await mother.run()


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        print(
            "\nBot stopped."
        )

    except Exception as e:

        print(
            "FATAL ERROR:",
            type(e).__name__,
            str(e)
        )
