#!/usr/bin/env python3
"""Test WebSocket connection to dashboard endpoint."""

import asyncio
import websockets
import json

async def test_websocket():
    """Test WebSocket connection and subscription."""
    uri = "ws://127.0.0.1:8000/dashboard/ws"
    
    print(f"Connecting to {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket connected successfully!")
            
            # Send subscription
            subscribe_msg = {
                "action": "subscribe",
                "symbols": ["AAPL", "GOOGL"]
            }
            await websocket.send(json.dumps(subscribe_msg))
            print(f"Sent subscription: {subscribe_msg}")
            
            # Wait for messages
            print("Waiting for messages (10 seconds)...")
            try:
                for i in range(5):
                    message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    data = json.loads(message)
                    print(f"Received: {data.get('type', 'unknown')} - {data}")
            except asyncio.TimeoutError:
                print("No messages received (timeout)")
                
    except websockets.exceptions.WebSocketException as e:
        print(f"❌ WebSocket error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
