import httpx
from typing import List, Optional, Dict, Any, Tuple
from app.config import settings
from app.schemas import ProductoCatalogoCreate, ProductoCatalogoUpdate
from app.services.catalog_service import CatalogService
from app.utils.logger import logger


class ProductService:
    """
    Fachada principal de productos.
    Todas las operaciones CRUD usan el catálogo (db.maxipetonline.com).
    El método lookup_sku_in_erp consulta el ERP como fallback.
    """

    # ── Delegación completa al catálogo ───────────────────────────────────────

    @staticmethod
    async def get_all_products(
        page: int = 1,
        limit: int = 20,
        sort_by: str = "id",
        order: str = "desc",
        filters: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[dict], int]:
        return await CatalogService.get_all_productos(
            page=page, limit=limit, sort_by=sort_by, order=order, filters=filters
        )

    @staticmethod
    async def get_product_by_id(product_id: str) -> Optional[dict]:
        try:
            return await CatalogService.get_producto_by_id(int(product_id))
        except (ValueError, TypeError):
            return None

    @staticmethod
    async def search_products(query: str, page: int = 1, limit: int = 20) -> Tuple[List[dict], int]:
        return await CatalogService.search_productos(query, page, limit)

    @staticmethod
    async def create_product(product_data: ProductoCatalogoCreate) -> dict:
        data = product_data.model_dump(exclude_none=True)
        return await CatalogService.create_producto(data)

    @staticmethod
    async def update_product(product_id: str, product_data: ProductoCatalogoUpdate) -> Optional[dict]:
        try:
            pid = int(product_id)
        except (ValueError, TypeError):
            return None
        data = product_data.model_dump(exclude_none=True)
        return await CatalogService.update_producto(pid, data)

    @staticmethod
    async def delete_product(product_id: str) -> bool:
        try:
            return await CatalogService.delete_producto(int(product_id))
        except (ValueError, TypeError):
            return False

    @staticmethod
    async def get_low_stock_products(threshold: Optional[int] = None) -> List[dict]:
        return await CatalogService.get_low_stock_productos(threshold)

    # ── Lookup SKU (catálogo primero, luego ERP) ─────────────────────────────

    @staticmethod
    async def lookup_sku(sku: str) -> Dict[str, Any]:
        """
        Busca un SKU en dos fuentes:
          1. Catálogo (db.maxipetonline.com → productos_catalogo)
          2. ERP (supabase.co → maxipet.products)

        Retorna:
          { found_in: "catalog", producto: {...} }
          { found_in: "erp",     erp_data: {...} }
        Lanza ValueError si no existe en ninguna.
        """
        # 1 — Catálogo
        catalog_product = await CatalogService.get_producto_by_sku(sku)
        if catalog_product:
            return {"found_in": "catalog", "producto": catalog_product}

        # 2 — ERP Supabase (schema maxipet, tabla products)
        erp_product = await ProductService.lookup_sku_in_erp(sku)
        if erp_product:
            return {"found_in": "erp", "erp_data": erp_product}

        raise ValueError(f"SKU '{sku}' no existe en el ERP. Contacte al administrador.")

    @staticmethod
    async def lookup_sku_in_erp(sku: str) -> Optional[dict]:
        """
        Consulta el ERP Supabase buscando por external_id (que almacena el SKU).
        Devuelve None si no se encuentra o si ocurre algún error.
        """
        headers = {
            "apikey": settings.supabase_key,
            "Authorization": f"Bearer {settings.supabase_key}",
            "Accept-Profile": "maxipet",
            "Content-Type": "application/json",
        }
        base_url = f"{settings.supabase_url.rstrip('/')}/rest/v1"
        url = f"{base_url}/products?external_id=eq.{sku}&select=*"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                return data[0] if data else None
            except Exception as e:
                logger.error(f"Error buscando SKU {sku} en ERP: {e}")
                return None
