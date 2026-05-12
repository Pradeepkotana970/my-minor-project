import os
import requests
import uuid
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class StartupManager:
    """Manages the startup-grade API features: billing, API keys, and external API requests."""
    
    def __init__(self):
        self.api_keys = {}
        self.tiers = {
            "free": {"max_requests": 1000, "price": "$0/mo"},
            "pro": {"max_requests": 50000, "price": "$49/mo"},
            "enterprise": {"max_requests": -1, "price": "$499/mo"}
        }

    def generate_api_key(self, user_id: str, tier: str = "free"):
        """Generates a pseudo developer API key for external integrations."""
        if tier not in self.tiers:
            tier = "free"
            
        new_key = f"sk_live_{uuid.uuid4().hex}"
        self.api_keys[new_key] = {
            "user_id": user_id,
            "tier": tier,
            "created_at": datetime.now().isoformat(),
            "status": "active"
        }
        return {
            "api_key": new_key,
            "tier": tier,
            "specs": self.tiers[tier]
        }

    def fetch_weather_context(self, latitude: float = 40.7128, longitude: float = -74.0060):
        """
        Fetches current weather context using the free Open-Meteo API.
        This external API data could be attached to the dashboard context
        to see if weather affects attendance patterns.
        """
        try:
            # Using Open-Meteo which doesn't require an API key
            url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            weather = data.get("current_weather", {})
            return {
                "temperature": weather.get("temperature"),
                "windspeed": weather.get("windspeed"),
                "is_day": weather.get("is_day") == 1,
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Failed to fetch weather from Open-Meteo: {e}")
            return {"status": "error", "message": str(e)}

# Singleton instance
startup_manager = StartupManager()
