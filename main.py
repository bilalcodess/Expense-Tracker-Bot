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
import asyncio
import logging

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

**Multiple expenses (NEW!):**
• "Today I spent 300 for groceries and 200 for phone accessories and 100 for petrol"
• "Paid 500 for lunch and 180 for Uber"

I'll automatically:
✅ Extract ALL expenses
✅ Categorize each one
✅ Save to Google Sheets

Commands:
/start - Show this message
/today - Today's total expenses
/help - Get help
    """
    await update.message.reply_text(welcome_msg)

async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show today's total"""
    try:
        total = sheets.get_today_total()
        count = sheets.get_today_count()
        await update.message.reply_text(
            f"💰 Today's Summary:\n\n"
            f"Total: ₹{total:.2f}\n"
            f"Transactions: {count}"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process expense messages - handles multiple expenses"""
    user_message = update.message.text
    chat_id = update.message.chat_id
    
    processing_msg = await update.message.reply_text("⏳ Processing...")
    
    try:
        # Parse expenses (returns list)
        expenses_list = await parser.parse_expense(user_message)
        
        if not expenses_list:
            await processing_msg.edit_text("❌ No expenses found. Try: 'Spent 200 on coffee'")
            return
        
        # Save all expenses to Google Sheets
        success_count = 0
        for expense_data in expenses_list:
            success = await sheets.add_expense(expense_data)
            if success:
                success_count += 1
        
        # Create response message
        if success_count == len(expenses_list):
            if len(expenses_list) == 1:
                # Single expense
                exp = expenses_list[0]
                response = f"""
✅ Expense Saved!

💵 Amount: ₹{exp['amount']}
📁 Category: {exp['category']}
🏷️ Item: {exp['item']}
🏪 Vendor: {exp['vendor']}
📅 Date: {exp['date']}
                """
            else:
                # Multiple expenses
                response = f"✅ Saved {success_count} expenses!\n\n"
                total = sum(exp['amount'] for exp in expenses_list)
                for i, exp in enumerate(expenses_list, 1):
                    response += f"{i}. ₹{exp['amount']} - {exp['item']} ({exp['category']})\n"
                response += f"\n💰 Total: ₹{total:.2f}"
        else:
            response = f"⚠️ Saved {success_count}/{len(expenses_list)} expenses. Check Google Sheet."
            
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        response = f"❌ Error: {str(e)}\n\nTry: 'Spent 200 on coffee'"
    
    await processing_msg.edit_text(response)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors"""
    logger.error(f"Update {update} caused error {context.error}")

def main():
    """Start the bot"""
    application = Application.builder().token(Config.TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", start_command))
    application.add_handler(CommandHandler("today", today_command))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    application.add_error_handler(error_handler)
    
    logger.info("🚀 Bot started!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
