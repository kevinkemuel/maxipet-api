from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from slowapi.errors import RateLimitExceeded
from app.config import settings
from app.middleware import (
    limiter,
    rate_limit_exceeded_handler,
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler,
    logging_middleware
)
from app.routers.v1 import (
    products_router,
    webhooks_router,
    inventory_router,
    health_router
)
from app.utils.logger import logger

# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add rate limiter state
app.state.limiter = limiter

# CORS middleware
cors_origins = settings.cors_origins.split(",") if settings.cors_origins != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging middleware
app.middleware("http")(logging_middleware)

# Exception handlers
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# API v1 router
api_v1 = APIRouter(prefix=f"/api/{settings.api_version}")

# Include all v1 routers
api_v1.include_router(products_router)
api_v1.include_router(webhooks_router)
api_v1.include_router(inventory_router)
api_v1.include_router(health_router)

# Include v1 router in main app
app.include_router(api_v1)

# Root endpoint (no auth required)
@app.get("/")
async def root():
    """
    Root endpoint - API status
    
    No authentication required
    """
    return {
        "status": "online",
        "name": settings.api_title,
        "version": settings.api_version,
        "docs": "/docs",
        "health": f"/api/{settings.api_version}/health/simple"
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting {settings.api_title} v{settings.api_version}")
    logger.info(f"Documentation available at /docs")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info(f"Shutting down {settings.api_title}")
