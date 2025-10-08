#!/bin/bash
# Quick test of ML tool selection via curl

echo "========================================"
echo "Testing ML Tool Selection"
echo "========================================"
echo ""

# First, login to get token
echo "1. Logging in..."
TOKEN=$(curl -s -X POST "http://127.0.0.1:8000/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test_ml_user&password=TestML123!" | jq -r '.access_token')

if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
  echo "❌ Login failed"
  exit 1
fi

echo "✅ Got auth token"
echo ""

# Test query
echo "2. Sending test query: 'What is the price of AAPL?'"
echo ""

RESPONSE=$(curl -s -X POST "http://127.0.0.1:8000/chat" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What is the price of AAPL?",
    "deployment": "gpt-oss-120b",
    "stream": false
  }')

echo "Response:"
echo "$RESPONSE" | jq -r '.answer' | head -n 5
echo ""

echo "========================================"
echo "✅ Test complete!"
echo "========================================"
echo ""
echo "Now check server logs for:"
echo "  - 'Tool selection: method=ml'"
echo "  - 'ML predicted X tools'"
echo "  - Confidence scores"
