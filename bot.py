import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from gemini_parser import extract_expense
from sheets_manager import save_expense

load_dotenv()
print("GEMINI:", os.getenv("GEMINI_API_KEY"))
BOT_TOKEN = os.getenv("BOT_TOKEN")

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    try:
        data = extract_expense(text)
        save_expense(data, text)
        await update.message.reply_text("✅ Expense saved")
    except Exception as e:
        print(e)
        await update.message.reply_text("❌ Could not save expense")

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

print("Bot running...")
app.run_polling()
