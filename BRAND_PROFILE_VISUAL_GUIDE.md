# 🎯 Brand Profile Sync - Visual Guide

## The Flow

```
BEFORE (Old Way)
┌──────────────────┐
│ Brand Signs Up   │  1. Manual process
│ → Create Account │  2. Separate profile step
│ → Fill Profile   │  3. Data entry duplication
│ → Save Profile   │
└──────────────────┘

AFTER (New Way) ✨
┌──────────────────────────────────────────┐
│ Brand Signs Up                           │
│ ┌────────────────────────────────────┐  │
│ │ Enter:                             │  │
│ │ - Brand Name                       │  │
│ │ - Email                            │  │
│ │ - Type (local/international)       │  │
│ │ - Password                         │  │
│ │ - Website (optional)               │  │
│ └────────────────────────────────────┘  │
│                   │                      │
│                   ▼                      │
│ ✨ AUTO-PROFILE CREATED                 │
│ (no extra action needed)                │
│                   │                      │
│                   ▼                      │
│ Redirected to Profile Editor            │
│ (all fields pre-filled)                 │
│                   │                      │
│                   ▼                      │
│ Can edit:                               │
│ • Brand name                            │
│ • Website                               │
│ • Instagram                             │
│ • Bio                                   │
│ • Logo                                  │
│                   │                      │
│                   ▼                      │
│ Save → Done!                            │
└──────────────────────────────────────────┘
```

---

## UI Layout - Profile Form

```
╔═══════════════════════════════════════════════════════════════╗
║  🏢 Brand Profile                                             ║
║  Keep the brand bio, links, and avatar consistent.            ║
╚═══════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────┐
│ Profile Info                                                │
│ Instagram-style bio that stays on-brand.                   │
└─────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────┐ ┌────────────────────┐
│ 📧 Office Email (read-only)          │ │ 🏷️ Brand Type      │
│ ┌──────────────────────────────────┐ │ │ (read-only)        │
│ │ contact@aurora.com               │ │ │ ┌────────────────┐ │
│ └──────────────────────────────────┘ │ │ │ Local          │ │
│ (gray box, can't edit)               │ │ │ └────────────────┘ │
└──────────────────────────────────────┘ └────────────────────┘

┌──────────────────────────────────────┐ ┌────────────────────┐
│ Brand Name ✏️                        │ │ Website URL ✏️     │
│ ┌──────────────────────────────────┐ │ │ ┌────────────────┐ │
│ │ Aurora Designs                   │ │ │ │ https://...    │ │
│ └──────────────────────────────────┘ │ │ └────────────────┘ │
└──────────────────────────────────────┘ └────────────────────┘

┌────────────────────────────────────────────────────────────┐
│ Instagram URL ✏️                                           │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ https://instagram.com/auroradesigns                      ││
│ └──────────────────────────────────────────────────────────┘│
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│ Short Description / Bio ✏️                                 │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ Soft tailoring, sculptural knitwear, and essentials      ││
│ │ for creative directors worldwide.                        ││
│ │                                                          ││
│ └──────────────────────────────────────────────────────────┘│
└────────────────────────────────────────────────────────────┘

                    ┌─────────────────────────┐
                    │ ✅ Save / Update        │
                    └─────────────────────────┘
```

---

## Database Relationship

```
┌─────────────────────────┐
│       Brand             │  (Authentication)
│  ─────────────────      │
│  id (UUID) ◄─┐          │
│  brand_name  │ FK       │
│  office_email│ link     │
│  brand_type  │          │
│  password    │          │
│  website_url │          │
└─────────────────────────┘
                │
                │ 1:1
                │
┌─────────────────────────┐
│   ProfileBrand          │  (Profile/Bio)
│  ─────────────────      │
│  id (UUID)              │
│  brand_id ────────────►┘│
│  brand_name             │
│  office_email (copy)    │
│  brand_type (copy)      │
│  brand_website          │
│  instagram_link         │
│  brand_logo_url         │
│  description            │
│  brand_metadata (JSON)  │
└─────────────────────────┘

Key: Each Brand has exactly ONE ProfileBrand
     ProfileBrand linked via brand_id foreign key
     Email & type read-only (copies from Brand)
     Other fields editable
```

---

## API Call Sequence

### 1️⃣ Sign Up (Auto-Creates Profile)

```
POST /api/v1/brand-auth/signup
Body:
{
  "brand_name": "Aurora Designs",
  "office_email": "contact@aurora.com",
  "brand_type": "local",
  "password": "secure123",
  "website_url": "https://aurora.com"
}

Backend Processing:
  1. Create Brand (auth credentials)
  2. Create ProfileBrand (profile data) ← AUTO
  3. Link via brand_id FK ← AUTO
  4. Generate JWT with role="brand"

Response:
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

### 2️⃣ Load Profile (Pre-Fill Form)

```
GET /api/v1/profile-brands/me
Headers:
  Authorization: Bearer eyJ0eXAi...

Backend:
  1. Validate JWT (extract brand_id)
  2. Query: SELECT * FROM profile_brands WHERE brand_id = ?
  3. Return profile data

Response:
{
  "id": "uuid-profile-1",
  "brand_id": "uuid-brand-1",
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

Frontend:
  Form pre-filled with all fields:
  • brand_name → input
  • brand_website → input
  • instagram_link → input
  • description → textarea
  • office_email → read-only div
  • brand_type → read-only div
```

### 3️⃣ Update Profile (Save Changes)

```
PUT /api/v1/profile-brands/me
Headers:
  Authorization: Bearer eyJ0eXAi...
Body:
{
  "brand_name": "Aurora Designs",
  "brand_website": "https://aurora.com",
  "instagram_link": "https://instagram.com/auroradesigns",
  "brand_logo_url": null,
  "description": "Ethical, sustainable fashion."
}

Backend:
  1. Validate JWT (extract brand_id)
  2. Query: SELECT * FROM profile_brands WHERE brand_id = ?
  3. Update fields (skip email & type)
  4. If description changed: regenerate embedding
  5. Update updated_at timestamp
  6. Return updated profile

Response:
{
  "id": "uuid-profile-1",
  "brand_id": "uuid-brand-1",
  "brand_name": "Aurora Designs",
  "instagram_link": "https://instagram.com/auroradesigns",
  "description": "Ethical, sustainable fashion.",
  "updated_at": "2025-01-29T10:15:00"
  // ... other fields
}

Frontend:
  1. Show success message ✅
  2. Update form state
  3. Show updated timestamp
```

---

## Field Permissions Matrix

```
┌────────────────┬─────┬──────────┬──────────────────────────┐
│ Field          │ Get │ Set      │ Notes                    │
├────────────────┼─────┼──────────┼──────────────────────────┤
│ brand_name     │ ✅  │ ✏️ Edit  │ Can change after signup  │
│ brand_website  │ ✅  │ ✏️ Edit  │ Update domain anytime    │
│ instagram_link │ ✅  │ ✏️ Edit  │ Add social handle        │
│ brand_logo_url │ ✅  │ ✏️ Edit  │ Update branding          │
│ description    │ ✅  │ ✏️ Edit  │ Update bio (re-embedded) │
│ office_email   │ ✅  │ 🔒 RO   │ Never edit (for security)│
│ brand_type     │ ✅  │ 🔒 RO   │ Account tier (immutable) │
│ created_at     │ ✅  │ 🔒 Auto │ Set at profile creation  │
│ updated_at     │ ✅  │ 🔒 Auto │ Updated on each save     │
└────────────────┴─────┴──────────┴──────────────────────────┘

Legend:
  ✅ = Can read (via GET /me or public endpoints)
  ✏️ Edit = Can modify (via PUT /me)
  🔒 RO = Read-only (shown but can't edit)
  🔒 Auto = Auto-managed by system
```

---

## State Machine - Brand Journey

```
                    ┌──────────────┐
                    │   Start      │
                    └──────┬───────┘
                           │
                           ▼
                ┌──────────────────────┐
                │ Brand Visits         │
                │ /auth/brand/signup   │
                └──────┬───────────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │ Enter Signup Data    │
            │ (name, email, etc)   │
            └──────┬───────────────┘
                   │
                   ▼
        ┌──────────────────────────────┐
        │ Submit Signup               │
        │ POST /brand-auth/signup     │
        └──────┬───────────────────────┘
               │
    ┌──────────┴──────────┐
    │                     │
    ▼                     ▼
┌────────┐          ┌──────────────┐
│ Fail   │          │ Success      │
│ 400 ❌ │          │ ✅ JWT Token │
└────────┘          └──────┬───────┘
                           │
                    ┌──────┴────────┐
                    │               │
                    ▼               ▼
            ┌──────────────┐  ┌──────────────┐
            │ Save Token   │  │ Auto-Create  │
            │ To Storage   │  │ ProfileBrand │
            └──────┬───────┘  └──────┬───────┘
                   │                 │
                   └────────┬────────┘
                            │
                            ▼
              ┌─────────────────────────┐
              │ Redirect to             │
              │ /advisor/brands/profile │
              └────────┬────────────────┘
                       │
                       ▼
          ┌──────────────────────────┐
          │ Load Profile             │
          │ GET /profile-brands/me   │
          └────────┬─────────────────┘
                   │
                   ▼
        ┌──────────────────────────┐
        │ Pre-Fill Form            │
        │ (all fields loaded)      │
        └────────┬─────────────────┘
                 │
     ┌───────────┴───────────┐
     │                       │
     ▼                       ▼
┌──────────┐        ┌──────────────────┐
│ Brand    │        │ Brand Edits      │
│ Leaves   │        │ Form             │
│ (saves)  │        │ (change fields)  │
└──────────┘        └────────┬─────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ Click Save           │
                  │ PUT /profile-brands/ │
                  │ /me                  │
                  └────────┬─────────────┘
                           │
               ┌───────────┴───────────┐
               │                       │
               ▼                       ▼
           ┌────────┐        ┌──────────────────┐
           │ Fail   │        │ Success          │
           │ 400 ❌ │        │ ✅ Profile Saved │
           └────────┘        └────────┬─────────┘
                                      │
                                      ▼
                           ┌──────────────────┐
                           │ Show Success Msg │
                           │ Profile Updated! │
                           └──────────────────┘
```

---

## Error Scenarios

```
Scenario 1: Sign-up fails
─────────────────────────
POST /brand-auth/signup
└─ Email already exists
   └─ Response: 400 "A brand with this email already exists"
   └─ Result: No profile created, user stays on signup form

Scenario 2: Profile auto-create fails
──────────────────────────────────────
POST /brand-auth/signup
└─ Create Brand ✅
└─ Create Profile ❌ (DB error)
   └─ Result: Brand created, profile creation logged as warning
   └─ Signup succeeds (JWT returned)
   └─ User redirected to /profile, gets 404 "Profile not found"
   └─ (Admin can fix this)

Scenario 3: Load profile without auth
──────────────────────────────────────
GET /profile-brands/me
└─ No JWT token provided
   └─ Response: 401 "Missing or invalid authorization header"

Scenario 4: Load other brand's profile
───────────────────────────────────────
GET /profile-brands/me
Headers: Authorization: Bearer <other_brand_token>
└─ JWT has different brand_id
   └─ Response: 404 (they can't access another's /me)

Scenario 5: Update with invalid data
─────────────────────────────────────
PUT /profile-brands/me
Body: { "brand_name": "", "description": "..." }
└─ Brand name is required
   └─ Response: 422 "Field required"
   └─ Client validation prevents this

Scenario 6: Try to edit read-only fields
──────────────────────────────────────────
PUT /profile-brands/me
Body: { "office_email": "newemail@....", "brand_type": "international" }
└─ These fields ignored by backend
   └─ Response: 200 (success, but fields not changed)
   └─ Email & type remain unchanged
```

---

## Performance Profile

```
Operation              Query Count    Time (approx)
──────────────────────────────────────────────────
Sign up               2 (Brand, Profile)   50-100ms
Load profile          1 (by brand_id FK)   10-20ms
Update profile        1 (by brand_id FK)   20-50ms
List profiles         1 (with pagination)  50-200ms
Search profiles       1 + in-memory sort   100-500ms
──────────────────────────────────────────────────

Notes:
- FK indexes on brand_id ensure fast lookups
- No N+1 query problems
- Pagination prevents large result sets
- Search done in-memory (semantic similarity)
```

---

## Security Checklist

```
✅ Email immutable after signup
   └─ Only readable in profile, not editable via API

✅ Brand type immutable after signup
   └─ Prevents account tier escalation (local → international)

✅ JWT validation on /me endpoints
   └─ Extracts brand_id from token, checks role="brand"

✅ Brand isolation
   └─ Can only access their own profile via /me
   └─ Other brands' profiles visible only via public endpoints

✅ Password hashing
   └─ bcrypt with salt (same as user auth)

✅ No SQL injection
   └─ SQLModel ORM parameterized queries

✅ No privilege escalation
   └─ Can't modify auth fields from profile API

✅ No profile duplication
   └─ brand_id UNIQUE constraint
```

---

## Documentation Structure

```
BRAND_PROFILE_README.md (THIS FILE)
  └─ High-level overview
  └─ Feature list
  └─ Visual diagrams

BRAND_PROFILE_QUICKSTART.md
  └─ Quick setup instructions
  └─ API testing with curl
  └─ Common troubleshooting

BRAND_PROFILE_SYNC.md
  └─ Complete technical details
  └─ Code changes documented
  └─ Database schema explained
  └─ Migration instructions

File Changes:
  └─ backend/app/models/models.py
  └─ backend/app/api/brand_auth.py
  └─ backend/app/api/profile_brands.py
  └─ backend/app/services/profile_brands_service.py
  └─ backend/app/schemas/profile_brands.py
  └─ frontend/app/advisor/brands/profile/page.tsx
  └─ frontend/lib/api.ts
  └─ frontend/app/advisor/brands/profile/page.module.css
```

---

## Ready to Go! 🚀

1. **Run Migration:** `python init_db.py`
2. **Start Services:** Backend + Frontend
3. **Test:** Sign up a brand, verify profile auto-creates
4. **Deploy:** No breaking changes, safe to merge

Questions? Check BRAND_PROFILE_QUICKSTART.md or BRAND_PROFILE_SYNC.md
