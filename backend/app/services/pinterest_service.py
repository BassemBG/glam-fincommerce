import requests
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from urllib.parse import urlencode
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.models import User, PinterestToken

logger = logging.getLogger(__name__)

PINTEREST_API_BASE = "https://api.pinterest.com/v5"
# Authorize endpoint must use the public host (www), not the API host
PINTEREST_OAUTH_URL = "https://www.pinterest.com/oauth"

# Import optional services - they might fail if not configured
try:
    from app.services.zep_service import update_user_persona_with_pins
except ImportError as e:
    logger.warning(f"Could not import update_user_persona_with_pins: {e}")
    def update_user_persona_with_pins(*args, **kwargs):
        logger.info("ZEP service not available, skipping persona update")
        return False

try:
    from app.services.vision_analyzer import analyze_image
except ImportError as e:
    logger.warning(f"Could not import analyze_image: {e}")
    def analyze_image(*args, **kwargs):
        return None

try:
    from app.services.embedding_service import get_embedding
except ImportError as e:
    logger.warning(f"Could not import get_embedding: {e}")
    def get_embedding(*args, **kwargs):
        return None

class PinterestOAuthService:
    """Handles Pinterest OAuth flow"""
    
    @staticmethod
    def get_oauth_url(state: str) -> str:
        """Generate the Pinterest OAuth URL for login"""
        # Pinterest uses space-separated scopes
        params = {
            "response_type": "code",
            "client_id": settings.PINTEREST_APP_ID,
            "redirect_uri": settings.PINTEREST_REDIRECT_URI,
            "scope": "boards:read pins:read user_accounts:read",
            "state": state
        }
        return f"{PINTEREST_OAUTH_URL}?{urlencode(params)}"
    
    @staticmethod
    def exchange_code_for_token(code: str) -> Dict:
        """Exchange authorization code for access token"""
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.PINTEREST_REDIRECT_URI
        }
        
        # Pinterest v5 expects Basic Auth with client_id:client_secret
        from requests.auth import HTTPBasicAuth
        
        logger.info(f"Exchanging code for token using endpoint: https://api.pinterest.com/v5/oauth/token")
        logger.info(f"Payload: grant_type={payload['grant_type']}, redirect_uri={payload['redirect_uri']}")
        
        response = requests.post(
            "https://api.pinterest.com/v5/oauth/token",
            data=payload,
            auth=HTTPBasicAuth(settings.PINTEREST_APP_ID, settings.PINTEREST_APP_SECRET),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10
        )

        logger.info(f"Token exchange response status: {response.status_code}")
        logger.info(f"Token exchange response: {response.text}")

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:  # pragma: no cover
            logger.error(
                "Pinterest token exchange failed: status=%s body=%s",
                response.status_code,
                response.text,
            )
            raise
        
        token_data = response.json()
        logger.info(f"Successfully exchanged code for token")
        
        return token_data
    
    @staticmethod
    def save_token_to_db(user_id: str, token_data: Dict, db: Session) -> 'PinterestToken':
        """Save Pinterest token to database"""
        # Calculate expiration time
        expires_in = token_data.get("expires_in", 3600)  # default 1 hour
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        # Check if token already exists
        existing_token = db.query(PinterestToken).filter(
            PinterestToken.user_id == user_id
        ).first()
        
        if existing_token:
            # Update existing token
            existing_token.access_token = token_data.get("access_token")
            existing_token.refresh_token = token_data.get("refresh_token")
            existing_token.expires_at = expires_at
            existing_token.updated_at = datetime.utcnow()
            db.add(existing_token)
        else:
            # Create new token record
            new_token = PinterestToken(
                user_id=user_id,
                access_token=token_data.get("access_token"),
                refresh_token=token_data.get("refresh_token"),
                expires_at=expires_at
            )
            db.add(new_token)
        
        db.commit()
        db.refresh(existing_token or new_token)
        logger.info(f"Saved Pinterest token for user {user_id}")
        
        return existing_token or new_token


class PinterestAPIService:
    """Handles Pinterest API calls to fetch boards and pins"""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    def get_user_account(self) -> Dict:
        """Get user account information"""
        try:
            response = requests.get(
                f"{PINTEREST_API_BASE}/user_account",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching user account: {e}")
            raise
    
    def get_boards(self) -> List[Dict]:
        """Get all user boards"""
        try:
            response = requests.get(
                f"{PINTEREST_API_BASE}/boards",
                headers=self.headers,
                params={
                    "fields": "id,name,description,image,privacy"
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            return data.get("items", [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching boards: {e}")
            raise
    
    def get_board_pins(self, board_id: str, limit: int = 20) -> List[Dict]:
        """Get pins from a specific board"""
        try:
            response = requests.get(
                f"{PINTEREST_API_BASE}/boards/{board_id}/pins",
                headers=self.headers,
                params={
                    "limit": limit,
                    "fields": "id,created_at,description,image,media,link"
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            return data.get("items", [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching pins from board {board_id}: {e}")
            raise


class PinterestPersonaService:
    """Integrates Pinterest data with user persona"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def sync_user_pinterest_data(self, user_id: str, access_token: str) -> Dict:
        """
        Sync all Pinterest data for user:
        1. Fetch boards
        2. Fetch pins from each board
        3. Extract style features from pins
        4. Update user persona in ZEP
        """
        try:
            api_service = PinterestAPIService(access_token)
            
            # Get user info
            user_account = api_service.get_user_account()
            logger.info(f"Fetched user account: {user_account.get('username')}")
            
            # Get all boards
            boards = api_service.get_boards()
            logger.info(f"Fetched {len(boards)} boards for user {user_id}")
            
            all_pins_data = []
            style_insights = {
                "boards": [],
                "pins": [],
                "colors": [],
                "styles": [],
                "themes": []
            }
            
            # Process each board
            for board in boards:
                board_id = board.get("id")
                board_name = board.get("name")
                board_desc = board.get("description", "")
                
                logger.info(f"Processing board: {board_name}")
                
                # Get pins from this board
                pins = api_service.get_board_pins(board_id, limit=20)
                logger.info(f"Found {len(pins)} pins in board {board_name}")
                
                board_data = {
                    "id": board_id,
                    "name": board_name,
                    "description": board_desc,
                    "pin_count": len(pins),
                    "pins": []
                }
                
                # Extract features from each pin
                for pin in pins:
                    pin_data = self._extract_pin_features(pin)
                    all_pins_data.append(pin_data)
                    board_data["pins"].append(pin_data)
                    
                    # Collect style insights
                    if pin_data.get("description"):
                        style_insights["pins"].append(pin_data["description"])
                    if pin_data.get("colors"):
                        style_insights["colors"].extend(pin_data["colors"])
                    if pin_data.get("style_tags"):
                        style_insights["styles"].extend(pin_data["style_tags"])
                
                style_insights["boards"].append({
                    "name": board_name,
                    "description": board_desc
                })
            
            # Update user persona in ZEP with collected insights
            update_user_persona_with_pins(
                user_id=user_id,
                pinterest_boards=style_insights["boards"],
                pins_data=all_pins_data,
                colors=style_insights["colors"],
                styles=style_insights["styles"]
            )
            
            # Update sync timestamp
            pinterest_token = self.db.query(PinterestToken).filter(
                PinterestToken.user_id == user_id
            ).first()
            
            if pinterest_token:
                pinterest_token.synced_at = datetime.utcnow()
                self.db.add(pinterest_token)
                self.db.commit()
            
            logger.info(f"Successfully synced Pinterest data for user {user_id}")
            
            return {
                "success": True,
                "boards_count": len(boards),
                "pins_count": len(all_pins_data),
                "user_account": user_account
            }
        
        except Exception as e:
            logger.error(f"Error syncing Pinterest data: {e}")
            raise
    
    def _extract_pin_features(self, pin: Dict) -> Dict:
        """Extract style features from a single pin"""
        pin_data = {
            "id": pin.get("id"),
            "description": pin.get("description", ""),
            "link": pin.get("link", ""),
            "created_at": pin.get("created_at"),
            "colors": [],
            "style_tags": [],
            "image_url": None
        }
        
        # Extract image URL
        image_data = pin.get("image", {})
        if isinstance(image_data, dict):
            pin_data["image_url"] = image_data.get("1200x", {}).get("url")
        
        # Parse description for style tags
        if pin_data["description"]:
            # Simple extraction of common style keywords
            description_lower = pin_data["description"].lower()
            style_keywords = [
                "casual", "formal", "elegant", "sporty", "bohemian",
                "minimalist", "vintage", "modern", "classic", "trendy",
                "comfortable", "chic", "edgy", "romantic", "professional"
            ]
            
            for keyword in style_keywords:
                if keyword in description_lower:
                    pin_data["style_tags"].append(keyword)
        
        # Vision analysis for color palette (if image available)
        if pin_data["image_url"]:
            try:
                # Vision analyzer to extract colors and style
                vision_results = analyze_image(pin_data["image_url"])
                
                if vision_results:
                    pin_data["colors"] = vision_results.get("colors", [])
                    pin_data["style_tags"].extend(
                        vision_results.get("style_elements", [])
                    )
            except Exception as e:
                logger.warning(f"Could not analyze image for pin {pin.get('id')}: {e}")
        
        return pin_data
