"""
Main entry point for the FastAPI application.
"""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.api.routers import auth, docs, scan
from app.core.logging import setup_logging, logger

# Initialize Logging
setup_logging()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://192.168.56.1:3000",
    ],
    allow_credentials=True, # Switching back to True for specific origins
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure uploads directory exists before mounting
import os
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# Serve uploaded files
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"DEBUG: Incoming {request.method} request to {request.url}")
    response = await call_next(request)
    print(f"DEBUG: Response status: {response.status_code}")
    return response

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred."},
    )

# Include Routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(docs.router, prefix="/api/docs", tags=["Documents"])
app.include_router(scan.router, prefix="/api/scan", tags=["Scanning"])

@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting {settings.APP_NAME}...")
    # Create tables automatically for SQLite
    from app.database import engine, Base
    import app.models # Ensure models are registered
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables verified/created.")

    # Pre-load ML models to speed up first scan
    logger.info("Pre-loading ML models (this may take a moment)...")
    from app.services.plagiarism import get_plagiarism_engine
    from app.services.ai_audit import AIAuditService
    get_plagiarism_engine()
    # Pre-warm AI Audit
    audit_service = AIAuditService()
    logger.info("ML models loaded successfully.")

@app.get("/")
async def root():
    return {"message": "Welcome to PlagX API", "version": settings.APP_VERSION}
