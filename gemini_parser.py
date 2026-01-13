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
        return f"""You are an expense extraction AI. Extract ALL expenses from this message.

Today's date: {today}
User message: "{user_message}"

If there are MULTIPLE expenses, return a JSON array with multiple objects.
If there is ONE expense, still return an array with one object.

Return ONLY valid JSON array (no markdown, no explanation):

[
  {{
    "date": "{today}",
    "amount": <number>,
    "currency": "INR",
    "category": "<Food|Shopping|Travel|Entertainment|Bills|Healthcare|Groceries|Other>",
    "sub_category": "<specific type>",
    "item": "<product/service name only>",
    "vendor": "<platform name or Unknown>",
    "payment_mode": "<UPI|Cash|Card|Unknown>",
    "notes": "<brief context>"
  }}
]

IMPORTANT RULES:
1. Extract EVERY expense amount mentioned (300, 200, 100, etc.)
2. Match each amount with its context (groceries, phone accessories, petrol)
3. Category mapping:
   - Groceries/vegetables/food items → "Groceries" or "Food"
   - Phone/mobile/electronics → "Shopping"
   - Petrol/fuel/diesel → "Travel"
   - Clothes/shoes → "Shopping"
   - Medicine/doctor → "Healthcare"
4. Item should be SHORT: "groceries", "phone accessories", "petrol", NOT full sentence
5. Return array even for single expense

Examples:

Input: "Spent 300 for groceries and 200 for phone accessories"
Output: [
  {{"date":"{today}","amount":300,"currency":"INR","category":"Groceries","sub_category":"Home groceries","item":"groceries","vendor":"Unknown","payment_mode":"Unknown","notes":"Home groceries"}},
  {{"date":"{today}","amount":200,"currency":"INR","category":"Shopping","sub_category":"Mobile accessories","item":"phone accessories","vendor":"Unknown","payment_mode":"Unknown","notes":"Mobile accessories"}}
]

Input: "Bought pizza from Swiggy for 500"
Output: [
  {{"date":"{today}","amount":500,"currency":"INR","category":"Food","sub_category":"Pizza","item":"pizza","vendor":"Swiggy","payment_mode":"Unknown","notes":"Food delivery"}}
]

Now parse: "{user_message}"
Return JSON array:"""

    async def parse_expense(self, message: str) -> list:
        """Returns list of expense dicts"""
        try:
            prompt = self.create_prompt(message)
            
            # Generate with Gemini
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.2,
                    max_output_tokens=2000,
                )
            )
            
            # Extract and clean text
            text = response.text.strip()
            
            # Remove markdown formatting
            text = re.sub(r'```json\s*', '', text)
            text = re.sub(r'```\s*', '', text)
            text = re.sub(r'^\s*json\s*', '', text, flags=re.IGNORECASE)
            text = text.strip()
            
            # Find JSON array
            array_match = re.search(r'\[.*\]', text, re.DOTALL)
            if array_match:
                text = array_match.group(0)
            
            print(f"📝 Gemini response: {text[:500]}")
            
            # Parse JSON array
            expenses_array = json.loads(text)
            
            # Ensure it's a list
            if not isinstance(expenses_array, list):
                expenses_array = [expenses_array]
            
            # Add metadata to each expense
            timestamp = datetime.now().isoformat()
            for expense in expenses_array:
                expense['raw_message'] = message
                expense['timestamp'] = timestamp
                
                # Clean item field
                if 'item' in expense:
                    item = str(expense['item']).lower()
                    words_to_remove = ['spent', 'on', 'from', 'rupees', 'rs', 'the', 'a', 'an', 'for', 'to', 'my', 'home']
                    item_words = [w for w in item.split() if w not in words_to_remove]
                    expense['item'] = ' '.join(item_words)[:50] if item_words else item[:50]
            
            print(f"✅ Parsed {len(expenses_array)} expense(s)")
            for i, exp in enumerate(expenses_array, 1):
                print(f"  {i}. ₹{exp.get('amount')} - {exp.get('item')} ({exp.get('category')})")
            
            return expenses_array
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON error: {e}")
            print(f"❌ Text: {text[:500]}")
            return self._fallback_parser(message)
            
        except Exception as e:
            print(f"❌ Error: {type(e).__name__}: {e}")
            return self._fallback_parser(message)
    
    def _fallback_parser(self, message: str) -> list:
        """Smart fallback - extracts multiple expenses"""
        print(f"⚠️ Using fallback parser for: {message}")
        
        expenses = []
        message_lower = message.lower()
        
        # Pattern to find amounts with context
        # Matches: "300 for groceries", "200 rupees on phone", etc.
        pattern = r'(\d+)\s*(?:rupees|rs|₹)?\s*(?:for|on|spent|paid)\s+([^,\d]+?)(?=\d+\s*(?:rupees|rs|₹)|and|$)'
        
        matches = re.finditer(pattern, message_lower, re.IGNORECASE)
        
        found_any = False
        for match in matches:
            found_any = True
            amount = float(match.group(1))
            context = match.group(2).strip()
            
            # Determine category and item from context
            category, sub_category, item = self._categorize_from_context(context)
            
            expense = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "amount": amount,
                "currency": Config.DEFAULT_CURRENCY,
                "category": category,
                "sub_category": sub_category,
                "item": item,
                "vendor": self._extract_vendor(context),
                "payment_mode": "Unknown",
                "notes": context[:100],
                "raw_message": message,
                "timestamp": datetime.now().isoformat(),
            }
            expenses.append(expense)
        
        # If no pattern match, try simple amount extraction
        if not found_any:
            amounts = re.findall(r'\b(\d+)\b', message)
            if amounts:
                amount = float(amounts[0])
                category, sub_category, item = self._categorize_from_context(message_lower)
                
                expense = {
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "amount": amount,
                    "currency": Config.DEFAULT_CURRENCY,
                    "category": category,
                    "sub_category": sub_category,
                    "item": item,
                    "vendor": self._extract_vendor(message_lower),
                    "payment_mode": "Unknown",
                    "notes": message[:100],
                    "raw_message": message,
                    "timestamp": datetime.now().isoformat(),
                }
                expenses.append(expense)
        
        return expenses if expenses else [self._default_expense(message)]
    
    def _categorize_from_context(self, context: str) -> tuple:
        """Returns (category, sub_category, item)"""
        context = context.lower()
        
        # Groceries
        grocery_keywords = ['grocery', 'groceries', 'vegetables', 'fruits', 'ration', 'provisions']
        if any(kw in context for kw in grocery_keywords):
            return ("Groceries", "Home groceries", "groceries")
        
        # Travel/Fuel
        travel_keywords = ['petrol', 'diesel', 'fuel', 'gas', 'uber', 'ola', 'taxi', 'auto', 'metro', 'bus']
        for kw in travel_keywords:
            if kw in context:
                return ("Travel", kw.title(), kw)
        
        # Shopping/Electronics
        electronics = ['phone', 'mobile', 'laptop', 'charger', 'headphone', 'earphone', 'cable', 'accessory', 'accessories']
        if any(kw in context for kw in electronics):
            return ("Shopping", "Electronics", self._extract_item_name(context, electronics))
        
        # Clothing
        clothing = ['jeans', 'shirt', 'tshirt', 't-shirt', 'shoes', 'pants', 'dress', 'clothes']
        if any(kw in context for kw in clothing):
            return ("Shopping", "Clothing", self._extract_item_name(context, clothing))
        
        # Food
        food_keywords = ['pizza', 'burger', 'biryani', 'food', 'lunch', 'dinner', 'breakfast', 'snacks', 'coffee', 'tea']
        if any(kw in context for kw in food_keywords):
            return ("Food", "Restaurant/Delivery", self._extract_item_name(context, food_keywords))
        
        # Healthcare
        health_keywords = ['medicine', 'doctor', 'hospital', 'pharmacy', 'medical', 'clinic']
        if any(kw in context for kw in health_keywords):
            return ("Healthcare", "Medical", self._extract_item_name(context, health_keywords))
        
        # Bills
        bill_keywords = ['electricity', 'water', 'internet', 'mobile bill', 'recharge', 'broadband']
        if any(kw in context for kw in bill_keywords):
            return ("Bills", "Utility", self._extract_item_name(context, bill_keywords))
        
        return ("Other", "Miscellaneous", context[:30])
    
    def _extract_item_name(self, context: str, keywords: list) -> str:
        """Extract the most relevant item name"""
        for kw in keywords:
            if kw in context:
                return kw
        # Return first meaningful word
        words = context.split()
        return words[0] if words else "item"
    
    def _extract_vendor(self, context: str) -> str:
        """Extract vendor/platform name"""
        vendors = {
            'swiggy': 'Swiggy', 'zomato': 'Zomato',
            'uber': 'Uber', 'ola': 'Ola',
            'amazon': 'Amazon', 'flipkart': 'Flipkart',
            'myntra': 'Myntra', 'ajio': 'Ajio',
            'bigbasket': 'BigBasket', 'blinkit': 'Blinkit',
            'zepto': 'Zepto', 'dunzo': 'Dunzo',
        }
        
        for key, name in vendors.items():
            if key in context:
                return name
        return "Unknown"
    
    def _default_expense(self, message: str) -> dict:
        """Return default expense when all parsing fails"""
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "amount": 0,
            "currency": Config.DEFAULT_CURRENCY,
            "category": "Other",
            "sub_category": "Needs review",
            "item": "unspecified",
            "vendor": "Unknown",
            "payment_mode": "Unknown",
            "notes": message[:100],
            "raw_message": message,
            "timestamp": datetime.now().isoformat(),
        }
