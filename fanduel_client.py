"""FanDuel API client for fetching player data and projections."""
import logging
from typing import Dict, Optional

import httpx
from cachetools import TTLCache

logger = logging.getLogger(__name__)


class FanDuelClient:
    """Client for interacting with FanDuel API."""
    
    def __init__(self):
        """Initialize the FanDuel client."""
        self.base_url = "https://api.fanduel.com"
        self.image_base_url = "https://d17odppiik753x.cloudfront.net/playerimages/nfl/300x300"
        self._cache = TTLCache(maxsize=500, ttl=3600)  # Cache for 1 hour
        self._client = httpx.AsyncClient(timeout=10.0)
    
    def get_player_image_url(self, player_id: str) -> str:
        """
        Get player image URL from CloudFront CDN.
        
        Args:
            player_id: FanDuel player ID (e.g., "124949-103020")
            
        Returns:
            URL to player image
        """
        # Extract the numeric part after the hyphen
        # e.g., "124949-103020" -> "103020"
        try:
            if "-" in player_id:
                numeric_id = player_id.split("-")[1]
            else:
                numeric_id = player_id
            
            return f"{self.image_base_url}/{numeric_id}.png"
        except Exception as e:
            logger.warning(f"Error parsing player ID {player_id}: {e}")
            return f"{self.image_base_url}/default.png"
    
    async def get_player_data(self, player_id: str, fixture_id: str = "124949") -> Optional[Dict]:
        """
        Fetch player data from FanDuel API.
        
        Args:
            player_id: FanDuel player ID (e.g., "124949-103020")
            fixture_id: FanDuel fixture/contest ID (default to NFL main)
            
        Returns:
            Dictionary with player data or None if fetch fails
        """
        cache_key = f"player_{player_id}"
        
        if cache_key in self._cache:
            logger.debug(f"Using cached FanDuel data for {player_id}")
            return self._cache[cache_key]
        
        try:
            # FanDuel API endpoint format
            url = f"{self.base_url}/fixture-lists/{fixture_id}/players/{player_id}"
            params = {
                "content_sources": "NUMBERFIRE,ROTOWIRE,ROTOGRINDERS"
            }
            
            response = await self._client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract relevant information
                player_info = self._parse_player_data(data)
                player_info["image_url"] = self.get_player_image_url(player_id)
                
                self._cache[cache_key] = player_info
                logger.info(f"Fetched FanDuel data for player {player_id}")
                return player_info
            else:
                logger.warning(f"FanDuel API returned {response.status_code} for {player_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching FanDuel data for {player_id}: {e}")
            return None
    
    def _parse_player_data(self, data: Dict) -> Dict:
        """
        Parse FanDuel API response into simplified format.
        
        Args:
            data: Raw API response
            
        Returns:
            Simplified player data dictionary
        """
        try:
            player_data = {
                "projection": None,
                "opponent": None,
                "injury_status": None,
                "injury_details": None,
                "expert_analysis": [],
                "recent_stats": None,
                "salary": None
            }
            
            # Extract projection (FPPG - Fantasy Points Per Game)
            if "fppg" in data:
                player_data["projection"] = round(float(data.get("fppg", 0)), 1)
            elif "projected_score" in data:
                player_data["projection"] = round(float(data.get("projected_score", 0)), 1)
            
            # Extract opponent
            if "opponent" in data:
                opp = data["opponent"]
                if isinstance(opp, dict):
                    player_data["opponent"] = opp.get("code") or opp.get("name")
                else:
                    player_data["opponent"] = str(opp)
            
            # Extract injury status
            if "injury" in data:
                injury = data["injury"]
                if isinstance(injury, dict):
                    player_data["injury_status"] = injury.get("status", "").upper()
                    player_data["injury_details"] = injury.get("description")
                else:
                    player_data["injury_status"] = str(injury).upper()
            
            # Extract salary
            if "salary" in data:
                player_data["salary"] = int(data.get("salary", 0))
            
            # Extract expert analysis from content sources
            if "content" in data:
                content = data["content"]
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict):
                            source = item.get("source", "Expert")
                            analysis = item.get("analysis") or item.get("summary")
                            if analysis:
                                player_data["expert_analysis"].append({
                                    "source": source,
                                    "text": analysis[:200]  # Truncate to 200 chars
                                })
            
            # Extract recent stats
            if "recent_games" in data:
                recent = data["recent_games"]
                if isinstance(recent, list) and len(recent) > 0:
                    # Average last 3 games
                    last_3 = recent[:3]
                    if last_3:
                        avg_points = sum(g.get("fppg", 0) for g in last_3) / len(last_3)
                        player_data["recent_stats"] = f"Last 3 avg: {avg_points:.1f} pts"
            
            return player_data
            
        except Exception as e:
            logger.error(f"Error parsing player data: {e}")
            return {
                "projection": None,
                "opponent": None,
                "injury_status": None,
                "injury_details": None,
                "expert_analysis": [],
                "recent_stats": None,
                "salary": None
            }
    
    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()


# Global instance
fanduel_client = FanDuelClient()
