#!/usr/bin/env python3
"""
Verify AWS LocalStack Integration without awslocal CLI.
This script uses boto3 directly to check resources.
"""
import os
import sys
import json

# Set LocalStack environment
os.environ['AWS_ENDPOINT_URL'] = 'http://localhost:4566'
os.environ['AWS_ACCESS_KEY_ID'] = 'test'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'test'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

try:
    import boto3
    print("✅ boto3 is installed")
except ImportError:
    print("❌ boto3 is not installed")
    print("   Install with: pip install boto3")
    sys.exit(1)

def check_localstack_health():
    """Check if LocalStack is running."""
    import requests
    try:
        response = requests.get('http://localhost:4566/_localstack/health', timeout=5)
        health = response.json()
        print("\n✅ LocalStack is running")
        
        running_services = [k for k, v in health['services'].items() if v == 'running']
        print(f"   Running services: {', '.join(running_services)}")
        return True
    except Exception as e:
        print(f"\n❌ LocalStack is not accessible: {e}")
        return False

def check_s3():
    """Check S3 bucket."""
    print("\n📦 Checking S3...")
    try:
        s3 = boto3.client('s3', endpoint_url='http://localhost:4566')
        response = s3.list_buckets()
        
        buckets = [b['Name'] for b in response.get('Buckets', [])]
        if 'stocktool-knowledge' in buckets:
            print("   ✅ Bucket 'stocktool-knowledge' exists")
            return True
        else:
            print(f"   ⚠️  Bucket not found. Available: {buckets}")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def check_dynamodb():
    """Check DynamoDB tables."""
    print("\n🗄️  Checking DynamoDB...")
    try:
        dynamodb = boto3.client('dynamodb', endpoint_url='http://localhost:4566')
        response = dynamodb.list_tables()
        
        tables = response.get('TableNames', [])
        required_tables = ['stocktool-conversations', 'stocktool-stock-cache']
        
        found = []
        missing = []
        for table in required_tables:
            if table in tables:
                print(f"   ✅ Table '{table}' exists")
                found.append(table)
            else:
                print(f"   ⚠️  Table '{table}' not found")
                missing.append(table)
        
        return len(missing) == 0
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def check_sqs():
    """Check SQS queues."""
    print("\n📨 Checking SQS...")
    try:
        sqs = boto3.client('sqs', endpoint_url='http://localhost:4566')
        response = sqs.list_queues()
        
        queue_urls = response.get('QueueUrls', [])
        found = any('stocktool-analysis-queue' in url for url in queue_urls)
        
        if found:
            print("   ✅ Queue 'stocktool-analysis-queue' exists")
            return True
        else:
            print("   ⚠️  Queue not found")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def check_sns():
    """Check SNS topics."""
    print("\n📢 Checking SNS...")
    try:
        sns = boto3.client('sns', endpoint_url='http://localhost:4566')
        response = sns.list_topics()
        
        topics = [t['TopicArn'] for t in response.get('Topics', [])]
        found = any('stocktool-notifications' in topic for topic in topics)
        
        if found:
            print("   ✅ Topic 'stocktool-notifications' exists")
            return True
        else:
            print("   ⚠️  Topic not found")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def check_cloudwatch():
    """Check CloudWatch."""
    print("\n📊 Checking CloudWatch...")
    try:
        cloudwatch = boto3.client('cloudwatch', endpoint_url='http://localhost:4566')
        # List metrics without MaxRecords parameter (not supported in some versions)
        response = cloudwatch.list_metrics(Namespace='StockTool')
        
        print(f"   ✅ CloudWatch is accessible")
        metrics_count = len(response.get('Metrics', []))
        if metrics_count > 0:
            print(f"   📈 {metrics_count} metrics in StockTool namespace")
        else:
            print(f"   💡 No metrics yet (will appear after application usage)")
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    """Run all checks."""
    print("=" * 60)
    print("AWS LocalStack Resource Verification")
    print("=" * 60)
    
    # Check LocalStack health
    if not check_localstack_health():
        print("\n💡 Start LocalStack with: docker compose up -d localstack")
        sys.exit(1)
    
    # Run all checks
    results = {
        'S3': check_s3(),
        'DynamoDB': check_dynamodb(),
        'SQS': check_sqs(),
        'SNS': check_sns(),
        'CloudWatch': check_cloudwatch()
    }
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    total = len(results)
    passed = sum(results.values())
    
    for service, status in results.items():
        icon = "✅" if status else "⚠️ "
        print(f"{service:15} {icon}")
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 All AWS resources are properly configured!")
        print("\n📚 Next steps:")
        print("   1. Run: python test_aws_integration.py")
        print("   2. Start app: python main.py")
        print("   3. Check docs: AWS_INTEGRATION.md")
        return 0
    else:
        print("\n⚠️  Some resources may not be initialized yet.")
        print("   This can happen if LocalStack just started.")
        print("   Wait 10-20 seconds and run this script again.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
