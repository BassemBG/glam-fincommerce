# Profile Brands Implementation Summary

## Overview
Added a complete profile brands system separate from brand ingestion. Users can now create, update, fetch, and search brand profiles with semantic vector search.

## Backend Components

### 1. Database Schema (`schema.sql`)
- Added `profile_brands` table with fields:
  - `id` (UUID, primary key)
  - `brand_name` (VARCHAR 255, unique, indexed)
  - `brand_website` (VARCHAR 500, optional)
  - `instagram_link` (VARCHAR 500, optional)
  - `brand_logo_url` (TEXT, optional)
  - `description` (TEXT, optional)
  - `description_embedding` (vector(384), for semantic search)
  - `metadata` (JSONB, flexible storage)
  - `created_at`, `updated_at` (timestamps)
- Added vector indices for efficient cosine similarity search

### 2. SQLModel (`backend/app/models/models.py`)
- `ProfileBrand` class with all table fields
- Compatible with async/sync database operations

### 3. Service Layer (`backend/app/services/profile_brands_service.py`)
`ProfileBrandsService` class with methods:
- **`upsert_profile_brand()`** - Create or update brand profile
  - Auto-generates embeddings for descriptions
  - Stores embeddings in metadata for semantic search
- **`get_profile_brand_by_name()`** - Fetch by exact brand name
- **`get_profile_brand_by_id()`** - Fetch by ID
- **`list_profile_brands()`** - Paginated list of all brands
- **`delete_profile_brand()`** - Delete by name
- **`search_by_description()`** - Semantic search using cosine similarity
- **`_cosine_similarity()`** - Vector similarity calculation

Uses `EmbeddingService` to generate 384-dim embeddings for efficient storage and search.

### 4. API Endpoints (`backend/app/api/profile_brands.py`)
All endpoints under `/api/v1/profile-brands`:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/` | Create/update brand profile (upsert) |
| GET | `/{brand_id}` | Fetch by ID |
| GET | `/name/{brand_name}` | Fetch by name |
| GET | `/` | List all brands (paginated) |
| POST | `/search` | Search by description (semantic) |
| PATCH | `/{brand_id}` | Partial update |
| DELETE | `/{brand_id}` | Delete brand |

### 5. Schemas (`backend/app/schemas/profile_brands.py`)
- `ProfileBrandCreate` - Request for create/update
- `ProfileBrandUpdate` - Request for patch updates
- `ProfileBrandResponse` - Single brand response
- `ProfileBrandSearchResponse` - Search results
- `ProfileBrandListResponse` - List response

### 6. Integration with Main App (`backend/app/main.py`)
- Imported and registered `profile_brands` router
- Router mounted at `/api/v1/profile-brands`

## Frontend Components

### 1. API Endpoints (`frontend/lib/api.ts`)
Added `profileBrands` object with endpoints:
```typescript
profileBrands: {
  upsert: "/api/v1/profile-brands",
  list: "/api/v1/profile-brands",
  getById: (id) => "/api/v1/profile-brands/{id}",
  getByName: (name) => "/api/v1/profile-brands/name/{name}",
  search: "/api/v1/profile-brands/search",
  update: (id) => "/api/v1/profile-brands/{id}",
  delete: (id) => "/api/v1/profile-brands/{id}",
}
```

### 2. Brand Profile Page (`frontend/app/advisor/brands/profile/page.tsx`)
- Updated to call backend API on save
- Form fields:
  - Brand name (required)
  - Website URL (optional)
  - Instagram URL (optional)
  - Brand logo (file upload with preview)
  - Short description (optional, used for semantic search)
- Status display (success/error messages)
- Clears form on successful save
- Uses `credentials: 'include'` for auth

## Key Features

### Semantic Search
- Descriptions are embedded using `all-MiniLM-L6-v2` (384 dimensions)
- Cosine similarity search for finding brands by description similarity
- Efficient vector indexing with ivfflat

### Upsert Pattern
- If brand name exists, update all fields
- If new, create a new profile
- Prevents duplicate brands (unique constraint on `brand_name`)

### Separation from Brand Ingestion
- `profile_brands` table is completely separate from ingestion Qdrant vectors
- Independent API namespace (`/profile-brands`)
- No interference with existing brand ingestion workflow

### Data Integrity
- Brand names are unique
- Metadata field for future extensibility
- Timestamps for audit trails
- Proper cascading and error handling

## Usage Example

### Upsert a Brand Profile (POST)
```bash
curl -X POST http://localhost:8000/api/v1/profile-brands \
  -H "Content-Type: application/json" \
  -d '{
    "brand_name": "Aurora Designs",
    "brand_website": "https://aurora.example",
    "instagram_link": "https://instagram.com/aurora_designs",
    "brand_logo_url": "https://cdn.example/logo.png",
    "description": "Soft tailoring and sculptural knitwear"
  }'
```

### Search by Description (POST)
```bash
curl -X POST http://localhost:8000/api/v1/profile-brands/search \
  -H "Content-Type: application/json" \
  -d '{"query": "minimalist sustainable fashion"}'
```

### Fetch by Name (GET)
```bash
curl http://localhost:8000/api/v1/profile-brands/name/Aurora%20Designs
```

## Database Migration
Run the schema migrations to create the `profile_brands` table:
```bash
# If using Alembic (recommended for production)
alembic revision --autogenerate -m "Add profile_brands table"
alembic upgrade head

# Or manually execute schema.sql
```

## Next Steps (Optional)
1. Add logo upload to S3/CDN with URL return
2. Implement bulk operations (import/export)
3. Add tags or categories to brands
4. Create brand analytics (most viewed, most added to outfits, etc.)
5. Build brand discovery feed/carousel
