# Brand Website Ingestion with CLIP Embeddings

## Overview

This document describes the enhanced brand ingestion pipeline that automatically extracts brand names, crawls products from websites using the Serper API, and generates CLIP embeddings for product images and descriptions.

## Architecture

### 1. Brand Name Extraction

**File**: [backend/app/services/brand_ingestion/web_scraper.py](backend/app/services/brand_ingestion/web_scraper.py#L66-L88)

Three-tier extraction strategy:

1. **Metadata (Preferred)**: Extracts `<meta property="og:site_name">` content
2. **Fallback to Title**: Uses `<title>` tag, cleaning common suffixes
3. **Domain Extraction**: Falls back to parsing domain name

```python
# Example
_extract_brand_name_from_metadata("https://www.zara.com")
# Returns: "Zara" (from og:site_name or title)
```

### 2. Product Crawling (Serper API)

**File**: [backend/app/services/brand_ingestion/web_scraper.py](backend/app/services/brand_ingestion/web_scraper.py#L90-L159)

Uses Serper API for intelligent product discovery:

- Queries: `site:{domain} products`
- Extracts first 10 products
- Returns: product name, description, image URL, product URL
- Fallback: HTML parsing if Serper returns no results

**Configuration**:
```bash
SERPER_API_KEY=your_serper_api_key
```

### 3. CLIP Embeddings for Products

**File**: [backend/app/services/brand_ingestion/embedding_service.py](backend/app/services/brand_ingestion/embedding_service.py#L36-L170)

New methods for product embeddings:

#### Text Embedding
```python
def _generate_clip_embedding_for_text(self, text: str) -> List[float]
```
- Uses `openai/clip-vit-base-patch32` model
- 512-dimensional embeddings
- Combines: brand name + product name + description

#### Image Embedding
```python
def _generate_clip_embedding_for_image_url(self, image_url: str) -> List[float]
```
- Downloads image from URL
- Generates CLIP image embedding
- Handles various image formats

#### Combined Embeddings
```python
def _combine_embeddings(self, image_embedding, text_embedding) -> List[float]
```
- Averages image + text embeddings (if both available)
- Falls back to image-only or text-only
- Ensures consistency with existing CLIP service

### 4. Qdrant Vector Storage

**Collection**: `clothing_embeddings` (reused from existing config)

**Payload Structure**:
```json
{
  "brand_name": "Zara",
  "product_name": "Blue Summer Dress",
  "product_description": "Lightweight cotton dress with floral pattern",
  "image_url": "https://example.azure.blob.core.windows.net/products/...",
  "product_url": "https://www.zara.com/product/123",
  "source": "website",
  "embedding_type": "clip"
}
```

## API Endpoints

### POST `/api/v1/brands/ingest`

Enhanced endpoint that intelligently routes based on input:

#### Website-only Ingestion
```bash
curl -X POST http://localhost:8000/api/v1/brands/ingest \
  -F "url=https://www.zara.com/" \
  -F "brand_name=Zara"
```

**Response**:
```json
{
  "brand_name": "Zara",
  "source": "website",
  "num_styles": 10,
  "point_ids": ["uuid1", "uuid2", ...],
  "style_groups": []
}
```

#### PDF Ingestion (unchanged)
```bash
curl -X POST http://localhost:8000/api/v1/brands/ingest \
  -F "file=@brand_profile.pdf" \
  -F "brand_name=Zara"
```

#### Combined PDF + Website
```bash
curl -X POST http://localhost:8000/api/v1/brands/ingest \
  -F "file=@brand_profile.pdf" \
  -F "url=https://www.zara.com/"
```

### GET `/api/v1/brands/`

Lists all ingested brands and their products/styles.

## Minimal Changes to Existing Code

### Files Modified

1. **[backend/app/services/brand_ingestion/web_scraper.py](backend/app/services/brand_ingestion/web_scraper.py)**
   - Added `_extract_brand_name_from_metadata()` function
   - Added `_crawl_products_with_serper()` function
   - Enhanced `scrape_brand_website()` to accept `brand_name_override` parameter
   - Added image URL extraction to HTML parser

2. **[backend/app/services/brand_ingestion/embedding_service.py](backend/app/services/brand_ingestion/embedding_service.py)**
   - Added lazy-loaded CLIP model initialization
   - Added 5 new methods for CLIP embeddings (text, image, combined)
   - Added `embed_product_for_website()` method
   - Added `upsert_product_to_qdrant()` method
   - Added `upsert_brand_products_from_website()` method
   - **Backward compatible**: All existing methods unchanged

3. **[backend/app/services/brand_ingestion/main.py](backend/app/services/brand_ingestion/main.py)**
   - Added `process_brand_website_for_products()` function
   - Existing `process_and_store_brand_data()` unchanged

4. **[backend/app/api/brands.py](backend/app/api/brands.py)**
   - Enhanced `/ingest` endpoint with intelligent routing
   - Separate flows for website-only vs. PDF vs. combined
   - **Backward compatible**: All existing functionality preserved

### Files NOT Modified

- ✅ No changes to folder structure
- ✅ No changes to existing database schema
- ✅ No new Qdrant collections created
- ✅ No Docker or container modifications
- ✅ Reuses existing: CLIP service, Azure storage, Qdrant setup

## Usage Examples

### Python CLI Testing

```bash
# Ingest website and store products
python -m app.services.brand_ingestion.main url https://www.zara.com/ Zara

# Ingest PDF (existing functionality)
python -m app.services.brand_ingestion.main pdf data/samples/Zara.pdf Zara
```

### Direct API Integration

```python
from app.services.brand_ingestion.main import process_brand_website_for_products

result = process_brand_website_for_products(
    url="https://www.zara.com/",
    brand_name_override="Zara"
)

print(f"Stored {result['num_stored']} products")
print(f"Point IDs: {result['point_ids']}")
```

## Configuration

### Required Environment Variables

```bash
# Existing
QDRANT_URL=https://your-qdrant-instance.com
QDRANT_API_KEY=your_api_key

# New
SERPER_API_KEY=your_serper_api_key

# Optional (for image embedding downloads)
AZURE_STORAGE_CONNECTION_STRING=...
```

### Optional: Azure Blob Storage for Images

If Azure storage is configured, product images can be uploaded and stored URLs used:

```python
from app.services.storage import storage_service

# Images are downloaded and stored in Qdrant payload
# No local disk persistence required
```

## Key Features

✅ **Automatic Brand Detection**
- Extracts from metadata, title, or domain
- Manual override available

✅ **Intelligent Product Crawling**
- Uses Serper API for reliable discovery
- Fallback to HTML parsing
- Limits to first 10 products per website

✅ **CLIP-based Embeddings**
- Combines image + text representations
- 512-dimensional vectors (same as existing CLIP service)
- Reuses existing clip_qdrant_service infrastructure

✅ **Minimal Code Changes**
- Backward compatible
- No existing features modified
- Follows existing patterns and conventions

✅ **Scalable Storage**
- Uses existing Qdrant collection
- No new database tables
- Image URLs stored (not base64)

## Troubleshooting

### No products found
```
⚠️ Serper returned no products, falling back to HTML parsing...
```
- Ensure `SERPER_API_KEY` is configured
- Check website structure for product containers
- Manual review of website HTML may be needed

### CLIP embedding errors
```
Failed to load CLIP model: [error]
```
- Install required packages: `pip install transformers torch pillow`
- Ensure sufficient disk space for model download (~400MB)

### Image download failures
```
Failed to generate CLIP embedding from image URL
```
- Check image URL accessibility
- Verify SSL certificates if using HTTPS
- Some websites block automated downloads

## Future Enhancements

1. **Batch processing**: Handle multiple products in parallel
2. **Caching**: Store downloaded images to avoid re-processing
3. **Product categorization**: Auto-tag products based on CLIP embeddings
4. **Image variations**: Handle multiple images per product
5. **Price extraction**: More robust price parsing

## Testing

### Unit Tests

```bash
# Test brand name extraction
pytest tests/test_brand_name_extraction.py

# Test Serper integration
pytest tests/test_serper_crawling.py -m serper

# Test CLIP embeddings
pytest tests/test_clip_embeddings.py
```

### Integration Test

```bash
# Full pipeline
curl -X POST http://localhost:8000/api/v1/brands/ingest \
  -F "url=https://www.zara.com/" \
  -F "brand_name=Zara"

# Verify products stored
curl http://localhost:8000/api/v1/brands/
```

## References

- [CLIP Model Documentation](https://github.com/openai/CLIP)
- [Serper API](https://serper.dev/)
- [Qdrant Vector Database](https://qdrant.tech/)
- [Existing CLIP Service](backend/app/services/clip_qdrant_service.py)
