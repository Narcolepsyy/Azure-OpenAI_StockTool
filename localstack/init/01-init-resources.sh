#!/bin/bash

# LocalStack initialization script
# This runs after LocalStack is ready

set -e

echo "🚀 Initializing LocalStack AWS resources for Stock Analysis Tool..."

# Configuration
REGION="us-east-1"
BUCKET_NAME="stocktool-knowledge"
DYNAMODB_TABLE="stocktool-conversations"
SQS_QUEUE="stocktool-analysis-queue"
SNS_TOPIC="stocktool-notifications"
SECRET_NAME="stocktool/api-keys"

# S3: Create bucket for knowledge base storage
echo "📦 Creating S3 bucket: $BUCKET_NAME"
awslocal s3 mb s3://$BUCKET_NAME --region $REGION || true
awslocal s3api put-bucket-versioning \
    --bucket $BUCKET_NAME \
    --versioning-configuration Status=Enabled

# Enable S3 event notifications
awslocal s3api put-bucket-notification-configuration \
    --bucket $BUCKET_NAME \
    --notification-configuration '{
        "TopicConfigurations": [{
            "TopicArn": "arn:aws:sns:us-east-1:000000000000:stocktool-notifications",
            "Events": ["s3:ObjectCreated:*"]
        }]
    }' || echo "⚠️  SNS topic not ready yet, skipping bucket notifications"

# DynamoDB: Create conversations table
echo "🗄️  Creating DynamoDB table: $DYNAMODB_TABLE"
awslocal dynamodb create-table \
    --table-name $DYNAMODB_TABLE \
    --attribute-definitions \
        AttributeName=conversation_id,AttributeType=S \
        AttributeName=timestamp,AttributeType=N \
    --key-schema \
        AttributeName=conversation_id,KeyType=HASH \
        AttributeName=timestamp,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --region $REGION || echo "Table may already exist"

# Enable TTL for automatic conversation cleanup (24 hours)
awslocal dynamodb update-time-to-live \
    --table-name $DYNAMODB_TABLE \
    --time-to-live-specification "Enabled=true, AttributeName=ttl" \
    --region $REGION || true

# Create stock cache table
echo "🗄️  Creating DynamoDB table: stocktool-stock-cache"
awslocal dynamodb create-table \
    --table-name stocktool-stock-cache \
    --attribute-definitions \
        AttributeName=symbol,AttributeType=S \
        AttributeName=data_type,AttributeType=S \
    --key-schema \
        AttributeName=symbol,KeyType=HASH \
        AttributeName=data_type,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --region $REGION || echo "Table may already exist"

# Enable TTL for stock cache (5 minutes)
awslocal dynamodb update-time-to-live \
    --table-name stocktool-stock-cache \
    --time-to-live-specification "Enabled=true, AttributeName=ttl" \
    --region $REGION || true

# SNS: Create notification topic
echo "📢 Creating SNS topic: $SNS_TOPIC"
SNS_TOPIC_ARN=$(awslocal sns create-topic \
    --name $SNS_TOPIC \
    --region $REGION \
    --output text --query 'TopicArn')
echo "Created SNS topic: $SNS_TOPIC_ARN"

# SQS: Create analysis queue
echo "📨 Creating SQS queue: $SQS_QUEUE"
QUEUE_URL=$(awslocal sqs create-queue \
    --queue-name $SQS_QUEUE \
    --attributes VisibilityTimeout=300,MessageRetentionPeriod=86400 \
    --region $REGION \
    --output text --query 'QueueUrl')
echo "Created SQS queue: $QUEUE_URL"

# Create dead letter queue
DLQ_URL=$(awslocal sqs create-queue \
    --queue-name "${SQS_QUEUE}-dlq" \
    --region $REGION \
    --output text --query 'QueueUrl')
echo "Created DLQ: $DLQ_URL"

# Get queue ARN for subscription
QUEUE_ARN=$(awslocal sqs get-queue-attributes \
    --queue-url $QUEUE_URL \
    --attribute-names QueueArn \
    --region $REGION \
    --output text --query 'Attributes.QueueArn')

# Subscribe SQS to SNS topic
echo "🔗 Subscribing SQS queue to SNS topic"
awslocal sns subscribe \
    --topic-arn $SNS_TOPIC_ARN \
    --protocol sqs \
    --notification-endpoint $QUEUE_ARN \
    --region $REGION || true

# Secrets Manager: Store API keys
echo "🔐 Creating Secrets Manager secret: $SECRET_NAME"
awslocal secretsmanager create-secret \
    --name $SECRET_NAME \
    --description "API keys for Stock Analysis Tool" \
    --secret-string '{
        "openai_api_key": "placeholder",
        "azure_openai_api_key": "placeholder",
        "brave_api_key": "placeholder",
        "finnhub_api_key": "placeholder",
        "alpha_vantage_api_key": "placeholder"
    }' \
    --region $REGION || echo "Secret may already exist"

# CloudWatch: Create log groups
echo "📊 Creating CloudWatch log groups"
awslocal logs create-log-group --log-group-name /aws/lambda/stock-analysis --region $REGION || true
awslocal logs create-log-group --log-group-name /stocktool/api --region $REGION || true
awslocal logs create-log-group --log-group-name /stocktool/tools --region $REGION || true

# Create CloudWatch dashboard
echo "📈 Creating CloudWatch dashboard"
awslocal cloudwatch put-dashboard \
    --dashboard-name stocktool-metrics \
    --dashboard-body '{
        "widgets": [
            {
                "type": "metric",
                "properties": {
                    "metrics": [
                        ["StockTool", "APILatency", {"stat": "Average"}],
                        [".", "ToolExecutionTime", {"stat": "Average"}],
                        [".", "CacheHitRate", {"stat": "Average"}]
                    ],
                    "period": 300,
                    "stat": "Average",
                    "region": "us-east-1",
                    "title": "Performance Metrics"
                }
            }
        ]
    }' \
    --region $REGION || true

# Lambda: Create execution role
echo "⚡ Setting up Lambda execution role"
ROLE_ARN="arn:aws:iam::000000000000:role/lambda-execution-role"

# Note: In LocalStack, we can skip complex IAM setup for local dev
# For production, use proper IAM roles with least privilege

echo "✅ LocalStack initialization complete!"
echo ""
echo "📋 Resource Summary:"
echo "  S3 Bucket: s3://$BUCKET_NAME"
echo "  DynamoDB Tables: $DYNAMODB_TABLE, stocktool-stock-cache"
echo "  SQS Queue: $QUEUE_URL"
echo "  SNS Topic: $SNS_TOPIC_ARN"
echo "  Secret: $SECRET_NAME"
echo ""
echo "🔍 Verify resources:"
echo "  awslocal s3 ls"
echo "  awslocal dynamodb list-tables"
echo "  awslocal sqs list-queues"
echo "  awslocal sns list-topics"
