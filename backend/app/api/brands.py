from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import Optional
from pathlib import Path
import tempfile

from app.schemas.brand import BrandIngestResponse, BrandListResponse, RecommendationClickRequest
from app.api.brand_auth import get_current_brand
from app.models.models import Brand, RecommendationMetric
from app.db.session import SessionLocal
from app.services.brand_ingestion.document_loader import DocumentLoader
from app.services.brand_ingestion.web_scraper import scrape_brand_website
from app.services.brand_ingestion.main import process_and_store_brand_data, process_brand_website_for_products
from app.services.brand_ingestion.embedding_service import EmbeddingService

router = APIRouter(tags=["brands"])


# Add OPTIONS handler for CORS preflight
@router.options("/{path_name:path}")
async def preflight_handler(path_name: str):
    return {"message": "CORS preflight OK"}


@router.post("/ingest", response_model=BrandIngestResponse)
async def ingest_brand(
    file: UploadFile = File(default=None),
    url: Optional[str] = Form(default=None),
    brand_name: Optional[str] = Form(default=None),
    current_brand: Brand = Depends(get_current_brand),
):
    """
    Ingest a brand via PDF upload or website URL and store embeddings.
    
    For website URLs:
    - Automatically extracts brand name from metadata
    - Crawls first 10 products using Serper API
    - Generates CLIP embeddings for product images + text
    - Stores all data in Qdrant
    
    For PDF uploads:
    - Extracts text and stores style groups
    """
    if not file and not url:
        raise HTTPException(status_code=400, detail="Provide a PDF file or website URL.")

    # =======================
    # Website-based ingestion
    # =======================
    if url and not file:
        try:
            # Use new product-focused ingestion
            result = await process_brand_website_for_products(
                url=url,
                brand_name_override=brand_name
            )
            
            if result.get("status") == "error":
                raise HTTPException(status_code=400, detail=result.get("error", "Website processing failed"))
            
            return BrandIngestResponse(
                brand_name=result.get("brand_name"),
                source="website",
                num_styles=result.get("num_products", 0),
                point_ids=result.get("point_ids", []),
                style_groups=[],  # Products are stored directly in Qdrant, not as style_groups
                products=result.get("products", [])  # Include products for frontend display
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Website ingestion failed: {str(e)}")
    
    # =======================
    # PDF-based ingestion
    # =======================
    if file and not url:
        raw_text_parts = []
        suffix = Path(file.filename or "brand.pdf").suffix or ".pdf"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            if not content:
                raise HTTPException(status_code=400, detail="Uploaded file is empty.")
            tmp.write(content)
            tmp.flush()
            tmp_path = Path(tmp.name)
        try:
            pdf_text = DocumentLoader.load(tmp_path)
            if pdf_text.strip():
                raw_text_parts.append(pdf_text)
        finally:
            tmp_path.unlink(missing_ok=True)
        
        if not raw_text_parts:
            raise HTTPException(status_code=400, detail="No content extracted from PDF.")
        
        raw_text = "\n\n".join(raw_text_parts)
        result = process_and_store_brand_data(raw_text, brand_name=brand_name or "New Brand")
        result["source"] = "pdf"
        return result
    
    # =======================
    # Combined PDF + URL
    # =======================
    raw_text_parts = []
    sources = []

    # Process PDF if provided
    if file:
        suffix = Path(file.filename or "brand.pdf").suffix or ".pdf"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            if not content:
                raise HTTPException(status_code=400, detail="Uploaded file is empty.")
            tmp.write(content)
            tmp.flush()
            tmp_path = Path(tmp.name)
        try:
            pdf_text = DocumentLoader.load(tmp_path)
            if pdf_text.strip():
                raw_text_parts.append(pdf_text)
                sources.append("pdf")
        finally:
            tmp_path.unlink(missing_ok=True)
    
    # Process URL if provided
    if url:
        try:
            scraped = scrape_brand_website(url, brand_name_override=brand_name)
            url_text = scraped.get("raw_text", "")
            if url_text.strip():
                raw_text_parts.append(url_text)
                sources.append("website")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Website scraping failed: {str(e)}")

    if not raw_text_parts:
        raise HTTPException(status_code=400, detail="No content extracted from provided sources.")

    # Combine all text sources
    raw_text = "\n\n".join(raw_text_parts)
    source = "+".join(sources)

    result = process_and_store_brand_data(raw_text, brand_name=brand_name or "New Brand")
    result["source"] = source
    return result


@router.get("/", response_model=BrandListResponse)
async def list_brands():
    """List all ingested brands aggregated from the embedding store."""
    service = EmbeddingService()
    brands = service.list_brands()
    return {"brands": brands}


@router.post("/click")
async def record_brand_click(
    request: RecommendationClickRequest,
    user_id: str
):
    """Record a click on a brand product."""
    db = SessionLocal()
    try:
        click = RecommendationMetric(
            user_id=user_id,
            product_id=str(request.product_id),
            brand_name=request.brand_name,
            event_type="click",
            source=request.source
        )
        db.add(click)
        db.commit()
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@router.post("/purchase-click")
async def record_brand_purchase_click(
    request: RecommendationClickRequest,
    user_id: str
):
    """Record a purchase intent click (external link)."""
    db = SessionLocal()
    try:
        click = RecommendationMetric(
            user_id=user_id,
            product_id=str(request.product_id),
            brand_name=request.brand_name,
            event_type="purchase_click",
            source=request.source
        )
        db.add(click)
        db.commit()
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@router.get("/explore")
async def explore_brands(
    user_id: Optional[str] = None,
    limit: int = 50,
    offset: Optional[str] = None
):
    """
    Explore brand products with optional DNA-based personalization.
    If user_id is provided, results are scored against their vibes and colors.
    """
    from app.services.brand_ingestion.brand_clip_service import brand_clip_service
    from app.services.style_dna_service import style_dna_service
    
    data = await brand_clip_service.list_products(limit=limit, offset=offset)
    products = data.get("products", [])
    
    # Record Impressions if user_id is present
    if user_id and products:
        db = SessionLocal()
        try:
            for p in products[:10]: # Just log first 10 for performance
                imp = RecommendationMetric(
                    user_id=user_id,
                    product_id=str(p.get("id")),
                    brand_name=p.get("brand_name") or "unknown",
                    event_type="impression",
                    source="explore"
                )
                db.add(imp)
            db.commit()
        except:
            pass # Don't block listing if logging fails
        finally:
            db.close()

    if not user_id or not products:
        return {
            "products": products,
            "next_offset": data.get("next_offset"),
            "personalized": False
        }
        
    try:
        # Get Style DNA
        dna = await style_dna_service.get_user_style_dna(user_id)
        if "error" in dna:
            return {
                "products": products,
                "next_offset": data.get("next_offset"),
                "personalized": False,
                "note": "DNA fetch failed"
            }
            
        vibes = dna.get("vibes", {})
        top_vibe = max(vibes, key=vibes.get) if vibes else "Casual"
        top_colors = [c.lower() for c in dna.get("colors", [])]
        
        # Simple scoring logic
        scored_products = []
        for p in products:
            score = 0.5 # Start with neutral
            desc = (p.get("product_description") or "").lower()
            name = (p.get("product_name") or "").lower()
            
            # Vibe boost
            if top_vibe.lower() in desc or top_vibe.lower() in name:
                score += 0.2
                
            # Color boost
            for color in top_colors:
                if color in desc or color in name:
                    score += 0.1
                    
            p["personal_score"] = round(min(score, 1.0), 2)
            scored_products.append(p)
            
        # Sort by personal score
        scored_products = sorted(scored_products, key=lambda x: x.get("personal_score", 0), reverse=True)
        
        return {
            "products": scored_products,
            "next_offset": data.get("next_offset"),
            "personalized": True,
            "top_vibe": top_vibe
        }
    except Exception as e:
        return {
            "products": products,
            "next_offset": data.get("next_offset"),
            "personalized": False,
            "error": str(e)
        }

