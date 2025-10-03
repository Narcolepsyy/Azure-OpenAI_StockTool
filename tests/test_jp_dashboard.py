#!/usr/bin/env python3
"""Test Japanese stock dashboard endpoints."""

import sys
sys.path.insert(0, '/home/khaitran/PycharmProjects/Azure-OpenAI_StockTool')

from app.services import yfinance_service

print("=" * 60)
print("Testing yfinance_service for Japanese stocks")
print("=" * 60)

# Test Toyota (7203.T)
print("\n1. Testing get_stock_info for Toyota (7203.T)...")
toyota_info = yfinance_service.get_stock_info('7203.T')
print(f"Symbol: {toyota_info.get('symbol')}")
print(f"Name: {toyota_info.get('name')}")
print(f"Current Price: ¥{toyota_info.get('current_price')}")
print(f"Change: {toyota_info.get('change')} ({toyota_info.get('percent_change')}%)")
print(f"Currency: {toyota_info.get('currency')}")

# Test news
print("\n2. Testing get_stock_news for Toyota...")
news = yfinance_service.get_stock_news('7203.T', limit=3)
print(f"Found {len(news)} news articles:")
for i, article in enumerate(news, 1):
    print(f"  {i}. {article['title'][:80]}...")
    print(f"     Publisher: {article['publisher']}")

# Test trend
print("\n3. Testing get_price_history for Toyota (1-month)...")
trend = yfinance_service.get_price_history('7203.T', period='1mo')
print(f"Trend: {trend.get('trend')}")
print(f"Period Change: {trend.get('period_change_percent'):.2f}%")
print(f"SMA 20: ¥{trend.get('sma_20'):.2f}")
if trend.get('sma_50'):
    print(f"SMA 50: ¥{trend.get('sma_50'):.2f}")

# Test Sony
print("\n4. Testing Sony (6758.T)...")
sony_info = yfinance_service.get_stock_info('6758.T')
print(f"Symbol: {sony_info.get('symbol')}")
print(f"Name: {sony_info.get('name')}")
print(f"Current Price: ¥{sony_info.get('current_price')}")

print("\n" + "=" * 60)
print("✅ All tests completed!")
print("=" * 60)
