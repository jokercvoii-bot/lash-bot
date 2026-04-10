import sqlite3
import calendar
import threading
import time
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = "8790900482:AAGww4359xEYm-kVOlr6Aqz95_0F9yr1PvQ"
ADMIN_USERNAME = "ricowalee"

# база
conn = sqlite3.connect("db.sqlite3", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY,
    user TEXT,
    user_id INTEGER,
    date TEXT,
    time TEXT,
    service TEXT,
    status TEXT
)
""")
conn.commit()

user_data = {}
logs = []

# лог
def log(text):
    logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {text}")

def logger():
    while True:
        time.sleep(5)
        print("\n--- LOG ---")
        if logs:
            for l in logs:
                print(l)
            logs.clear()
        else:
            print("Нет событий")

threading.Thread(target=logger, daemon=True).start()

# тексты
texts = {
    "ru": {
        "menu":"💄 LashDinostry",
        "book":"📅 Записаться",
        "lang":"🌍 Язык",
        "date":"Выбери дату",
        "service":"Выбери услугу",
        "time":"Выбери время",
        "done":"✅ Записано\nС вами скоро свяжется lash-мастер 💄",
        "timeout":"❗ Если мастер не написал — напишите: https://t.me/ricowalee"
    },
    "en": {
        "menu":"💄 LashDinostry",
        "book":"📅 Book",
        "lang":"🌍 Language",
        "date":"Choose date",
        "service":"Choose service",
        "time":"Choose time",
        "done":"✅ Booked\nThe lash master will contact you soon 💄",
        "timeout":"❗ If no reply — contact: https://t.me/ricowalee"
    },
    "uz": {
        "menu":"💄 LashDinostry",
        "book":"📅 Yozilish",
        "lang":"🌍 Til",
        "date":"Sana tanlang",
        "service":"Xizmat tanlang",
        "time":"Vaqt tanlang",
        "done":"✅ Yozildingiz\nTez orada lash master siz bilan bog‘lanadi 💄",
        "timeout":"❗ Javob bo‘lmasa yozing: https://t.me/ricowalee"
    }
}

services = {
    "ru": ["Наращивание ресниц","Ламинирование ресниц","Окрашивание ресниц","Окрашивание бровей","Коррекция бровей","Ламинирование бровей"],
    "en": ["Eyelash extensions","Lash lamination","Lash coloring","Brow coloring","Brow correction","Brow lamination"],
    "uz": ["Kiprik kengaytirish","Kiprik laminatsiya","Kiprik bo‘yash","Qosh bo‘yash","Qosh tuzatish","Qosh laminatsiya"]
}

def get_lang(uid):
    return user_data.get(uid, {}).get("lang", "ru")

async def safe_user(user):
    if user.id not in user_data:
        user_data[user.id] = {"lang": "ru"}

# таймер 30 минут
def timeout(user_id, lang):
    time.sleep(1800)
    try:
        Bot(TOKEN).send_message(user_id, texts[lang]["timeout"])
        log(f"TIMEOUT {user_id}")
    except Exception as e:
        log(f"ERROR {e}")

# старт
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await safe_user(user)

    log(f"START {user.username}")

    if user.username == ADMIN_USERNAME:
        kb = [[InlineKeyboardButton("📋 Заявки", callback_data="admin")]]
        await update.message.reply_text("👨‍💼 Админ панель", reply_markup=InlineKeyboardMarkup(kb))
        return

    lang = get_lang(user.id)

    kb = [
        [InlineKeyboardButton(texts[lang]["book"], callback_data="book")],
        [InlineKeyboardButton(texts[lang]["lang"], callback_data="lang")]
    ]

    await update.message.reply_text(texts[lang]["menu"], reply_markup=InlineKeyboardMarkup(kb))

# кнопки
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    await safe_user(user)
    lang = get_lang(user.id)

    log(f"CLICK {query.data}")

    if query.data == "lang":
        kb = [[
            InlineKeyboardButton("🇷🇺", callback_data="ru"),
            InlineKeyboardButton("🇬🇧", callback_data="en"),
            InlineKeyboardButton("🇺🇿", callback_data="uz")
        ]]
        await query.message.reply_text("Language", reply_markup=InlineKeyboardMarkup(kb))

    elif query.data in ["ru","en","uz"]:
        user_data[user.id]["lang"] = query.data
        lang = get_lang(user.id)

        kb = [
            [InlineKeyboardButton(texts[lang]["book"], callback_data="book")],
            [InlineKeyboardButton(texts[lang]["lang"], callback_data="lang")]
        ]
        await query.message.reply_text(texts[lang]["menu"], reply_markup=InlineKeyboardMarkup(kb))

    elif query.data == "book":
        now = datetime.now()
        days = calendar.monthrange(now.year, now.month)[1]

        kb, row = [], []
        for d in range(now.day, days+1):
            row.append(InlineKeyboardButton(str(d), callback_data=f"d_{d}"))
            if len(row) == 3:
                kb.append(row)
                row = []
        if row:
            kb.append(row)

        await query.message.reply_text(texts[lang]["date"], reply_markup=InlineKeyboardMarkup(kb))

    elif query.data.startswith("d_"):
        user_data[user.id]["date"] = query.data.split("_")[1]
        lang = get_lang(user.id)

        kb = [[InlineKeyboardButton(s, callback_data=f"s_{s}")] for s in services[lang]]
        await query.message.reply_text(texts[lang]["service"], reply_markup=InlineKeyboardMarkup(kb))

    elif query.data.startswith("s_"):
        user_data[user.id]["service"] = query.data[2:]
        lang = get_lang(user.id)

        kb, row = [], []
        for h in range(10,19):
            row.append(InlineKeyboardButton(f"{h}:00", callback_data=f"t_{h}"))
            if len(row) == 3:
                kb.append(row)
                row = []
        if row:
            kb.append(row)

        await query.message.reply_text(texts[lang]["time"], reply_markup=InlineKeyboardMarkup(kb))

    elif query.data.startswith("t_"):
        h = query.data.split("_")[1]
        data = user_data.get(user.id, {})

        cursor.execute("INSERT INTO bookings VALUES(NULL,?,?,?,?,?,?)",
                       (user.username,user.id,data.get("date"),f"{h}:00",data.get("service"),"new"))
        conn.commit()

        log(f"BOOK {user.username}")

        await query.message.reply_text(texts[lang]["done"])

        threading.Thread(target=timeout, args=(user.id, lang), daemon=True).start()

    elif query.data == "admin":
        cursor.execute("SELECT id,date,time,service,user FROM bookings")
        rows = cursor.fetchall()

        if not rows:
            await query.message.reply_text("Нет заявок")
            return

        kb = [[InlineKeyboardButton(f"{r[1]} {r[2]}", callback_data=f"a_{r[0]}")] for r in rows]
        await query.message.reply_text("📋 Заявки", reply_markup=InlineKeyboardMarkup(kb))

# CMD
def console():
    while True:
        cmd = input()
        if cmd == "/resetBooked":
            cursor.execute("DELETE FROM bookings")
            conn.commit()
            print("🧹 Заявки очищены")

threading.Thread(target=console, daemon=True).start()

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(buttons))

app.run_polling()
