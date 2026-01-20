#!/usr/bin/env python3
"""
Simple WebSocket test script to validate the API Gateway WebSocket connection.
This script connects to the WebSocket API and sends a test message.

Usage:
    python test_websocket.py wss://xxxxx.execute-api.region.amazonaws.com/prod
"""

import asyncio
import json
import sys


async def test_websocket(websocket_url):
    """Test WebSocket connection and messaging"""
    try:
        # Note: websockets library is not installed by default
        # Install with: pip install websockets
        import websockets
        
        print(f"Connecting to {websocket_url}...")
        
        async with websockets.connect(websocket_url) as websocket:
            print("✓ Connected successfully!")
            
            # Send a test message
            test_message = {
                "action": "start_scan",
                "token": "test_token",
                "file_content": "",
                "target_hole_codes": ["HOLE-1", "HOLE-2", "HOLE-3"]
            }
            
            print(f"Sending message: {json.dumps(test_message, indent=2)}")
            await websocket.send(json.dumps(test_message))
            print("✓ Message sent!")
            
            # Receive messages for 30 seconds
            print("\nListening for messages (30 seconds)...")
            try:
                async with asyncio.timeout(30):
                    while True:
                        message = await websocket.recv()
                        data = json.loads(message)
                        print(f"\n📨 Received: {data.get('type', 'UNKNOWN')}")
                        print(json.dumps(data, indent=2))
                        
                        # Stop if we receive COMPLETE or ERROR
                        if data.get('type') in ['COMPLETE', 'ERROR']:
                            print("\n✓ Test completed!")
                            break
            except asyncio.TimeoutError:
                print("\n⏱️  Timeout reached")
                
    except ImportError:
        print("❌ Error: 'websockets' library not found")
        print("Install with: pip install websockets")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python test_websocket.py <websocket_url>")
        print("Example: python test_websocket.py wss://xxxxx.execute-api.us-east-1.amazonaws.com/prod")
        sys.exit(1)
    
    websocket_url = sys.argv[1]
    
    # Validate URL format
    if not websocket_url.startswith('wss://'):
        print("❌ Error: WebSocket URL must start with 'wss://'")
        sys.exit(1)
    
    print("=" * 60)
    print("WebSocket Connection Test")
    print("=" * 60)
    
    asyncio.run(test_websocket(websocket_url))
    
    print("\n" + "=" * 60)
    print("Test completed")
    print("=" * 60)


if __name__ == "__main__":
    main()
