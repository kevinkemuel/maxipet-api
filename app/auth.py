from fastapi import HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from app.config import settings

api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)

async def validate_api_key(header_value: str = Security(api_key_header)):
    if header_value == settings.api_key_token:
        return header_value
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, 
        detail="API Key inválida"
    )