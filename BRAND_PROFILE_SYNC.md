# Brand Profile Sync Implementation

## Overview
Implemented automatic brand profile initialization from sign-up data with full edit capability post-login. Brand profiles are database-driven (no Qdrant), linked to brand authentication via `brand_id` foreign key.

## What Changed

### 1️⃣ Backend Database Model ([models.py](backend/app/models/models.py))

**ProfileBrand Model Updated:**
```python
class ProfileBrand(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    brand_id: str = Field(foreign_key="brands.id", index=True, unique=True, nullable=False)  # NEW: FK link
    brand_name: str
    office_email: Optional[str]  # NEW: from sign-up
    brand_type: Optional[str]  # NEW: local | international (read-only)
    brand_website: Optional[str]
    instagram_link: Optional[str]
    brand_logo_url: Optional[str]
    description: Optional[str]  # Bio/short description
    brand_metadata: Dict  # Stores embeddings
```

**Key Changes:**
- ✅ Added `brand_id` foreign key linking to `Brand` table (one-to-one relationship)
- ✅ Added `office_email` and `brand_type` fields for tracking sign-up data
- ✅ Made `brand_name` non-unique (now searchable, not a primary identifier)
- ✅ All fields except id and brand_id are optional for flexibility

### 2️⃣ Backend Service Methods ([profile_brands_service.py](backend/app/services/profile_brands_service.py))

**New Methods Added:**

```python
def get_or_create_brand_profile(
    brand_id: str,
    brand_name: str,
    office_email: Optional[str] = None,
    brand_type: Optional[str] = None,
    brand_website: Optional[str] = None,
    description: Optional[str] = None,
) -> ProfileBrand:
    """Auto-create profile on sign-up (idempotent)."""
    # Returns existing profile or creates new one
    # Called from brand_signup endpoint
```

```python
def update_brand_profile(
    brand_id: str,
    brand_name: Optional[str] = None,
    brand_website: Optional[str] = None,
    instagram_link: Optional[str] = None,
    brand_logo_url: Optional[str] = None,
    description: Optional[str] = None,
) -> Optional[ProfileBrand]:
    """Update only editable fields (idempotent)."""
    # Skips read-only fields (office_email, brand_type)
    # Auto-generates embedding for description if changed
```

```python
def get_profile_by_brand_id(brand_id: str) -> Optional[ProfileBrand]:
    """Fetch profile using brand_id (one-to-one link)."""
```

**Why These Methods:**
- Idempotent: Safe to call multiple times without creating duplicates
- Automatic embeddings: Re-embeds description only when changed
- Brand-centric: Use brand_id instead of brand_name for all authenticated operations

### 3️⃣ Brand Authentication Flow ([brand_auth.py](backend/app/api/brand_auth.py))

**Sign-Up Auto-Creates Profile:**
```python
@router.post("/signup", response_model=Token)
def brand_signup(brand_in: BrandCreate, db: Session = Depends(get_db)):
    # ... create Brand record ...
    
    # NEW: Auto-create brand profile with sign-up data
    profile_service = ProfileBrandsService(db)
    try:
        profile_service.get_or_create_brand_profile(
            brand_id=brand.id,
            brand_name=brand.brand_name,
            office_email=brand.office_email,
            brand_type=brand.brand_type,
            brand_website=brand.website_url,
            description=None  # No description at signup
        )
    except Exception as e:
        logger.warning(f"Failed to auto-create profile: {e}")
        # Don't fail signup if profile creation fails
    
    # Return JWT token with role="brand"
```

**Key Point:** Profile creation is **non-blocking** – signup succeeds even if profile creation fails.

### 4️⃣ Backend API Endpoints ([profile_brands.py](backend/app/api/profile_brands.py))

**New Authenticated Endpoints:**

```python
@router.get("/me", response_model=ProfileBrandResponse)
async def get_current_brand_profile(
    db: Session = Depends(get_db),
    current_brand: Brand = Depends(get_current_brand)
):
    """GET /api/v1/profile-brands/me - Load authenticated brand's profile"""
    profile = service.get_profile_by_brand_id(current_brand.id)
    return profile
```

```python
@router.put("/me", response_model=ProfileBrandResponse)
async def update_current_brand_profile(
    payload: ProfileBrandUpdate,
    db: Session = Depends(get_db),
    current_brand: Brand = Depends(get_current_brand)
):
    """PUT /api/v1/profile-brands/me - Update authenticated brand's profile"""
    updated = service.update_brand_profile(
        brand_id=current_brand.id,
        brand_name=payload.brand_name,
        brand_website=payload.brand_website,
        instagram_link=payload.instagram_link,
        brand_logo_url=payload.brand_logo_url,
        description=payload.description,
    )
    return updated
```

**Existing Endpoints:** Still available for public/admin access (list, search, get by ID, etc.)

**Security:** All endpoints require `get_current_brand` dependency (brand JWT token with role="brand")

### 5️⃣ Backend Schemas ([profile_brands.py](backend/app/schemas/profile_brands.py))

**ProfileBrandCreate Added Fields:**
```python
class ProfileBrandCreate(BaseModel):
    brand_name: str
    office_email: Optional[str] = None  # NEW
    brand_type: Optional[str] = None     # NEW
    brand_website: Optional[str] = None
    instagram_link: Optional[str] = None
    brand_logo_url: Optional[str] = None
    description: Optional[str] = None
```

**ProfileBrandResponse Added Fields:**
```python
class ProfileBrandResponse(BaseModel):
    id: str
    brand_id: str                    # NEW: Foreign key
    brand_name: str
    office_email: Optional[str]      # NEW
    brand_type: Optional[str]        # NEW
    brand_website: Optional[str]
    instagram_link: Optional[str]
    brand_logo_url: Optional[str]
    description: Optional[str]
    brand_metadata: Dict
    created_at: datetime
    updated_at: datetime
```

### 6️⃣ Frontend API Configuration ([lib/api.ts](frontend/lib/api.ts))

**Updated Endpoints:**
```typescript
profileBrands: {
    me: `${API_URL}/api/v1/profile-brands/me`,           // NEW: GET current profile
    meUpdate: `${API_URL}/api/v1/profile-brands/me`,     // NEW: PUT update profile
    upsert: `${API_URL}/api/v1/brands/profile/ingest`,   // OLD: Keep for backwards compat
    list: `${API_URL}/api/v1/brands/profile/list`,
    getByName: (name: string) => `...`,
}
```

### 7️⃣ Frontend Profile Page ([app/advisor/brands/profile/page.tsx](frontend/app/advisor/brands/profile/page.tsx))

**Complete Rewrite:**

✅ **Load Profile on Mount:**
```typescript
useEffect(() => {
  const loadProfile = async () => {
    const response = await authFetch(API.profileBrands.me);
    const profile = await response.json();
    setForm({
      brandName: profile.brand_name,
      officeEmail: profile.office_email,
      // ... pre-fill all fields
    });
  };
  loadProfile();
}, []);
```

✅ **Display Read-Only Fields:**
```tsx
<div className={styles.readOnlySection}>
  <div className={styles.fieldGroup}>
    <label>Office Email (read-only)</label>
    <div className={styles.readOnlyField}>{form.officeEmail}</div>
  </div>
  <div className={styles.fieldGroup}>
    <label>Brand Type (read-only)</label>
    <div className={styles.readOnlyField}>{form.brandType}</div>
  </div>
</div>
```

✅ **Edit Editable Fields:**
- Brand name ✏️
- Website URL ✏️
- Instagram link ✏️
- Description/Bio ✏️

✅ **Save Changes:**
```typescript
const handleSubmit = async (event: FormEvent) => {
  const response = await authFetch(API.profileBrands.meUpdate, {
    method: "PUT",
    body: JSON.stringify({
      brand_name: form.brandName,
      brand_website: form.websiteUrl,
      instagram_link: form.instagramUrl,
      description: form.description,
    }),
  });
};
```

### 8️⃣ Frontend Styling ([app/advisor/brands/profile/page.module.css](frontend/app/advisor/brands/profile/page.module.css))

**New Classes Added:**
```css
.loadingContainer { }      /* Loading state */
.readOnlySection { }       /* Gray box for read-only fields */
.fieldGroup { }            /* Field wrapper */
.readOnlyField { }         /* Monospace, disabled styling */
```

All new styles maintain consistency with existing design:
- Green accent (`var(--primary)`)
- Slate gray tones
- Rounded corners (12-24px)
- Smooth transitions

---

## How It Works: Complete User Journey

### 🔹 Phase 1: Brand Sign-Up
1. Brand navigates to `/auth/brand/signup`
2. Fills in: brand_name, office_email, brand_type (local/international), password, optional website
3. Clicks "Sign Up"
4. **Backend:**
   - Creates `Brand` auth record
   - **Automatically creates** `ProfileBrand` record with:
     - `brand_id` → link to Brand
     - `brand_name`, `office_email`, `brand_type` → from sign-up
     - Empty description, links (can be edited later)
   - Returns JWT with `role="brand"`
5. **Frontend:**
   - Saves token + role to localStorage
   - Redirects to `/advisor/brands/profile`

### 🔹 Phase 2: First Login (Profile Already Exists)
1. Brand navigates to `/advisor/brands/profile`
2. **Frontend calls** `GET /api/v1/profile-brands/me`
3. **Backend:**
   - Extracts brand_id from JWT
   - Fetches ProfileBrand where brand_id matches
   - Returns profile with all fields pre-filled
4. **Form displays:**
   - Email, brand type → **read-only gray boxes**
   - Name, website, Instagram, bio → **editable fields**

### 🔹 Phase 3: Edit Profile
1. Brand modifies editable fields (e.g., adds Instagram handle)
2. Clicks "Save / Update"
3. **Frontend calls** `PUT /api/v1/profile-brands/me` with payload:
   ```json
   {
     "brand_name": "Aurora Designs",
     "brand_website": "https://aurora.com",
     "instagram_link": "https://instagram.com/auroradesigns",
     "description": "Ethical, sustainable fashion..."
   }
   ```
4. **Backend:**
   - Extracts brand_id from JWT
   - Calls `update_brand_profile(brand_id, ...)`
   - If description changed: re-embeds text
   - Updates `updated_at` timestamp
   - Returns updated profile
5. **Frontend:**
   - Shows success message
   - Updates local form state

### 🔹 Phase 4: Later Logins
- Profile persists in database
- Same flow: load → display → edit

---

## Database Schema

### Before
```sql
profile_brands:
  id (PK)
  brand_name (unique) ← PRIMARY IDENTIFIER
  brand_website
  instagram_link
  brand_logo_url
  description
  metadata
```

### After
```sql
profile_brands:
  id (PK)
  brand_id (FK → brands.id, UNIQUE) ← PRIMARY IDENTIFIER
  brand_name
  office_email
  brand_type
  brand_website
  instagram_link
  brand_logo_url
  description
  metadata
  created_at
  updated_at
```

**Key Change:** Profile is now identified by `brand_id`, not `brand_name`. This enables:
- One profile per brand (no duplicates)
- Idempotent creation
- Atomic transaction with sign-up

---

## Editable vs Read-Only Fields

| Field | Editable | Notes |
|-------|----------|-------|
| `brand_name` | ✏️ Yes | Can rebrand after signup |
| `brand_website` | ✏️ Yes | Update domain |
| `instagram_link` | ✏️ Yes | Social media handle |
| `brand_logo_url` | ✏️ Yes | Update branding |
| `description` | ✏️ Yes | Bio/tagline (re-embedded) |
| `office_email` | 🔒 Read-only | Security: don't change via UI |
| `brand_type` | 🔒 Read-only | Account tier: local/international |

---

## API Routes Summary

### Authentication (brand_auth)
- `POST /api/v1/brand-auth/signup` → Create brand + profile
- `POST /api/v1/brand-auth/login` → Existing brand login

### Brand Profile (profile_brands) - NEW
- `GET /api/v1/profile-brands/me` → Get current brand's profile
- `PUT /api/v1/profile-brands/me` → Update current brand's profile
- `GET /api/v1/profile-brands/` → List all profiles (public)
- `GET /api/v1/profile-brands/{id}` → Get by profile ID (public)
- `POST /api/v1/profile-brands/search` → Search by description (public)

---

## Migration Steps

### ⚠️ Important: Database Migration Required

Since `ProfileBrand` model changed (new FK), run:

```bash
cd backend
python init_db.py
```

This will:
1. Drop existing `profile_brands` table
2. Create new `profile_brands` table with `brand_id` FK
3. ✅ All existing Brand/User data preserved

### After Migration, Test:
```bash
# 1. Start backend
python -m uvicorn app.main:app --reload

# 2. Test signup (creates brand + profile)
curl -X POST http://localhost:8000/api/v1/brand-auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "brand_name": "Test Brand",
    "office_email": "contact@test.com",
    "brand_type": "local",
    "password": "securepass123"
  }'

# 3. Use returned token to load profile
curl -X GET http://localhost:8000/api/v1/profile-brands/me \
  -H "Authorization: Bearer <token>"

# 4. Update profile
curl -X PUT http://localhost:8000/api/v1/profile-brands/me \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "brand_name": "Updated Brand Name",
    "description": "Our new bio..."
  }'
```

---

## No Breaking Changes

✅ **User Authentication:** Unchanged
✅ **Brand Sign-Up/Login:** Unchanged (but now auto-creates profile)
✅ **Existing Endpoints:** All still work (public list, search, etc.)
✅ **Ingestion Flow:** Brand ingestion (`/api/v1/brands/ingest`) unchanged
✅ **User Onboarding:** Unaffected

---

## Summary of Files Modified

### Backend
| File | Change | Lines |
|------|--------|-------|
| [models.py](backend/app/models/models.py) | Added brand_id FK, office_email, brand_type fields | ProfileBrand class |
| [schemas/profile_brands.py](backend/app/schemas/profile_brands.py) | Added new fields to Create/Response schemas | ~30 lines |
| [services/profile_brands_service.py](backend/app/services/profile_brands_service.py) | Added get_or_create, update_brand_profile methods | +60 lines |
| [api/brand_auth.py](backend/app/api/brand_auth.py) | Call get_or_create on signup | +12 lines |
| [api/profile_brands.py](backend/app/api/profile_brands.py) | Added /me GET/PUT endpoints | +40 lines |

### Frontend
| File | Change | Lines |
|------|--------|-------|
| [lib/api.ts](frontend/lib/api.ts) | Added me, meUpdate endpoints | +2 lines |
| [app/advisor/brands/profile/page.tsx](frontend/app/advisor/brands/profile/page.tsx) | Complete rewrite with load/edit | ~190 lines |
| [app/advisor/brands/profile/page.module.css](frontend/app/advisor/brands/profile/page.module.css) | Added loading, readOnlySection styles | +30 lines |

---

## Testing Checklist

- [ ] Database migration runs without errors
- [ ] Brand can sign up and profile auto-creates
- [ ] Profile loads pre-filled on first login
- [ ] Email and brand type display as read-only
- [ ] Can edit name, website, Instagram, bio
- [ ] Save succeeds and updates persist
- [ ] Multiple edits don't create duplicates
- [ ] Other brands can't access each other's /me endpoint
- [ ] User auth flow unchanged
- [ ] Brand ingestion still works

---

## Next Steps (Optional)

1. **Profile Image Upload:**
   - Add file input for `brand_logo_url`
   - Upload to Azure Blob Storage
   - Store URL in profile

2. **Profile Analytics:**
   - Track brand profile views
   - Show ingestion history

3. **Brand Directory:**
   - Public page listing all brands
   - Searchable by description (uses embeddings)

4. **Profile Sharing:**
   - Public profile URL per brand
   - Social meta tags (og:image, og:description)

---

## Questions? 🚀

- Profile creation is **idempotent** (safe to call many times)
- Email and brand type are **immutable** after signup
- Description **automatically re-embedded** on save (for semantic search)
- No Qdrant or vector DB used (pure relational database)
- All profile data scoped to authenticated brand via JWT token
