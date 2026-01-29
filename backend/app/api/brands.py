from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import Optional
from pathlib import Path
import tempfile

from app.schemas.brand import BrandIngestResponse, BrandListResponse
from app.api.brand_auth import get_current_brand
from app.models.models import Brand
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


@router.get("/products/{brand_name}")
async def get_brand_products(brand_name: str, limit: int = 10):
    """Get all ingested products for a brand from Qdrant BrandEmbedding collection."""
    from qdrant_client import QdrantClient
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    try:
        client = QdrantClient(
            url=os.getenv("QDRANT_URL", "http://localhost:6333"),
            api_key=os.getenv("QDRANT_API_KEY")
        )
        
        # Scroll all points and filter by brand name in Python
        all_points = []
        offset = None
        
        while True:
            results, next_offset = client.scroll(
                collection_name="BrandEmbedding",
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )
            
            if not results:
                break
                
            all_points.extend(results)
            
            if next_offset is None:
                break
            offset = next_offset
        
        # Filter by brand name
        products = []
        for point in all_points:
            if point.payload.get("brand_name") == brand_name:
                products.append({
                    "id": point.id,
                    "product_name": point.payload.get("product_name"),
                    "product_description": point.payload.get("product_description"),
                    "azure_image_url": point.payload.get("azure_image_url"),
                    "image_base64": point.payload.get("image_base64"),
                    "source": point.payload.get("source")
                })
                if len(products) >= limit:
                    break
        
        return {"brand_name": brand_name, "products": products, "count": len(products)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch products: {str(e)}")

