import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api import auth, closet, outfits, stylist, user, brands, profile_brands, profile_qdrant
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory and serve static files
uploads_dir = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(closet.router, prefix=f"{settings.API_V1_STR}/closet", tags=["closet"])
app.include_router(outfits.router, prefix=f"{settings.API_V1_STR}/outfits", tags=["outfits"])
app.include_router(stylist.router, prefix=f"{settings.API_V1_STR}/stylist", tags=["stylist"])
app.include_router(user.router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
app.include_router(brands.router, prefix=f"{settings.API_V1_STR}/brands", tags=["brands"])
app.include_router(profile_brands.router, prefix=f"{settings.API_V1_STR}", tags=["profile-brands"])
app.include_router(profile_qdrant.router, prefix=f"{settings.API_V1_STR}", tags=["brands-profile"])



@app.get("/")
def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME} API"}
