from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional
from pathlib import Path
import tempfile

from app.schemas.brand import BrandIngestResponse, BrandListResponse
from app.services.brand_ingestion.document_loader import DocumentLoader
from app.services.brand_ingestion.web_scraper import scrape_brand_website
from app.services.brand_ingestion.main import process_and_store_brand_data
from app.services.brand_ingestion.embedding_service import EmbeddingService

router = APIRouter(tags=["brands"])


@router.post("/ingest", response_model=BrandIngestResponse)
async def ingest_brand(
    file: UploadFile = File(default=None),
    url: Optional[str] = Form(default=None),
    brand_name: Optional[str] = Form(default=None),
):
    """Ingest a brand via PDF upload or website URL and store embeddings."""
    if not file and not url:
        raise HTTPException(status_code=400, detail="Provide a PDF file or website URL.")

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
        scraped = scrape_brand_website(url)
        url_text = scraped.get("raw_text", "")
        if url_text.strip():
            raw_text_parts.append(url_text)
            sources.append("website")

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
