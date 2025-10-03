# AWS Lambda Function: Stock Data Updater

## Overview
This Lambda function automatically updates stock data in DynamoDB on a scheduled basis (e.g., daily at market close).

## Trigger
**EventBridge (CloudWatch Events)** - Scheduled cron expression:
```
# Run daily at 4:30 PM EST (market close + 30 minutes)
cron(30 16 ? * MON-FRI *)
```

## Functionality
1. Fetches latest stock quotes from yfinance API
2. Stores data in DynamoDB with 24-hour TTL
3. Sends SNS notification with update summary
4. Handles errors gracefully with retry logic

## Environment Variables
- `DYNAMODB_TABLE_CACHE`: DynamoDB table name (default: `stocktool-stock-cache`)
- `SNS_TOPIC_ARN`: SNS topic for notifications
- `AWS_ENDPOINT_URL`: LocalStack endpoint (for local testing)

## Local Testing
```bash
cd lambda_functions/stock_updater
python handler.py
```

## Deployment to LocalStack
```bash
# Package Lambda function
cd lambda_functions/stock_updater
pip install -r requirements.txt -t .
zip -r function.zip .

# Create Lambda function in LocalStack
awslocal lambda create-function \
  --function-name stock-data-updater \
  --runtime python3.11 \
  --role arn:aws:iam::000000000000:role/lambda-execution-role \
  --handler handler.lambda_handler \
  --zip-file fileb://function.zip \
  --timeout 300 \
  --memory-size 512

# Create EventBridge rule
awslocal events put-rule \
  --name stock-updater-schedule \
  --schedule-expression 'cron(30 16 ? * MON-FRI *)'

# Add Lambda as target
awslocal events put-targets \
  --rule stock-updater-schedule \
  --targets "Id"="1","Arn"="arn:aws:lambda:us-east-1:000000000000:function:stock-data-updater"

# Test invoke
awslocal lambda invoke \
  --function-name stock-data-updater \
  --payload '{"symbols": ["AAPL", "GOOGL"]}' \
  response.json

cat response.json
```

## Monitoring
View CloudWatch logs:
```bash
awslocal logs tail /aws/lambda/stock-data-updater --follow
```

## Cost Optimization
- **Free Tier**: 1M requests/month + 400,000 GB-seconds
- This function: ~30 invocations/month (daily weekdays)
- Memory: 512 MB, Duration: ~30-60s
- **Estimated Cost**: FREE (well within free tier)
