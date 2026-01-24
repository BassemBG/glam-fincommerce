"""
Zep Cloud integration service for user profiling.
Handles user creation and management in Zep.

GRAPH MODEL:
- Node: User (identified by user_id)
- Node: Pin (identified by pin_id, created as JSON episodes)
- Episode: JSON attributes attached to Pin nodes (color, style_keywords, image_url, etc.)
- Relationship: User --[SAVED_PIN]--> Pin (explicit fact triple)
- Source: onboarding_profile, Pinterest

ARCHITECTURE:
- Zep Thread: Conversational memory (natural language messages for stylist chat)
- Zep Graph: Long-term persona (structured facts about preferences, pins, style)
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
    from zep_cloud.types import Message
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
    print(f"\n=== CREATE_ZEP_THREAD CALLED === user_id={user_id}")
    print(f"zep_client is: {zep_client}")
    logger.info(f"[Zep] ****CREATE_ZEP_THREAD**** ENTRY user_id={user_id}")
    logger.info(f"[Zep] ****ZEP_CLIENT_STATE**** {zep_client}")
    
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


def add_onboarding_to_graph(user_id: str, onboarding_data: dict, user_email: str = None, thread_id: str = None):
    """Add onboarding data as messages to the user's thread. Zep will automatically ingest into graph."""
    print(f"\n=== ADD_ONBOARDING_TO_GRAPH CALLED === user_id={user_id}, thread_id={thread_id}")
    print(f"zep_client is: {zep_client}")
    logger.info(f"[Zep] ****ADD_ONBOARDING_TO_GRAPH**** ENTRY user_id={user_id}, thread={thread_id}")
    logger.info(f"[Zep] ****ZEP_CLIENT_STATE**** {zep_client}")

    if not zep_client:
        logger.error("✗ [Zep] Zep client is None! ZEP_API_KEY not set or import failed.")
        return False

    if not thread_id:
        logger.error("✗ [Zep] ****ERROR**** thread_id is required for add_onboarding_to_graph")
        return False

    try:
        import json

        payload = {
            "user_id": str(user_id),
            "user_email": user_email,
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

        # Remove empty fields to keep messages clean
        payload = {k: v for k, v in payload.items() if v not in (None, [], "")}

        if not payload:
            logger.warning(f"[Zep] ****WARNING**** No onboarding payload to add for user {user_id}")
            return True

        payload_json = json.dumps(payload)
        logger.info(f"[Zep] ****PAYLOAD**** {payload_json}")

        # Create message for onboarding data
        message = Message(
            name=f"User {user_id}",
            role="user",
            content=f"Onboarding profile completed: {payload_json}",
            metadata={
                "source": "onboarding_profile",
                "user_id": str(user_id),
                "user_email": user_email,
            },
        )

        logger.info(f"[Zep] ****SENDING_MESSAGE**** to thread {thread_id}")
        response = zep_client.thread.add_messages(
            thread_id=thread_id,
            messages=[message],
        )

        logger.info(f"[Zep] ****SUCCESS**** Onboarding message added to thread {thread_id}")
        logger.info(f"[Zep] ****RESPONSE**** {response}")
        return True

    except Exception as e:
        logger.error(f"✗ [Zep] ****EXCEPTION**** in add_onboarding_to_graph: {type(e).__name__}: {e}", exc_info=True)
        import traceback
        logger.error(f"[Zep] Full traceback:\n{traceback.format_exc()}")
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
    print(f"\n=== CREATE_ZEP_USER CALLED === user_id={user_id}, email={email}, full_name={full_name}")
    print(f"zep_client is: {zep_client}")
    logger.info(f"[Zep] ****CREATE_ZEP_USER**** ENTRY user_id={user_id}, email={email}, full_name={full_name}")
    logger.info(f"[Zep] ****ZEP_CLIENT_STATE**** {zep_client}")
    
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
        logger.info(f"[Zep] Calling zep_client.user.add() with user_id={user_id}")
        zep_user = zep_client.user.add(
            user_id=str(user_id),
            email=email,
            first_name=first_name,
            last_name=last_name,
            metadata={"created_from": "virtual_closet"}
        )
        logger.info(f"✓ [Zep] User created successfully in Zep!")
        logger.info(f"[Zep] User ID: {user_id}")
        logger.info(f"[Zep] Email: {email}")
        logger.info(f"[Zep] Name: {first_name} {last_name}")
        logger.info(f"[Zep] User object: {zep_user}")
        
        # Create thread for the user
        thread_id = create_zep_thread(user_id)
        
        return zep_user, thread_id
    except Exception as e:
        logger.error(f"✗ [Zep] Failed to create Zep user {user_id}: {e}", exc_info=True)
        # Don't raise - allow signup to continue even if Zep fails
        return None, None


def add_pin_to_user_graph(user_id: str, pin: dict, thread_id: str = None):
    """
    Add a single Pinterest pin as a message to the user's thread.
    Zep will automatically ingest into the user graph.
    
    Args:
        user_id: User ID
        pin: Dictionary containing pin data
        thread_id: Thread ID for the user
    
    Returns:
        True if successful, None otherwise
    """
    logger.info(f"[Zep] ****ADD_PIN_TO_USER**** called for user {user_id}, pin={pin.get('id')}, thread={thread_id}")

    if not zep_client:
        logger.warning("✗ [Zep] Zep client not initialized. Cannot add pin to graph.")
        return None

    if not thread_id:
        logger.error("✗ [Zep] ****ERROR**** thread_id is required for add_pin_to_user_graph")
        return None
    
    try:
        import json
        
        # Prepare pin JSON structure for message
        pin_json = {
            "pin_id": pin.get("id"),
            "type": pin.get("type", "unknown"),
            "color": pin.get("colors", []),
            "pattern": pin.get("pattern", []),
            "style_keywords": pin.get("style_tags", []),
            "board": pin.get("board_name", ""),
            "image_url": pin.get("image_url", ""),
            "description": pin.get("description", ""),
            "link": pin.get("link", ""),
            "source": "Pinterest",
            "timestamp": pin.get("created_at") or pin.get("timestamp", ""),
        }
        
        pin_json_str = json.dumps(pin_json)
        logger.info(f"[Zep] ****PAYLOAD**** {pin_json_str}")
        
        message = Message(
            name=f"User {user_id}",
            role="user",
            content=f"Saved Pinterest pin: {pin_json_str}",
            metadata={
                "source": "Pinterest",
                "pin_id": pin.get("id"),
                "user_id": str(user_id),
            },
        )

        logger.info(f"[Zep] ****SENDING_MESSAGE**** to thread {thread_id}")
        response = zep_client.thread.add_messages(
            thread_id=thread_id,
            messages=[message],
        )
        
        logger.info(f"[Zep] ****SUCCESS**** Pin message added to thread {thread_id}")
        logger.info(f"[Zep] ****RESPONSE**** {response}")
        return True
        
    except Exception as e:
        logger.error(f"✗ [Zep] ****EXCEPTION**** Failed to add pin {pin.get('id')} to graph for user {user_id}: {e}", exc_info=True)
        return None


def link_pin_to_user(user_id: str, pin_id: str, thread_id: str = None):
    """
    Deprecated: Pins are now added as messages to the thread, not as separate nodes.
    Zep will automatically relate them to the user graph from the messages.
    
    This function is kept for backward compatibility but does not create fact triples.
    
    Args:
        user_id: User ID
        pin_id: Pinterest pin ID
        thread_id: Thread ID (not used with message approach)
    
    Returns:
        None
    """
    logger.info(f"[Zep] ****LINK_PIN_TO_USER**** deprecated - pins added as messages instead (user={user_id}, pin={pin_id})")
    return None


def update_user_persona_with_pins(user_id: str, pinterest_boards: list, pins_data: list, colors: list = None, styles: list = None):
    """
    Update user persona in Zep with Pinterest data.
    Stores each pin as a JSON episode in the user's graph with attributes:
    - pin_id, type, color, pattern, style_keywords, board, image_url, source, timestamp
    
    Args:
        user_id: User ID
        pinterest_boards: List of board dictionaries with name and description
        pins_data: List of pin data dictionaries
        colors: List of color preferences extracted from pins
        styles: List of style tags extracted from pins
    """
    if not zep_client:
        logger.error("✗ [Zep] Zep client not initialized. Cannot update persona.")
        return False
    
    try:
        logger.info(f"[Zep] Updating persona for user {user_id} with {len(pins_data)} Pinterest pins")
        
        # Add each pin as a JSON episode to the user graph
        # Deprecated: pin nodes and SAVED_PIN relationships
        # This function remains for backward-compatibility logging only.
        logger.info(f"[Zep] Pins received for persona update: {len(pins_data)} (pin nodes not created)")
        
        # Log summary
        if styles:
            unique_styles = list(set(styles))
            logger.info(f"[Zep] Style insights: {', '.join(unique_styles[:10])}")
        
        if colors:
            unique_colors = list(set(colors))
            logger.info(f"[Zep] Color palette: {', '.join(unique_colors[:10])}")
        
        logger.info(f"[Zep] Boards: {len(pinterest_boards)} | Total pins processed: {len(pins_data)}")
        
        return True
    
    except Exception as e:
        logger.error(f"✗ [Zep] Failed to update persona with Pinterest data: {e}", exc_info=True)
        return False


def add_outfit_summary_to_graph(user_id: str, summary: dict, image_url: str = None, timestamp: str = None, user_email: str = None, thread_id: str = None):
    """
    Store a single outfit summary as a message to the user's thread.

    Design intent:
    - Messages are the source of truth for persona memory. Zep ingests them automatically into the per-user graph.
    - We intentionally avoid manual graph writes here (no nodes/edges created) to keep persona updates simple and safe.
    - When we need structured, queryable entities (e.g., outfit similarity, analytics), we can add explicit graph logic later.
    """
    print(f"\n=== ADD_OUTFIT_SUMMARY_TO_GRAPH CALLED === user_id={user_id}, thread_id={thread_id}")
    print(f"zep_client is: {zep_client}")
    logger.info(f"[Zep] ****ADD_OUTFIT_SUMMARY**** ENTRY user_id={user_id}, thread={thread_id}")
    logger.info(f"[Zep] ****ZEP_CLIENT_STATE**** {zep_client}")

    if not zep_client:
        logger.error("✗ [Zep] Zep client not initialized. Cannot add outfit summary.")
        return None

    if not thread_id:
        logger.error("✗ [Zep] ****ERROR**** thread_id is required for add_outfit_summary_to_graph")
        return None

    try:
        import json
        # Compact natural-language content so the thread stays human-readable.
        nl_summary = summary.get("summary") or "Outfit summary not provided"
        items = ", ".join(summary.get("items", [])) or "items not specified"
        colors = ", ".join(summary.get("colors", [])) or "colors not specified"
        styles = ", ".join(summary.get("style_keywords", [])) or "style not specified"
        fit = summary.get("fit") or "fit not specified"
        occasion = summary.get("occasion") or "occasion not specified"

        content = (
            f"Outfit observed from Pinterest. "
            f"Summary: {nl_summary}. Items: {items}. Colors: {colors}. "
            f"Style: {styles}. Fit: {fit}. Occasion: {occasion}. "
            f"Image URL: {image_url or 'n/a'}. Timestamp: {timestamp or 'n/a'}."
        )

        # Minimal JSON payload kept in metadata for future machine use; Zep will ingest message text into graph.
        payload = {
            "user_id": str(user_id),
            "user_email": user_email,
            "image_url": image_url,
            "summary": summary.get("summary"),
            "items": summary.get("items", []),
            "colors": summary.get("colors", []),
            "style_keywords": summary.get("style_keywords", []),
            "fit": summary.get("fit"),
            "occasion": summary.get("occasion"),
            "source": "pinterest",
            "timestamp": timestamp,
        }
        data_str = json.dumps(payload)
        logger.info(f"[Zep] ****PAYLOAD**** {data_str}")

        message = Message(
            name=f"User {user_id}",
            role="user",
            content=content,
            metadata={
                "source": "pinterest_outfit_summary",
                "user_id": str(user_id),
                "user_email": user_email,
            },
        )

        logger.info(f"[Zep] ****SENDING_MESSAGE**** to thread {thread_id}")
        response = zep_client.thread.add_messages(
            thread_id=thread_id,
            messages=[message],
        )

        logger.info(f"[Zep] ****SUCCESS**** Outfit summary message added to thread {thread_id}")
        logger.info(f"[Zep] ****RESPONSE**** {response}")
        return True
    except Exception as e:
        logger.error(f"✗ [Zep] ****EXCEPTION**** Failed to add outfit summary for user {user_id}: {e}", exc_info=True)
        return None


def update_user_persona_with_outfit_summaries(user_id: str, summaries: list, pinterest_boards: list = None, colors: list = None, styles: list = None, user_email: str = None, thread_id: str = None):
    """
    Store outfit summaries as messages to the user's thread.

    Design intent:
    - Persona memory is driven by messages; Zep ingests them automatically into the per-user graph.
    - No manual graph entities or edges are created here to avoid duplicating message content.
    - Future: add explicit graph entities only if we need structured queries (similarity, analytics).
    """
    print(f"\n=== UPDATE_USER_PERSONA_WITH_OUTFIT_SUMMARIES CALLED === user_id={user_id}, {len(summaries)} summaries, thread_id={thread_id}")
    print(f"zep_client is: {zep_client}")
    logger.info(f"[Zep] ****UPDATE_PERSONA**** ENTRY user_id={user_id}, {len(summaries)} summaries, thread={thread_id}")
    logger.info(f"[Zep] ****ZEP_CLIENT_STATE**** {zep_client}")

    if not zep_client:
        logger.error("✗ [Zep] Zep client not initialized. Cannot update persona.")
        return False

    if not thread_id:
        logger.error("✗ [Zep] ****ERROR**** thread_id is required for update_user_persona_with_outfit_summaries")
        return False

    try:
        added = 0
        for s in summaries:
            result = add_outfit_summary_to_graph(
                user_id=user_id,
                summary=s.get("summary_data", {}),
                image_url=s.get("image_url"),
                timestamp=s.get("timestamp"),
                user_email=user_email,
                thread_id=thread_id,
            )
            if result:
                added += 1

        logger.info(f"[Zep] ****SUCCESS**** Added {added}/{len(summaries)} outfit summaries for user {user_id}")
        if styles:
            logger.info(f"[Zep] ****STYLES**** {', '.join(list(set(styles))[:10])}")
        if colors:
            logger.info(f"[Zep] ****COLORS**** {', '.join(list(set(colors))[:10])}")
        return True
    except Exception as e:
        logger.error(f"✗ [Zep] ****EXCEPTION**** Failed to store outfit summaries: {e}", exc_info=True)
        return False

# TODO (graph schema, future work - do NOT implement yet):
# - Outfit entity with attributes (items, colors, styles, fit, occasion, source, image_url, timestamp)
# - SAVED_OUTFIT relationship from User -> Outfit
# - HAS_COLOR, HAS_STYLE edges for analytics and similarity
# - Optional embeddings for outfit similarity search
