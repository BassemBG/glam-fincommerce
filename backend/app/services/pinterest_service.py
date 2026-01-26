import requests
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from urllib.parse import urlencode
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.models import User, PinterestToken
from app.services.storage import storage_service

logger = logging.getLogger(__name__)

PINTEREST_API_BASE = "https://api.pinterest.com/v5"
# Authorize endpoint must use the public host (www), not the API host
PINTEREST_OAUTH_URL = "https://www.pinterest.com/oauth"

# Import optional services - they might fail if not configured
try:
    from app.services.zep_service import update_user_persona_with_outfit_summaries
except ImportError as e:
    logger.warning(f"Could not import update_user_persona_with_pins: {e}")
    def update_user_persona_with_outfit_summaries(*args, **kwargs):
        logger.info("ZEP service not available, skipping persona update")
        return False

try:
    from app.services.outfit_filter import filter_pinterest_pins, summarize_outfit
except ImportError as e:
    logger.warning(f"Could not import outfit_filter: {e}")
    def filter_pinterest_pins(pins, descriptions=None):
        logger.info("[Filter] Outfit filter not available, using all pins")
        return {"accepted": pins, "rejected": [], "failed": [], "stats": {"total": len(pins), "accepted": len(pins)}}
    def summarize_outfit(*args, **kwargs):
        return None

try:
    from app.services.vision_analyzer import analyze_image
except ImportError:
    def analyze_image(*args, **kwargs):
        return None

try:
    from app.services.embedding_service import get_embedding
except ImportError:
    def get_embedding(*args, **kwargs):
        return None

try:
    from app.services.embedding_service import embedding_service
except ImportError:
    embedding_service = None

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
                    "fields": "id,created_at,description,image[original,1200x,400x,236x],media,link"
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            items = data.get("items", [])
            
            # Log first pin structure for debugging
            if items:
                logger.info(f"[API Response] First pin structure: {items[0]}")
            
            return items
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching pins from board {board_id}: {e}")
            raise


class PinterestPersonaService:
    """Integrates Pinterest data with user persona"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def sync_user_pinterest_data(self, user_id: str, access_token: str) -> Dict:
        """
        Sync all Pinterest data for user:
        1. Fetch boards
        2. Fetch pins from each board
        3. Extract style features from pins
        4. Update user persona in ZEP
        """
        logger.info(f"[Pinterest Sync] ****STARTING_SYNC**** for user {user_id}")
        logger.info(f"[Pinterest Sync] Access token length: {len(access_token) if access_token else 0}")
        
        # Fetch user email and thread from database for Zep integration
        from app.models.models import User
        user = self.db.query(User).filter(User.id == user_id).first()
        user_email = user.email if user else None
        logger.info(f"[Pinterest Sync] ****USER_EMAIL**** {user_email}")
        
        # Reuse existing thread if present; create only if missing
        from app.services.zep_service import create_zep_thread
        thread_id = getattr(user, "zep_thread_id", None)
        if thread_id:
            logger.info(f"[Pinterest Sync] ****THREAD_ID_REUSE**** {thread_id}")
        else:
            thread_id = create_zep_thread(str(user_id))
            logger.info(f"[Pinterest Sync] ****THREAD_ID_CREATED**** {thread_id}")
            if thread_id:
                user.zep_thread_id = thread_id
                self.db.add(user)
                self.db.commit()
                self.db.refresh(user)
                logger.info(f"[Pinterest Sync] ****THREAD_ID_SAVED**** {thread_id}")

        if not thread_id:
            logger.error(f"[Pinterest Sync] ****ERROR**** Failed to obtain thread for user {user_id}")
            return {
                "success": False,
                "error": "Failed to obtain Zep thread",
                "user_id": user_id
            }
        
        try:
            logger.info(f"[Pinterest Sync] Creating PinterestAPIService")
            api_service = PinterestAPIService(access_token)
            
            # Get user info
            logger.info(f"[Pinterest Sync] Calling get_user_account()")
            user_account = api_service.get_user_account()
            logger.info(f"[Pinterest Sync] ****FETCHED_USER**** {user_account.get('username')}")
            logger.info(f"[Pinterest Sync] User account data: {user_account}")
            
            # Get all boards
            boards = api_service.get_boards()
            logger.info(f"[Pinterest Sync] ****BOARDS_FOUND**** {len(boards)} boards for user {user_id}")
            if boards:
                for b in boards:
                    logger.info(
                        "Board => id=%s | name=%s | desc=%s",
                        b.get("id"), b.get("name"), (b.get("description") or "").strip()
                    )
            
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
                
                logger.info(f"[Pinterest Sync] ****PROCESSING_BOARD**** {board_name}")
                
                # Get pins from this board
                pins = api_service.get_board_pins(board_id, limit=20)
                logger.info(f"[Pinterest Sync] ****PINS_IN_BOARD**** {len(pins)} pins in board {board_name}")
                
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
                    # Add board name to pin data for graph storage
                    pin_data["board_name"] = board_name
                    all_pins_data.append(pin_data)
                    board_data["pins"].append(pin_data)

                    # Verbose logging of retrieved pin data for debugging
                    logger.info(
                        "Pin => board=%s | id=%s | created_at=%s | img=%s | desc=%s | link=%s | styles=%s | colors=%s",
                        board_name,
                        pin_data.get("id"),
                        pin_data.get("created_at"),
                        pin_data.get("image_url"),
                        (pin_data.get("description") or "").strip(),
                        pin_data.get("link"),
                        pin_data.get("style_tags"),
                        pin_data.get("colors"),
                    )
                    
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
            
            # EXPLICIT DECISION: Skip pins without images before filtering
            # Pins without images cannot be analyzed by vision model and are not useful for outfit styling
            pins_with_images = [pin for pin in all_pins_data if pin.get("image_url")]
            pins_without_images = [pin for pin in all_pins_data if not pin.get("image_url")]
            
            logger.info(f"[Pinterest Sync] ****PIN_STATS**** Total: {len(all_pins_data)} | With images: {len(pins_with_images)} | Skipped (no image): {len(pins_without_images)}")
            
            if pins_without_images:
                logger.warning(f"[Pinterest Sync] Skipping {len(pins_without_images)} pins without images: {[p.get('id') for p in pins_without_images]}")
            
            # FILTERING STEP: Filter pins with images to keep only outfit/fashion-related content
            print("="*80)
            print(f"🔍 [PINTEREST FILTER] Starting VLM filtering for {len(pins_with_images)} pins")
            print("="*80)
            logger.info(f"[Pinterest Sync] ****FILTERING_PINS**** Starting outfit filtering for {len(pins_with_images)} pins with images")
            
            filter_result = filter_pinterest_pins(pins_with_images)
            filtered_pins = filter_result["accepted"]
            filter_stats = filter_result["stats"]
            
            print("="*80)
            print(f"✅ [FILTER COMPLETE] Accepted: {len(filtered_pins)} | Rejected: {filter_stats.get('rejected', 0)}")
            print(f"📊 Filter Stats: {filter_stats}")
            print("="*80)
            logger.info(f"[Pinterest Sync] ****FILTER_RESULTS**** {filter_stats}")
            
            if len(filtered_pins) == 0:
                print("⚠️  [WARNING] NO PINS PASSED FILTER - NOTHING WILL BE STORED OR INDEXED")
                logger.warning("[Pinterest Sync] No pins passed filter - skipping storage and indexing")
            
            # STEP 1: DOWNLOAD & STORE FILTERED PIN IMAGES
            # ================================================
            stored_pins = []
            print("\n" + "="*80)
            print(f"💾 [STORAGE] Downloading and storing {len(filtered_pins)} filtered pin images")
            print("="*80)
            logger.info(f"[Pinterest Sync] ****STORING_IMAGES**** Downloading and storing {len(filtered_pins)} filtered pin images")
            
            for pin in filtered_pins:
                pin_id = pin.get("id")
                image_url = pin.get("image_url")
                
                if not image_url:
                    logger.warning(f"[Pinterest Sync] Skipping pin {pin_id}: no image URL")
                    continue
                
                try:
                    # Download image bytes from Pinterest
                    print(f"  📥 Downloading pin {pin_id}...")
                    logger.info(f"[Pinterest Sync] Downloading image for pin {pin_id}")
                    response = requests.get(image_url, timeout=10)
                    response.raise_for_status()
                    image_content = response.content
                    print(f"     ✓ Downloaded {len(image_content)} bytes")
                    
                    # Generate storage filename
                    file_name = f"pinterest_{pin_id}.jpg"
                    
                    # Upload via storage_service (S3 or local)
                    print(f"  ☁️  Uploading to storage...")
                    stored_url = await storage_service.upload_file(
                        image_content,
                        file_name,
                        "image/jpeg"
                    )
                    print(f"     ✓ Stored at: {stored_url}")
                    
                    # Prepare metadata for storage and indexing
                    metadata = {
                        "source": "pinterest",
                        "pin_id": pin_id,
                        "board_name": pin.get("board_name"),
                        "description": pin.get("description"),
                        "colors": pin.get("colors", []),
                        "style_tags": pin.get("style_tags", []),
                        "created_at": pin.get("created_at"),
                        "original_url": image_url,
                        "stored_url": stored_url
                    }
                    
                    stored_pins.append({
                        "pin_id": pin_id,
                        "stored_url": stored_url,
                        "metadata": metadata,
                        "colors": pin.get("colors", []),
                        "style_tags": pin.get("style_tags", []),
                        "board_name": pin.get("board_name")
                    })
                    
                    logger.info(f"[Pinterest Sync] ✓ Stored pin {pin_id} at {stored_url}")
                
                except Exception as e:
                    print(f"  ❌ FAILED to store pin {pin_id}: {e}")
                    logger.warning(f"[Pinterest Sync] ✗ Failed to store pin {pin_id}: {e}")
                    continue
            
            print("="*80)
            print(f"✅ [STORAGE COMPLETE] Successfully stored {len(stored_pins)}/{len(filtered_pins)} pin images")
            print("="*80)
            logger.info(f"[Pinterest Sync] ****STORED_IMAGES**** Successfully stored {len(stored_pins)} pin images")
            
            if len(stored_pins) == 0:
                print("⚠️  [WARNING] NO IMAGES STORED - NOTHING WILL BE INDEXED IN QDRANT")
                logger.warning("[Pinterest Sync] No images stored - skipping Qdrant indexing")
            
            # STEP 2: INDEX STORED PINS IN QDRANT (separate collection)
            # ========================================================
            print("\n" + "="*80)
            print(f"🔵 [QDRANT] Indexing {len(stored_pins)} pins in Qdrant collection 'pinterest_pins'")
            print(f"🔵 [QDRANT] URL: {settings.QDRANT_URL}")
            print(f"🔵 [QDRANT] API Key: {'✓ SET' if settings.QDRANT_API_KEY else '❌ MISSING'}")
            print("="*80)
            logger.info(f"[Pinterest Sync] ****INDEXING_QDRANT**** Indexing {len(stored_pins)} pins in Qdrant collection 'pinterest_pins'")
            
            try:
                from qdrant_client import QdrantClient
                from qdrant_client.models import VectorParams, Distance, PointStruct
                import uuid as uuid_module
                
                # Initialize Qdrant client with API key
                print("  🔌 Connecting to Qdrant...")
                qdrant_client = QdrantClient(
                    url=settings.QDRANT_URL,
                    api_key=settings.QDRANT_API_KEY
                )
                print("     ✓ Connected to Qdrant")
                
                # Ensure collection exists
                print("  📦 Checking collection 'pinterest_pins'...")
                collection_exists = False
                vector_size_correct = False
                
                try:
                    collection_info = qdrant_client.get_collection("pinterest_pins")
                    collection_exists = True
                    
                    # Get vector size - try different attribute paths
                    try:
                        vector_size = collection_info.config.params.vectors.size
                    except:
                        try:
                            vector_size = collection_info.config.vectors.size
                        except:
                            vector_size = 768  # Default to wrong size if we can't read
                    
                    print(f"     ✓ Collection exists | Points count: {collection_info.points_count} | Vector size: {vector_size}")
                    
                    # Check if vector size is correct (should be 384 for Gemini embeddings)
                    if vector_size == 384:
                        vector_size_correct = True
                        logger.info("[Pinterest Sync] Collection 'pinterest_pins' exists with correct vector size")
                    else:
                        print(f"     ⚠️  Vector size mismatch! Expected 384-dim, got {vector_size}-dim")
                except Exception as e:
                    collection_exists = False
                    print(f"     ℹ️  Collection not found")
                
                # Delete and recreate if needed
                if collection_exists and not vector_size_correct:
                    print("     🗑️  Deleting old collection...")
                    try:
                        qdrant_client.delete_collection("pinterest_pins")
                        print("     ✓ Old collection deleted")
                    except Exception as e:
                        print(f"     ⚠️  Error deleting collection: {str(e)}")
                
                # Create collection if it doesn't exist or was deleted
                if not collection_exists or not vector_size_correct:
                    print(f"     📝 Creating collection with 384-dim vectors...")
                    try:
                        qdrant_client.create_collection(
                            collection_name="pinterest_pins",
                            vectors_config=VectorParams(size=384, distance=Distance.COSINE)
                        )
                        print("     ✓ Collection 'pinterest_pins' created with 384-dim vectors")
                        logger.info("[Pinterest Sync] Created collection 'pinterest_pins' with 384-dim vectors")
                    except Exception as e:
                        print(f"     ⚠️  Error creating collection: {str(e)}")
                        logger.error(f"[Pinterest Sync] Error creating collection: {str(e)}")
                
                indexed_count = 0
                print(f"\n  📝 Indexing {len(stored_pins)} pins...")
                for idx, stored_pin in enumerate(stored_pins, 1):
                    pin_id = stored_pin["pin_id"]
                    print(f"\n  [{idx}/{len(stored_pins)}] Processing pin {pin_id}")
                    try:
                        # Generate embedding for pin metadata
                        metadata_text = f"{stored_pin['metadata'].get('description', '')} {' '.join(stored_pin.get('style_tags', []))}"
                        print(f"     🧠 Generating embedding (text: {len(metadata_text)} chars)...")
                        
                        # Get embedding
                        embedding = await embedding_service.get_text_embedding(metadata_text)
                        print(f"     ✓ Embedding generated (dim: {len(embedding) if embedding else 0})")
                        
                        # Prepare Qdrant point
                        point_id = str(uuid_module.uuid4())
                        payload = {
                            "type": "pinterest_pin",
                            "user_id": user_id,
                            "pin_id": pin_id,
                            "image_url": stored_pin["stored_url"],
                            "board_name": stored_pin.get("board_name"),
                            "colors": stored_pin.get("colors", []),
                            "style_tags": stored_pin.get("style_tags", []),
                            "description": stored_pin['metadata'].get('description'),
                            "created_at": stored_pin['metadata'].get('created_at'),
                            "metadata": stored_pin["metadata"]
                        }
                        print(f"     📤 Upserting to Qdrant (point_id: {point_id[:8]}...)")
                        
                        # Upsert to Qdrant (separate collection for Pinterest)
                        qdrant_client.upsert(
                            collection_name="pinterest_pins",
                            points=[
                                PointStruct(
                                    id=uuid_module.UUID(point_id).int % (2**63),  # Convert UUID to valid positive int ID
                                    vector=embedding,
                                    payload=payload
                                )
                            ]
                        )
                        print(f"     ✓ Upserted to Qdrant successfully")
                        
                        # Save to database
                        print(f"     💾 Saving to local database...")
                        from app.models.models import PinterestPin
                        pinterest_pin_record = PinterestPin(
                            user_id=user_id,
                            pin_id=pin_id,
                            board_name=stored_pin.get("board_name", ""),
                            description=stored_pin['metadata'].get('description'),
                            original_url=stored_pin['metadata'].get('original_url'),
                            stored_url=stored_pin["stored_url"],
                            colors=stored_pin.get("colors", []),
                            style_tags=stored_pin.get("style_tags", []),
                            qdrant_point_id=point_id,
                            qdrant_vector=embedding,
                            metadata_json=stored_pin["metadata"]
                        )
                        self.db.add(pinterest_pin_record)
                        print(f"     ✓ Saved to database")
                        
                        indexed_count += 1
                        print(f"  ✅ [{idx}/{len(stored_pins)}] Successfully indexed pin {pin_id}")
                        logger.info(f"[Pinterest Sync] ✓ Indexed pin {pin_id} in Qdrant (point_id={point_id})")
                    
                    except Exception as e:
                        print(f"  ❌ [{idx}/{len(stored_pins)}] FAILED to index pin {pin_id}: {str(e)}")
                        logger.warning(f"[Pinterest Sync] ✗ Failed to index pin {pin_id}: {e}", exc_info=True)
                        continue
                
                self.db.commit()
                print("\n" + "="*80)
                if indexed_count == len(stored_pins):
                    print(f"✅✅✅ [QDRANT SUCCESS] ALL {indexed_count} PINS INDEXED SUCCESSFULLY ✅✅✅")
                elif indexed_count > 0:
                    print(f"⚠️  [QDRANT PARTIAL] {indexed_count}/{len(stored_pins)} pins indexed (some failed)")
                else:
                    print(f"❌❌❌ [QDRANT FAILURE] NO PINS INDEXED - ALL FAILED ❌❌❌")
                print("="*80)
                logger.info(f"[Pinterest Sync] ****INDEXED_SUCCESS**** Indexed {indexed_count}/{len(stored_pins)} pins in Qdrant")
                
                # Verify by checking collection count
                try:
                    final_count = qdrant_client.get_collection("pinterest_pins")
                    print(f"🔵 [QDRANT VERIFY] Collection now has {final_count.points_count} total points")
                except Exception as verify_e:
                    print(f"⚠️  Could not verify collection count: {verify_e}")
            
            except Exception as e:
                print("\n" + "="*80)
                print(f"❌❌❌ [QDRANT ERROR] CRITICAL FAILURE - NO DATA INDEXED ❌❌❌")
                print(f"Error: {str(e)}")
                print("="*80)
                logger.error(f"[Pinterest Sync] ****QDRANT_ERROR**** Failed to index pins in Qdrant: {e}", exc_info=True)
            
            # STEP 3: SUMMARIZE OUTFITS & UPDATE ZEP PERSONA
            # ================================================
            # Summarize outfits from accepted pins (image-only analysis)
            outfit_summaries = []
            for pin in filtered_pins:
                img = pin.get("image_url")
                summary_data = summarize_outfit(img) if img else None
                if summary_data:
                    outfit_summaries.append({
                        "image_url": img,
                        "summary_data": summary_data,
                        "timestamp": pin.get("created_at") or pin.get("timestamp"),
                    })
            logger.info(f"[Pinterest Sync] ****OUTFIT_SUMMARIES**** Prepared {len(outfit_summaries)} outfit summaries for storage")
            
            # Deduplicate aggregated style insights to avoid noise
            unique_colors = list(set(style_insights["colors"]))
            unique_styles = list(set(style_insights["styles"]))
            
            logger.info(f"[Pinterest Sync] ****STYLE_INSIGHTS**** Colors: {len(unique_colors)} | Styles: {len(unique_styles)}")
            
            # ZEP GRAPH MODEL UPDATE:
            # - Store outfit summaries as messages to the user's thread
            # - Zep will automatically ingest into user graph
            # - No Pin nodes or SAVED_PIN relationships are created
            logger.info(f"[Pinterest Sync] ****CALLING_PERSONA_UPDATE**** with thread_id={thread_id}")
            update_user_persona_with_outfit_summaries(
                user_id=user_id,
                summaries=outfit_summaries,
                pinterest_boards=style_insights["boards"],
                colors=unique_colors,
                styles=unique_styles,
                user_email=user_email,
                thread_id=thread_id,
            )
            
            # Update sync timestamp
            pinterest_token = self.db.query(PinterestToken).filter(
                PinterestToken.user_id == user_id
            ).first()
            
            if pinterest_token:
                pinterest_token.synced_at = datetime.utcnow()
                self.db.add(pinterest_token)
                self.db.commit()
            
            logger.info(f"[Pinterest Sync] ****SYNC_COMPLETE**** Successfully synced Pinterest data for user {user_id}")
            logger.info(
                "Pinterest sync summary: boards=%s pins=%s user=%s",
                len(boards), len(all_pins_data), user_account.get("username")
            )
            
            return {
                "success": True,
                "boards_count": len(boards),
                "pins_count": len(all_pins_data),
                "user_account": user_account
            }
        
        except Exception as e:
            logger.error(f"[Pinterest Sync] ****EXCEPTION**** Error syncing Pinterest data: {e}", exc_info=True)
            logger.error(f"[Pinterest Sync] Exception type: {type(e).__name__}")
            logger.error(f"[Pinterest Sync] Exception args: {e.args}")
            raise
    
    def _extract_pin_features(self, pin: Dict) -> Dict:
        """Extract style features from a single pin"""
        
        # Log raw pin structure for debugging
        logger.debug(f"[PIN] Processing pin {pin.get('id')}")
        logger.debug(f"[PIN] Pin keys: {list(pin.keys())}")
        logger.debug(f"[PIN] Full pin data: {pin}")
        
        pin_data = {
            "id": pin.get("id"),
            "description": pin.get("description", ""),
            "link": pin.get("link", ""),
            "created_at": pin.get("created_at"),
            "colors": [],
            "style_tags": [],
            "image_url": None
        }
        
        # Extract image URL - try multiple possible structures
        image_data = pin.get("image", {})
        logger.debug(f"[PIN] image field type: {type(image_data)}")
        
        if isinstance(image_data, dict):
            # Try different size keys in order of preference
            for size_key in ["1200x", "original", "orig", "600x", "400x", "236x"]:
                if size_key in image_data and isinstance(image_data[size_key], dict):
                    pin_data["image_url"] = image_data[size_key].get("url")
                    if pin_data["image_url"]:
                        logger.info(f"[PIN] Found image URL for pin {pin.get('id')} using size {size_key}")
                        break
        
        # Also check for media field as fallback
        if not pin_data["image_url"] and pin.get("media"):
            media_data = pin.get("media", {})
            logger.debug(f"[PIN] Trying media field for pin {pin.get('id')}")
            if isinstance(media_data, dict) and media_data.get("images"):
                images = media_data["images"]
                if isinstance(images, dict):
                    for size_key in ["1200x", "orig", "600x"]:
                        if size_key in images and isinstance(images[size_key], dict):
                            pin_data["image_url"] = images[size_key].get("url")
                            if pin_data["image_url"]:
                                logger.info(f"[PIN] Found image URL from media.images.{size_key}")
                                break
        
        if not pin_data["image_url"]:
            logger.warning(f"[PIN] No image URL found for pin {pin.get('id')}")
        
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
