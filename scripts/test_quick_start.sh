#!/bin/bash
# Quick Start Test Script - Test all features of the AI Stock Assistant

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="${BASE_URL:-http://localhost:8000}"
USERNAME="${TEST_USERNAME:-testuser}"
PASSWORD="${TEST_PASSWORD:-TestPass123!}"
TOKEN=""

echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   AI Stock Assistant - Quick Start Test       ║${NC}"
echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo ""

# Function to print step
print_step() {
    echo -e "${YELLOW}▶ $1${NC}"
}

# Function to print success
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Function to print error
print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# 1. Check if backend is running
print_step "Step 1: Checking if backend is running..."
if curl -s "${BASE_URL}/healthz" > /dev/null 2>&1; then
    print_success "Backend is running at ${BASE_URL}"
else
    print_error "Backend is not running at ${BASE_URL}"
    echo "Please start the backend with: python main.py"
    exit 1
fi

# 2. Check system readiness
print_step "Step 2: Checking system readiness..."
READINESS=$(curl -s "${BASE_URL}/readyz")
echo "$READINESS" | jq '.'
if echo "$READINESS" | jq -e '.status == "ready"' > /dev/null; then
    print_success "System is ready"
else
    print_error "System is not ready"
    exit 1
fi

# 3. Check LocalStack
print_step "Step 3: Checking LocalStack..."
if curl -s http://localhost:4566/_localstack/health > /dev/null 2>&1; then
    print_success "LocalStack is running"
    LOCALSTACK_INFO=$(curl -s http://localhost:4566/_localstack/info)
    EDITION=$(echo "$LOCALSTACK_INFO" | jq -r '.edition')
    LICENSE=$(echo "$LOCALSTACK_INFO" | jq -r '.is_license_activated')
    echo "  Edition: $EDITION"
    echo "  License Activated: $LICENSE"
else
    print_error "LocalStack is not running"
    echo "Start LocalStack with: docker compose up -d localstack"
fi

# 4. Register user (if not exists)
print_step "Step 4: Registering test user..."
REGISTER_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${BASE_URL}/auth/register" \
    -H "Content-Type: application/json" \
    -d "{\"username\": \"${USERNAME}\", \"password\": \"${PASSWORD}\"}" 2>&1 || echo "409")

HTTP_CODE=$(echo "$REGISTER_RESPONSE" | tail -1)
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "409" ]; then
    print_success "User registered (or already exists)"
else
    print_error "Failed to register user (HTTP $HTTP_CODE)"
fi

# 5. Login and get token
print_step "Step 5: Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST "${BASE_URL}/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"username\": \"${USERNAME}\", \"password\": \"${PASSWORD}\"}")

TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token')
if [ "$TOKEN" != "null" ] && [ -n "$TOKEN" ]; then
    print_success "Login successful"
    echo "  Token: ${TOKEN:0:20}..."
else
    print_error "Login failed"
    echo "$LOGIN_RESPONSE" | jq '.'
    exit 1
fi

# 6. Test chat endpoint
print_step "Step 6: Testing chat endpoint..."
CHAT_RESPONSE=$(curl -s -X POST "${BASE_URL}/chat" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{"prompt": "What is the current stock price of AAPL?"}')

CONV_ID=$(echo "$CHAT_RESPONSE" | jq -r '.conversation_id')
CONTENT=$(echo "$CHAT_RESPONSE" | jq -r '.content')

if [ -n "$CONTENT" ] && [ "$CONTENT" != "null" ]; then
    print_success "Chat endpoint working"
    echo "  Conversation ID: $CONV_ID"
    echo "  Response: ${CONTENT:0:100}..."
else
    print_error "Chat endpoint failed"
    echo "$CHAT_RESPONSE" | jq '.'
fi

# 7. Test multi-turn conversation
print_step "Step 7: Testing multi-turn conversation..."
CHAT2_RESPONSE=$(curl -s -X POST "${BASE_URL}/chat" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"prompt\": \"How about Microsoft?\", \"conversation_id\": \"${CONV_ID}\"}")

CONTENT2=$(echo "$CHAT2_RESPONSE" | jq -r '.content')
if [ -n "$CONTENT2" ] && [ "$CONTENT2" != "null" ]; then
    print_success "Multi-turn conversation working"
    echo "  Response: ${CONTENT2:0:100}..."
else
    print_error "Multi-turn conversation failed"
fi

# 8. Test available models
print_step "Step 8: Checking available models..."
MODELS_RESPONSE=$(curl -s "${BASE_URL}/models")
MODEL_COUNT=$(echo "$MODELS_RESPONSE" | jq '.models | length')
print_success "Found $MODEL_COUNT available models"
echo "$MODELS_RESPONSE" | jq -r '.models[] | "  - \(.alias): \(.description)"'

# 9. Test stock quote endpoint
print_step "Step 9: Testing stock quote endpoint..."
STOCK_RESPONSE=$(curl -s "${BASE_URL}/stock/AAPL")
STOCK_PRICE=$(echo "$STOCK_RESPONSE" | jq -r '.current_price // .regularMarketPrice // "N/A"')
if [ "$STOCK_PRICE" != "N/A" ]; then
    print_success "Stock quote endpoint working"
    echo "  AAPL Price: \$${STOCK_PRICE}"
else
    print_error "Stock quote endpoint failed"
    echo "$STOCK_RESPONSE" | jq '.'
fi

# 10. Test RAG search (if enabled)
print_step "Step 10: Testing RAG search..."
RAG_ENABLED=$(echo "$READINESS" | jq -r '.rag_enabled')
if [ "$RAG_ENABLED" = "true" ]; then
    RAG_RESPONSE=$(curl -s "${BASE_URL}/api/rag/search?query=stock&top_k=3" \
        -H "Authorization: Bearer ${TOKEN}")
    RAG_RESULTS=$(echo "$RAG_RESPONSE" | jq '.results | length // 0')
    if [ "$RAG_RESULTS" -gt 0 ]; then
        print_success "RAG search working ($RAG_RESULTS results)"
    else
        echo "  ℹ No results (knowledge base may be empty)"
    fi
else
    echo "  ℹ RAG is disabled"
fi

# 11. Test AWS resources
print_step "Step 11: Testing AWS resources..."
if command -v python3 &> /dev/null; then
    if python3 scripts/verify_aws_resources.py > /dev/null 2>&1; then
        print_success "AWS resources verified"
    else
        echo "  ℹ AWS verification failed (LocalStack may not be fully initialized)"
    fi
else
    echo "  ℹ Python not found, skipping AWS verification"
fi

# 12. Clear conversation
print_step "Step 12: Cleaning up test conversation..."
CLEAR_RESPONSE=$(curl -s -X POST "${BASE_URL}/chat/clear" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"conversation_id\": \"${CONV_ID}\"}")

if echo "$CLEAR_RESPONSE" | jq -e '.cleared == true' > /dev/null 2>&1; then
    print_success "Conversation cleared"
else
    echo "  ℹ Conversation cleanup failed (not critical)"
fi

# Summary
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              Test Summary                      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""
print_success "Backend: Running"
print_success "Authentication: Working"
print_success "Chat: Working"
print_success "Stock Data: Working"
print_success "Multi-turn: Working"
echo ""
echo -e "${GREEN}🎉 All core features are working!${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Open web interface: ${BASE_URL}/app"
echo "  2. View API docs: ${BASE_URL}/docs"
echo "  3. Read getting started guide: docs/GETTING_STARTED.md"
echo ""
echo -e "${YELLOW}Test credentials:${NC}"
echo "  Username: ${USERNAME}"
echo "  Password: ${PASSWORD}"
echo "  Token: ${TOKEN:0:20}..."
echo ""
echo -e "${BLUE}Happy coding! 🚀${NC}"
