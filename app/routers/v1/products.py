from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import List, Optional
from decimal import Decimal
from app.schemas import (
    ProductResponse,
    ProductCreate,
    ProductUpdate,
    PaginatedResponse,
    MessageResponse
)
from app.services.product_service import ProductService
from app.services.webhook_service import WebhookService
from app.auth import validate_api_key
from app.utils.logger import logger

router = APIRouter(prefix="/products", tags=["Products"])

@router.get("", response_model=PaginatedResponse)
async def list_products(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("updated_at", description="Field to sort by"),
    order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    brand: Optional[str] = Query(None, description="Filter by brand"),
    min_price: Optional[Decimal] = Query(None, ge=0, description="Minimum price"),
    max_price: Optional[Decimal] = Query(None, ge=0, description="Maximum price"),
    availability: Optional[str] = Query(None, description="Filter by availability"),
    api_key: str = Depends(validate_api_key)
):
    """
    List all products with pagination and filters
    
    - **page**: Page number (default: 1)
    - **limit**: Items per page (default: 20, max: 100)
    - **sort_by**: Field to sort by (default: updated_at)
    - **order**: Sort order (asc/desc, default: desc)
    - **brand**: Filter by brand
    - **min_price**: Minimum price filter
    - **max_price**: Maximum price filter
    - **availability**: Filter by availability status
    """
    try:
        filters = {}
        if brand:
            filters['brand'] = brand
        if min_price is not None:
            filters['min_price'] = min_price
        if max_price is not None:
            filters['max_price'] = max_price
        if availability:
            filters['availability'] = availability
        
        products, total = await ProductService.get_all_products(
            page=page,
            limit=limit,
            sort_by=sort_by,
            order=order,
            filters=filters if filters else None
        )
        
        pages = (total + limit - 1) // limit
        
        return PaginatedResponse(
            items=products,
            total=total,
            page=page,
            limit=limit,
            pages=pages
        )
    except Exception as e:
        logger.exception(f"Error listing products: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching products: {str(e)}"
        )

@router.get("/search", response_model=PaginatedResponse)
async def search_products(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    api_key: str = Depends(validate_api_key)
):
    """
    Search products by title or description
    
    - **q**: Search query (required)
    - **page**: Page number
    - **limit**: Items per page
    """
    try:
        products, total = await ProductService.search_products(q, page, limit)
        pages = (total + limit - 1) // limit
        
        return PaginatedResponse(
            items=products,
            total=total,
            page=page,
            limit=limit,
            pages=pages
        )
    except Exception as e:
        logger.exception(f"Error searching products: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching products: {str(e)}"
        )

@router.get("/{product_id}")
async def get_product(
    product_id: str,
    api_key: str = Depends(validate_api_key)
):
    """Get a single product by ID"""
    try:
        product = await ProductService.get_product_by_id(product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product {product_id} not found"
            )
        return product
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error fetching product: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching product: {str(e)}"
        )

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_product(
    product: ProductCreate,
    api_key: str = Depends(validate_api_key)
):
    """
    Create a new product (Admin only)
    
    Triggers webhook event: `product.created`
    """
    try:
        new_product = await ProductService.create_product(product)
        
        # Trigger webhook
        await WebhookService.dispatch_to_all_subscribers(
            event_type="product.created",
            payload={
                "product_id": new_product.get('id'),
                "product": new_product
            }
        )
        
        return new_product
    except Exception as e:
        logger.exception(f"Error creating product: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating product: {str(e)}"
        )

@router.put("/{product_id}")
async def update_product(
    product_id: str,
    product: ProductUpdate,
    api_key: str = Depends(validate_api_key)
):
    """
    Update a product (Admin only)
    
    Triggers webhook event: `product.updated`
    """
    try:
        updated_product = await ProductService.update_product(product_id, product)
        if not updated_product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product {product_id} not found"
            )
        
        # Trigger webhook
        await WebhookService.dispatch_to_all_subscribers(
            event_type="product.updated",
            payload={
                "product_id": product_id,
                "product": updated_product
            }
        )
        
        return updated_product
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error updating product: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating product: {str(e)}"
        )

@router.patch("/{product_id}")
async def partial_update_product(
    product_id: str,
    product: ProductUpdate,
    api_key: str = Depends(validate_api_key)
):
    """
    Partially update a product (Admin only)
    
    Same as PUT but semantically indicates partial update
    """
    return await update_product(product_id, product, api_key)

@router.delete("/{product_id}", response_model=MessageResponse)
async def delete_product(
    product_id: str,
    api_key: str = Depends(validate_api_key)
):
    """
    Delete a product (Admin only)
    
    Triggers webhook event: `product.deleted`
    """
    try:
        # Get product before deleting for webhook
        product = await ProductService.get_product_by_id(product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product {product_id} not found"
            )
        
        await ProductService.delete_product(product_id)
        
        # Trigger webhook
        await WebhookService.dispatch_to_all_subscribers(
            event_type="product.deleted",
            payload={
                "product_id": product_id,
                "product": product
            }
        )
        
        return MessageResponse(
            message="Product deleted successfully",
            detail=f"Product {product_id} has been deleted"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting product: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting product: {str(e)}"
        )
