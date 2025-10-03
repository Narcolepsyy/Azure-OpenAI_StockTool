#!/bin/bash

# AWS LocalStack Quick Start Script
# This script initializes and tests the AWS integration

set -e

echo "🚀 AI Stocks Assistant - AWS LocalStack Setup"
echo "=============================================="
echo ""

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check for Docker Compose (both standalone and plugin versions)
DOCKER_COMPOSE_CMD=""
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
    echo "✅ Docker and Docker Compose (standalone) are installed"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
    echo "✅ Docker and Docker Compose (plugin) are installed"
else
    echo "❌ Docker Compose is not installed. Please install Docker Compose."
    echo "   Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

echo ""

# Install awslocal if not present
if ! command -v awslocal &> /dev/null; then
    echo "📦 Installing awscli-local..."
    
    # Try different installation methods
    if command -v pipx &> /dev/null; then
        # Use pipx if available (recommended for newer systems)
        pipx install awscli-local 2>/dev/null || echo "⚠️  pipx install failed, trying pip with user flag..."
    fi
    
    # Fall back to pip with --user flag if pipx didn't work or isn't available
    if ! command -v awslocal &> /dev/null; then
        pip install --user awscli-local 2>/dev/null || \
        pip3 install --user awscli-local 2>/dev/null || \
        echo "⚠️  Could not install awscli-local automatically."
    fi
    
    # Check if installation succeeded
    if ! command -v awslocal &> /dev/null; then
        echo "⚠️  awscli-local not installed. Some verification commands will be skipped."
        echo "   To install manually: pip install --user awscli-local"
        echo "   Or: pipx install awscli-local"
        AWSLOCAL_AVAILABLE=false
    else
        AWSLOCAL_AVAILABLE=true
    fi
else
    AWSLOCAL_AVAILABLE=true
fi

# Start LocalStack
echo "🐳 Starting LocalStack..."
$DOCKER_COMPOSE_CMD up -d localstack

# Wait for LocalStack to be ready
echo "⏳ Waiting for LocalStack to initialize (this may take 30-60 seconds)..."
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if curl -s http://localhost:4566/_localstack/health | grep -q "\"s3\": \"running\""; then
        echo "✅ LocalStack is ready!"
        break
    fi
    attempt=$((attempt + 1))
    sleep 2
    echo "   Attempt $attempt/$max_attempts..."
done

if [ $attempt -eq $max_attempts ]; then
    echo "❌ LocalStack failed to start. Check logs with: $DOCKER_COMPOSE_CMD logs localstack"
    exit 1
fi

echo ""
echo "🔧 Verifying AWS resources..."

if [ "$AWSLOCAL_AVAILABLE" = false ]; then
    echo "⚠️  Skipping AWS resource verification (awslocal not available)"
    echo "   Resources are still created by LocalStack init scripts"
    echo ""
    echo "📊 LocalStack Dashboard: http://localhost:4566/_localstack/health"
    echo ""
    echo "✨ Setup complete! You can now start the application:"
    echo "   python main.py"
    echo ""
    exit 0
fi

# Verify S3
echo -n "  S3 Bucket: "
if awslocal s3 ls s3://stocktool-knowledge &> /dev/null; then
    echo "✅ stocktool-knowledge"
else
    echo "❌ Not found"
fi

# Verify DynamoDB
echo -n "  DynamoDB Tables: "
TABLES=$(awslocal dynamodb list-tables --output text --query 'TableNames' 2>/dev/null || echo "")
if echo "$TABLES" | grep -q "stocktool-conversations"; then
    echo "✅ stocktool-conversations"
else
    echo "❌ Not found"
fi

if echo "$TABLES" | grep -q "stocktool-stock-cache"; then
    echo "    ✅ stocktool-stock-cache"
else
    echo "    ❌ Not found"
fi

# Verify SQS
echo -n "  SQS Queue: "
if awslocal sqs list-queues | grep -q "stocktool-analysis-queue"; then
    echo "✅ stocktool-analysis-queue"
else
    echo "❌ Not found"
fi

# Verify SNS
echo -n "  SNS Topic: "
if awslocal sns list-topics | grep -q "stocktool-notifications"; then
    echo "✅ stocktool-notifications"
else
    echo "❌ Not found"
fi

echo ""
echo "🧪 Running integration tests..."

# Test S3
echo "  Testing S3 upload..."
echo "Test document content" > /tmp/test-doc.txt
awslocal s3 cp /tmp/test-doc.txt s3://stocktool-knowledge/test/test-doc.txt &> /dev/null
if awslocal s3 ls s3://stocktool-knowledge/test/test-doc.txt &> /dev/null; then
    echo "    ✅ Upload successful"
    awslocal s3 rm s3://stocktool-knowledge/test/test-doc.txt &> /dev/null
else
    echo "    ❌ Upload failed"
fi

# Test DynamoDB
echo "  Testing DynamoDB write..."
awslocal dynamodb put-item \
    --table-name stocktool-conversations \
    --item '{
        "conversation_id": {"S": "test-123"},
        "timestamp": {"N": "1696262400000"},
        "messages": {"S": "[{\"role\": \"user\", \"content\": \"test\"}]"},
        "ttl": {"N": "'$(date -d "+24 hours" +%s)'"}
    }' &> /dev/null

if awslocal dynamodb get-item \
    --table-name stocktool-conversations \
    --key '{"conversation_id": {"S": "test-123"}, "timestamp": {"N": "1696262400000"}}' \
    | grep -q "test-123"; then
    echo "    ✅ Write successful"
else
    echo "    ❌ Write failed"
fi

# Test SQS
echo "  Testing SQS message..."
QUEUE_URL=$(awslocal sqs list-queues --output text --query "QueueUrls[?contains(@, 'stocktool-analysis-queue')]" | head -1)
MESSAGE_ID=$(awslocal sqs send-message \
    --queue-url "$QUEUE_URL" \
    --message-body '{"test": "message"}' \
    --output text --query 'MessageId')

if [ ! -z "$MESSAGE_ID" ]; then
    echo "    ✅ Message sent: $MESSAGE_ID"
else
    echo "    ❌ Message send failed"
fi

echo ""
echo "📊 LocalStack Dashboard: http://localhost:4566/_localstack/health"
echo ""
echo "🎯 Quick Commands:"
echo "  List S3 files:      awslocal s3 ls s3://stocktool-knowledge/"
echo "  Query DynamoDB:     awslocal dynamodb scan --table-name stocktool-conversations"
echo "  Check SQS messages: awslocal sqs receive-message --queue-url $QUEUE_URL"
echo "  View logs:          $DOCKER_COMPOSE_CMD logs -f localstack"
echo "  Stop LocalStack:    $DOCKER_COMPOSE_CMD down"
echo ""
echo "✨ Setup complete! You can now start the application:"
echo "   python main.py"
echo ""
