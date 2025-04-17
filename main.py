import random
from telegram import Update, Poll, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    MessageHandler, filters, PollAnswerHandler
)
from docx import Document

TOKEN = "8046408146:AAHPaFK0RGq547XadP3GTDF1At5WVi49b48"

FANLAR = {
    "MO'M": "tests/MO'M o'zbek.docx",
    "OO'M": "tests/OO'M o'zbek.docx",
    "OT va BA": "tests/OT va BA o'zbek.docx",
    "TIM": "tests/TIM o'zbek.docx"
}

QUIZ_TIME = 15  # sekund

user_sessions = {}

def parse_docx(filename):
    doc = Document(filename)
    full_text = [para.text.strip() for para in doc.paragraphs if para.text.strip()]
    data = "\n".join(full_text).split('++++')

    questions = []
    for item in data:
        parts = item.strip().split('====')
        if len(parts) >= 2:
            question = parts[0].strip()
            options = [opt.strip() for opt in parts[1:] if opt.strip()]
            correct_index = next((i for i, opt in enumerate(options) if opt.startswith('#')), None)
            if correct_index is not None:
                options[correct_index] = options[correct_index].replace('#', '').strip()
                questions.append((question, options))
    return questions

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Agar oldingi session bo'lsa, uni bekor qilamiz
    if user_id in user_sessions:
        user_sessions.pop(user_id)
        await update.message.reply_text("⛔️ Oldingi test bekor qilindi.")

    # Bosh menyuni ko'rsatamiz
    keyboard = [[fan] for fan in FANLAR.keys()]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("📚 Quyidagi fanlardan birini tanlang:", reply_markup=reply_markup)


async def fan_tanlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tanlangan_fan = update.message.text
    if tanlangan_fan in FANLAR:
        questions = parse_docx(FANLAR[tanlangan_fan])
        random.shuffle(questions)
        user_sessions[update.effective_user.id] = {
            'questions': questions,
            'current_question': 0,
            'chat_id': update.effective_chat.id
        }
        await update.message.reply_text(f"{tanlangan_fan} fani bo'yicha test boshlanmoqda!")
        await send_next_question(update.effective_user.id, context)
    else:
        await update.message.reply_text("Mavjud fanlardan tanlang!")

async def send_next_question(user_id, context: ContextTypes.DEFAULT_TYPE):
    session = user_sessions.get(user_id)

    if session and session['current_question'] < len(session['questions']):
        question, options = session['questions'][session['current_question']]
        options = [opt if len(opt) <= 100 else opt[:97] + '...' for opt in options]

        correct_option = options[0]
        random.shuffle(options)
        correct_index = options.index(correct_option)

        message = await context.bot.send_poll(
            chat_id=session['chat_id'],
            question=question[:300],
            options=options,
            type=Poll.QUIZ,
            correct_option_id=correct_index,
            open_period=QUIZ_TIME,
            is_anonymous=False
        )

        session['poll_id'] = message.poll.id
        session['current_question'] += 1
    else:
        await context.bot.send_message(
            chat_id=session['chat_id'],
            text="✅ Test yakunlandi!"
        )
        user_sessions.pop(user_id, None)

async def receive_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.poll_answer.user.id
    session = user_sessions.get(user_id)
    if session and session['poll_id'] == update.poll_answer.poll_id:
        await send_next_question(user_id, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_sessions:
        user_sessions.pop(user_id)
        await update.message.reply_text("❌ Test bekor qilindi.")
    else:
        await update.message.reply_text("Sizda hech qanday faol test yo'q.")

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Iltimos, /start orqali boshlang.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('cancel', cancel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fan_tanlash))
    app.add_handler(PollAnswerHandler(receive_poll_answer))
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    print("Bot ishga tushdi...")
    app.run_polling()
