from telegram import Update
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    filters,
    ContextTypes
)
from config import Config
from gemini_parser import ExpenseParser
from sheets_manager import SheetsManager
import logging
from aiohttp import web
import asyncio
from datetime import datetime
import pytz

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

parser = ExpenseParser()
sheets = SheetsManager()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message"""
    welcome_msg = """
🎯 Welcome to Expense Tracker Bot!

You can add expenses in multiple ways:

**Single expense:**
• "Spent 200 on pizza from Swiggy"
• "Bought jeans for ₹1500 from Myntra"

**Multiple expenses:**
• "Today I spent 300 for groceries and 200 for phone accessories and 100 for petrol"

I'll automatically:
✅ Extract ALL expenses
✅ Categorize each one
✅ Save to Google Sheets

Commands:
/start - Show this message
/today - Today's total expenses
    """
    await update.message.reply_text(welcome_msg)

async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show today's total"""
    try:
        total = sheets.get_today_total()
        count = sheets.get_today_count()
        await update.message.reply_text(
            f"💰 Today's Summary:\n\nTotal: ₹{total:.2f}\nTransactions: {count}"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process expense messages"""
    user_message = update.message.text
    processing_msg = await update.message.reply_text("⏳ Processing...")
    
    # Get date when user sent the message
    ist = pytz.timezone('Asia/Kolkata')
    timestamp = update.message.date.astimezone(ist)
    date_str = timestamp.strftime("%d %b %Y")
    
    try:
        expenses_list = await parser.parse_expense(user_message)
        
        if not expenses_list:
            await processing_msg.edit_text("❌ No expenses found")
            return
        
        success_count = 0
        for expense_data in expenses_list:
            success = await sheets.add_expense(expense_data)
            if success:
                success_count += 1
        
        if success_count == len(expenses_list):
            if len(expenses_list) == 1:
                exp = expenses_list[0]
                response = f"✅ Saved!\n\n💵 ₹{exp['amount']}\n📁 {exp['category']}\n🏷️ {exp['item']}\n🏪 {exp['vendor']}\n\n📅 {date_str}"
            else:
                response = f"✅ Saved {success_count} expenses!\n\n"
                total = sum(exp['amount'] for exp in expenses_list)
                for i, exp in enumerate(expenses_list, 1):
                    response += f"{i}. ₹{exp['amount']} - {exp['item']}\n"
                response += f"\n💰 Total: ₹{total:.2f}\n📅 {date_str}"
        else:
            response = f"⚠️ Saved {success_count}/{len(expenses_list)} expenses"
            
    except Exception as e:
        logger.error(f"Error: {e}")
        response = f"❌ Error: {str(e)}"
    
    await processing_msg.edit_text(response)

async def health_check(request):
    return web.Response(text="OK")

async def start_http_server():
    """Start HTTP server for Render health checks"""
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    import os
    port = int(os.getenv('PORT', 10000))
    
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"🌐 HTTP server started on port {port}")

def main():
    """Start the bot"""
    application = Application.builder().token(Config.TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("today", today_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    loop = asyncio.get_event_loop()
    loop.create_task(start_http_server())
    
    logger.info("🚀 Bot started!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
