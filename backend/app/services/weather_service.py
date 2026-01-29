import httpx
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class WeatherService:
    @staticmethod
    async def get_weather(city: str = "Tunis") -> Optional[Dict[str, Any]]:
        """
        Fetches current weather for a city using wttr.in (v3 JSON format).
        Returns a simplified dict of weather conditions.
        """
        try:
            url = f"https://wttr.in/{city}?format=j1"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                if response.status_code != 200:
                    logger.error(f"Weather API error: {response.status_code}")
                    return None
                
                data = response.json()
                current = data.get("current_condition", [{}])[0]
                temp_c = current.get("temp_C")
                desc = current.get("weatherDesc", [{}])[0].get("value")
                
                # Check for rain in next 24h
                is_rainy = "Rain" in desc or "Showers" in desc
                
                return {
                    "city": city,
                    "temp_c": int(temp_c) if temp_c else None,
                    "description": desc,
                    "is_rainy": is_rainy,
                    "raw_data": current
                }
        except Exception as e:
            logger.error(f"Failed to fetch weather: {e}")
            return None

weather_service = WeatherService()
