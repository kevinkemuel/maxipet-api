import httpx
from typing import List, Optional, Dict, Any
from app.config import settings
from app.utils.logger import logger

class SupabaseService:
    """Service for interacting with Supabase REST API"""
    
    @staticmethod
    def _get_headers() -> Dict[str, str]:
        """Get Supabase headers"""
        return {
            "apikey": settings.supabase_key,
            "Authorization": f"Bearer {settings.supabase_key}",
            "Content-Profile": "maxipet",
            "Accept-Profile": "maxipet",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
    
    @staticmethod
    def _get_base_url() -> str:
        """Get Supabase base URL"""
        return f"{settings.supabase_url.rstrip('/')}/rest/v1"
    
    @staticmethod
    async def insert(table: str, data: Dict[str, Any]) -> Optional[Dict]:
        """Insert a record into a table"""
        headers = SupabaseService._get_headers()
        url = f"{SupabaseService._get_base_url()}/{table}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, headers=headers, json=data)
                response.raise_for_status()
                result = response.json()
                return result[0] if result else None
            except Exception as e:
                logger.error(f"Error inserting into {table}: {str(e)}")
                raise
    
    @staticmethod
    async def select(
        table: str,
        filters: Optional[Dict[str, Any]] = None,
        select: str = "*",
        order: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """Select records from a table"""
        headers = SupabaseService._get_headers()
        
        # Build query params
        params = [f"select={select}"]
        
        if filters:
            for key, value in filters.items():
                params.append(f"{key}=eq.{value}")
        
        if order:
            params.append(f"order={order}")
        
        if limit:
            params.append(f"limit={limit}")
        
        query_string = "&".join(params)
        url = f"{SupabaseService._get_base_url()}/{table}?{query_string}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Error selecting from {table}: {str(e)}")
                raise
    
    @staticmethod
    async def update(
        table: str,
        filters: Dict[str, Any],
        data: Dict[str, Any]
    ) -> Optional[Dict]:
        """Update records in a table"""
        headers = SupabaseService._get_headers()
        
        # Build filter params
        filter_params = "&".join([f"{k}=eq.{v}" for k, v in filters.items()])
        url = f"{SupabaseService._get_base_url()}/{table}?{filter_params}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.patch(url, headers=headers, json=data)
                response.raise_for_status()
                result = response.json()
                return result[0] if result else None
            except Exception as e:
                logger.error(f"Error updating {table}: {str(e)}")
                raise
    
    @staticmethod
    async def delete(table: str, filters: Dict[str, Any]) -> bool:
        """Delete records from a table"""
        headers = SupabaseService._get_headers()
        
        # Build filter params
        filter_params = "&".join([f"{k}=eq.{v}" for k, v in filters.items()])
        url = f"{SupabaseService._get_base_url()}/{table}?{filter_params}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.delete(url, headers=headers)
                response.raise_for_status()
                return True
            except Exception as e:
                logger.error(f"Error deleting from {table}: {str(e)}")
                raise
