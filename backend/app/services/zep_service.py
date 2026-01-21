"""
Zep Cloud integration service for user profiling.
Handles user creation and management in Zep.
"""
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize Zep client
API_KEY = settings.ZEP_API_KEY
zep_client = None

logger.info(f"ZEP_API_KEY present: {bool(API_KEY)}")

try:
    from zep_cloud.client import Zep
    if API_KEY:
        try:
            zep_client = Zep(api_key=API_KEY)
            logger.info("✓ Zep client initialized successfully")
        except Exception as e:
            logger.error(f"✗ Failed to initialize Zep client: {e}", exc_info=True)
    else:
        logger.warning("✗ ZEP_API_KEY environment variable not set. Zep integration disabled.")
except ImportError as e:
    logger.error(f"✗ zep-cloud package not installed: {e}")



def create_zep_user(user_id: str, email: str, full_name: str = None):
    """
    Create a user in Zep Cloud.
    
    Args:
        user_id: Unique identifier for the user (from database)
        email: User's email address
        full_name: User's full name (will be split into first/last name)
    
    Returns:
        dict: The created Zep user object, or None if creation failed
    """
    logger.info(f"[Zep] Attempting to create user: user_id={user_id}, email={email}, full_name={full_name}")
    
    if not zep_client:
        logger.error("✗ [Zep] Zep client not initialized. Cannot create user.")
        return None
    
    try:
        # Parse full_name into first and last name
        first_name = None
        last_name = None
        if full_name:
            name_parts = full_name.strip().split(maxsplit=1)
            first_name = name_parts[0] if len(name_parts) > 0 else None
            last_name = name_parts[1] if len(name_parts) > 1 else None
        
        logger.info(f"[Zep] User details: first_name={first_name}, last_name={last_name}")
        
        # Create user in Zep
        logger.info(f"[Zep] Calling zep_client.user.add()...")
        zep_user = zep_client.user.add(
            user_id=str(user_id),
            email=email,
            first_name=first_name,
            last_name=last_name,
            metadata={"created_from": "virtual_closet"}
        )
        logger.info(f"✓ [Zep] User created successfully: {zep_user}")
        return zep_user
    except Exception as e:
        logger.error(f"✗ [Zep] Failed to create Zep user {user_id}: {e}", exc_info=True)
        # Don't raise - allow signup to continue even if Zep fails
        return None
