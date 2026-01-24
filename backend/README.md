# Backend (FastAPI) — Glam FinCommerce

A FastAPI backend for the AI Virtual Closet and Stylist experience. It powers authentication, Pinterest integration, closet item uploads + AI analysis, outfit management, and the stylist chat.

## Features Implemented

- Auth
  - Signup and login with JWT tokens
  - `GET /api/v1/users/me` returns the current user profile
- User Onboarding
  - `POST /api/v1/users/onboarding` stores profile and style preferences
  - Zep thread creation and graph updates for user profiling
- Pinterest Integration
  - `GET /api/v1/auth/pinterest/login` returns OAuth URL
  - `GET /api/v1/auth/pinterest/callback` exchanges code, saves token, and syncs boards/pins
  - `GET /api/v1/auth/pinterest/status` returns connection state
- Closet
  - `POST /api/v1/closet/upload` uploads a clothing item, runs AI analysis + optional background removal, stores to DB
  - `GET /api/v1/closet/items` lists items for the current user
  - `DELETE /api/v1/closet/items/{id}` removes an item
- Outfits
  - `GET /api/v1/outfits` lists outfits with expanded item details
  - `GET /api/v1/outfits/{id}` returns outfit details
  - `POST /api/v1/outfits/compare` evaluates a new item against your closet (AI)
  - `DELETE /api/v1/outfits/{id}` removes an outfit
- Stylist Chat
  - `POST /api/v1/stylist/chat` conversational assistant using closet, outfits, and user photo
  - `POST /api/v1/stylist/outfits/save` persists an AI-proposed outfit
- Static Uploads
  - Images served under `/uploads` (created automatically)

## Prerequisites

- Python 3.10+
- Optional: A virtual environment (recommended)

## Setup

```bash
# From repository root
cd backend

# Create venv (PowerShell on Windows)
python -m venv .venv
. .venv/Scripts/Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

## Environment Variables

The app loads settings from `.env` in `backend/` (see `app/core/config.py`). You can start with the defaults and add keys as needed.

Important keys:

- `SECRET_KEY` — JWT signing key
- `DATABASE_URL` — SQLite by default: `sqlite:///./virtual_closet.db`
- `GEMINI_API_KEY` — for AI services that use Gemini (optional depending on your flows)
- `ZEP_API_KEY` — for Zep Cloud profiling/graph
- `PINTEREST_APP_ID`, `PINTEREST_APP_SECRET`, `PINTEREST_REDIRECT_URI`, `PINTEREST_FRONTEND_REDIRECT` — OAuth setup
- Optional AWS for image storage: `S3_BUCKET`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`

Create `backend/.env` (example):

```env
PROJECT_NAME=AI Virtual Closet
API_V1_STR=/api/v1
SECRET_KEY=change-this-in-prod
ACCESS_TOKEN_EXPIRE_MINUTES=11520
DATABASE_URL=sqlite:///./virtual_closet.db

GEMINI_API_KEY=
ZEP_API_KEY=

PINTEREST_APP_ID=1543846
PINTEREST_APP_SECRET=your-secret-here
PINTEREST_REDIRECT_URI=http://localhost:3000/auth/pinterest-callback
PINTEREST_FRONTEND_REDIRECT=http://localhost:3000/onboarding

S3_BUCKET=virtual-closet-assets
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-east-1
```

## Initialize the Database

Tables and a demo user can be created via `init_db.py`.

```bash
# From backend/
python init_db.py
```

To seed rich demo data (items + curated outfits):

```bash
python seed_demo_data.py
```

## Run the App

Development server (auto-reload):

```bash
uvicorn app.main:app --reload
# Server: http://127.0.0.1:8000
# OpenAPI: http://127.0.0.1:8000/api/v1/openapi.json
```

## Quick API Reference

Base path: `/api/v1`

- Auth
  - `POST /auth/signup` → returns `{ access_token, token_type }`
  - `POST /auth/login` → returns `{ access_token, token_type }`
  - `GET /auth/pinterest/login` → `{ oauth_url, state }`
  - `GET /auth/pinterest/callback?code=...&user_id=...` → saves token + syncs data
  - `GET /auth/pinterest/status` → `{ connected, synced_at }`
- Users
  - `GET /users/me`
  - `POST /users/onboarding`
  - `POST /users/body-photo` (multipart file) → saves full-body photo
- Closet
  - `POST /closet/upload` (multipart file) → analyzes and stores item
  - `GET /closet/items`
  - `DELETE /closet/items/{id}`
- Outfits
  - `GET /outfits`
  - `GET /outfits/{id}`
  - `POST /outfits/compare` (multipart file)
  - `DELETE /outfits/{id}`
- Stylist
  - `POST /stylist/chat` → `{ reply, suggestions, ... }`
  - `POST /stylist/outfits/save`

Authorization: send the JWT as `Authorization: Bearer <token>` on protected endpoints.

## Notes

- Uploads directory is auto-created and mounted at `/uploads`.
- Some services (vision analysis, try-on, shopping advisor) may rely on external APIs or models; ensure relevant keys are set.
- Pinterest flow requires the frontend to pass `user_id` to the callback; the backend saves tokens and triggers data sync.

## Troubleshooting

- If you see "No user found" on closet uploads, ensure the demo user exists or log in and hit settings once to create your user context.
- For onboarding, verify `needsOnboarding` logic on the frontend and that tokens are sent to `/users/onboarding`.
- Check server logs for detailed messages; many endpoints include informative logging for flow tracing.
