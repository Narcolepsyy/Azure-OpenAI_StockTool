#!/bin/bash
# Deploy Lambda Functions to LocalStack

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Deploy Lambda Functions to LocalStack     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""

# Configuration
LAMBDA_RUNTIME="python3.11"
LAMBDA_ROLE="arn:aws:iam::000000000000:role/lambda-role"
AWS_REGION="${AWS_REGION:-us-east-1}"
ENDPOINT_URL="http://localhost:4566"

# Set LocalStack credentials
export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-test}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-test}"
export AWS_DEFAULT_REGION="${AWS_REGION}"

# Check if LocalStack is running
echo -e "${YELLOW}▶ Checking LocalStack...${NC}"
if ! curl -s "${ENDPOINT_URL}/_localstack/health" > /dev/null 2>&1; then
    echo -e "${RED}✗ LocalStack is not running${NC}"
    echo "Start LocalStack with: docker compose up -d localstack"
    exit 1
fi
echo -e "${GREEN}✓ LocalStack is running${NC}"
echo ""

# Function to deploy Lambda
deploy_lambda() {
    local FUNCTION_NAME=$1
    local HANDLER=$2
    local CODE_DIR=$3
    local DESCRIPTION=$4
    local MEMORY_SIZE=${5:-128}
    local TIMEOUT=${6:-30}
    
    echo -e "${YELLOW}▶ Deploying Lambda: ${FUNCTION_NAME}${NC}"
    
    # Create deployment package
    TEMP_DIR=$(mktemp -d)
    cp -r "${CODE_DIR}"/* "${TEMP_DIR}/"
    
    # Install dependencies if requirements.txt exists
    if [ -f "${CODE_DIR}/requirements_simple.txt" ]; then
        echo "  Installing minimal dependencies..."
        # For simplified version, boto3 is already in Lambda runtime
        # No additional dependencies needed
    elif [ -f "${CODE_DIR}/requirements.txt" ]; then
        echo "  Installing dependencies..."
        pip install -q -r "${CODE_DIR}/requirements.txt" -t "${TEMP_DIR}/" --upgrade \
            --no-cache-dir \
            --platform manylinux2014_x86_64 \
            --only-binary=:all: 2>/dev/null || \
        pip install -q -r "${CODE_DIR}/requirements.txt" -t "${TEMP_DIR}/" --upgrade --no-cache-dir
        
        # Remove unnecessary files to reduce size
        find "${TEMP_DIR}" -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
        find "${TEMP_DIR}" -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
        find "${TEMP_DIR}" -name "*.pyc" -delete 2>/dev/null || true
        find "${TEMP_DIR}" -name "*.pyo" -delete 2>/dev/null || true
        find "${TEMP_DIR}" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    fi
    
    # Create ZIP package
    PACKAGE_FILE="${TEMP_DIR}/${FUNCTION_NAME}.zip"
    cd "${TEMP_DIR}"
    zip -q -r "${PACKAGE_FILE}" .
    cd - > /dev/null
    
    # Delete existing function if it exists
    aws lambda delete-function \
        --function-name "${FUNCTION_NAME}" \
        --endpoint-url "${ENDPOINT_URL}" \
        --region "${AWS_REGION}" \
        2>/dev/null || true
    
    # Create Lambda function
    aws lambda create-function \
        --function-name "${FUNCTION_NAME}" \
        --runtime "${LAMBDA_RUNTIME}" \
        --role "${LAMBDA_ROLE}" \
        --handler "${HANDLER}" \
        --description "${DESCRIPTION}" \
        --timeout "${TIMEOUT}" \
        --memory-size "${MEMORY_SIZE}" \
        --zip-file "fileb://${PACKAGE_FILE}" \
        --endpoint-url "${ENDPOINT_URL}" \
        --region "${AWS_REGION}" \
        --environment "Variables={
            AWS_ENDPOINT_URL=${ENDPOINT_URL},
            DYNAMODB_TABLE_CACHE=stocktool-stock-cache,
            SNS_TOPIC_ARN=arn:aws:sns:us-east-1:000000000000:stocktool-notifications
        }" \
        > /dev/null
    
    # Cleanup
    rm -rf "${TEMP_DIR}"
    
    echo -e "${GREEN}✓ Lambda deployed: ${FUNCTION_NAME}${NC}"
}

# Deploy stock_updater Lambda
deploy_lambda \
    "stocktool-stock-updater" \
    "handler_simple.lambda_handler" \
    "lambda_functions/stock_updater" \
    "Daily stock data updater (simplified)" \
    128 \
    30

echo ""
echo -e "${YELLOW}▶ Creating EventBridge schedule...${NC}"

# Create EventBridge rule for daily execution
aws events put-rule \
    --name "stocktool-daily-update" \
    --description "Trigger stock data update daily at market close (4:30 PM ET)" \
    --schedule-expression "cron(30 20 * * ? *)" \
    --endpoint-url "${ENDPOINT_URL}" \
    --region "${AWS_REGION}" \
    > /dev/null

# Add Lambda permission for EventBridge
aws lambda add-permission \
    --function-name "stocktool-stock-updater" \
    --statement-id "AllowEventBridgeInvoke" \
    --action "lambda:InvokeFunction" \
    --principal "events.amazonaws.com" \
    --source-arn "arn:aws:events:us-east-1:000000000000:rule/stocktool-daily-update" \
    --endpoint-url "${ENDPOINT_URL}" \
    --region "${AWS_REGION}" \
    > /dev/null 2>&1 || true

# Set EventBridge target
aws events put-targets \
    --rule "stocktool-daily-update" \
    --targets "Id=1,Arn=arn:aws:lambda:us-east-1:000000000000:function:stocktool-stock-updater" \
    --endpoint-url "${ENDPOINT_URL}" \
    --region "${AWS_REGION}" \
    > /dev/null

echo -e "${GREEN}✓ EventBridge schedule created${NC}"
echo ""

# Test Lambda invocation
echo -e "${YELLOW}▶ Testing Lambda invocation...${NC}"

TEST_EVENT='{
  "symbols": ["AAPL", "GOOGL", "MSFT"]
}'

INVOKE_RESULT=$(aws lambda invoke \
    --function-name "stocktool-stock-updater" \
    --payload "${TEST_EVENT}" \
    --endpoint-url "${ENDPOINT_URL}" \
    --region "${AWS_REGION}" \
    /tmp/lambda-output.json \
    --query 'StatusCode' \
    --output text)

if [ "$INVOKE_RESULT" = "200" ]; then
    echo -e "${GREEN}✓ Lambda invocation successful${NC}"
    echo ""
    echo "Response:"
    cat /tmp/lambda-output.json | jq '.'
    rm /tmp/lambda-output.json
else
    echo -e "${RED}✗ Lambda invocation failed${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║            Deployment Summary                  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}✓ Lambda Function: stocktool-stock-updater${NC}"
echo -e "${GREEN}✓ EventBridge Rule: stocktool-daily-update${NC}"
echo -e "${GREEN}✓ Schedule: Daily at 4:30 PM ET (market close)${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. View function: aws lambda get-function --function-name stocktool-stock-updater --endpoint-url ${ENDPOINT_URL}"
echo "  2. Test manually: aws lambda invoke --function-name stocktool-stock-updater --endpoint-url ${ENDPOINT_URL} output.json"
echo "  3. View logs: aws logs tail /aws/lambda/stocktool-stock-updater --endpoint-url ${ENDPOINT_URL} --follow"
echo "  4. Check CloudWatch dashboard: ./scripts/create_cloudwatch_dashboard.sh"
echo ""
echo -e "${GREEN}🎉 Lambda deployment complete!${NC}"
