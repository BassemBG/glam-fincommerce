# 🔍 Debugging AI Outfit Generation

## Issue
The AI responds with: "It seems there was an issue generating a [occasion] look. Please try again later or check your closet for available items."

## Root Cause Analysis
This message suggests the AI agent is running successfully BUT:
1. **No items found in closet** - The user's closet might be empty
2. **Tool failure** - The closet search tool might be failing silently
3. **AI fallback** - The AI can't create outfits without items

## Diagnostic Steps

### 1. Check if you have items in your closet
- Go to the Upload page
- Upload at least 5-10 clothing items
- Make sure they're analyzed successfully

### 2. Verify items are in Qdrant
Run this in a Python shell:
```python
from app.services.clip_qdrant_service import clip_qdrant_service
import asyncio

async def check_items():
    # Replace with your actual user ID
    user_id = "YOUR_USER_ID_HERE"
    result = await clip_qdrant_service.get_user_items(user_id, limit=10)
    print(f"Found {len(result['items'])} items")
    for item in result['items']:
        print(f"  - {item['clothing'].get('sub_category', 'Unknown')}")

asyncio.run(check_items())
```

### 3. Check backend logs
After trying to generate an outfit, look for `[STREAM]` logs in your backend terminal:
```
INFO: [STREAM] Final response received: ...
INFO: [STREAM] Parsed response: ...
```

### 4. Test the closet tool directly
The AI uses a tool to search your closet. If this tool fails, the AI has no items to work with.

## Quick Fix
1. **Upload more items** to your closet (at least 5-10 diverse pieces)
2. **Try again** with a specific request like "show me my blue tops"
3. **Check the logs** to see what the AI is actually receiving

## Expected Behavior
When working correctly, you should see:
- AI finds items in your closet
- Suggests 2-3 outfit combinations
- Each outfit has a score and reasoning
- Clicking an outfit shows the try-on visualization
