# Qdrant Vector Database Setup Guide

Complete guide to set up Qdrant for clothing embeddings storage.

---

## 🐳 Step 1: Install Docker

Make sure Docker is installed and running on your system.

**Windows**: Download from https://www.docker.com/products/docker-desktop/

---

## 🚀 Step 2: Start Qdrant with Docker

Run this command in your terminal:

```bash
docker run -p 6333:6333 -p 6334:6334 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant
```

**Windows PowerShell:**
```powershell
docker run -p 6333:6333 -p 6334:6334 -v ${PWD}/qdrant_storage:/qdrant/storage qdrant/qdrant
```

**What this does:**
- `-p 6333:6333` - Maps port 6333 (HTTP API)
- `-p 6334:6334` - Maps port 6334 (gRPC API)
- `-v .../qdrant_storage:/qdrant/storage` - Persists data to local folder
- `qdrant/qdrant` - Official Qdrant Docker image

**Verify it's running:**
- Open browser: http://localhost:6333/dashboard
- You should see the Qdrant dashboard

---

## 📊 Step 3: Access Qdrant Dashboard

1. Open: **http://localhost:6333/dashboard**
2. You'll see the Qdrant web interface
3. Collections will appear here once created

---

## 🔧 Step 4: Create Collection (Automatic)

The collection is **automatically created** when you run the application!

The code in `app/services/qdrant_service.py` will:
1. Connect to Qdrant
2. Check if collection exists
3. Create it if it doesn't exist

**Collection Settings:**
- **Name**: `clothing_embeddings`
- **Vector Size**: `768` dimensions
- **Distance Metric**: `Cosine` (for semantic similarity)

---

## 🧪 Step 5: Test the Setup

Run this test script to verify everything works:

```bash
cd backend
python test_qdrant_setup.py
```

This will:
- ✅ Check Qdrant connection
- ✅ Create collection if needed
- ✅ Store a test embedding
- ✅ Search for similar items
- ✅ Show collection stats

---

## 📝 Step 6: Verify in Dashboard

1. Go to http://localhost:6333/dashboard
2. Click on **Collections** tab
3. You should see: `clothing_embeddings`
4. Click on it to see:
   - Points count
   - Vector size (768)
   - Distance metric (Cosine)

---

## 🔍 How It Works in the Project

### When Clothing is Ingested:

1. **Clothing Analysis** (Groq) → Gets clothing attributes
2. **Brand Detection** (Groq) → Gets brand info
3. **Price Lookup** (Tavily) → Gets price range
4. **Embedding Generation** → Creates 768-dim vector
5. **Store in Qdrant** → Saves vector + metadata

### What Gets Stored:

```json
{
  "vector": [0.123, -0.456, ...],  // 768 dimensions
  "payload": {
    "user_id": "user-123",
    "clothing": {
      "category": "clothing",
      "sub_category": "T-shirt",
      "colors": ["red", "white"],
      "material": "cotton",
      "vibe": "casual",
      ...
    },
    "brand": "Pull&Bear",
    "price": 99.0,
    "price_range": "mid-range",
    "ingested_at": "2026-01-21T..."
  }
}
```

---

## 🛠️ Manual Collection Creation (Optional)

If you want to create the collection manually via code:

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

client = QdrantClient(url="http://localhost:6333")

client.create_collection(
    collection_name="clothing_embeddings",
    vectors_config=VectorParams(
        size=768,
        distance=Distance.COSINE
    )
)
```

---

## 🔗 Configuration

In `backend/.env`:
```env
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=  # Optional, not needed for local
QDRANT_COLLECTION_NAME=clothing_embeddings
```

---

## ✅ Verification Checklist

- [ ] Docker is running
- [ ] Qdrant container is running (`docker ps`)
- [ ] Dashboard accessible at http://localhost:6333/dashboard
- [ ] Collection `clothing_embeddings` exists (auto-created)
- [ ] Test script runs successfully
- [ ] Can store embeddings via clothing ingestion

---

## 🐛 Troubleshooting

### "Connection refused" error:
- Make sure Docker is running
- Check if Qdrant container is running: `docker ps`
- Verify port 6333 is not blocked by firewall

### Collection not created:
- Check logs for errors
- Verify QDRANT_URL in .env is correct
- Try creating manually using the code above

### Data persistence:
- Data is saved in `backend/qdrant_storage/` folder
- This folder is created automatically
- To reset: stop container, delete folder, restart

---

## 📚 Next Steps

Once Qdrant is running:
1. Run `python test_groq.py full` to test full pipeline
2. Check dashboard to see stored embeddings
3. Use semantic search to find similar clothing items

