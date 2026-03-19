from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import List, Optional
from decimal import Decimal
from app.schemas import (
    ProductoCatalogoCreate,
    ProductoCatalogoUpdate,
    ProductoCatalogoResponse,
    SkuLookupResponse,
    PaginatedResponse,
    MessageResponse,
)
from app.services.product_service import ProductService
from app.services.webhook_service import WebhookService
from app.auth import validate_api_key
from app.utils.logger import logger

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", response_model=PaginatedResponse)
async def list_products(
    page: int = Query(1, ge=1, description="Número de página"),
    limit: int = Query(20, ge=1, le=100, description="Ítems por página"),
    sort_by: str = Query("id", description="Campo para ordenar"),
    order: str = Query("desc", pattern="^(asc|desc)$", description="Orden (asc/desc)"),
    marca: Optional[str] = Query(None, description="Filtrar por marca"),
    min_price: Optional[Decimal] = Query(None, ge=0, description="Precio mínimo"),
    max_price: Optional[Decimal] = Query(None, ge=0, description="Precio máximo"),
    publicado: Optional[str] = Query(None, description="Filtrar por publicado (0/1)"),
    visible_catalogo: Optional[str] = Query(None, description="Filtrar por visibilidad (0/1)"),
    api_key: str = Depends(validate_api_key),
):
    """
    Lista productos del catálogo con paginación y filtros.

    - **marca**: Filtrar por marca
    - **publicado**: `1` = publicado, `0` = no publicado
    - **visible_catalogo**: `1` = visible, `0` = oculto
    - **min_price / max_price**: Rango de precio
    """
    try:
        filters: dict = {}
        if marca:
            filters["marca"] = marca
        if min_price is not None:
            filters["min_price"] = min_price
        if max_price is not None:
            filters["max_price"] = max_price
        if publicado is not None:
            filters["publicado"] = publicado
        if visible_catalogo is not None:
            filters["visible_catalogo"] = visible_catalogo

        products, total = await ProductService.get_all_products(
            page=page,
            limit=limit,
            sort_by=sort_by,
            order=order,
            filters=filters or None,
        )

        pages = (total + limit - 1) // limit if total else 0

        return PaginatedResponse(
            items=products,
            total=total,
            page=page,
            limit=limit,
            pages=pages,
        )
    except Exception as e:
        logger.exception(f"Error listando productos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener productos: {e}",
        )


@router.get("/search", response_model=PaginatedResponse)
async def search_products(
    q: str = Query(..., min_length=1, description="Texto a buscar (nombre, SKU o marca)"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    api_key: str = Depends(validate_api_key),
):
    """
    Busca productos por nombre, SKU o marca.
    """
    try:
        products, total = await ProductService.search_products(q, page, limit)
        pages = (total + limit - 1) // limit if total else 0

        return PaginatedResponse(
            items=products,
            total=total,
            page=page,
            limit=limit,
            pages=pages,
        )
    except Exception as e:
        logger.exception(f"Error buscando productos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error buscando productos: {e}",
        )


# IMPORTANTE: /sku/{sku} debe estar antes de /{product_id}
@router.get("/sku/{sku}", response_model=SkuLookupResponse)
async def lookup_by_sku(
    sku: str,
    api_key: str = Depends(validate_api_key),
):
    """
    Busca un producto por SKU con doble fallback:

    1. **Catálogo** (`productos_catalogo`) — devuelve `found_in: "catalog"` con datos completos.
    2. **ERP** (Supabase ERP) — si no existe en catálogo, devuelve `found_in: "erp"` con datos del ERP
       que pueden usarse para pre-llenar el formulario de creación.
    3. **404** — si no existe en ninguno: `"SKU no existe en el ERP. Contacte al administrador."`
    """
    try:
        result = await ProductService.lookup_sku(sku)
        return SkuLookupResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.exception(f"Error en lookup de SKU {sku}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error buscando SKU: {e}",
        )


@router.get("/{product_id}")
async def get_product(
    product_id: str,
    api_key: str = Depends(validate_api_key),
):
    """Obtiene un producto por ID con todas sus relaciones (fotos, categorías, especies)."""
    try:
        product = await ProductService.get_product_by_id(product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto {product_id} no encontrado",
            )
        return product
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error obteniendo producto {product_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener producto: {e}",
        )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_product(
    product: ProductoCatalogoCreate,
    api_key: str = Depends(validate_api_key),
):
    """
    Crea un nuevo producto en el catálogo.

    Dispara webhook: `product.created`
    """
    try:
        new_product = await ProductService.create_product(product)

        await WebhookService.dispatch_to_all_subscribers(
            event_type="product.created",
            payload={"product_id": new_product.get("id"), "product": new_product},
        )

        return new_product
    except Exception as e:
        logger.exception(f"Error creando producto: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear producto: {e}",
        )


@router.put("/{product_id}")
async def update_product(
    product_id: str,
    product: ProductoCatalogoUpdate,
    api_key: str = Depends(validate_api_key),
):
    """
    Actualiza un producto del catálogo.

    Dispara webhook: `product.updated`
    """
    try:
        updated = await ProductService.update_product(product_id, product)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto {product_id} no encontrado",
            )

        await WebhookService.dispatch_to_all_subscribers(
            event_type="product.updated",
            payload={"product_id": product_id, "product": updated},
        )

        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error actualizando producto {product_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar producto: {e}",
        )


@router.patch("/{product_id}")
async def partial_update_product(
    product_id: str,
    product: ProductoCatalogoUpdate,
    api_key: str = Depends(validate_api_key),
):
    """Actualización parcial — mismo comportamiento que PUT."""
    return await update_product(product_id, product, api_key)


@router.delete("/{product_id}", response_model=MessageResponse)
async def delete_product(
    product_id: str,
    api_key: str = Depends(validate_api_key),
):
    """
    Elimina un producto del catálogo.

    Dispara webhook: `product.deleted`
    """
    try:
        product = await ProductService.get_product_by_id(product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto {product_id} no encontrado",
            )

        await ProductService.delete_product(product_id)

        await WebhookService.dispatch_to_all_subscribers(
            event_type="product.deleted",
            payload={"product_id": product_id, "product": product},
        )

        return MessageResponse(
            message="Producto eliminado correctamente",
            detail=f"Producto {product_id} ha sido eliminado",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error eliminando producto {product_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar producto: {e}",
        )
