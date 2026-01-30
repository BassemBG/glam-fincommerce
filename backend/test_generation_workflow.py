"""Debug test for generation evaluation workflow"""
import asyncio
import sys
import logging
sys.path.insert(0, '.')

# Enable all logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(name)s - %(levelname)s - %(message)s'
)

from app.services.ragas_service import ragas_service

# Test single generation evaluation
async def test_gen_eval():
    print("=" * 60)
    print("Testing Generation Evaluation Workflow")
    print("=" * 60)
    
    try:
        result = await ragas_service.evaluate_generation(
            question='What outfit would you recommend?',
            contexts=['User likes minimalist style', 'Budget is 200 TND'],
            answer='I recommend a black t-shirt with blue jeans for a clean minimalist look within budget.',
            pipeline='test_workflow',
            metadata={'test': True}
        )
        print(f"\nResult: {result}")
        print(f"Result type: {type(result)}")
        return result
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(test_gen_eval())
