import os
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api import auth, closet, outfits, stylist, user, clothing_ingestion
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.core.config import settings

logger = logging.getLogger(__name__)

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
app.include_router(closet.router, prefix=f"{settings.API_V1_STR}/closet", tags=["closet"])
app.include_router(clothing_ingestion.router)
app.include_router(outfits.router, prefix=f"{settings.API_V1_STR}/outfits", tags=["outfits"])
app.include_router(stylist.router, prefix=f"{settings.API_V1_STR}/stylist", tags=["stylist"])
app.include_router(user.router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])

@app.get("/")
def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME} API"}
