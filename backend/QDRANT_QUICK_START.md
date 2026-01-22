# 🚀 Qdrant Quick Start Guide

## Step-by-Step Setup

### 1️⃣ Start Qdrant with Docker

**Option A: Using Docker Compose (Recommended)**
```bash
cd backend
docker-compose up -d
```

**Option B: Using Docker directly**
```bash
docker run -p 6333:6333 -p 6334:6334 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant
```

**Windows PowerShell:**
```powershell
docker run -p 6333:6333 -p 6334:6334 -v ${PWD}/qdrant_storage:/qdrant/storage qdrant/qdrant
```

### 2️⃣ Verify Qdrant is Running

Open in browser: **http://localhost:6333/dashboard**

You should see the Qdrant dashboard.

### 3️⃣ Test the Setup

```bash
cd backend
python test_qdrant_setup.py
```

This will:
- ✅ Check connection
- ✅ Create collection automatically
- ✅ Test storing/searching embeddings

### 4️⃣ Collection Details

**Collection Name**: `clothing_embeddings`

**Configuration**:
- **Vector Size**: 768 dimensions
- **Distance Metric**: Cosine
- **Purpose**: Store clothing item embeddings for semantic search

### 5️⃣ How Collection is Created

The collection is **automatically created** by `app/services/qdrant_service.py` when:
- The service initializes
- You run any clothing ingestion
- You call the Qdrant service

**No manual creation needed!** The code handles it.

---

## 📊 Viewing in Dashboard

1. Go to: http://localhost:6333/dashboard
2. Click **Collections** tab
3. See `clothing_embeddings` collection
4. Click to view:
   - Points count
   - Vector configuration
   - Search interface

---

## 🔍 What Gets Stored

Each clothing item is stored as:

```json
{
  "id": 123456789,
  "vector": [0.123, -0.456, ...],  // 768 dimensions
  "payload": {
    "user_id": "user-123",
    "clothing": {
      "category": "clothing",
      "sub_category": "T-shirt",
      "colors": ["red", "white"],
      "material": "cotton",
      "vibe": "casual",
      "season": "All Seasons"
    },
    "brand": "Pull&Bear",
    "price": 99.0,
    "price_range": "mid-range",
    "ingested_at": "2026-01-21T..."
  }
}
```

---

## ✅ Verification

After running `test_qdrant_setup.py`, you should see:
- ✅ Connection successful
- ✅ Collection exists
- ✅ Test embedding stored
- ✅ Search working

Then run the full pipeline:
```bash
python test_groq.py full
```

Check the dashboard to see your clothing embeddings!

