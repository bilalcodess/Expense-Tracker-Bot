import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
    CREDENTIALS_FILE = "credentials.json"
    SHEET_NAME = "Expenses"
    
    # Currency defaults
    DEFAULT_CURRENCY = "INR"
    TIMEZONE = "Asia/Kolkata"

