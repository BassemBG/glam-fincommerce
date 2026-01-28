"""
Test script to debug the AI outfit generation issue
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.orchestrator import agent_orchestrator

async def test_outfit_generation():
    """Test the outfit generation with a simple query"""
    
    # Test user ID (replace with a real one from your database)
    test_user_id = "test-user-123"
    
    # Test message
    test_message = "generate me a casual everyday look"
    
    print("=" * 60)
    print("Testing AI Outfit Generation")
    print("=" * 60)
    print(f"User ID: {test_user_id}")
    print(f"Message: {test_message}")
    print("=" * 60)
    print()
    
    try:
        # Call the agent
        result = await agent_orchestrator.chat(
            user_id=test_user_id,
            message=test_message,
            history=[]
        )
        
        print("✅ SUCCESS!")
        print()
        print("Response:")
        print(result.get("response", "No response"))
        print()
        print("Images:")
        print(result.get("images", []))
        print()
        print("Suggested Outfits:")
        for outfit in result.get("suggested_outfits", []):
            print(f"  - {outfit.get('name', 'Unnamed')} (Score: {outfit.get('score', 0)}/10)")
        print()
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_outfit_generation())
