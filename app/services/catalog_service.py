import httpx
from typing import List, Optional, Dict, Any, Tuple
from app.config import settings
from app.utils.logger import logger

# Select completo con todas las relaciones
PRODUCTO_SELECT = (
    "id,SKU,nombre,descripcion,precio,marca,inventario,bajo_inventario,"
    "publicado,visible_catalogo,"
    "producto_fotos(id,url,es_principal,orden),"
    "producto_categorias(categoria_id,categorias(id,nombre,slug)),"
    "producto_especies(especie_id,especies(id,nombre))"
)

# Select liviano para listados
PRODUCTO_LIST_SELECT = (
    "id,SKU,nombre,precio,marca,inventario,bajo_inventario,"
    "publicado,visible_catalogo,"
    "producto_fotos(url,es_principal),"
    "producto_categorias(categorias(nombre))"
)


class CatalogService:
    """
    Servicio para interactuar con el Supabase del catálogo (db.maxipetonline.com).
    Usa el schema 'public' — sin Content-Profile/Accept-Profile headers.
    """

    @staticmethod
    def _get_headers(prefer_representation: bool = False) -> Dict[str, str]:
        headers = {
            "apikey": settings.supabase_catalog_key,
            "Authorization": f"Bearer {settings.supabase_catalog_key}",
            "Content-Type": "application/json",
        }
        if prefer_representation:
            headers["Prefer"] = "return=representation"
        return headers

    @staticmethod
    def _base_url() -> str:
        return f"{settings.supabase_catalog_url.rstrip('/')}/rest/v1"

    # ── Listado con paginación y filtros ──────────────────────────────────────

    @staticmethod
    async def get_all_productos(
        page: int = 1,
        limit: int = 20,
        sort_by: str = "id",
        order: str = "desc",
        filters: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[dict], int]:
        """
        Devuelve (productos, total).
        filters admite: marca, categoria_id, publicado, visible_catalogo,
                        min_price, max_price, q (búsqueda libre).
        """
        headers = CatalogService._get_headers()
        base_url = CatalogService._base_url()

        params: List[str] = [f"select={PRODUCTO_LIST_SELECT}"]

        if filters:
            if filters.get("marca"):
                params.append(f"marca=eq.{filters['marca']}")
            if filters.get("publicado") is not None:
                params.append(f"publicado=eq.{filters['publicado']}")
            if filters.get("visible_catalogo") is not None:
                params.append(f"visible_catalogo=eq.{filters['visible_catalogo']}")
            # precio es string en la tabla; comparación lexicográfica aproximada
            if filters.get("min_price") is not None:
                params.append(f"precio=gte.{filters['min_price']}")
            if filters.get("max_price") is not None:
                params.append(f"precio=lte.{filters['max_price']}")
            if filters.get("q"):
                q = filters["q"]
                params.append(f"or=(nombre.ilike.*{q}*,SKU.ilike.*{q}*,marca.ilike.*{q}*)")

        params.append(f"order={sort_by}.{order}")
        offset = (page - 1) * limit
        params.append(f"limit={limit}")
        params.append(f"offset={offset}")

        url = f"{base_url}/productos_catalogo?{'&'.join(params)}"

        async with httpx.AsyncClient() as client:
            # Productos
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            productos = response.json()

            # Total
            count_headers = {**headers, "Prefer": "count=exact"}
            count_params = [p for p in params if not p.startswith(("limit=", "offset=", "order=", "select="))]
            count_url = f"{base_url}/productos_catalogo?select=id&{'&'.join(count_params)}" if count_params else f"{base_url}/productos_catalogo?select=id"
            count_response = await client.get(count_url, headers=count_headers)
            total = int(count_response.headers.get("Content-Range", "0-0/0").split("/")[-1])

            return productos, total

    # ── Por ID ────────────────────────────────────────────────────────────────

    @staticmethod
    async def get_producto_by_id(producto_id: int) -> Optional[dict]:
        headers = CatalogService._get_headers()
        url = f"{CatalogService._base_url()}/productos_catalogo?id=eq.{producto_id}&select={PRODUCTO_SELECT}"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data[0] if data else None

    # ── Por SKU ───────────────────────────────────────────────────────────────

    @staticmethod
    async def get_producto_by_sku(sku: str) -> Optional[dict]:
        """Busca en el catálogo por SKU (exacto). Devuelve None si no existe."""
        headers = CatalogService._get_headers()
        url = (
            f"{CatalogService._base_url()}/productos_catalogo"
            f"?SKU=eq.{sku}&select={PRODUCTO_SELECT}"
        )

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                return data[0] if data else None
            except Exception as e:
                logger.error(f"Error buscando SKU {sku} en catálogo: {e}")
                return None

    # ── Búsqueda libre ────────────────────────────────────────────────────────

    @staticmethod
    async def search_productos(query: str, page: int = 1, limit: int = 20) -> Tuple[List[dict], int]:
        return await CatalogService.get_all_productos(
            page=page, limit=limit, filters={"q": query}
        )

    # ── CRUD ──────────────────────────────────────────────────────────────────

    @staticmethod
    async def create_producto(data: dict) -> dict:
        headers = CatalogService._get_headers(prefer_representation=True)
        url = f"{CatalogService._base_url()}/productos_catalogo"

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            return result[0] if result else {}

    @staticmethod
    async def update_producto(producto_id: int, data: dict) -> Optional[dict]:
        headers = CatalogService._get_headers(prefer_representation=True)
        url = f"{CatalogService._base_url()}/productos_catalogo?id=eq.{producto_id}"

        async with httpx.AsyncClient() as client:
            response = await client.patch(url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            return result[0] if result else None

    @staticmethod
    async def delete_producto(producto_id: int) -> bool:
        headers = CatalogService._get_headers()
        url = f"{CatalogService._base_url()}/productos_catalogo?id=eq.{producto_id}"

        async with httpx.AsyncClient() as client:
            response = await client.delete(url, headers=headers)
            response.raise_for_status()
            return True

    # ── Bajo inventario ───────────────────────────────────────────────────────

    @staticmethod
    async def get_low_stock_productos(threshold: Optional[int] = None) -> List[dict]:
        if threshold is None:
            from app.config import settings
            threshold = settings.low_stock_threshold

        headers = CatalogService._get_headers()
        # inventario es TEXT en la tabla — comparación como número con cast
        url = (
            f"{CatalogService._base_url()}/productos_catalogo"
            f"?inventario=lt.{threshold}"
            f"&inventario=not.is.null"
            f"&select={PRODUCTO_LIST_SELECT}"
            f"&order=inventario.asc"
        )

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Error obteniendo productos con bajo inventario: {e}")
                return []
