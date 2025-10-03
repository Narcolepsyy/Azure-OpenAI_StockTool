#!/usr/bin/env python3
"""
Test Lambda Functions Locally or in LocalStack
"""
import json
import os
import sys
from datetime import datetime

import boto3
from botocore.exceptions import ClientError

# Configuration
ENDPOINT_URL = os.getenv('AWS_ENDPOINT_URL', 'http://localhost:4566')
REGION = os.getenv('AWS_REGION', 'us-east-1')

# AWS clients
lambda_client = boto3.client(
    'lambda',
    endpoint_url=ENDPOINT_URL,
    region_name=REGION,
    aws_access_key_id='test',
    aws_secret_access_key='test'
)

logs_client = boto3.client(
    'logs',
    endpoint_url=ENDPOINT_URL,
    region_name=REGION,
    aws_access_key_id='test',
    aws_secret_access_key='test'
)


def print_header(text: str):
    """Print formatted header"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")


def invoke_lambda(function_name: str, event: dict) -> dict:
    """
    Invoke Lambda function and return response.
    
    Args:
        function_name: Name of Lambda function
        event: Event payload
        
    Returns:
        Response dict with status and payload
    """
    print(f"▶ Invoking Lambda: {function_name}")
    print(f"  Event: {json.dumps(event, indent=2)}")
    
    try:
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(event)
        )
        
        status_code = response['StatusCode']
        payload = json.loads(response['Payload'].read())
        
        print(f"  ✓ Status Code: {status_code}")
        print(f"  ✓ Response:")
        print(json.dumps(payload, indent=2))
        
        return {
            'success': status_code == 200,
            'status_code': status_code,
            'payload': payload
        }
        
    except ClientError as e:
        print(f"  ✗ Error: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def list_lambda_functions():
    """List all Lambda functions"""
    print_header("Available Lambda Functions")
    
    try:
        response = lambda_client.list_functions()
        functions = response.get('Functions', [])
        
        if not functions:
            print("No Lambda functions found")
            return []
        
        for func in functions:
            print(f"  • {func['FunctionName']}")
            print(f"    Runtime: {func['Runtime']}")
            print(f"    Handler: {func['Handler']}")
            print(f"    Memory: {func['MemorySize']} MB")
            print(f"    Timeout: {func['Timeout']} seconds")
            print()
        
        return functions
        
    except ClientError as e:
        print(f"Error listing functions: {e}")
        return []


def get_lambda_logs(function_name: str, limit: int = 20):
    """Get recent Lambda logs"""
    print_header(f"Recent Logs for {function_name}")
    
    log_group_name = f"/aws/lambda/{function_name}"
    
    try:
        # Get log streams
        streams_response = logs_client.describe_log_streams(
            logGroupName=log_group_name,
            orderBy='LastEventTime',
            descending=True,
            limit=5
        )
        
        if not streams_response.get('logStreams'):
            print("No log streams found")
            return
        
        # Get logs from most recent stream
        stream_name = streams_response['logStreams'][0]['logStreamName']
        
        events_response = logs_client.get_log_events(
            logGroupName=log_group_name,
            logStreamName=stream_name,
            limit=limit
        )
        
        events = events_response.get('events', [])
        
        if not events:
            print("No log events found")
            return
        
        for event in events:
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            message = event['message'].strip()
            print(f"[{timestamp}] {message}")
        
    except ClientError as e:
        print(f"Error getting logs: {e}")


def test_stock_updater():
    """Test stock updater Lambda function"""
    print_header("Testing Stock Updater Lambda")
    
    function_name = "stocktool-stock-updater"
    
    # Test with default symbols
    print("\n1. Test with default symbols:")
    event1 = {}
    result1 = invoke_lambda(function_name, event1)
    
    # Test with custom symbols
    print("\n2. Test with custom symbols:")
    event2 = {
        "symbols": ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"]
    }
    result2 = invoke_lambda(function_name, event2)
    
    # Get logs
    print("\n3. Check logs:")
    get_lambda_logs(function_name, limit=30)
    
    return result1 and result2


def main():
    """Main test runner"""
    print_header("Lambda Function Testing Tool")
    
    # Check LocalStack connection
    try:
        lambda_client.list_functions()
        print("✓ Connected to LocalStack")
    except Exception as e:
        print(f"✗ Cannot connect to LocalStack: {e}")
        print("\nMake sure LocalStack is running:")
        print("  docker compose up -d localstack")
        sys.exit(1)
    
    # List functions
    functions = list_lambda_functions()
    
    if not functions:
        print("\n⚠ No Lambda functions deployed")
        print("Deploy Lambda functions with:")
        print("  ./scripts/deploy_lambda.sh")
        sys.exit(0)
    
    # Run tests
    print_header("Running Lambda Tests")
    
    test_stock_updater()
    
    print_header("Test Summary")
    print("✓ All tests completed")
    print("\nNext steps:")
    print("  1. Check CloudWatch metrics")
    print("  2. View dashboard: ./scripts/create_cloudwatch_dashboard.sh")
    print("  3. Monitor Lambda executions in real-time")


if __name__ == '__main__':
    main()
