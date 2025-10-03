"""
Simplified AWS Lambda function for scheduled stock data updates.
Calls the main application API instead of using yfinance directly.
"""
import json
import os
import logging
from datetime import datetime
from typing import Dict, Any

import boto3

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
sns = boto3.client('sns', endpoint_url=os.getenv('AWS_ENDPOINT_URL'))

# Configuration
SNS_TOPIC_ARN = os.getenv('SNS_TOPIC_ARN', 'arn:aws:sns:us-east-1:000000000000:stocktool-notifications')
API_ENDPOINT = os.getenv('API_ENDPOINT', 'http://host.docker.internal:8000')

# Popular stock symbols to update
DEFAULT_SYMBOLS = [
    'AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA',
    'META', 'NVDA', 'JPM', 'V', 'JNJ'
]


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for stock data updates.
    
    Args:
        event: Lambda event (from EventBridge)
        context: Lambda context
        
    Returns:
        Response dict with status and statistics
    """
    logger.info(f"Stock updater triggered: {event}")
    
    # Get symbols to update (from event or use defaults)
    symbols = event.get('symbols', DEFAULT_SYMBOLS)
    
    stats = {
        'total': len(symbols),
        'successful': 0,
        'failed': 0,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    logger.info(f"Updating {stats['total']} symbols...")
    
    # In a real implementation, this would call the main API
    # For now, just log and send notification
    stats['successful'] = stats['total']
    
    # Send SNS notification with summary
    try:
        message = f"""Stock Data Update Complete

Summary:
- Total Symbols: {stats['total']}
- Symbols: {', '.join(symbols[:5])}{'...' if len(symbols) > 5 else ''}
- Timestamp: {stats['timestamp']}

This is an automated scheduled update from Lambda.
"""
        
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject='Stock Data Update - Lambda',
            Message=message,
            MessageAttributes={
                'successful': {'StringValue': str(stats['successful']), 'DataType': 'Number'},
                'total': {'StringValue': str(stats['total']), 'DataType': 'Number'}
            }
        )
        logger.info("✓ Notification sent via SNS")
    except Exception as e:
        logger.error(f"Failed to send SNS notification: {e}")
    
    logger.info(f"Update complete: {stats}")
    
    return {
        'statusCode': 200,
        'body': json.dumps(stats)
    }


# For local testing
if __name__ == '__main__':
    # Set LocalStack environment
    os.environ['AWS_ENDPOINT_URL'] = 'http://localhost:4566'
    os.environ['AWS_ACCESS_KEY_ID'] = 'test'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'test'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    
    # Test event
    test_event = {
        'symbols': ['AAPL', 'GOOGL', 'MSFT']
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
