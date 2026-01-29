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
from app.services.tryon_generator import tryon_generator
from app.services.style_dna_service import style_dna_service
import uuid
import json
import logging

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


class TryOnRequest(BaseModel):
    items: List[Dict[str, Any]]

@router.post("/tryon")
async def tryon_preview(
    request: TryOnRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Generate an AI try-on preview.
    Does not save the outfit.
    """
    logging.info(f"[TRYON] Request received from user {current_user.id}")
    logging.info(f"[TRYON] Number of items: {len(request.items)}")
    logging.info(f"[TRYON] Items data: {request.items}")
    
    if not current_user.full_body_image:
        logging.warning(f"[TRYON] User {current_user.id} has no body photo")
        raise HTTPException(status_code=400, detail="User must upload a body photo first")

    # The request.items should contain image_url and body_region
    try:
        logging.info(f"[TRYON] Calling tryon_generator with body image: {current_user.full_body_image[:50]}...")
        result = await tryon_generator.generate_tryon_image(
            body_image_url=current_user.full_body_image,
            clothing_items=request.items
        )
        if result:
            logging.info(f"[TRYON] Success! Generated URL: {result.get('url')}")
            return {"url": result.get("url")}
        else:
            # Fallback to collage if AI generation fails
            logging.warning(f"[TRYON] AI generation returned None, trying collage fallback")
            collage = await tryon_generator.generate_outfit_collage(request.items)
            if collage:
                logging.info(f"[TRYON] Collage fallback success: {collage.get('url')}")
                return {"url": collage.get("url")}
            logging.error(f"[TRYON] Both AI and collage generation failed")
            raise HTTPException(status_code=500, detail="Failed to generate try-on")
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[TRYON] Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/outfits/save")
async def save_outfit(
    outfit_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Save a curated outfit to the database and Qdrant gallery.
    """
    logging.info(f"[SAVE] Request from user {current_user.id}: {outfit_data}")
    print(f"[DEBUG] Full outfit_data received: {json.dumps(outfit_data, indent=2)}")
    
    user_id_to_save = current_user.id
    db_user = current_user
    
    # 1. Get item IDs and fetch actual items from QDRANT
    item_ids = outfit_data.get("items", [])
    print(f"[DEBUG] Received item_ids: {item_ids} (Type: {type(item_ids)})")
    
    if isinstance(item_ids, str):
        try:
            item_ids = json.loads(item_ids)
        except:
            item_ids = []
    
    print(f"[DEBUG] Processed item_ids: {item_ids}")
    
    # Fetch item details from Qdrant Cloud
    qdrant_items = await clip_qdrant_service.get_items_by_ids(item_ids)
    
    # 2. Generate global description and tags
    # We need to adapt this to work with Qdrant items (which have different structure than SQL models)
    # But outfit_service.generate_outfit_metadata was recently updated to handle ClothingItem list
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
    
    meta = await outfit_service.generate_outfit_metadata(pseudo_items)
    description = meta.get("description", "")
    style_tags = json.dumps(meta.get("style_tags", []))
    
    tryon_image_url = ""
    tryon_image_bytes = ""

    print(f"[DEBUG] Attempting try-on for user {user_id_to_save}")
    print(f"[DEBUG] Body image: {db_user.full_body_image if db_user else 'None'}")
    print(f"[DEBUG] Number of items for try-on: {len(qdrant_items)}")

    # Check if a custom try-on URL was already provided (e.g., from manual selection)
    provided_tryon_url = outfit_data.get("tryon_image_url")
    if provided_tryon_url:
        print(f"[DEBUG] Using provided try-on URL: {provided_tryon_url}")
        tryon_image_url = provided_tryon_url
    elif db_user and db_user.full_body_image and qdrant_items:
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
    
    # If we have a URL but no bytes (e.g. from a previous front-end call), fetch the bytes to generate CLIP embeddings
    if not tryon_image_bytes and tryon_image_url:
        try:
            import httpx
            print(f"[DEBUG] Fetching image bytes from URL for Qdrant storage: {tryon_image_url}")
            async with httpx.AsyncClient() as client:
                img_res = await client.get(tryon_image_url)
                if img_res.status_code == 200:
                    tryon_image_bytes = img_res.content
                    print(f"[DEBUG] Successfully fetched {len(tryon_image_bytes)} bytes")
        except Exception as e:
            print(f"[DEBUG] Failed to fetch image bytes for Qdrant: {e}")

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
        print(f"[DEBUG] Sending to Qdrant collection: {clip_qdrant_service.outfits_collection_name}")
        await clip_qdrant_service.store_outfit_with_image(
            outfit_id=str(db_outfit.id),
            image_data=tryon_image_bytes,
            outfit_data=outfit_metadata,
            user_id=user_id_to_save,
            image_url=tryon_image_url
        )
    else:
        print(f"[DEBUG] Skipping Qdrant storage: no image bytes available")

    return db_outfit
    
@router.get("/search")
async def search_closet_visual(
    query: str,
    current_user: User = Depends(get_current_user)
):
    """
    Direct visual search in the closet using CLIP (text-to-image).
    """
    try:
        results = await clip_qdrant_service.search_by_text(query, current_user.id, limit=20)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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

@router.get("/style-dna")
async def get_style_dna(
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve user style DNA including vibes radar and top colors.
    """
    try:
        return await style_dna_service.get_user_style_dna(current_user.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
