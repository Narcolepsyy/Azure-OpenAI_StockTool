import os
import requests
from dotenv import load_dotenv

load_dotenv()

BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")

if not BRAVE_API_KEY:
    raise ValueError("BRAVE_API_KEY not found in environment variables")

response = requests.get(
  "https://api.search.brave.com/res/v1/web/search",
  headers={
    "Accept": "application/json",
    "Accept-Encoding": "gzip",
    "x-subscription-token": BRAVE_API_KEY
  },
  params={
    "q": "SBI住信ネット銀行 顧客基盤 成長戦略 2025",
    "country": "JP",
    "search_lang": "jp",
    "ui_lang": "ja-JP"
  },
).json()