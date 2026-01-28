#!/usr/bin/env python
"""
Quick test to verify Azure upload works with the fixed event loop
"""
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.storage import storage_service
from app.core.config import settings

def test_azure_upload():
    """Test Azure blob upload with async"""
    print(f"[*] Testing Azure upload...")
    print(f"[*] Azure connection: {settings.AZURE_STORAGE_CONNECTION_STRING[:50]}...")
    print(f"[*] Container: {settings.AZURE_STORAGE_CONTAINER}")
    
    # Create test image bytes
    test_image = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    
    # Define async upload function
    async def test_upload():
        print("[*] Starting async upload...")
        url = await storage_service.upload_file(test_image, "test/azure_upload_test.png", "image/png")
        print(f"[OK] Upload successful: {url}")
        return url
    
    # Run with new event loop (like we do in brand_clip_service.py)
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            url = loop.run_until_complete(asyncio.wait_for(test_upload(), timeout=30.0))
            print(f"[OK] Final URL: {url}")
        finally:
            loop.close()
    except asyncio.TimeoutError:
        print("[ERROR] Upload timed out after 30s")
    except Exception as e:
        print(f"[ERROR] Upload failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_azure_upload()
