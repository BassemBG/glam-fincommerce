# Quick Start Guide: Brand Website Ingestion

## 🚀 Quick Setup

### 1. Add Environment Variable
```bash
# Add to .env file
SERPER_API_KEY=your_serper_api_key_here
```

### 2. Test the API

**Website Ingestion** (Auto brand detection + product crawling + CLIP embeddings):
```bash
curl -X POST http://localhost:8000/api/v1/brands/ingest \
  -F "url=https://www.zara.com/"
```

**With Brand Override**:
```bash
curl -X POST http://localhost:8000/api/v1/brands/ingest \
  -F "url=https://www.zara.com/" \
  -F "brand_name=Zara"
```

**View Ingested Data**:
```bash
curl http://localhost:8000/api/v1/brands/
```

---

## 📋 What Was Added

### New Functions

| File | Function | Purpose |
|------|----------|---------|
| web_scraper.py | `_extract_brand_name_from_metadata()` | Extract brand from `og:site_name` or `title` |
| web_scraper.py | `_crawl_products_with_serper()` | Use Serper API to find products |
| embedding_service.py | `embed_product_for_website()` | Generate CLIP embeddings for products |
| embedding_service.py | `upsert_product_to_qdrant()` | Store product with embedding in Qdrant |
| embedding_service.py | `upsert_brand_products_from_website()` | Batch upsert multiple products |
| main.py | `process_brand_website_for_products()` | Orchestrate entire pipeline |

### Enhanced Endpoints

| Endpoint | Change | Notes |
|----------|--------|-------|
| POST /api/v1/brands/ingest | Website-focused flow added | Intelligent routing based on input |

---

## 🔍 Pipeline Overview

```
Website URL
    ↓
Extract Brand Name (og:site_name → title → domain)
    ↓
Crawl Products (Serper API or HTML fallback)
    ↓
For each product:
  - Download image
  - Generate CLIP text embedding
  - Generate CLIP image embedding
  - Combine embeddings
    ↓
Store in Qdrant (clothing_embeddings collection)
    ↓
Return point IDs + metadata
```

---

## 📊 Data Flow

### Input: Website URL
```
https://www.zara.com/
```

### Processing Steps
1. **Brand Detection**: Extracts "Zara" from metadata
2. **Product Crawl**: Finds first 10 products
   - Product name
   - Description
   - Image URL
   - Product URL
3. **CLIP Embeddings**: 
   - Text: brand + product name + description → 512-dim vector
   - Image: downloaded image → 512-dim vector
   - Combined: average of both vectors
4. **Qdrant Storage**: Upserts products with embeddings

### Output: Qdrant Payload
```json
{
  "brand_name": "Zara",
  "product_name": "Blue Summer Dress",
  "product_description": "Lightweight cotton...",
  "image_url": "https://example.com/image.jpg",
  "product_url": "https://www.zara.com/product/123",
  "source": "website",
  "embedding_type": "clip",
  "vector": [0.123, -0.456, ..., 0.789]  // 512 dimensions
}
```

---

## 🛠️ Troubleshooting

### Check 1: Is SERPER_API_KEY set?
```bash
echo $SERPER_API_KEY  # Should show your key
```

### Check 2: Is Qdrant running?
```bash
curl http://localhost:6333/health
```

### Check 3: Test brand extraction
```python
from app.services.brand_ingestion.web_scraper import _extract_brand_name_from_metadata
name = _extract_brand_name_from_metadata("https://www.zara.com/")
print(name)  # Should print "Zara" or similar
```

### Check 4: Test Serper API
```python
from app.services.brand_ingestion.web_scraper import _crawl_products_with_serper
products = _crawl_products_with_serper("https://www.zara.com/", "Zara")
print(len(products))  # Should be > 0
```

### Check 5: Test CLIP embedding
```python
from app.services.brand_ingestion.embedding_service import EmbeddingService
service = EmbeddingService()
emb = service.embed_product_for_website(
    brand_name="Zara",
    product_name="Dress",
    product_description="Summer dress",
    image_url=None
)
print(len(emb))  # Should be 512
```

---

## 📈 Expected Performance

| Step | Duration | Notes |
|------|----------|-------|
| Brand extraction | <1s | Fast |
| Serper query | 2-5s | Network dependent |
| Product crawling | 2-3s | Parse results |
| CLIP embeddings × 10 | 5-10s | Depends on image sizes |
| Qdrant upsert | <1s | Fast |
| **Total** | **10-20s** | Per website |

---

## 🔄 Backward Compatibility

✅ **All existing features work unchanged:**
- PDF ingestion still works
- Style group extraction still works
- `/api/v1/brands/` list endpoint unchanged
- Existing Qdrant queries still work

✅ **No breaking changes:**
- No new database tables
- No schema migrations
- No new environment variables required (except SERPER_API_KEY)
- No folder structure changes

---

## 🎯 Next Steps

1. **Test with sample websites:**
   ```bash
   # Try these sites
   https://www.zara.com/
   https://www.hm.com/
   https://www.forever21.com/
   ```

2. **Monitor logs:**
   ```bash
   tail -f logs/brand_ingestion.log
   ```

3. **Query Qdrant to verify storage:**
   ```bash
   # List all stored products
   curl http://localhost:6333/collections/clothing_embeddings/count
   ```

4. **Run integration tests:**
   ```bash
   pytest tests/test_brand_ingestion.py -v
   ```

---

## 📚 Documentation

- 📖 Full details: [BRAND_WEBSITE_INGESTION.md](BRAND_WEBSITE_INGESTION.md)
- 📋 Implementation checklist: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
- 🔧 Modified files: See list below

---

## 📝 Modified Files

1. `backend/app/services/brand_ingestion/web_scraper.py`
   - Added brand extraction from metadata
   - Added Serper API integration
   - Maintained backward compatibility

2. `backend/app/services/brand_ingestion/embedding_service.py`
   - Added CLIP model support
   - Added product embedding methods
   - Extended upsert functionality

3. `backend/app/services/brand_ingestion/main.py`
   - Added website product processing pipeline

4. `backend/app/api/brands.py`
   - Enhanced ingest endpoint
   - Intelligent routing for different input types

---

## ✨ Key Features

✅ **Automatic Brand Detection**  
✅ **Serper-based Product Crawling**  
✅ **CLIP Image + Text Embeddings**  
✅ **Qdrant Storage**  
✅ **100% Backward Compatible**  
✅ **No New Infrastructure**  
✅ **Minimal Code Changes**  

---

## 🆘 Support

For issues or questions, check:
1. [Troubleshooting section](#-troubleshooting) above
2. [BRAND_WEBSITE_INGESTION.md](BRAND_WEBSITE_INGESTION.md#troubleshooting)
3. Logs: `backend/logs/brand_ingestion.log`
4. Qdrant admin: `http://localhost:6333/dashboard`

---

**Status**: ✅ Ready to Use  
**Last Updated**: January 26, 2026
