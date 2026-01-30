
import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

# Mock settings
os.environ["AZURE_OPENAI_ENDPOINT"] = "http://mock"
os.environ["AZURE_OPENAI_API_KEY"] = "mock"
os.environ["QDRANT_URL"] = "http://mock"

async def test():
    from backend.app.agents.tools_sets.advisor_tools import recommend_brand_items_dna
    try:
        # We don't need real IDs, just want to see if it starts and hits a 'not callable' error
        print("Starting test...")
        await recommend_brand_items_dna(user_id="test_user")
    except Exception as e:
        print(f"Caught top-level: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
