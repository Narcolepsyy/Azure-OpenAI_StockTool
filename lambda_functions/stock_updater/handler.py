"""
AWS Lambda function for scheduled stock data updates.
Triggered by EventBridge (CloudWatch Events) daily at market close.
"""
import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

import boto3
import yfinance as yf

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
dynamodb = boto3.resource('dynamodb', endpoint_url=os.getenv('AWS_ENDPOINT_URL'))
sns = boto3.client('sns', endpoint_url=os.getenv('AWS_ENDPOINT_URL'))

# Configuration
CACHE_TABLE_NAME = os.getenv('DYNAMODB_TABLE_CACHE', 'stocktool-stock-cache')
SNS_TOPIC_ARN = os.getenv('SNS_TOPIC_ARN', 'arn:aws:sns:us-east-1:000000000000:stocktool-notifications')

# Popular stock symbols to update
DEFAULT_SYMBOLS = [
    'AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA',
    'META', 'NVDA', 'JPM', 'V', 'JNJ',
    '^GSPC', '^DJI', '^IXIC'  # Indices
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
        'errors': []
    }
    
    table = dynamodb.Table(CACHE_TABLE_NAME)
    
    for symbol in symbols:
        try:
            logger.info(f"Updating {symbol}...")
            
            # Fetch stock data
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Get latest quote
            quote_data = {
                'symbol': symbol,
                'price': info.get('currentPrice') or info.get('previousClose'),
                'change': info.get('regularMarketChange'),
                'change_percent': info.get('regularMarketChangePercent'),
                'volume': info.get('volume'),
                'market_cap': info.get('marketCap'),
                'pe_ratio': info.get('trailingPE'),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Store in DynamoDB with TTL
            ttl = int((datetime.utcnow() + timedelta(hours=24)).timestamp())
            
            table.put_item(Item={
                'symbol': symbol,
                'data_type': 'quote',
                'data': json.dumps(quote_data),
                'ttl': ttl,
                'updated_at': quote_data['updated_at']
            })
            
            logger.info(f"✓ Updated {symbol}: ${quote_data['price']}")
            stats['successful'] += 1
            
        except Exception as e:
            error_msg = f"Failed to update {symbol}: {str(e)}"
            logger.error(error_msg)
            stats['failed'] += 1
            stats['errors'].append(error_msg)
    
    # Send SNS notification with summary
    try:
        message = f"""Stock Data Update Complete

Summary:
- Total Symbols: {stats['total']}
- Successful: {stats['successful']}
- Failed: {stats['failed']}

Timestamp: {datetime.utcnow().isoformat()}
"""
        
        if stats['errors']:
            message += f"\nErrors:\n" + "\n".join(stats['errors'][:5])
        
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject='Stock Data Update Complete',
            Message=message,
            MessageAttributes={
                'successful': {'StringValue': str(stats['successful']), 'DataType': 'Number'},
                'failed': {'StringValue': str(stats['failed']), 'DataType': 'Number'}
            }
        )
        logger.info("Notification sent via SNS")
    except Exception as e:
        logger.error(f"Failed to send SNS notification: {e}")
    
    return {
        'statusCode': 200,
        'body': json.dumps(stats)
    }


def update_historical_data(symbol: str, period: str = '1mo') -> bool:
    """
    Update historical price data for a symbol.
    
    Args:
        symbol: Stock symbol
        period: Period to fetch (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
        
    Returns:
        True if successful
    """
    try:
        ticker = yf.Ticker(symbol)
        history = ticker.history(period=period)
        
        if history.empty:
            logger.warning(f"No historical data for {symbol}")
            return False
        
        # Store in DynamoDB
        table = dynamodb.Table(CACHE_TABLE_NAME)
        ttl = int((datetime.utcnow() + timedelta(days=7)).timestamp())
        
        historical_data = {
            'dates': history.index.strftime('%Y-%m-%d').tolist(),
            'open': history['Open'].tolist(),
            'high': history['High'].tolist(),
            'low': history['Low'].tolist(),
            'close': history['Close'].tolist(),
            'volume': history['Volume'].tolist()
        }
        
        table.put_item(Item={
            'symbol': symbol,
            'data_type': f'historical_{period}',
            'data': json.dumps(historical_data),
            'ttl': ttl,
            'updated_at': datetime.utcnow().isoformat()
        })
        
        logger.info(f"Updated historical data for {symbol} ({period})")
        return True
        
    except Exception as e:
        logger.error(f"Failed to update historical data for {symbol}: {e}")
        return False


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
