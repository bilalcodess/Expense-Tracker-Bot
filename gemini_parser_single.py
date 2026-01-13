import google.generativeai as genai
from datetime import datetime
import json
import re
from config import Config

genai.configure(api_key=Config.GEMINI_API_KEY)

class ExpenseParser:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
    def create_prompt(self, user_message: str) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        return f"""Extract expense data from: "{user_message}"

Return ONLY this JSON format (no markdown, no code blocks):
{{"date":"{today}","amount":NUMBER,"currency":"INR","category":"CATEGORY","sub_category":"SUBCATEGORY","item":"ITEM","vendor":"VENDOR","payment_mode":"MODE","notes":"NOTES"}}

Rules:
- amount: extract number only from rupees/₹/rs
- category: Food|Shopping|Travel|Entertainment|Bills|Healthcare|Groceries|Other
- sub_category: Pizza|Jeans|Taxi|Movie|etc (specific type)
- item: ONLY the product/service name (e.g., "pizza", "jeans", "ride")
- vendor: Platform name (Swiggy, Myntra, Uber, Zomato, Amazon, Flipkart, etc.) or "Unknown"
- payment_mode: UPI|Cash|Card|Unknown
- notes: Brief context (NOT the full message)

Examples:
"Spent 500 on pizza from Swiggy" → item: "pizza", vendor: "Swiggy", category: "Food"
"Bought jeans for 1500 from Myntra" → item: "jeans", vendor: "Myntra", category: "Shopping"
"Uber ride 180" → item: "ride", vendor: "Uber", category: "Travel"

Current message: "{user_message}"
Return JSON:"""

    async def parse_expense(self, message: str) -> dict:
        try:
            prompt = self.create_prompt(message)
            
            # Generate with higher token limit
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.2,
                    max_output_tokens=1000,  # Increased from 500
                )
            )
            
            # Extract and clean text
            text = response.text.strip()
            
            # Remove all markdown formatting
            text = re.sub(r'```json\s*', '', text)
            text = re.sub(r'```\s*', '', text)
            text = re.sub(r'^\s*json\s*', '', text, flags=re.IGNORECASE)
            text = text.strip()
            
            # Find JSON object
            json_match = re.search(r'\{[^}]+\}', text, re.DOTALL)
            if json_match:
                text = json_match.group(0)
            
            print(f"📝 Raw Gemini response: {text[:300]}")
            
            # Parse JSON
            expense_data = json.loads(text)
            
            # Validate and clean item field
            if 'item' in expense_data:
                item = expense_data['item'].lower()
                # Remove common words to keep only the actual item
                words_to_remove = ['spent', 'on', 'from', 'rupees', 'rs', 'the', 'a', 'an', 'for', 'to', 'order']
                item_words = [w for w in item.split() if w not in words_to_remove]
                expense_data['item'] = ' '.join(item_words)[:50]
            
            # Add metadata
            expense_data['raw_message'] = message
            expense_data['timestamp'] = datetime.now().isoformat()
            
            print(f"✅ Parsed: Amount={expense_data.get('amount')}, Vendor={expense_data.get('vendor')}, Item={expense_data.get('item')}")
            return expense_data
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON error: {e}")
            print(f"❌ Problematic text: {text[:500]}")
            return self._fallback_parser(message, str(e))
            
        except Exception as e:
            print(f"❌ Error: {type(e).__name__}: {e}")
            return self._fallback_parser(message, str(e))
    
    def _fallback_parser(self, message: str, error: str) -> dict:
        """Smart fallback parser"""
        print(f"⚠️ Using fallback for: {message}")
        
        # Extract amount
        amount = 0
        amount_patterns = [
            r'₹\s*(\d+(?:\.\d{2})?)',
            r'rs\.?\s*(\d+(?:\.\d{2})?)',
            r'rupees?\s*(\d+(?:\.\d{2})?)',
            r'(\d+)\s*(?:rupees|rs|₹)',
            r'\b(\d+)\b'
        ]
        for pattern in amount_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                amount = float(match.group(1))
                break
        
        message_lower = message.lower()
        vendor = "Unknown"
        category = "Other"
        item = "unspecified"
        
        # Vendor detection with category
        vendors = {
            'swiggy': ('Swiggy', 'Food', 'food delivery'),
            'zomato': ('Zomato', 'Food', 'food delivery'),
            'uber': ('Uber', 'Travel', 'ride'),
            'ola': ('Ola', 'Travel', 'ride'),
            'amazon': ('Amazon', 'Shopping', 'product'),
            'flipkart': ('Flipkart', 'Shopping', 'product'),
            'myntra': ('Myntra', 'Shopping', 'clothing'),
            'bigbasket': ('BigBasket', 'Groceries', 'groceries'),
            'blinkit': ('Blinkit', 'Groceries', 'groceries'),
            'zepto': ('Zepto', 'Groceries', 'groceries'),
        }
        
        for key, (vend, cat, default_item) in vendors.items():
            if key in message_lower:
                vendor = vend
                category = cat
                item = default_item
                break
        
        # Extract specific items
        items = {
            'pizza': ('Food', 'pizza'),
            'burger': ('Food', 'burger'),
            'coffee': ('Food', 'coffee'),
            'tea': ('Food', 'tea'),
            'jeans': ('Shopping', 'jeans'),
            'shirt': ('Shopping', 'shirt'),
            'shoes': ('Shopping', 'shoes'),
            'ride': ('Travel', 'ride'),
            'taxi': ('Travel', 'taxi'),
            'movie': ('Entertainment', 'movie ticket'),
            'lunch': ('Food', 'lunch'),
            'dinner': ('Food', 'dinner'),
            'breakfast': ('Food', 'breakfast'),
        }
        
        for key, (cat, item_name) in items.items():
            if key in message_lower:
                item = item_name
                if category == "Other":
                    category = cat
                break
        
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "amount": amount,
            "currency": Config.DEFAULT_CURRENCY,
            "category": category,
            "sub_category": item.title(),
            "item": item,
            "vendor": vendor,
            "payment_mode": "Unknown",
            "notes": f"Auto-parsed from: {message[:100]}",
            "raw_message": message,
            "timestamp": datetime.now().isoformat(),
        }
