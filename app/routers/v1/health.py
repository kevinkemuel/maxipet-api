from fastapi import APIRouter, Depends
from datetime import datetime
import httpx
from app.schemas import HealthCheckResponse
from app.config import settings
from app.auth import validate_api_key
from app.utils.logger import logger

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("", response_model=HealthCheckResponse)
async def health_check(api_key: str = Depends(validate_api_key)):
    """
    Comprehensive health check
    
    Checks:
    - API status
    - Supabase connectivity
    - API version info
    """
    services = {}
    
    # Check Supabase REST API
    try:
        headers = {
            "apikey": settings.supabase_key,
            "Authorization": f"Bearer {settings.supabase_key}",
            "Content-Profile": "maxipet",
            "Accept-Profile": "maxipet"
        }
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Test with a simple query to products table
            response = await client.get(
                f"{settings.supabase_url.rstrip('/')}/rest/v1/products?limit=1",
                headers=headers
            )
            if response.status_code < 500:
                services["supabase"] = {
                    "status": "healthy",
                    "url": settings.supabase_url,
                    "type": "REST API"
                }
            else:
                services["supabase"] = {
                    "status": "unhealthy",
                    "error": f"Status code: {response.status_code}"
                }
    except Exception as e:
        logger.error(f"Supabase health check failed: {str(e)}")
        services["supabase"] = {"status": "unhealthy", "error": str(e)}
    
    # Overall status
    all_healthy = all(
        service.get("status") == "healthy"
        for service in services.values()
    )
    
    return HealthCheckResponse(
        status="healthy" if all_healthy else "degraded",
        version=settings.api_version,
        timestamp=datetime.utcnow(),
        services=services
    )

@router.get("/simple")
async def simple_health_check():
    """Simple health check without authentication"""
    return {
        "status": "online",
        "version": settings.api_version,
        "timestamp": datetime.utcnow().isoformat()
    }
