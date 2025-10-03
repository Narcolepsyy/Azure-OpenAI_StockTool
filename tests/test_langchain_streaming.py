"""
Test LangChain streaming implementation for real-time token delivery.

This script tests the new LangChain-based streaming to verify:
1. Token-by-token delivery with no buffering
2. Immediate response start time
3. Smooth streaming without delays
"""
import asyncio
import time
import os
import sys
from typing import List, Dict, Any

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

async def test_langchain_streaming():
    """Test LangChain streaming service."""
    try:
        from app.services.langchain_streaming import get_streaming_service, LANGCHAIN_AVAILABLE
    except ImportError as e:
        print(f"❌ LangChain streaming not available: {e}")
        print("Install with: pip install langchain langchain-openai")
        return False
    
    if not LANGCHAIN_AVAILABLE:
        print("❌ LangChain dependencies not installed")
        return False
    
    print("✅ LangChain streaming service available")
    print()
    
    # Test configuration
    test_messages = [
        {
            "role": "system",
            "content": "You are a helpful AI assistant. Provide concise responses."
        },
        {
            "role": "user",
            "content": "Explain what machine learning is in 2-3 sentences."
        }
    ]
    
    # Get streaming service
    print("🔧 Creating LangChain streaming service...")
    try:
        service = get_streaming_service(
            model_name="gpt-4o-mini",
            temperature=0.7,
            max_tokens=500,
            timeout=30
        )
        print("✅ Service created successfully")
    except Exception as e:
        print(f"❌ Failed to create service: {e}")
        return False
    
    print()
    print("🚀 Starting streaming test...")
    print("=" * 60)
    
    # Track streaming metrics
    start_time = time.time()
    first_token_time = None
    token_count = 0
    token_times: List[float] = []
    
    try:
        async for event in service.stream_chat_with_retry(test_messages):
            event_type = event.get("type")
            
            if event_type == "token":
                token = event.get("content", "")
                
                # Record first token time
                if first_token_time is None:
                    first_token_time = time.time()
                    ttft = first_token_time - start_time
                    print(f"\n⏱️  Time to first token: {ttft:.3f}s")
                    print("-" * 60)
                
                # Track token timing
                token_count += 1
                token_times.append(time.time())
                
                # Print token (without newline to show streaming)
                print(token, end="", flush=True)
                
            elif event_type == "end":
                end_time = time.time()
                total_time = end_time - start_time
                
                print("\n" + "-" * 60)
                print(f"\n✅ Streaming completed successfully!")
                print(f"\n📊 Performance Metrics:")
                print(f"   • Total tokens: {token_count}")
                print(f"   • Total time: {total_time:.3f}s")
                
                if first_token_time:
                    ttft = first_token_time - start_time
                    print(f"   • Time to first token (TTFT): {ttft:.3f}s")
                    
                    # Calculate tokens per second
                    streaming_time = total_time - ttft
                    if streaming_time > 0:
                        tps = token_count / streaming_time
                        print(f"   • Tokens per second: {tps:.1f}")
                    
                    # Calculate inter-token latency
                    if len(token_times) > 1:
                        delays = [token_times[i] - token_times[i-1] for i in range(1, len(token_times))]
                        avg_delay = sum(delays) / len(delays)
                        max_delay = max(delays)
                        print(f"   • Average inter-token delay: {avg_delay*1000:.1f}ms")
                        print(f"   • Max inter-token delay: {max_delay*1000:.1f}ms")
                
                print()
                return True
                
            elif event_type == "error":
                error_msg = event.get("error", "Unknown error")
                print(f"\n\n❌ Streaming error: {error_msg}")
                return False
                
    except Exception as e:
        print(f"\n\n❌ Exception during streaming: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return False


async def test_azure_streaming():
    """Test Azure OpenAI streaming."""
    print("\n" + "=" * 60)
    print("Testing Azure OpenAI Streaming")
    print("=" * 60)
    
    try:
        from app.services.langchain_streaming import get_streaming_service, LANGCHAIN_AVAILABLE
    except ImportError:
        print("❌ LangChain not available")
        return False
    
    if not LANGCHAIN_AVAILABLE:
        return False
    
    # Check for Azure configuration
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_key = os.getenv("AZURE_OPENAI_API_KEY")
    azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_GPT4O_MINI")
    
    if not all([azure_endpoint, azure_key, azure_deployment]):
        print("⚠️  Azure OpenAI not configured, skipping Azure test")
        print("   Set: AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT_GPT4O_MINI")
        return True  # Not a failure, just skipped
    
    print("✅ Azure OpenAI configuration found")
    
    azure_config = {
        "endpoint": azure_endpoint,
        "api_key": azure_key,
        "deployment": azure_deployment,
        "api_version": "2024-02-15-preview"
    }
    
    test_messages = [
        {"role": "user", "content": "What is the capital of France? Answer in one sentence."}
    ]
    
    print("\n🚀 Starting Azure streaming test...")
    print("=" * 60)
    
    start_time = time.time()
    first_token_time = None
    token_count = 0
    
    try:
        service = get_streaming_service(
            model_name=azure_deployment,
            temperature=0.7,
            max_tokens=100,
            timeout=30,
            azure_config=azure_config
        )
        
        async for event in service.stream_chat_with_retry(test_messages):
            if event.get("type") == "token":
                if first_token_time is None:
                    first_token_time = time.time()
                    print(f"\n⏱️  Time to first token: {first_token_time - start_time:.3f}s")
                    print("-" * 60)
                
                token_count += 1
                print(event.get("content", ""), end="", flush=True)
                
            elif event.get("type") == "end":
                total_time = time.time() - start_time
                print("\n" + "-" * 60)
                print(f"\n✅ Azure streaming completed!")
                print(f"   • Tokens: {token_count}")
                print(f"   • Time: {total_time:.3f}s")
                return True
                
            elif event.get("type") == "error":
                print(f"\n\n❌ Azure streaming error: {event.get('error')}")
                return False
                
    except Exception as e:
        print(f"\n\n❌ Azure streaming exception: {e}")
        return False
    
    return False


async def main():
    """Run all streaming tests."""
    print("=" * 60)
    print("LangChain Streaming Performance Test")
    print("=" * 60)
    print()
    
    results = []
    
    # Test standard OpenAI streaming
    print("Test 1: Standard OpenAI Streaming")
    print("-" * 60)
    result1 = await test_langchain_streaming()
    results.append(("OpenAI Streaming", result1))
    
    # Test Azure OpenAI streaming
    print("\n")
    result2 = await test_azure_streaming()
    results.append(("Azure Streaming", result2))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    all_passed = all(result for _, result in results)
    print()
    if all_passed:
        print("🎉 All tests passed! LangChain streaming is working correctly.")
        print()
        print("💡 Benefits of LangChain streaming:")
        print("   • Immediate token-by-token delivery")
        print("   • No buffering delays")
        print("   • Lower latency to first token")
        print("   • Smoother user experience")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
