import os
import json
import asyncio
import logging
from typing import Dict, Any
from app.services.groq_vision_service import groq_vision_service

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class ProfileAnalyzer:
    """
    Analyzes user physical characteristics from full-body photos using Groq Vision.
    Results are saved to a JSON file as per user request.
    """
    
    def __init__(self):
        self.ai_service = groq_vision_service
        self.output_dir = "profile_data"
        os.makedirs(self.output_dir, exist_ok=True)

    async def analyze_and_stock(self, image_path: str, user_id: str = "default_user") -> str:
        """
        Main pipeline: Analyze image -> Extract attributes -> Save to JSON.
        
        Args:
            image_path: Path to the full-body image.
            user_id: Identifier for the user to name the JSON file.
            
        Returns:
            Path to the saved JSON file.
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found at {image_path}")

        logger.info(f"🚀 Starting profile analysis for {user_id}...")
        
        with open(image_path, "rb") as f:
            image_data = f.read()

        # Prompt tuned for the specific requested fields
        prompt = """You are a professional physiological analyst.
Analyze this full-body photo and provide highly accurate estimations for:
1. Morphology (body shape/type)
2. Skin Color (tone)
3. Height (estimate)
4. Weight (estimate)

Return ONLY a JSON object with these EXACT keys:
{
  "morphology": "...",
  "skin_color": "...",
  "height": "...",
  "weight": "...",
  "confidence": 0.95
}
Return ONLY JSON. No headers, no markdown, no conversational text."""

        try:
            # Call Groq Vision
            raw_response = await self.ai_service._call_vision(image_data, prompt, json_format=True)
            
            # Extract JSON from potential markdown wrapping
            json_text = raw_response.strip()
            if json_text.startswith("```"):
                json_text = json_text.split("```")[1]
                if json_text.startswith("json"):
                    json_text = json_text[4:]
                json_text = json_text.strip()
            
            profile_data = json.loads(json_text)
            
            # Enrich with metadata
            result = {
                "user_id": user_id,
                "analysis": profile_data,
                "processed_at": __import__('datetime').datetime.now().isoformat()
            }

            # Save to JSON file as requested
            file_path = os.path.join(self.output_dir, f"profile_{user_id}.json")
            with open(file_path, "w") as f:
                json.dump(result, f, indent=2)
            
            logger.info(f"✅ Analysis complete! Profile stocked in: {file_path}")
            return file_path

        except Exception as e:
            logger.error(f"❌ Analysis failed: {str(e)}")
            raise

async def main():
    # Example usage:
    # 1. Provide an image path
    # 2. Run: python analyze_profile.py
    
    sample_image = "aaaa.jpeg" # Change to your image path
    
    if not os.path.exists(sample_image):
        print(f"\n⚠️  Please place a photo at '{sample_image}' to test the script.")
        print("   Usage: Change the 'sample_image' variable in this script to point to your JPG/PNG file.\n")
        return

    analyzer = ProfileAnalyzer()
    try:
        saved_file = await analyzer.analyze_and_stock(sample_image, "test_user_01")
        print(f"\nSuccessfully analyzed profile. Result:")
        with open(saved_file, "r") as f:
            print(f.read())
    except Exception as e:
        print(f"Error during execution: {e}")

if __name__ == "__main__":
    asyncio.run(main())
