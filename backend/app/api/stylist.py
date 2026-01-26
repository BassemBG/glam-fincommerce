from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from app.db.session import get_db
from app.services.outfit_service import outfit_service
from app.agents.orchestrator import agent_orchestrator
from app.services.vision_analyzer import vision_analyzer
from app.services.clip_qdrant_service import clip_qdrant_service
from app.services.zep_service import add_outfit_summary_to_graph
from app.models.models import ClothingItem, User, Outfit
import uuid
import json

from app.api.user import get_current_user

router = APIRouter()

from fastapi.responses import StreamingResponse

@router.post("/chat")
async def chat_with_stylist(
    message: str = Form(...),
    history: Optional[str] = Form(None), 
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_id = current_user.id
    parsed_history = []
    if history:
        try: parsed_history = json.loads(history)
        except: parsed_history = []

    image_data = None
    if file:
        image_data = await file.read()

    async def sse_generator():
        async for event in agent_orchestrator.chat_stream(
            user_id=user_id,
            message=message,
            history=parsed_history,
            image_data=image_data
        ):
            yield f"data: {event}\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")


import json
import logging

@router.post("/outfits/save")
async def save_outfit(
    outfit_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_id = current_user.id
    db_user = current_user
    
    user_id_to_save = user_id
    
    # 1. Get item IDs and fetch actual items from QDRANT
    item_ids = outfit_data.get("items", [])
    if isinstance(item_ids, str):
        try:
            item_ids = json.loads(item_ids)
        except:
            item_ids = []
    
    # Fetch item details from Qdrant Cloud
    qdrant_items = await clip_qdrant_service.get_items_by_ids(item_ids)
    
    # 2. Generate global description and tags
    # We need to adapt this to work with Qdrant items (which have different structure than SQL models)
    # But stylist_chat.generate_outfit_metadata was recently updated to handle ClothingItem list
    # Let's ensure it can handle dicts or adapt the call
    from app.models.models import ClothingItem
    pseudo_items = [
        ClothingItem(
            id=item["id"],
            sub_category=item["clothing"].get("sub_category"),
            body_region=item["clothing"].get("body_region"),
            image_url=item.get("image_url", ""),
            metadata_json=item["clothing"]
        ) for item in qdrant_items
    ]
    
    meta = await stylist_chat.generate_outfit_metadata(pseudo_items)
    description = meta.get("description", "")
    style_tags = json.dumps(meta.get("style_tags", []))
    
    tryon_image_url = ""
    tryon_image_bytes = ""

    print(f"[DEBUG] Attempting try-on for user {user_id_to_save}")
    print(f"[DEBUG] Body image: {db_user.full_body_image if db_user else 'None'}")
    print(f"[DEBUG] Number of items for try-on: {len(qdrant_items)}")

    if db_user and db_user.full_body_image and qdrant_items:
        clothing_items_for_tryon = [
            {
                "image_url": item["image_url"],
                "body_region": item["clothing"].get("body_region"),
                "category": item["clothing"].get("category", "clothing"),
                "sub_category": item["clothing"].get("sub_category", "")
            }
            for item in qdrant_items
        ]
        try:
            print(f"[DEBUG] Calling tryon_generator.generate_tryon_image...")
            tryon_result = await tryon_generator.generate_tryon_image(
                body_image_url=db_user.full_body_image,
                clothing_items=clothing_items_for_tryon
            )
            if tryon_result:
                tryon_image_url = tryon_result.get("url")
                tryon_image_bytes = tryon_result.get("bytes")
                print(f"[DEBUG] Try-on generation SUCCESS: {tryon_image_url}")
                logging.info(f"Generated try-on image: {tryon_image_url}")
            else:
                print(f"[DEBUG] Try-on generation returned None, trying collage fallback")
                collage_result = await tryon_generator.generate_outfit_collage(clothing_items_for_tryon)
                if collage_result:
                    tryon_image_url = collage_result.get("url")
                    tryon_image_bytes = collage_result.get("bytes")
                    print(f"[DEBUG] Collage generation SUCCESS: {tryon_image_url}")
        except Exception as e:
            print(f"[DEBUG] Try-on/Collage generation ERROR: {str(e)}")
            logging.error(f"Try-on generation failed: {e}")
            # Final attempt: Collage if try-on failed with error
            try:
                collage_result = await tryon_generator.generate_outfit_collage(clothing_items_for_tryon)
                if collage_result:
                    tryon_image_url = collage_result.get("url")
                    tryon_image_bytes = collage_result.get("bytes")
            except:
                pass
    else:
        # No user photo, generate collage directly
        try:
            print(f"[DEBUG] No user photo, creating collage for {len(qdrant_items)} items")
            clothing_items_for_collage = [
                {
                    "image_url": item["image_url"],
                    "mask_url": item.get("mask_url"),
                    "category": item["clothing"].get("category", "clothing")
                }
                for item in qdrant_items
            ]
            collage_result = await tryon_generator.generate_outfit_collage(clothing_items_for_collage)
            if collage_result:
                tryon_image_url = collage_result.get("url")
                tryon_image_bytes = collage_result.get("bytes")
                print(f"[DEBUG] Direct collage SUCCESS: {tryon_image_url}")
        except Exception as e:
            print(f"[DEBUG] Collage failed: {e}")
    
    # 4. Create initial DB record (Optional but good for fallback/relational tracking)
    provided_name = outfit_data.get("name", "")
    ai_name = meta.get("name")
    
    # Prioritize AI name if provided name is generic or missing
    final_name = ai_name if (ai_name and (not provided_name or "Outfit " in provided_name)) else provided_name
    if not final_name:
        final_name = f"Outfit {uuid.uuid4().hex[:6]}"

    db_outfit = Outfit(
        user_id=user_id_to_save,
        name=final_name,
        occasion=outfit_data.get("occasion"),
        vibe=outfit_data.get("vibe"),
        items=json.dumps(item_ids) if isinstance(item_ids, list) else item_ids,
        score=outfit_data.get("score", 0.0),
        reasoning=outfit_data.get("reasoning"),
        description=description,
        style_tags=style_tags,
        tryon_image_url=tryon_image_url,
        created_by="ai"
    )
    
    db.add(db_outfit)
    db.commit()
    db.refresh(db_outfit)

    # 5. Send outfit summary to Zep for persona memory
    if db_user and getattr(db_user, "zep_thread_id", None):
        item_names = [
            item.get("clothing", {}).get("sub_category")
            or item.get("clothing", {}).get("category")
            or "item"
            for item in qdrant_items
        ]
        colors = []
        for item in qdrant_items:
            colors.extend(item.get("clothing", {}).get("colors", []))
        # dedupe colors while preserving order
        seen = set()
        dedup_colors = []
        for c in colors:
            if c not in seen:
                dedup_colors.append(c)
                seen.add(c)

        summary_payload = {
            "summary": description or "Outfit saved",
            "items": item_names,
            "colors": dedup_colors,
            "style_keywords": meta.get("style_tags", []),
            "fit": outfit_data.get("vibe"),
            "occasion": outfit_data.get("occasion"),
        }

        add_outfit_summary_to_graph(
            user_id=user_id_to_save,
            summary=summary_payload,
            image_url=tryon_image_url,
            timestamp=None,
            user_email=db_user.email,
            thread_id=db_user.zep_thread_id,
        )
    
    # 6. Save to Qdrant (CLIP Visual Storage for Outfits)
    # This is now the PRIMARY way we'll load outfits in the /outfits page
    if tryon_image_bytes:
        outfit_metadata = {
            "name": final_name,
            "description": description,
            "items": item_ids,
            "reasoning": db_outfit.reasoning,
            "score": db_outfit.score,
            "style_tags": meta.get("style_tags", []),
            "item_images": [item.get("image_url") for item in qdrant_items if item.get("image_url")]
        }
        await clip_qdrant_service.store_outfit_with_image(
            outfit_id=str(db_outfit.id),
            image_data=tryon_image_bytes,
            outfit_data=outfit_metadata,
            user_id=user_id_to_save,
            image_url=tryon_image_url
        )

    return db_outfit

@router.post("/advisor/compare")
async def advisor_compare(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    content = await file.read()
    try:
        return await outfit_service.advisor_compare(current_user.id, content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
