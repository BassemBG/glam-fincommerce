"""
BRAND PRODUCT INGESTION - VALIDATION & FILTERING SUMMARY
=========================================================

🎯 CHANGES MADE

1. STRICT PRODUCT VALIDATION
   - Added _is_valid_product() function in web_scraper.py
   - Validates ALL products before storage
   
   Required fields:
   ✓ product_name (non-empty, min 3 chars)
   ✓ image_url (valid http/https URL)
   ✓ description OR price_text (some content)
   
   Exclusion patterns:
   ✗ Navigation elements (about, contact, cart, etc.)
   ✗ Hero banners and category pages
   ✗ Blog posts and social media links
   ✗ "New Products", "Promotions", "Categories" sections
   ✗ Generic menu items
   ✗ Elements with very short descriptions (<20 chars, no price)

2. AZURE IMAGE UPLOAD INTEGRATION
   - Downloads each product image once
   - Uploads to Azure Blob Storage (brands/{brand}/{product}-{id}.jpg)
   - Stores BOTH URLs in payload:
     * azure_image_url: Storage URL (for serving)
     * original_image_url: Source URL (for reference)
   - Falls back to original URL if Azure upload fails
   - Skips products where image download fails

3. IMPROVED SERPER QUERY
   - Changed from "site:domain products"
   - To: "site:domain (buy OR shop OR product) -category -blog -about"
   - Filters out 20 results → keeps first 10 valid products
   - Validates each result before adding

4. ENHANCED ERROR HANDLING
   - Products without images are skipped (returns None, not exception)
   - Logging shows validation decisions
   - Batch upsert tracks skipped vs. successful

5. PAYLOAD STRUCTURE (Qdrant BrandEmbedding)
   {
       "brand_name": "BrandName",
       "product_name": "Product Title",
       "product_description": "Full description",
       "azure_image_url": "https://storage.blob.../brands/...",
       "original_image_url": "https://website.com/product.jpg",
       "image_base64": "data:image/jpeg;base64,...",
       "product_url": "https://website.com/product",
       "source": "website",
       "storage": "azure" | "source",
       "embedding_type": "clip"
   }

📊 VALIDATION FLOW

Serper API → Products
    ↓
_is_valid_product() → Filter non-products
    ↓
Download image → Skip if fails
    ↓
Generate CLIP embeddings (512-dim)
    ↓
Upload to Azure → Use URL or fallback to original
    ↓
Store in Qdrant BrandEmbedding

✅ TESTING

Run validation test:
    python test_product_validation.py

Run full ingestion test:
    python -m app.services.brand_ingestion.main url https://example.com Brand

Expected outcome:
    - Only products with images/descriptions stored
    - No navigation/UI elements in Qdrant
    - Each product has Azure URL + CLIP embeddings

🔧 CONFIGURATION

Required environment variables:
    SERPER_API_KEY - For product crawling
    AZURE_STORAGE_CONNECTION_STRING - For image storage
    AZURE_STORAGE_CONTAINER - Container name
    QDRANT_URL - Vector database
    QDRANT_API_KEY - Authentication

📝 FILES MODIFIED

1. web_scraper.py
   - Added EXCLUDE_PATTERNS
   - Added _is_valid_product()
   - Updated Serper extraction with validation
   - Updated HTML fallback with validation
   - Improved Serper query

2. brand_clip_service.py
   - Added image download validation
   - Integrated Azure upload via storage_service
   - Returns None for invalid products (instead of raising)
   - Stores azure_image_url + original_image_url
   - Updated payload structure
   - Added truncation for CLIP text (max 77 tokens)

3. main.py
   - Added product details logging
   - Shows validation status

4. NEW: test_product_validation.py
   - Unit tests for validation logic
   - Covers all exclude patterns

🚫 NOT CHANGED

✓ PDF ingestion (embedding_service.py)
✓ Folder structure
✓ File names
✓ Clothing embeddings (CLIPQdrantService)
✓ Existing collections

⚡ PERFORMANCE NOTES

- Image download: ~1-3s per product
- Azure upload: ~1-2s per product (async)
- CLIP embedding: ~0.5s per product (CPU)
- Total: ~10-50s for 10 products (depending on network)

🔒 ISOLATION

- BrandEmbedding collection completely separate
- 512-dim CLIP vectors (not 384-dim FastEmbed)
- No impact on clothing_clip_embeddings
- Reuses CLIP model but separate Qdrant collection
