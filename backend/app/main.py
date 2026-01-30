import os
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.api import auth, brand_auth, closet, outfits, stylist, user, clothing_ingestion, brands, profile_brands, profile_qdrant, ragas_analytics
from app.core.config import settings

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation error on {request.url.path}: {exc.errors()}")
    
    # Handle non-serializable body (like bytes from file uploads)
    body = exc.body if hasattr(exc, 'body') else None
    if isinstance(body, bytes):
        try:
            body = body.decode("utf-8")
        except:
            body = "<binary data>"
            
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
            "body": body
        },
    )

# Create uploads directory and serve static files
uploads_dir = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(brand_auth.router, prefix=f"{settings.API_V1_STR}/brand-auth", tags=["brand-auth"])
app.include_router(closet.router, prefix=f"{settings.API_V1_STR}/closet", tags=["closet"])
app.include_router(clothing_ingestion.router)
app.include_router(outfits.router, prefix=f"{settings.API_V1_STR}/outfits", tags=["outfits"])
app.include_router(stylist.router, prefix=f"{settings.API_V1_STR}/stylist", tags=["stylist"])
app.include_router(user.router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
app.include_router(brands.router, prefix=f"{settings.API_V1_STR}/brands", tags=["brands"])
app.include_router(profile_brands.router, prefix=f"{settings.API_V1_STR}", tags=["profile-brands"])
app.include_router(profile_qdrant.router, prefix=f"{settings.API_V1_STR}", tags=["brands-profile"])
app.include_router(ragas_analytics.router, prefix=f"{settings.API_V1_STR}", tags=["ragas-analytics"])



@app.get("/")
def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME} API"}
