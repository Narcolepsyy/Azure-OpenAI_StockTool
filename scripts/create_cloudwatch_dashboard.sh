#!/bin/bash
# Create CloudWatch Dashboard for Stock Tool Monitoring

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Create CloudWatch Dashboard               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
ENDPOINT_URL="http://localhost:4566"
DASHBOARD_NAME="StockTool-Monitoring"

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

# Create dashboard JSON
echo -e "${YELLOW}▶ Creating dashboard configuration...${NC}"

DASHBOARD_BODY=$(cat <<'EOF'
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          [ "StockTool", "APILatency", { "stat": "Average" } ],
          [ "...", { "stat": "p99" } ]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "API Latency",
        "yAxis": {
          "left": {
            "label": "Milliseconds"
          }
        }
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          [ "StockTool", "ToolExecutionTime", { "stat": "Average" } ],
          [ "...", { "stat": "p95" } ]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "Tool Execution Time",
        "yAxis": {
          "left": {
            "label": "Milliseconds"
          }
        }
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          [ "StockTool", "CacheHitRate", { "stat": "Average" } ]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "Cache Hit Rate",
        "yAxis": {
          "left": {
            "label": "Percentage",
            "min": 0,
            "max": 100
          }
        }
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          [ "StockTool", "ModelTokenUsage", { "stat": "Sum" } ]
        ],
        "period": 300,
        "stat": "Sum",
        "region": "us-east-1",
        "title": "Model Token Usage",
        "yAxis": {
          "left": {
            "label": "Tokens"
          }
        }
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          [ "StockTool", "ModelLatency", { "stat": "Average" } ],
          [ "...", { "stat": "p99" } ]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "Model Latency",
        "yAxis": {
          "left": {
            "label": "Milliseconds"
          }
        }
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          [ "AWS/Lambda", "Invocations", { "stat": "Sum" } ],
          [ ".", "Errors", { "stat": "Sum" } ],
          [ ".", "Throttles", { "stat": "Sum" } ]
        ],
        "period": 300,
        "stat": "Sum",
        "region": "us-east-1",
        "title": "Lambda Metrics"
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          [ "AWS/Lambda", "Duration", { "stat": "Average" } ],
          [ "...", { "stat": "Maximum" } ]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "Lambda Duration"
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          [ "AWS/SQS", "NumberOfMessagesSent", { "stat": "Sum" } ],
          [ ".", "NumberOfMessagesReceived", { "stat": "Sum" } ],
          [ ".", "ApproximateNumberOfMessagesVisible", { "stat": "Average" } ]
        ],
        "period": 300,
        "stat": "Sum",
        "region": "us-east-1",
        "title": "SQS Queue Metrics"
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          [ "AWS/DynamoDB", "ConsumedReadCapacityUnits", { "stat": "Sum" } ],
          [ ".", "ConsumedWriteCapacityUnits", { "stat": "Sum" } ]
        ],
        "period": 300,
        "stat": "Sum",
        "region": "us-east-1",
        "title": "DynamoDB Capacity"
      }
    },
    {
      "type": "log",
      "properties": {
        "query": "SOURCE '/aws/lambda/stocktool-stock-updater'\n| fields @timestamp, @message\n| filter @message like /ERROR/ or @message like /WARN/\n| sort @timestamp desc\n| limit 20",
        "region": "us-east-1",
        "title": "Recent Errors/Warnings"
      }
    }
  ]
}
EOF
)

# Create the dashboard
aws cloudwatch put-dashboard \
    --dashboard-name "${DASHBOARD_NAME}" \
    --dashboard-body "${DASHBOARD_BODY}" \
    --endpoint-url "${ENDPOINT_URL}" \
    --region "${AWS_REGION}" \
    > /dev/null

echo -e "${GREEN}✓ Dashboard created: ${DASHBOARD_NAME}${NC}"
echo ""

# Create alarms
echo -e "${YELLOW}▶ Creating CloudWatch alarms...${NC}"

# High API Latency Alarm
aws cloudwatch put-metric-alarm \
    --alarm-name "StockTool-HighAPILatency" \
    --alarm-description "Alert when API latency exceeds 2 seconds" \
    --metric-name "APILatency" \
    --namespace "StockTool" \
    --statistic "Average" \
    --period 300 \
    --threshold 2000 \
    --comparison-operator "GreaterThanThreshold" \
    --evaluation-periods 2 \
    --endpoint-url "${ENDPOINT_URL}" \
    --region "${AWS_REGION}" \
    > /dev/null 2>&1 || true

echo -e "${GREEN}✓ Alarm created: StockTool-HighAPILatency${NC}"

# Low Cache Hit Rate Alarm
aws cloudwatch put-metric-alarm \
    --alarm-name "StockTool-LowCacheHitRate" \
    --alarm-description "Alert when cache hit rate drops below 50%" \
    --metric-name "CacheHitRate" \
    --namespace "StockTool" \
    --statistic "Average" \
    --period 300 \
    --threshold 50 \
    --comparison-operator "LessThanThreshold" \
    --evaluation-periods 2 \
    --endpoint-url "${ENDPOINT_URL}" \
    --region "${AWS_REGION}" \
    > /dev/null 2>&1 || true

echo -e "${GREEN}✓ Alarm created: StockTool-LowCacheHitRate${NC}"

# Lambda Errors Alarm
aws cloudwatch put-metric-alarm \
    --alarm-name "StockTool-LambdaErrors" \
    --alarm-description "Alert when Lambda functions have errors" \
    --metric-name "Errors" \
    --namespace "AWS/Lambda" \
    --statistic "Sum" \
    --period 300 \
    --threshold 5 \
    --comparison-operator "GreaterThanThreshold" \
    --evaluation-periods 1 \
    --endpoint-url "${ENDPOINT_URL}" \
    --region "${AWS_REGION}" \
    > /dev/null 2>&1 || true

echo -e "${GREEN}✓ Alarm created: StockTool-LambdaErrors${NC}"
echo ""

# List all dashboards
echo -e "${YELLOW}▶ Available dashboards:${NC}"
aws cloudwatch list-dashboards \
    --endpoint-url "${ENDPOINT_URL}" \
    --region "${AWS_REGION}" \
    --query 'DashboardEntries[].DashboardName' \
    --output table

echo ""

# List all alarms
echo -e "${YELLOW}▶ Active alarms:${NC}"
aws cloudwatch describe-alarms \
    --endpoint-url "${ENDPOINT_URL}" \
    --region "${AWS_REGION}" \
    --query 'MetricAlarms[].{Name:AlarmName,State:StateValue,Metric:MetricName}' \
    --output table

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║            Dashboard Summary                   ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}✓ Dashboard Name: ${DASHBOARD_NAME}${NC}"
echo -e "${GREEN}✓ Widgets: 10 metric widgets${NC}"
echo -e "${GREEN}✓ Alarms: 3 configured${NC}"
echo ""
echo -e "${YELLOW}Dashboard includes:${NC}"
echo "  • API Latency (average & p99)"
echo "  • Tool Execution Time"
echo "  • Cache Hit Rate"
echo "  • Model Token Usage"
echo "  • Model Latency"
echo "  • Lambda Metrics (invocations, errors, throttles)"
echo "  • Lambda Duration"
echo "  • SQS Queue Metrics"
echo "  • DynamoDB Capacity Usage"
echo "  • Recent Errors/Warnings Log"
echo ""
echo -e "${YELLOW}View dashboard:${NC}"
echo "  aws cloudwatch get-dashboard --dashboard-name ${DASHBOARD_NAME} --endpoint-url ${ENDPOINT_URL}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Run application to generate metrics: python main.py"
echo "  2. Make API calls to populate dashboard data"
echo "  3. View real-time metrics in CloudWatch"
echo "  4. Set up SNS for alarm notifications"
echo ""
echo -e "${GREEN}🎉 CloudWatch dashboard created!${NC}"
