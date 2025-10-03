"""
Test AWS LocalStack integration.
Run this after starting LocalStack to verify all services work correctly.
"""
import os
import sys
import json
import time
from datetime import datetime, timezone

# Set LocalStack environment
os.environ['USE_LOCALSTACK'] = 'true'
os.environ['AWS_ENDPOINT_URL'] = 'http://localhost:4566'
os.environ['AWS_ACCESS_KEY_ID'] = 'test'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'test'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

# Test imports
try:
    from app.services.aws import (
        get_s3_service,
        get_dynamodb_service,
        get_sqs_service,
        get_cloudwatch_service
    )
    print("✅ AWS services imported successfully")
except ImportError as e:
    print(f"❌ Failed to import AWS services: {e}")
    print("   Install dependencies: pip install boto3 botocore")
    sys.exit(1)


def test_s3():
    """Test S3 operations."""
    print("\n📦 Testing S3...")
    try:
        s3 = get_s3_service()
        
        # Upload test file
        test_content = b"Test content for AWS integration"
        import io
        s3.upload_fileobj(io.BytesIO(test_content), 'test/integration_test.txt')
        print("  ✓ Upload successful")
        
        # Download test file
        downloaded = s3.download_fileobj('test/integration_test.txt')
        assert downloaded == test_content, "Content mismatch"
        print("  ✓ Download successful")
        
        # List files
        files = s3.list_files(prefix='test/')
        assert len(files) > 0, "No files found"
        print(f"  ✓ List successful ({len(files)} files)")
        
        # Check existence
        exists = s3.file_exists('test/integration_test.txt')
        assert exists, "File should exist"
        print("  ✓ Existence check successful")
        
        # Cleanup
        s3.delete_file('test/integration_test.txt')
        print("  ✓ Delete successful")
        
        print("✅ S3 tests passed!")
        return True
    except Exception as e:
        print(f"❌ S3 test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dynamodb():
    """Test DynamoDB operations."""
    print("\n🗄️  Testing DynamoDB...")
    try:
        # Test conversations
        db = get_dynamodb_service('conversation')
        
        test_messages = [
            {'role': 'user', 'content': 'What is AAPL stock price?'},
            {'role': 'assistant', 'content': 'AAPL is trading at $175.50'}
        ]
        
        # Store conversation
        success = db.put_conversation(
            'test-conv-123',
            test_messages,
            user_id='test-user',
            metadata={'test': True}
        )
        assert success, "Failed to store conversation"
        print("  ✓ Conversation stored")
        
        # Retrieve conversation
        messages = db.get_conversation('test-conv-123')
        assert messages is not None, "Failed to retrieve conversation"
        assert len(messages) == 2, f"Expected 2 messages, got {len(messages)}"
        print("  ✓ Conversation retrieved")
        
        # Test cache
        cache = get_dynamodb_service('cache')
        
        test_data = {'symbol': 'AAPL', 'price': 175.50}
        success = cache.put_cache_item('AAPL', test_data, ttl_seconds=300)
        assert success, "Failed to cache item"
        print("  ✓ Cache item stored")
        
        # Retrieve cached item
        cached = cache.get_cache_item('AAPL')
        assert cached is not None, "Failed to retrieve cached item"
        assert cached['price'] == 175.50, "Cached data mismatch"
        print("  ✓ Cache item retrieved")
        
        # Cleanup
        db.delete_conversation('test-conv-123')
        print("  ✓ Conversation deleted")
        
        print("✅ DynamoDB tests passed!")
        return True
    except Exception as e:
        print(f"❌ DynamoDB test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_sqs():
    """Test SQS operations."""
    print("\n📨 Testing SQS...")
    try:
        sqs = get_sqs_service()
        
        # Send message
        test_task = {
            'task': 'test_analysis',
            'symbol': 'AAPL',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        message_id = sqs.send_message(test_task)
        assert message_id is not None, "Failed to send message"
        print(f"  ✓ Message sent: {message_id}")
        
        # Receive message
        time.sleep(1)  # Wait for message to be available
        messages = sqs.receive_messages(max_messages=1, wait_time_seconds=2)
        assert len(messages) > 0, "No messages received"
        print(f"  ✓ Message received")
        
        # Process message
        received_task = messages[0]['body']
        assert received_task['task'] == 'test_analysis', "Task mismatch"
        print("  ✓ Message content verified")
        
        # Delete message
        success = sqs.delete_message(messages[0]['receipt_handle'])
        assert success, "Failed to delete message"
        print("  ✓ Message deleted")
        
        # Get queue attributes
        attrs = sqs.get_queue_attributes()
        print(f"  ✓ Queue attributes retrieved ({len(attrs)} attributes)")
        
        print("✅ SQS tests passed!")
        return True
    except Exception as e:
        print(f"❌ SQS test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cloudwatch():
    """Test CloudWatch operations."""
    print("\n📊 Testing CloudWatch...")
    try:
        cw = get_cloudwatch_service()
        
        # Put metric
        success = cw.put_metric('TestMetric', 42.0, unit='Count')
        assert success, "Failed to put metric"
        print("  ✓ Metric published")
        
        # Track API latency
        cw.track_api_latency('/test', 123.45, status_code=200)
        print("  ✓ API latency tracked")
        
        # Track tool execution
        cw.track_tool_execution('test_tool', 50.0, success=True)
        print("  ✓ Tool execution tracked")
        
        # Track cache hit
        cw.track_cache_hit_rate('test_cache', hit=True)
        print("  ✓ Cache hit rate tracked")
        
        # Track model usage
        cw.track_model_usage('gpt-4o-mini', 500, 1200.0)
        print("  ✓ Model usage tracked")
        
        # Query metrics
        from datetime import timedelta
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=1)
        
        datapoints = cw.query_metrics(
            'TestMetric',
            start_time,
            end_time,
            period=300,
            stat='Average'
        )
        print(f"  ✓ Metrics queried ({len(datapoints)} datapoints)")
        
        print("✅ CloudWatch tests passed!")
        return True
    except Exception as e:
        print(f"❌ CloudWatch test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("AWS LocalStack Integration Tests")
    print("=" * 60)
    
    # Check LocalStack is running
    import requests
    try:
        response = requests.get('http://localhost:4566/_localstack/health', timeout=5)
        health = response.json()
        print(f"\n✅ LocalStack is running")
        print(f"   Services: {', '.join(health.get('services', {}).keys())}")
    except Exception as e:
        print(f"\n❌ LocalStack is not running or not accessible")
        print(f"   Error: {e}")
        print("\n💡 Start LocalStack with: docker-compose up -d localstack")
        sys.exit(1)
    
    # Run tests
    results = {
        'S3': test_s3(),
        'DynamoDB': test_dynamodb(),
        'SQS': test_sqs(),
        'CloudWatch': test_cloudwatch()
    }
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for service, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{service:15} {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 All tests passed! AWS integration is working correctly.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
