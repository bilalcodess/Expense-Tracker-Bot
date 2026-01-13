import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import Config
from datetime import datetime

class SheetsManager:
    def __init__(self):
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            Config.CREDENTIALS_FILE, scope
        )
        self.client = gspread.authorize(creds)
        self.sheet = self.client.open_by_key(Config.GOOGLE_SHEET_ID)
        self.worksheet = self._get_or_create_worksheet()
        
    def _get_or_create_worksheet(self):
        """Get worksheet or create with headers if doesn't exist"""
        try:
            worksheet = self.sheet.worksheet(Config.SHEET_NAME)
        except gspread.WorksheetNotFound:
            worksheet = self.sheet.add_worksheet(
                title=Config.SHEET_NAME, 
                rows=1000, 
                cols=11
            )
            # Add headers
            headers = [
                "Date", "Amount", "Currency", "Category", "Sub-Category",
                "Item", "Vendor", "Payment Mode", "Notes", 
                "Raw Message", "Timestamp"
            ]
            worksheet.append_row(headers)
            
            # Format headers (bold)
            worksheet.format('A1:K1', {
                "textFormat": {"bold": True},
                "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9}
            })
            
        return worksheet
    
    async def add_expense(self, expense_data: dict) -> bool:
        """Add expense row to sheet"""
        try:
            row = [
                expense_data.get('date', ''),
                expense_data.get('amount', 0),
                expense_data.get('currency', Config.DEFAULT_CURRENCY),
                expense_data.get('category', 'Other'),
                expense_data.get('sub_category', ''),
                expense_data.get('item', ''),
                expense_data.get('vendor', 'Unknown'),
                expense_data.get('payment_mode', 'Unknown'),
                expense_data.get('notes', ''),
                expense_data.get('raw_message', ''),
                expense_data.get('timestamp', datetime.now().isoformat())
            ]
            
            self.worksheet.append_row(row, value_input_option='USER_ENTERED')
            return True
            
        except Exception as e:
            print(f"Error adding to sheet: {e}")
            return False
    
    def get_today_total(self) -> float:
        """Get today's total expenses"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            all_records = self.worksheet.get_all_records()
            
            total = sum(
                float(record['Amount']) 
                for record in all_records 
                if record.get('Date') == today
            )
            return total
        except:
            return 0.0

    def get_today_count(self) -> int:
        """Get count of today's transactions"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            all_records = self.worksheet.get_all_records()
            count = sum(1 for record in all_records if record.get('Date') == today)
            return count
        except:
            return 0
