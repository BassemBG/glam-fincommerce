
import asyncio
import os
import sys
import logging

# Add the backend directory to sys.path
sys.path.append(os.path.join(os.getcwd(), "backend"))

# Load environment variables from .env
from dotenv import load_dotenv
load_dotenv(os.path.join(os.getcwd(), "backend", ".env"))

from app.agents.tools_sets.advisor_tools import recommend_brand_items_dna

async def test_advisor_tool():
    try:
        # Use the ID from seed_demo_data or an existing one
        user_id = "test-user-dna-1"
        # We need to make sure we are calling the tool correctly. 
        # Tools in LangChain are called via .invoke() or .ainvoke()
        result = await recommend_brand_items_dna.ainvoke({"user_id": user_id, "query": "sweatshirt"})
        print("--- TOOL OUTPUT ---")
        print(result)
        print("--- END OUTPUT ---")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error calling tool: {e}")

if __name__ == "__main__":
    asyncio.run(test_advisor_tool())
