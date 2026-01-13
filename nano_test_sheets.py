import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from dotenv import load_dotenv

load_dotenv()

# Test Google Sheets connection
scope = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive'
]

try:
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    
    sheet_id = os.getenv('GOOGLE_SHEET_ID')
    sheet = client.open_by_key(sheet_id)
    
    print("✅ SUCCESS! Connected to Google Sheet")
    print(f"📄 Sheet name: {sheet.title}")
    print(f"📊 Worksheets: {[ws.title for ws in sheet.worksheets()]}")
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    print("\nCommon fixes:")
    print("1. Check credentials.json exists")
    print("2. Verify Sheet ID in .env file")
    print("3. Make sure you shared Sheet with service account email")
