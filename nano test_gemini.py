import google.generativeai as genai
from config import Config
import os
from dotenv import load_dotenv

load_dotenv()

# Test Gemini API
api_key = os.getenv('GEMINI_API_KEY')
print(f"API Key found: {api_key[:20]}..." if api_key else "❌ No API key")

try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    test_prompt = """Extract expense data from: "Spent 500 on pizza from Swiggy"
    
Return ONLY JSON:
{
  "amount": 500,
  "category": "Food",
  "vendor": "Swiggy",
  "item": "pizza"
}"""
    
    response = model.generate_content(test_prompt)
    print("\n✅ Gemini Response:")
    print(response.text)
    
except Exception as e:
    print(f"\n❌ Error: {e}")
