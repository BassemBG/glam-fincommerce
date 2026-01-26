# Creating Persona: Pinterest + Profiling + Zep Cloud Flow

## Overview

The app builds a rich, multi-dimensional user persona by collecting data from **onboarding**, **body analysis**, **wardrobe uploads**, **outfit composition**, **closet summaries**, and **Pinterest integration**—all of which flow into **Zep Cloud** as natural-language messages. Zep then automatically ingests these into a **user graph** for intelligent styling recommendations.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Data Sources                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. ONBOARDING              2. BODY PHOTO              3. CLOSET │
│     ↓                           ↓                          ↓      │
│  - Gender                    - Body Type              - Items    │
│  - Age                       - Skin Tone              - Colors   │
│  - Country                   - Height                 - Vibes    │
│  - Style Profile             - Morphology             - Materials│
│  - Budget                    - Physical Desc          - Stats    │
│  - Preferences               ↓                        ↓          │
│  ↓                           Zep Message             Zep Message│
│  Zep Message                 "User's Body            "Closet    │
│  "Onboarding Profile"        Morphology..."          Summary"   │
│                                                                   │
│  4. OUTFIT CREATION         5. PINTEREST SYNC                   │
│     ↓                           ↓                                │
│  - Items Selected            - Boards                           │
│  - Style Tags               - Pins                             │
│  - Occasion                 - Colors                           │
│  - Vibe                     - Styles                           │
│  - AI Metadata              - Trends                           │
│  ↓                          ↓                                   │
│  Zep Message                Zep Message                         │
│  "Outfit: [description]"    "Pinterest: [boards,              │
│                              pins, palette, styles]"            │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                                ↓
                         ┌───────────────┐
                         │  Zep Cloud    │
                         │  ───────────  │
                         │ Thread ID     │
                         │ (Messages)    │
                         └───────────────┘
                                ↓
                  ┌─────────────────────────────┐
                  │   Zep Graph Ingestion       │
                  │  (Automatic from Messages)  │
                  ├─────────────────────────────┤
                  │ - User Node                 │
                  │ - Entities: Body Type,      │
                  │   Styles, Colors, etc.      │
                  │ - Relationships: HAS_STYLE, │
                  │   LIKES_COLOR, etc.         │
                  │ - Embeddings                │
                  └─────────────────────────────┘
                                ↓
                  ┌─────────────────────────────┐
                  │   Stylist Agent             │
                  │   (LangGraph + Zep)         │
                  ├─────────────────────────────┤
                  │ Query Persona               │
                  │ → Outfit Recommendations    │
                  │ → Budget Constraints        │
                  │ → Style Advice              │
                  └─────────────────────────────┘
```

---

## Data Flow Walkthrough

### 1. Onboarding Profile → Zep

**File:** `frontend/app/onboarding/page.tsx`  
**Backend:** `backend/app/api/user.py` → `/users/onboarding`

**Frontend → Backend:**
```json
{
  "gender": "female",
  "age": 28,
  "country": "Tunisia",
  "daily_style": "modern chic",
  "color_preferences": ["black/white/grey", "pastels"],
  "fit_preference": "regular",
  "price_comfort": "medium",
  "budget_limit": 500,
  "clothing_description": "I have a classic wardrobe...",
  "styled_combinations": "I usually pair..."
}
```

**Backend Processing:**
```python
# backend/app/api/user.py
@router.post("/onboarding")
async def complete_onboarding(
    payload: dict,
    current_user: User = Depends(get_current_user)
):
    # Store in User model
    user.gender = payload.get("gender")
    user.age = payload.get("age")
    user.country = payload.get("country")
    # ... etc
    user.onboarding_completed = True
    db.commit()
    
    # Post to Zep
    thread_id = user.zep_thread_id
    add_onboarding_to_graph(
        user_id=user.id,
        onboarding_data=payload,
        user_email=user.email,
        thread_id=thread_id
    )
```

**Zep Message Composed:** `backend/app/services/zep_service.py::add_onboarding_to_graph()`
```
Content:
"Onboarding Profile:
- Gender: female
- Age: 28
- Country: Tunisia
- Daily Style: modern chic
- Color Preferences: black/white/grey, pastels
- Fit Preference: regular
- Price Comfort: medium
- Budget Limit: $500
- Description: I have a classic wardrobe...
- Styled Combinations: I usually pair..."

Metadata:
{
  "source": "onboarding",
  "user_id": "...",
  "user_email": "..."
}
```

**Zep Ingestion:** Automatically extracts entities like "female", "modern chic", "pastels", "Tunisia", "$500" into the user graph.

---

### 2. Body Photo Upload → Morphology → Zep

**File:** `frontend/app/settings/page.tsx`  
**Backend:** `backend/app/api/user.py` → `/users/body-photo`

**Frontend → Backend:**
- Upload binary image file (e.g., full-body selfie)

**Backend Processing:**
```python
# backend/app/api/user.py
@router.post("/users/body-photo")
async def upload_body_photo(
    file: UploadFile,
    current_user: User = Depends(get_current_user)
):
    # 1. Save image to storage
    image_url = await storage_service.upload_file(...)
    
    # 2. Analyze via Groq Vision
    analysis = await vision_analyzer.analyze_body_type(file_content)
    # Returns: { "body_type": "pear", "skin_tone": "warm", "height": "5'6\"", ... }
    
    # 3. Post to Zep
    add_morphology_to_thread(
        user_id=current_user.id,
        thread_id=current_user.zep_thread_id,
        morphology_data=analysis
    )
    
    return { "image_url": image_url, "morphology": analysis }
```

**Zep Message Composed:** `backend/app/services/zep_service.py::add_morphology_to_thread()`
```
Content:
"User's Body Morphology and Physical Description:
- Body Type: Pear-shaped
- Skin Tone: Warm undertones
- Estimated Height: 5'6\"
- Hair Characteristics: ...
- Proportions: ...
Details: This body type benefits from A-line cuts, darker tones on bottom..."

Metadata:
{
  "source": "body_morphology",
  "user_id": "...",
  "body_type": "pear",
  "skin_tone": "warm"
}
```

**Zep Ingestion:** Extracts "pear-shaped", "warm skin tone", "5'6\"" etc. as user attributes linked to the User node.

---

### 3. Clothing Item Upload → Item Stored Locally + Qdrant (Not Yet in Zep)

**File:** `frontend/app/upload/page.tsx`  
**Backend:** `backend/app/api/closet.py` → `/closet/upload`

**Frontend → Backend:**
- Upload binary image file (e.g., a shirt)

**Backend Processing:**
```python
# backend/app/api/closet.py
@router.post("/closet/upload")
async def upload_clothing(file: UploadFile, current_user: User = Depends(...)):
    # 1. Save to storage
    image_url = await storage_service.upload_file(...)
    
    # 2. Analyze via Groq Vision
    analysis = await vision_analyzer.analyze_clothing(file_content)
    # Returns: {
    #   "category": "top",
    #   "sub_category": "shirt",
    #   "colors": ["white", "blue"],
    #   "vibe": "casual",
    #   "material": "cotton",
    #   "styling_tips": "..."
    # }
    
    # 3. Save to SQL (ClothingItem)
    db_item = ClothingItem(
        user_id=current_user.id,
        category="top",
        sub_category="shirt",
        image_url=image_url,
        metadata_json=analysis
    )
    db.add(db_item)
    db.commit()
    
    # 4. Index in Qdrant (vector search)
    await clip_qdrant_service.index_item(db_item.id, image_url, analysis)
    
    return { "id": db_item.id, "analysis": analysis, "image_url": image_url }
```

**Current State:** 
- ✅ Items stored in **SQL** (ClothingItem)
- ✅ Items indexed in **Qdrant** (CLIP embeddings + metadata)
- ⚠️ **NOT** posted to Zep as individual messages (only closet summary is)

**Why Not Individual Items to Zep?**
- Too verbose: 100 items = 100 messages (noise)
- **Better approach:** Post a closet summary periodically (see step 5 below)

---

### 4. Outfit Creation & Save → Zep

**File:** `frontend/app/stylist/page.tsx`  
**Backend:** `backend/app/api/stylist.py` → `/stylist/outfits/save`

**Frontend → Backend:**
```json
{
  "items": ["item_id_1", "item_id_2", "item_id_3"],
  "occasion": "casual brunch",
  "vibe": "relaxed chic",
  "tryon_image": "<base64 or URL>"
}
```

**Backend Processing:**
```python
# backend/app/api/stylist.py
@router.post("/stylist/outfits/save")
async def save_outfit(payload: dict, current_user: User = Depends(...)):
    # 1. Generate AI metadata
    items = [db.query(ClothingItem).get(id) for id in payload["items"]]
    metadata = await stylist_chat.generate_outfit_metadata(items)
    # Returns: { "name": "Urban Explorer", "description": "...", "style_tags": [...] }
    
    # 2. Save outfit to SQL
    outfit = Outfit(
        user_id=current_user.id,
        items=json.dumps(payload["items"]),
        occasion=payload.get("occasion"),
        vibe=payload.get("vibe"),
        description=metadata.get("description"),
        style_tags=json.dumps(metadata.get("style_tags", []))
    )
    db.add(outfit)
    db.commit()
    
    # 3. Index in Qdrant
    await clip_qdrant_service.index_outfit(outfit.id, payload.get("tryon_image"), metadata)
    
    # 4. Post to Zep
    add_outfit_summary_to_graph(
        user_id=current_user.id,
        summary={
            "summary": metadata.get("description"),
            "items": [item.sub_category for item in items],
            "colors": [...],
            "style_keywords": metadata.get("style_tags")
        },
        image_url=payload.get("tryon_image"),
        thread_id=current_user.zep_thread_id
    )
    
    return { "id": outfit.id, "metadata": metadata, ... }
```

**Zep Message Composed:** `backend/app/services/zep_service.py::add_outfit_summary_to_graph()`
```
Content:
"Outfit: Urban Explorer
Items: shirt, jeans, blazer
Colors: white, navy, cream
Style: casual, minimalist, #streetwear, #chic
Occasion: casual brunch
Vibe: relaxed chic
Image: https://..."

Metadata:
{
  "source": "outfit_save",
  "user_id": "...",
  "style_keywords": ["streetwear", "chic"],
  "occasion": "casual brunch"
}
```

**Zep Ingestion:** Extracts outfit attributes and links them as SAVED_OUTFIT relationships.

---

### 5. Closet Summary (Wardrobe Overview) → Zep

**File:** `backend/app/api/closet.py` → `/closet/summarize`

**Trigger:** User clicks "Summarize Closet" in Settings (or via API)

**Backend Processing:**
```python
# backend/app/api/closet.py
@router.post("/closet/summarize")
async def summarize_closet(current_user: User = Depends(...)):
    # 1. Fetch all items from Qdrant
    items = await clip_qdrant_service.get_user_items(current_user.id, limit=300)
    
    # 2. Generate summary
    summary = await stylist_chat.generate_closet_summary(
        items=items,
        user_profile={
            "gender": current_user.gender,
            "country": current_user.country,
            "budget_limit": current_user.budget_limit,
            "style": current_user.daily_style
        }
    )
    # Returns: {
    #   "headline": "Modern Minimalist with Seasonal Flair",
    #   "summary": "A curated 62-piece wardrobe...",
    #   "stats": {
    #     "total_items": 62,
    #     "top_categories": ["top", "bottom", "outerwear"],
    #     "color_palette": ["white", "black", "navy"],
    #     "style_vibes": ["minimalist", "casual chic"],
    #     "seasonal_coverage": ["spring", "fall"]
    #   },
    #   "insights": ["Add statement outerwear...", ...],
    #   "tags": ["capsule", "minimalist"]
    # }
    
    # 3. Post to Zep
    add_closet_summary_to_graph(
        user_id=current_user.id,
        summary=summary,
        user_email=current_user.email,
        thread_id=current_user.zep_thread_id
    )
    
    return { "summary": summary, "count": 62, "thread_id": ... }
```

**Zep Message Composed:** `backend/app/services/zep_service.py::add_closet_summary_to_graph()`
```
Content:
"Closet Summary — Modern Minimalist with Seasonal Flair
Items: 62
Top Categories: top, bottom, outerwear
Palette: white, black, navy, cream
Vibes: minimalist, casual chic
Seasonal: spring, fall, summer
Insights:
- Neutral base: black, white, grey tees and bottoms
- Layering core: denim jacket or lightweight blazer
- Footwear trio: clean sneakers, smart boots, dress shoe
Tags: capsule, minimalist

Details: A curated 62-piece wardrobe showcasing tops, bottoms, outerwear. 
Palette leans white, black, navy; vibes skew minimalist, casual chic. 
Seasonal readiness: spring, fall, summer."

Metadata:
{
  "source": "closet_summary",
  "user_id": "...",
  "total_items": 62,
  "top_categories": ["top", "bottom", "outerwear"],
  "tags": ["capsule", "minimalist"]
}
```

**Zep Ingestion:** Extracts wardrobe characteristics and uses as context for future styling.

---

### 6. Pinterest Integration → Sync → Zep

**File:** `frontend/app/settings/page.tsx`  
**Backend:** `backend/app/api/auth.py` → `/auth/pinterest/callback` → `backend/app/services/pinterest_service.py`

**Flow:**
```
1. User clicks "Connect Pinterest"
   ↓
2. Frontend redirects to Pinterest OAuth
   ↓
3. Pinterest redirects back to /auth/pinterest/callback?code=...&state=...
   ↓
4. Backend exchanges code for access token
   ↓
5. Backend stores token in DB (PinterestToken)
   ↓
6. PinterestPersonaService.sync_user_pinterest_data() runs
   - Fetches all boards
   - Fetches all pins from each board
   - Extracts colors, styles, descriptions
   ↓
7. Each pin → add_pin_to_user_graph() → Zep Message
   ↓
8. update_user_persona_with_outfit_summaries() → Zep Message with board summary
```

**Backend Processing:**
```python
# backend/app/api/auth.py
@router.get("/pinterest/callback")
def pinterest_callback(code: str, user_id: str, db: Session = ...):
    # 1. Exchange code for token
    token_data = PinterestOAuthService.exchange_code_for_token(code)
    
    # 2. Save token
    PinterestOAuthService.save_token_to_db(user_id, token_data, db)
    
    # 3. Sync Pinterest data
    persona_service = PinterestPersonaService(db)
    sync_result = persona_service.sync_user_pinterest_data(
        user_id=user_id,
        access_token=token_data.get("access_token")
    )
    
    return { "success": True, "boards_count": ..., "pins_count": ... }
```

**Zep Messages (one per pin or summary):**
```
Content (per pin):
"Pinterest Pin from [board_name]:
Description: A white minimalist bedroom with plants...
Colors: white, green, grey
Styles: minimalist, scandinavian
Source: https://..."

Content (board summary):
"Pinterest Boards Overview:
- Interior Inspiration (35 pins): minimalist, white, plants
- Fashion Looks (82 pins): casual chic, denim, neutral
- Travel Ideas (15 pins): beach, tropical, vibrant
Style Insights: minimalist, casual, natural colors
Color Palette: white, grey, green, blue, beige"
```

**Zep Ingestion:** Creates comprehensive style nodes from curated pins; establishes preferences like "minimalist", "casual chic", "white color palette".

---

## Zep Cloud: Persona Graph Building

### How Zep Ingests Messages → Persona

**Process:**
1. Message posted to `thread/{thread_id}/messages`
2. Zep Cloud **automatically** processes message text
3. Extracts **entities** (adjectives, nouns, preferences)
4. Creates/updates **User graph node** with facts
5. Links **relationships** (HAS_STYLE, LIKES_COLOR, etc.)

### Current Zep Graph Structure

```
[User Node]
├── HAS_STYLE: ["minimalist", "casual chic", "modern"]
├── LIKES_COLOR: ["white", "black", "navy", "pastels"]
├── BODY_TYPE: "pear"
├── SKIN_TONE: "warm"
├── LOCATION: "Tunisia"
├── BUDGET: "$500"
├── PREFERRED_MATERIALS: ["cotton", "linen"]
├── SEASONAL_PREFERENCE: ["spring", "fall"]
├── OUTFIT_HISTORY: [outfit_1, outfit_2, ...]
└── PINTEREST_INSPIRATION: [pin_1, pin_2, ...]
```

### How Stylist Uses Persona

**File:** `backend/app/agents/stylist_graph.py`

```python
# When user asks for outfit recommendation:
# 1. Query Zep graph for user persona
persona = zep_client.graph.get_user_entity(user_id)

# 2. Extract preferences
preferred_styles = persona.get("HAS_STYLE")
budget = persona.get("BUDGET")
body_type = persona.get("BODY_TYPE")

# 3. Pass to LangGraph Agent
# Agent uses this context to:
#   - Filter wardrobe by user's body type
#   - Match colors to skin tone
#   - Respect budget constraints
#   - Suggest outfits aligned with learned style
#   - Avoid patterns they don't like
```

---

## Data Flow Summary Table

| Data Source | File | Backend Endpoint | Zep Message Type | Frequency |
|---|---|---|---|---|
| **Onboarding** | `onboarding/page.tsx` | `POST /users/onboarding` | "Onboarding Profile" | Once (at signup) |
| **Body Photo** | `settings/page.tsx` | `POST /users/body-photo` | "Body Morphology" | As needed (update) |
| **Clothing Item** | `upload/page.tsx` | `POST /closet/upload` | *(not posted individually)* | Per item |
| **Outfit Save** | `stylist/page.tsx` | `POST /stylist/outfits/save` | "Outfit Summary" | Per outfit created |
| **Closet Summary** | `settings/page.tsx` | `POST /closet/summarize` | "Closet Summary" | On demand |
| **Pinterest** | `settings/page.tsx` → OAuth | `GET /auth/pinterest/callback` | "Pinterest Pins + Board Summary" | Per sync |

---

## Key Files & Responsibilities

### Frontend
- **`app/onboarding/page.tsx`** — Onboarding form (6 steps) → POST onboarding profile
- **`app/settings/page.tsx`** — Body photo upload, Pinterest connect, closet summary trigger
- **`app/upload/page.tsx`** — Clothing item upload
- **`app/stylist/page.tsx`** — Outfit creation & save

### Backend: API Routes
- **`app/api/auth.py`** — Pinterest OAuth callback & sync trigger
- **`app/api/user.py`** — Onboarding, body photo upload
- **`app/api/closet.py`** — Item upload, closet summary
- **`app/api/stylist.py`** — Outfit save

### Backend: Services
- **`app/services/zep_service.py`** — All Zep posting helpers
  - `add_onboarding_to_graph()` — Onboarding → Zep
  - `add_morphology_to_thread()` — Body analysis → Zep
  - `add_outfit_summary_to_graph()` — Outfit → Zep
  - `add_closet_summary_to_graph()` — Closet summary → Zep
  - `add_pin_to_user_graph()` — Pinterest pin → Zep
  - `update_user_persona_with_outfit_summaries()` — Batch outfit updates
  - `update_user_persona_with_pinterest_data()` — Pinterest board summary → Zep

- **`app/services/pinterest_service.py`** — OAuth & Pinterest data fetch
- **`app/services/stylist_chat.py`** — AI metadata generation (outfits, closet summary)
- **`app/services/vision_analyzer.py`** — Groq Vision for body & clothing analysis
- **`app/services/clip_qdrant_service.py`** — Vector indexing & retrieval (Qdrant)

### Database
- **`app/models/models.py`**
  - `User` — Stores onboarding profile, zep_thread_id
  - `ClothingItem` — Individual clothing pieces
  - `Outfit` — Saved outfit combinations
  - `PinterestToken` — OAuth token storage
  - `ClothingIngestionHistory` — Historical analysis records

### Zep Cloud
- **Thread:** Stores all messages (source of truth for persona)
- **Graph:** Auto-ingested user persona (entities, relationships)
- **API:** Queried by Stylist Agent for recommendations

---

## Current State & Gaps

### ✅ Implemented
- Onboarding → Zep
- Body morphology → Zep
- Outfit summaries → Zep
- Closet summary → Zep (newly added)
- Pinterest pins + boards → Zep
- SQL storage for user profile, items, outfits
- Qdrant vector indexing for items & outfits
- Stylist Agent using Zep persona for recommendations

### ⚠️ Gaps / Future Work
- **Individual item posting to Zep:** Currently, items are stored in SQL + Qdrant but NOT posted individually (too noisy). Consider posting on first add or in batch summaries.
- **Periodic closet summary:** Currently on-demand. Could add a cron job to re-summarize monthly.
- **Persona graph queries:** Stylist Agent currently queries via LLM; could add direct graph queries for structured data.
- **Feedback loop:** No mechanism to learn what outfit recommendations were saved/liked; could add explicit feedback to refine graph.
- **Pinterest updates:** One-time sync; no polling for new pins or board changes.

---

## Testing the Persona Flow

### 1. Sign Up & Onboarding
```bash
# In Postman or curl:
POST http://localhost:8000/api/v1/auth/signup
{
  "email": "test@example.com",
  "password": "password123",
  "full_name": "Test User"
}

# Complete onboarding
POST http://localhost:8000/api/v1/users/onboarding
Authorization: Bearer <token>
{
  "gender": "female",
  "age": 28,
  "country": "Tunisia",
  "daily_style": "modern chic",
  "color_preferences": ["black", "white"],
  "budget_limit": 500
}
```

### 2. Upload Body Photo
```bash
POST http://localhost:8000/api/v1/users/body-photo
Authorization: Bearer <token>
Content-Type: multipart/form-data
file: <image.jpg>

# Response includes morphology data
```

### 3. Upload Clothing Items
```bash
POST http://localhost:8000/api/v1/closet/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data
file: <shirt.jpg>
```

### 4. Create & Save Outfit
```bash
POST http://localhost:8000/api/v1/stylist/outfits/save
Authorization: Bearer <token>
{
  "items": ["item_id_1", "item_id_2"],
  "occasion": "casual brunch",
  "vibe": "relaxed chic"
}
```

### 5. Trigger Closet Summary
```bash
POST http://localhost:8000/api/v1/closet/summarize
Authorization: Bearer <token>
```

### 6. Connect Pinterest
1. Visit `http://localhost:3000/settings`
2. Click "Connect Pinterest"
3. Authorize on Pinterest
4. Callback syncs data automatically

### 7. Verify Zep Messages
```bash
# Query Zep thread messages (requires Zep SDK or API):
zep_client.thread.get(thread_id=user.zep_thread_id)

# Should see messages:
# - Onboarding Profile
# - Body Morphology
# - Multiple outfit summaries
# - Closet Summary
# - Pinterest pins & boards
```

---

## Debugging

**Check if Zep client is initialized:**
```python
# backend/app/services/zep_service.py
print(f"zep_client: {zep_client}")  # Should not be None
```

**Check if thread_id is being stored:**
```python
# In database:
SELECT id, email, zep_thread_id FROM users;
```

**Monitor Zep postings in logs:**
```
[Zep] ****ADD_ONBOARDING_TO_GRAPH**** ENTRY
[Zep] ****SENDING_MESSAGE**** to thread thread_xxx
[Zep] ****SUCCESS**** Onboarding message added to thread thread_xxx
```

**If nothing posting to Zep:**
1. Check `ZEP_API_KEY` is set in `.env`
2. Check `zep_client` is not None at startup
3. Verify `thread_id` is not None when posting
4. Check exception logs for API errors

---

## Architecture Decisions

1. **Messages as source of truth:** Instead of manual graph writes, we post natural-language messages. Zep ingests them automatically. This avoids duplication and keeps the system simple.

2. **No individual item messages:** Too verbose. Instead, we summarize wardrobe periodically.

3. **Qdrant for vectors, SQL for records:** SQL stores ownership & metadata; Qdrant provides vector search for similar items/outfits.

4. **Async flow:** Body analysis, outfit metadata, closet summary all use AI services (async); results saved + posted to Zep.

5. **Pinterest as flavor, not filter:** Pinterest pins enrich persona (preferred styles, colors) but don't restrict closet. User can ignore.

---

## Summary

**Persona is built from:**
1. **Explicit user input** (onboarding profile)
2. **Physical analysis** (body morphology)
3. **Wardrobe composition** (closet items → summary)
4. **Outfit choices** (saved combinations)
5. **Curated inspiration** (Pinterest boards & pins)

**All flows through:**
- **Frontend** → HTTP POST with data
- **Backend services** → Normalize & analyze
- **Zep Cloud** → Store as messages, auto-ingest as persona graph
- **Stylist Agent** → Query persona, generate recommendations

**Result:** A rich, multi-dimensional understanding of user style that evolves as they interact with the app.
