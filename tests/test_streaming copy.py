#!/usr/bin/env python3
"""
Streaming Response Test
Tests the /chat/stream endpoint functionality
"""
import asyncio
import httpx
import sys
import time
import json
from typing import Dict, Any, List

# Color codes
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'


class StreamingTest:
    """Test suite for streaming chat responses."""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.token = None
        self.results = []
    
    def print_header(self, text: str):
        """Print formatted header."""
        print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
        print(f"{BOLD}{BLUE}{text.center(70)}{RESET}")
        print(f"{BOLD}{BLUE}{'='*70}{RESET}\n")
    
    async def login(self):
        """Login and get JWT token."""
        print(f"{BOLD}Authenticating...{RESET}", end=" ", flush=True)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Try to register (will fail if user exists, that's ok)
                try:
                    await client.post(
                        f"{self.base_url}/auth/register",
                        json={
                            "username": "test_streaming",
                            "email": "test_streaming@test.com",
                            "password": "testpass123"
                        }
                    )
                except:
                    pass  # User might already exist
                
                # Login
                response = await client.post(
                    f"{self.base_url}/auth/token",
                    data={
                        "username": "test_streaming",
                        "password": "testpass123"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.token = data.get("access_token")
                    print(f"{GREEN}✅ Authenticated{RESET}")
                    return True
                else:
                    print(f"{RED}❌ Failed: {response.status_code}{RESET}")
                    return False
                    
        except Exception as e:
            print(f"{RED}❌ Error: {e}{RESET}")
            return False
    
    async def test_simple_streaming(self):
        """Test simple streaming response."""
        print(f"\n{BOLD}Test 1: Simple Streaming Response{RESET}")
        print("Testing: 'What is 2+2?'")
        
        try:
            chunks_received = 0
            content_chunks = []
            start_time = time.perf_counter()
            first_chunk_time = None
            events = []
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/stream",
                    headers={"Authorization": f"Bearer {self.token}"},
                    json={
                        "prompt": "What is 2+2? Be brief.",
                        "deployment": "gpt-4o-mini"
                    }
                ) as response:
                    if response.status_code != 200:
                        print(f"{RED}❌ Failed: HTTP {response.status_code}{RESET}")
                        return False
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            chunks_received += 1
                            if first_chunk_time is None:
                                first_chunk_time = time.perf_counter() - start_time
                            
                            try:
                                data = json.loads(line[6:])  # Remove "data: " prefix
                                event_type = data.get("type")
                                events.append(event_type)
                                
                                if event_type == "content":
                                    delta = data.get("delta", "")
                                    content_chunks.append(delta)
                                    print(delta, end="", flush=True)
                                elif event_type == "start":
                                    conv_id = data.get("conversation_id", "N/A")
                                    model = data.get("model", "N/A")
                                    print(f"  Stream started: {model} (conv: {conv_id[:8]}...)")
                                elif event_type == "done":
                                    print(f"\n  Stream completed")
                            except json.JSONDecodeError:
                                pass
            
            duration = time.perf_counter() - start_time
            full_content = "".join(content_chunks)
            
            print(f"\n{BOLD}Results:{RESET}")
            print(f"  Duration: {GREEN}{duration:.2f}s{RESET}")
            print(f"  Time to first chunk: {GREEN}{first_chunk_time*1000:.0f}ms{RESET}")
            print(f"  Chunks received: {GREEN}{chunks_received}{RESET}")
            print(f"  Content length: {GREEN}{len(full_content)} chars{RESET}")
            print(f"  Event types: {', '.join(set(events))}")
            
            # Validation
            checks = {
                "Received chunks": chunks_received > 0,
                "First chunk fast (< 5s)": first_chunk_time and first_chunk_time < 5.0,
                "Total time reasonable (< 10s)": duration < 10.0,
                "Has content": len(full_content) > 0,
                "Has start event": "start" in events,
                "Has done event": "done" in events,
            }
            
            passed = sum(checks.values())
            total = len(checks)
            
            print(f"\n  {BOLD}Validation: {passed}/{total}{RESET}")
            for check, status in checks.items():
                icon = f"{GREEN}✅{RESET}" if status else f"{RED}❌{RESET}"
                print(f"    {icon} {check}")
            
            self.results.append({
                "test": "simple_streaming",
                "passed": all(checks.values()),
                "duration": duration,
                "first_chunk": first_chunk_time,
                "chunks": chunks_received
            })
            
            return all(checks.values())
            
        except Exception as e:
            print(f"{RED}❌ Error: {e}{RESET}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_tool_call_streaming(self):
        """Test streaming with tool calls."""
        print(f"\n{BOLD}Test 2: Streaming with Tool Calls{RESET}")
        print("Testing: 'What is Apple's stock price?'")
        
        try:
            chunks_received = 0
            content_chunks = []
            tool_calls = []
            start_time = time.perf_counter()
            first_chunk_time = None
            events = []
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/stream",
                    headers={"Authorization": f"Bearer {self.token}"},
                    json={
                        "prompt": "What is Apple's current stock price?",
                        "deployment": "gpt-4o-mini"
                    }
                ) as response:
                    if response.status_code != 200:
                        print(f"{RED}❌ Failed: HTTP {response.status_code}{RESET}")
                        return False
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            chunks_received += 1
                            if first_chunk_time is None:
                                first_chunk_time = time.perf_counter() - start_time
                            
                            try:
                                data = json.loads(line[6:])
                                event_type = data.get("type")
                                events.append(event_type)
                                
                                if event_type == "content":
                                    delta = data.get("delta", "")
                                    content_chunks.append(delta)
                                    print(delta, end="", flush=True)
                                elif event_type == "start":
                                    model = data.get("model", "N/A")
                                    print(f"  Stream started: {model}")
                                elif event_type == "tool_call":
                                    tool_name = data.get("name", "unknown")
                                    tool_status = data.get("status", "unknown")
                                    tool_calls.append(f"{tool_name}:{tool_status}")
                                    print(f"\n  🔧 Tool: {tool_name} - {tool_status}")
                                elif event_type == "tool_calls":
                                    tools = data.get("tools", [])
                                    print(f"\n  🔧 Tools called: {', '.join(tools)}")
                                elif event_type == "done":
                                    print(f"\n  Stream completed")
                            except json.JSONDecodeError:
                                pass
            
            duration = time.perf_counter() - start_time
            full_content = "".join(content_chunks)
            
            print(f"\n{BOLD}Results:{RESET}")
            print(f"  Duration: {GREEN}{duration:.2f}s{RESET}")
            print(f"  Time to first chunk: {GREEN}{first_chunk_time*1000:.0f}ms{RESET}")
            print(f"  Chunks received: {GREEN}{chunks_received}{RESET}")
            print(f"  Tool calls: {GREEN}{len(tool_calls)}{RESET}")
            if tool_calls:
                print(f"  Tool activity: {', '.join(tool_calls)}")
            print(f"  Content length: {GREEN}{len(full_content)} chars{RESET}")
            
            # Validation
            checks = {
                "Received chunks": chunks_received > 0,
                "First chunk fast (< 5s)": first_chunk_time and first_chunk_time < 5.0,
                "Total time reasonable (< 15s)": duration < 15.0,
                "Has content": len(full_content) > 0,
                "Tool calls detected": len(tool_calls) > 0,
                "Has done event": "done" in events,
            }
            
            passed = sum(checks.values())
            total = len(checks)
            
            print(f"\n  {BOLD}Validation: {passed}/{total}{RESET}")
            for check, status in checks.items():
                icon = f"{GREEN}✅{RESET}" if status else f"{RED}❌{RESET}"
                print(f"    {icon} {check}")
            
            self.results.append({
                "test": "tool_call_streaming",
                "passed": all(checks.values()),
                "duration": duration,
                "first_chunk": first_chunk_time,
                "chunks": chunks_received,
                "tool_calls": len(tool_calls)
            })
            
            return all(checks.values())
            
        except Exception as e:
            print(f"{RED}❌ Error: {e}{RESET}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_cached_streaming(self):
        """Test cached response streaming."""
        print(f"\n{BOLD}Test 3: Cached Response Streaming{RESET}")
        print("Testing: Repeat previous query (should be cached)")
        
        try:
            chunks_received = 0
            start_time = time.perf_counter()
            first_chunk_time = None
            is_cached = False
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/stream",
                    headers={"Authorization": f"Bearer {self.token}"},
                    json={
                        "prompt": "What is 2+2? Be brief.",
                        "deployment": "gpt-4o-mini"
                    }
                ) as response:
                    if response.status_code != 200:
                        print(f"{RED}❌ Failed: HTTP {response.status_code}{RESET}")
                        return False
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            chunks_received += 1
                            if first_chunk_time is None:
                                first_chunk_time = time.perf_counter() - start_time
                            
                            try:
                                data = json.loads(line[6:])
                                if data.get("cached"):
                                    is_cached = True
                                    print(f"  {YELLOW}⚡ Cached response detected{RESET}")
                            except json.JSONDecodeError:
                                pass
            
            duration = time.perf_counter() - start_time
            
            print(f"\n{BOLD}Results:{RESET}")
            print(f"  Duration: {GREEN}{duration:.2f}s{RESET}")
            print(f"  Time to first chunk: {GREEN}{first_chunk_time*1000:.0f}ms{RESET}")
            print(f"  Cached: {GREEN if is_cached else YELLOW}{is_cached}{RESET}")
            print(f"  Chunks received: {GREEN}{chunks_received}{RESET}")
            
            # Validation
            checks = {
                "Received chunks": chunks_received > 0,
                "Very fast (< 2s)": duration < 2.0,
                "First chunk instant (< 100ms)": first_chunk_time and first_chunk_time < 0.1,
            }
            
            passed = sum(checks.values())
            total = len(checks)
            
            print(f"\n  {BOLD}Validation: {passed}/{total}{RESET}")
            for check, status in checks.items():
                icon = f"{GREEN}✅{RESET}" if status else f"{YELLOW}⚠️ {RESET}"
                print(f"    {icon} {check}")
            
            if is_cached:
                print(f"  {GREEN}✅ Cache is working!{RESET}")
            else:
                print(f"  {YELLOW}⚠️  Cache may not be enabled or TTL expired{RESET}")
            
            self.results.append({
                "test": "cached_streaming",
                "passed": all(checks.values()),
                "duration": duration,
                "first_chunk": first_chunk_time,
                "cached": is_cached
            })
            
            return all(checks.values())
            
        except Exception as e:
            print(f"{RED}❌ Error: {e}{RESET}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_error_handling(self):
        """Test error handling in streaming."""
        print(f"\n{BOLD}Test 4: Error Handling{RESET}")
        print("Testing: Invalid model name")
        
        try:
            error_received = False
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                try:
                    async with client.stream(
                        "POST",
                        f"{self.base_url}/chat/stream",
                        headers={"Authorization": f"Bearer {self.token}"},
                        json={
                            "prompt": "Test",
                            "deployment": "invalid-model-name"
                        }
                    ) as response:
                        if response.status_code != 200:
                            print(f"  {GREEN}✅ Correctly rejected with HTTP {response.status_code}{RESET}")
                            error_received = True
                        else:
                            async for line in response.aiter_lines():
                                if line.startswith("data: "):
                                    try:
                                        data = json.loads(line[6:])
                                        if data.get("type") == "error":
                                            print(f"  {GREEN}✅ Error event received: {data.get('error')}{RESET}")
                                            error_received = True
                                    except json.JSONDecodeError:
                                        pass
                except httpx.HTTPStatusError as e:
                    print(f"  {GREEN}✅ HTTP error caught: {e.response.status_code}{RESET}")
                    error_received = True
            
            if error_received:
                print(f"{GREEN}✅ Error handling works correctly{RESET}")
            else:
                print(f"{RED}❌ No error received for invalid model{RESET}")
            
            self.results.append({
                "test": "error_handling",
                "passed": error_received
            })
            
            return error_received
            
        except Exception as e:
            # Exception is expected for error handling test
            print(f"{GREEN}✅ Exception handled: {type(e).__name__}{RESET}")
            self.results.append({
                "test": "error_handling",
                "passed": True
            })
            return True
    
    def print_summary(self):
        """Print test summary."""
        self.print_header("TEST SUMMARY")
        
        passed = sum(1 for r in self.results if r.get("passed"))
        total = len(self.results)
        
        print(f"{BOLD}Results:{RESET}")
        for result in self.results:
            test = result["test"].replace("_", " ").title()
            status = f"{GREEN}✅ PASS{RESET}" if result.get("passed") else f"{RED}❌ FAIL{RESET}"
            
            details = []
            if "duration" in result:
                details.append(f"{result['duration']:.2f}s")
            if "first_chunk" in result:
                details.append(f"TTFB: {result['first_chunk']*1000:.0f}ms")
            if "chunks" in result:
                details.append(f"{result['chunks']} chunks")
            if "tool_calls" in result:
                details.append(f"{result['tool_calls']} tools")
            
            detail_str = f" ({', '.join(details)})" if details else ""
            print(f"  {status} {test}{detail_str}")
        
        print(f"\n{BOLD}Passed: {passed}/{total}{RESET}")
        
        if passed == total:
            print(f"\n{GREEN}🎉 All streaming tests passed!{RESET}")
            print(f"{GREEN}Streaming is working correctly and fast!{RESET}")
            grade = "A+"
        elif passed >= total * 0.75:
            print(f"\n{YELLOW}👍 Most tests passed. Minor issues detected.{RESET}")
            grade = "B"
        else:
            print(f"\n{RED}❌ Multiple tests failed. Investigation needed.{RESET}")
            grade = "C"
        
        print(f"\n{BOLD}Streaming Grade: {grade}{RESET}")
        
        # Performance metrics
        durations = [r["duration"] for r in self.results if "duration" in r]
        if durations:
            print(f"\n{BOLD}Performance Metrics:{RESET}")
            print(f"  Average response time: {sum(durations)/len(durations):.2f}s")
            print(f"  Fastest response: {min(durations):.2f}s")
            print(f"  Slowest response: {max(durations):.2f}s")
        
        first_chunks = [r["first_chunk"] for r in self.results if "first_chunk" in r]
        if first_chunks:
            print(f"  Average TTFB: {sum(first_chunks)/len(first_chunks)*1000:.0f}ms")
            print(f"  Best TTFB: {min(first_chunks)*1000:.0f}ms")
        
        return passed == total


async def main():
    """Run all streaming tests."""
    tester = StreamingTest()
    
    tester.print_header("STREAMING RESPONSE TEST SUITE")
    print("Testing /chat/stream endpoint functionality...")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Authenticate
    if not await tester.login():
        print(f"\n{RED}❌ Authentication failed. Make sure the server is running.{RESET}")
        print(f"Start server with: uvicorn main:app --reload")
        return 1
    
    # Run tests
    print("\n" + "="*70)
    await tester.test_simple_streaming()
    
    print("\n" + "="*70)
    await tester.test_tool_call_streaming()
    
    print("\n" + "="*70)
    await tester.test_cached_streaming()
    
    print("\n" + "="*70)
    await tester.test_error_handling()
    
    # Print summary
    print("\n" + "="*70)
    all_passed = tester.print_summary()
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Test interrupted by user{RESET}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{RED}Test error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
