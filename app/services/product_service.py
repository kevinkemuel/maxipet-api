import httpx
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.config import settings
from app.schemas import ProductCreate, ProductUpdate
from app.utils.logger import logger

class ProductService:
    """Service for managing products via Supabase"""
    
    @staticmethod
    def _get_headers() -> Dict[str, str]:
        """Get Supabase headers"""
        return {
            "apikey": settings.supabase_key,
            "Authorization": f"Bearer {settings.supabase_key}",
            "Accept-Profile": "maxipet",
            "Content-Type": "application/json"
        }
    
    @staticmethod
    def _get_base_url() -> str:
        """Get Supabase base URL"""
        return f"{settings.supabase_url.rstrip('/')}/rest/v1"
    
    @staticmethod
    async def get_all_products(
        page: int = 1,
        limit: int = 20,
        sort_by: str = "updated_at",
        order: str = "desc",
        filters: Optional[Dict[str, Any]] = None
    ) -> tuple[List[dict], int]:
        """
        Get all products with pagination and filters
        
        Returns:
            tuple: (products list, total count)
        """
        headers = ProductService._get_headers()
        base_url = ProductService._get_base_url()
        
        # Build query
        query_params = []
        select_query = "select=*"
        
        # Add filters
        if filters:
            if filters.get('brand'):
                query_params.append(f"brand=eq.{filters['brand']}")
            if filters.get('availability'):
                query_params.append(f"availability=eq.{filters['availability']}")
            if filters.get('min_price'):
                query_params.append(f"price=gte.{filters['min_price']}")
            if filters.get('max_price'):
                query_params.append(f"price=lte.{filters['max_price']}")
        
        # Add sorting
        order_direction = "asc" if order == "asc" else "desc"
        query_params.append(f"order={sort_by}.{order_direction}")
        
        # Add pagination
        offset = (page - 1) * limit
        query_params.append(f"limit={limit}")
        query_params.append(f"offset={offset}")
        
        query_string = "&".join([select_query] + query_params)
        url = f"{base_url}/products?{query_string}"
        
        async with httpx.AsyncClient() as client:
            # Get products
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            products = response.json()
            
            # Get total count
            count_headers = {**headers, "Prefer": "count=exact"}
            count_url = f"{base_url}/products?select=count"
            if filters:
                filter_params = [p for p in query_params if not p.startswith(('limit=', 'offset=', 'order='))]
                if filter_params:
                    count_url += "&" + "&".join(filter_params)
            
            count_response = await client.get(count_url, headers=count_headers)
            total = int(count_response.headers.get('Content-Range', '0-0/0').split('/')[-1])
            
            return products, total
    
    @staticmethod
    async def get_product_by_id(product_id: str) -> Optional[dict]:
        """Get a single product by ID"""
        headers = ProductService._get_headers()
        base_url = ProductService._get_base_url()
        url = f"{base_url}/products?id=eq.{product_id}&select=*"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            products = response.json()
            return products[0] if products else None
    
    @staticmethod
    async def search_products(query: str, page: int = 1, limit: int = 20) -> tuple[List[dict], int]:
        """
        Search products by title or description
        
        Returns:
            tuple: (products list, total count)
        """
        headers = ProductService._get_headers()
        base_url = ProductService._get_base_url()
        
        # Supabase text search
        offset = (page - 1) * limit
        url = f"{base_url}/products?or=(title.ilike.*{query}*,description.ilike.*{query}*)&select=*&limit={limit}&offset={offset}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            products = response.json()
            
            # Get count
            count_url = f"{base_url}/products?or=(title.ilike.*{query}*,description.ilike.*{query}*)&select=count"
            count_headers = {**headers, "Prefer": "count=exact"}
            count_response = await client.get(count_url, headers=count_headers)
            total = int(count_response.headers.get('Content-Range', '0-0/0').split('/')[-1])
            
            return products, total
    
    @staticmethod
    async def create_product(product_data: ProductCreate) -> dict:
        """Create a new product"""
        headers = ProductService._get_headers()
        headers["Prefer"] = "return=representation"
        base_url = ProductService._get_base_url()
        url = f"{base_url}/products"
        
        # Convert to dict and handle Decimal/HttpUrl
        data = product_data.model_dump()
        data['price'] = str(data['price'])
        data['image_link'] = str(data['image_link'])
        data['link'] = str(data['link'])
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()[0]
    
    @staticmethod
    async def update_product(product_id: str, product_data: ProductUpdate) -> Optional[dict]:
        """Update an existing product"""
        headers = ProductService._get_headers()
        headers["Prefer"] = "return=representation"
        base_url = ProductService._get_base_url()
        url = f"{base_url}/products?id=eq.{product_id}"
        
        # Convert to dict, excluding None values
        data = product_data.model_dump(exclude_none=True)
        if 'price' in data:
            data['price'] = str(data['price'])
        if 'image_link' in data:
            data['image_link'] = str(data['image_link'])
        if 'link' in data:
            data['link'] = str(data['link'])
        
        async with httpx.AsyncClient() as client:
            response = await client.patch(url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            return result[0] if result else None
    
    @staticmethod
    async def delete_product(product_id: str) -> bool:
        """Delete a product"""
        headers = ProductService._get_headers()
        base_url = ProductService._get_base_url()
        url = f"{base_url}/products?id=eq.{product_id}"
        
        async with httpx.AsyncClient() as client:
            response = await client.delete(url, headers=headers)
            response.raise_for_status()
            return True
    
    @staticmethod
    async def get_low_stock_products(threshold: Optional[int] = None) -> List[dict]:
        """Get products with low stock"""
        if threshold is None:
            threshold = settings.low_stock_threshold
        
        headers = ProductService._get_headers()
        base_url = ProductService._get_base_url()
        url = f"{base_url}/products?inventory_count=lt.{threshold}&select=*&order=inventory_count.asc"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
