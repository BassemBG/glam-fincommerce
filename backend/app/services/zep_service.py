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



def create_zep_thread(user_id: str):
    """
    Create a thread in Zep Cloud for a user.
    
    Args:
        user_id: Unique identifier for the user
    
    Returns:
        str: The thread ID, or None if creation failed
    """
    logger.info(f"[Zep] Attempting to create thread for user: {user_id}")
    
    if not zep_client:
        logger.error("✗ [Zep] Zep client not initialized. Cannot create thread.")
        return None
    
    try:
        import uuid
        thread_id = f"thread_{user_id}_{uuid.uuid4().hex[:8]}"
        
        logger.info(f"[Zep] Calling zep_client.thread.create() with thread_id={thread_id}")
        thread = zep_client.thread.create(
            thread_id=thread_id,
            user_id=str(user_id)
        )
        logger.info(f"✓ [Zep] Thread created successfully: {thread}")
        return thread_id
    except Exception as e:
        logger.error(f"✗ [Zep] Failed to create thread for user {user_id}: {e}", exc_info=True)
        return None


def add_onboarding_to_thread(user_id: str, thread_id: str, onboarding_data: dict):
    """
    Add onboarding data to a user's thread in Zep Cloud.
    
    Args:
        user_id: User identifier
        thread_id: Thread ID where messages will be added
        onboarding_data: Dictionary containing onboarding form data
    
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"[Zep] Adding onboarding data to thread {thread_id} for user {user_id}")
    
    if not zep_client:
        logger.error("✗ [Zep] Zep client not initialized. Cannot add messages.")
        return False


def add_onboarding_to_graph(user_id: str, onboarding_data: dict):
    """Add onboarding data as graph data in Zep for the user graph."""
    logger.info(f"[Zep] Adding onboarding data to graph for user {user_id}")

    if not zep_client:
        logger.error("✗ [Zep] Zep client not initialized. Cannot add graph data.")
        return False

    try:
        import json

        payload = {
            "age": onboarding_data.get("age"),
            "education": onboarding_data.get("education"),
            "daily_style": onboarding_data.get("daily_style"),
            "color_preferences": onboarding_data.get("color_preferences"),
            "fit_preference": onboarding_data.get("fit_preference"),
            "price_comfort": onboarding_data.get("price_comfort"),
            "buying_priorities": onboarding_data.get("buying_priorities"),
            "clothing_description": onboarding_data.get("clothing_description"),
            "styled_combinations": onboarding_data.get("styled_combinations"),
        }

        # Remove empty fields to keep graph clean
        payload = {k: v for k, v in payload.items() if v not in (None, [], "")}

        if not payload:
            logger.warning(f"[Zep] No onboarding payload to add to graph for user {user_id}")
            return True

        logger.info(f"[Zep] Calling graph.add for user {user_id} with payload: {payload}")
        result = zep_client.graph.add(
            user_id=str(user_id),
            data=json.dumps(payload),
            type="json",
            source_description="onboarding_profile"
        )
        logger.info(f"✓ [Zep] Onboarding data added to graph successfully! Episode UUID: {getattr(result, 'uuid', 'N/A')}")
        return True
    except Exception as e:
        logger.error(f"✗ [Zep] Failed to add onboarding data to graph for user {user_id}: {e}", exc_info=True)
        return False
    
    try:
        from zep_cloud import Message
        
        # Create messages from onboarding data
        messages = []
        
        # Profile info message
        if onboarding_data.get("age") or onboarding_data.get("education"):
            profile_msg = "Profile: "
            if onboarding_data.get("age"):
                profile_msg += f"Age {onboarding_data['age']}, "
            if onboarding_data.get("education"):
                profile_msg += f"Studies at {onboarding_data['education']}"
            messages.append(Message(
                content=profile_msg.strip(),
                role="user"
            ))
        
        # Daily style message
        if onboarding_data.get("daily_style"):
            messages.append(Message(
                content=f"My daily style preference: {onboarding_data['daily_style']}",
                role="user"
            ))
        
        # Color preferences message
        if onboarding_data.get("color_preferences"):
            colors = ", ".join(onboarding_data["color_preferences"])
            messages.append(Message(
                content=f"Colors I feel good in: {colors}",
                role="user"
            ))
        
        # Fit preference message
        if onboarding_data.get("fit_preference"):
            messages.append(Message(
                content=f"My fit preference: {onboarding_data['fit_preference']}",
                role="user"
            ))
        
        # Price comfort message
        if onboarding_data.get("price_comfort"):
            messages.append(Message(
                content=f"Price comfort zone: {onboarding_data['price_comfort']}",
                role="user"
            ))
        
        # Buying priorities message
        if onboarding_data.get("buying_priorities"):
            priorities = ", ".join(onboarding_data["buying_priorities"])
            messages.append(Message(
                content=f"Buying priorities: {priorities}",
                role="user"
            ))
        
        # Clothing description message
        if onboarding_data.get("clothing_description"):
            messages.append(Message(
                content=f"My wardrobe: {onboarding_data['clothing_description']}",
                role="user"
            ))
        
        # Styled combinations message
        if onboarding_data.get("styled_combinations"):
            messages.append(Message(
                content=f"My favorite combinations: {onboarding_data['styled_combinations']}",
                role="user"
            ))
        
        if not messages:
            logger.warning(f"[Zep] No onboarding data to add to thread {thread_id}")
            return True
        
        logger.info(f"[Zep] Adding {len(messages)} messages to thread {thread_id}")
        zep_client.thread.add_messages_batch(
            thread_id=thread_id,
            messages=messages
        )
        logger.info(f"✓ [Zep] Successfully added {len(messages)} messages to thread {thread_id}")
        return True
    except Exception as e:
        logger.error(f"✗ [Zep] Failed to add messages to thread {thread_id}: {e}", exc_info=True)
        return False


def create_zep_user(user_id: str, email: str, full_name: str = None):
    """
    Create a user in Zep Cloud and also create a thread for them.
    
    Args:
        user_id: Unique identifier for the user (from database)
        email: User's email address
        full_name: User's full name (will be split into first/last name)
    
    Returns:
        tuple: (zep_user, thread_id) or (None, None) if creation failed
    """
    logger.info(f"[Zep] Attempting to create user: user_id={user_id}, email={email}, full_name={full_name}")
    
    if not zep_client:
        logger.error("✗ [Zep] Zep client not initialized. Cannot create user.")
        return None, None
    
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
        
        # Create thread for the user
        thread_id = create_zep_thread(user_id)
        
        return zep_user, thread_id
    except Exception as e:
        logger.error(f"✗ [Zep] Failed to create Zep user {user_id}: {e}", exc_info=True)
        # Don't raise - allow signup to continue even if Zep fails
        return None, None
