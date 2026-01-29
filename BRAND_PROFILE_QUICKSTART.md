# 🚀 Quick Start: Brand Profile Sync

## What Just Happened?
✅ Brand profiles now **auto-initialize** from sign-up data
✅ Brands can **edit their profile** after login
✅ Email & brand type are **read-only** (for security)
✅ Everything is **database-driven** (no Qdrant)

---

## 1️⃣ Run Database Migration

**REQUIRED FIRST:**
```bash
cd backend
python init_db.py
```

This creates the `profile_brands` table with the new `brand_id` foreign key. Takes ~5 seconds.

---

## 2️⃣ Start Backend & Frontend

```bash
# Terminal 1: Backend
cd backend
python -m uvicorn app.main:app --reload

# Terminal 2: Frontend
cd frontend
npm run dev
```

---

## 3️⃣ Test the Flow

### Test Sign-Up + Auto-Create Profile
```bash
curl -X POST http://localhost:8000/api/v1/brand-auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "brand_name": "Aurora Designs",
    "office_email": "contact@aurora.com",
    "brand_type": "local",
    "password": "secure123",
    "website_url": "https://aurora.com"
  }'
```

**Response:** 
```json
{
  "access_token": "eyJ0eXAi...",
  "token_type": "bearer"
}
```

### Test Load Profile
```bash
curl -X GET http://localhost:8000/api/v1/profile-brands/me \
  -H "Authorization: Bearer eyJ0eXAi..."
```

**Response:**
```json
{
  "id": "uuid...",
  "brand_id": "uuid...",
  "brand_name": "Aurora Designs",
  "office_email": "contact@aurora.com",
  "brand_type": "local",
  "brand_website": "https://aurora.com",
  "instagram_link": null,
  "brand_logo_url": null,
  "description": null,
  "created_at": "2025-01-29T10:00:00",
  "updated_at": "2025-01-29T10:00:00"
}
```

### Test Update Profile
```bash
curl -X PUT http://localhost:8000/api/v1/profile-brands/me \
  -H "Authorization: Bearer eyJ0eXAi..." \
  -H "Content-Type: application/json" \
  -d '{
    "brand_name": "Aurora Designs",
    "instagram_link": "https://instagram.com/auroradesigns",
    "description": "Sustainable, ethical fashion for creative professionals."
  }'
```

---

## 4️⃣ Test in Browser

1. Go to `http://localhost:3000/auth/brand/signup`
2. Fill in brand info:
   - Brand name: "Aurora Designs"
   - Email: "contact@aurora.com"
   - Type: "Local"
   - Password: "test123"
3. Click "Sign Up"
4. **Auto-redirects to** `/advisor/brands/profile`
5. Profile pre-filled with sign-up data
6. Edit Instagram, bio, website
7. Click "Save / Update"
8. Success! ✨

---

## Architecture

```
Sign Up Flow:
┌─────────────────────────────────────────┐
│ Brand submits sign-up form              │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ POST /brand-auth/signup                 │
└────────────────┬────────────────────────┘
                 │
      ┌──────────┴──────────┐
      │                     │
      ▼                     ▼
┌──────────────┐    ┌──────────────────┐
│ Create Brand │    │ Create Profile   │
│ (auth creds) │    │ (profile data)   │
└──────────────┘    └──────────────────┘
      │                     │
      └──────────┬──────────┘
                 │
                 ▼
      ┌────────────────────┐
      │ Return JWT token   │
      │ role="brand"       │
      └────────────────────┘
                 │
                 ▼
      ┌─────────────────────────┐
      │ Redirect to /me profile │
      │ (pre-filled form)       │
      └─────────────────────────┘
```

---

## Database Schema

```sql
-- Brand authentication record
CREATE TABLE brands (
  id UUID PRIMARY KEY,
  brand_name VARCHAR UNIQUE NOT NULL,
  office_email VARCHAR UNIQUE NOT NULL,
  brand_type VARCHAR,  -- "local" | "international"
  hashed_password VARCHAR NOT NULL,
  website_url VARCHAR,
  logo_url VARCHAR,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);

-- Brand profile (linked via brand_id)
CREATE TABLE profile_brands (
  id UUID PRIMARY KEY,
  brand_id UUID UNIQUE NOT NULL REFERENCES brands(id),  -- NEW FK
  brand_name VARCHAR NOT NULL,
  office_email VARCHAR,  -- NEW: from sign-up
  brand_type VARCHAR,    -- NEW: from sign-up (local|international)
  brand_website VARCHAR,
  instagram_link VARCHAR,
  brand_logo_url VARCHAR,
  description TEXT,
  brand_metadata JSON,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

---

## Editable Fields

| Field | Editable | Why |
|-------|----------|-----|
| Brand Name | ✏️ | Rebrand anytime |
| Website | ✏️ | Update domain |
| Instagram | ✏️ | Social link |
| Logo URL | ✏️ | New branding |
| Bio/Description | ✏️ | Update brand story |
| Email | 🔒 | Security: linked to account |
| Brand Type | 🔒 | Account tier (local/intl) |

---

## API Endpoints

### Brand Auth
```
POST   /api/v1/brand-auth/signup          Create brand + auto profile
POST   /api/v1/brand-auth/login           Login brand
GET    /api/v1/brand-auth/me              Get current brand info
```

### Brand Profile (NEW)
```
GET    /api/v1/profile-brands/me          Get authenticated brand's profile
PUT    /api/v1/profile-brands/me          Update authenticated brand's profile
GET    /api/v1/profile-brands/            List all profiles (public)
GET    /api/v1/profile-brands/{id}        Get by profile ID (public)
POST   /api/v1/profile-brands/search      Search by description (public)
```

**All /me endpoints** require `Authorization: Bearer <token>` header

---

## Key Files Changed

### Backend
- `app/models/models.py` – Added brand_id FK to ProfileBrand
- `app/api/brand_auth.py` – Auto-create profile on signup
- `app/api/profile_brands.py` – New /me GET/PUT endpoints
- `app/services/profile_brands_service.py` – New service methods
- `app/schemas/profile_brands.py` – Updated schemas

### Frontend
- `app/advisor/brands/profile/page.tsx` – Load + edit profile
- `lib/api.ts` – New /me endpoints
- `app/advisor/brands/profile/page.module.css` – New styles

---

## Troubleshooting

### Q: "no such table: profile_brands" error
**A:** Run `python init_db.py` in backend directory

### Q: Profile not loading on first login
**A:** Check browser console for 404/401 errors. Verify JWT token includes `role="brand"`

### Q: Can't edit email or brand type
**A:** That's correct! Those are read-only after signup for security

### Q: Changes not saving
**A:** Check network tab in DevTools. Verify PUT request to `/api/v1/profile-brands/me`

---

## What's Next?

Optional enhancements:
- [ ] Image upload widget for brand logo
- [ ] Profile analytics dashboard
- [ ] Public brand directory with search
- [ ] Profile sharing (social meta tags)

---

## Questions?

Check [BRAND_PROFILE_SYNC.md](BRAND_PROFILE_SYNC.md) for complete implementation details.
