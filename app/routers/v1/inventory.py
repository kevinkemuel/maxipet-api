from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import List, Optional
from app.schemas import (
    InventoryUpdate,
    InventoryAdjustment,
    InventoryHistoryResponse,
    MessageResponse
)
from app.services.inventory_service import InventoryService
from app.services.product_service import ProductService
from app.auth import validate_api_key
from app.config import settings
from app.utils.logger import logger

router = APIRouter(prefix="/inventory", tags=["Inventory"])

@router.get("/low-stock")
async def get_low_stock_products(
    threshold: Optional[int] = Query(None, ge=0, description="Stock threshold"),
    api_key: str = Depends(validate_api_key)
):
    """
    Get products with low inventory
    
    - **threshold**: Custom threshold (default from settings)
    
    Returns products where inventory_count < threshold
    """
    try:
        products = await ProductService.get_low_stock_products(threshold)
        return {
            "threshold": threshold or settings.low_stock_threshold,
            "count": len(products),
            "products": products
        }
    except Exception as e:
        logger.exception(f"Error fetching low stock products: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching low stock products: {str(e)}"
        )

@router.patch("/{product_id}")
async def update_product_inventory(
    product_id: str,
    inventory_data: InventoryUpdate,
    api_key: str = Depends(validate_api_key)
):
    """
    Update product inventory count
    
    - **inventory_count**: New inventory count
    - **reason**: Optional reason for the change
    
    Triggers webhooks:
    - `stock.updated`: Always triggered when stock changes
    - `stock.low`: Triggered if stock falls below threshold
    """
    try:
        updated_product = await InventoryService.update_inventory(
            product_id=product_id,
            new_count=inventory_data.inventory_count,
            reason=inventory_data.reason,
            created_by=api_key[:10]  # Use first 10 chars of API key
        )
        
        return updated_product
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.exception(f"Error updating inventory: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating inventory: {str(e)}"
        )

@router.post("/{product_id}/adjust")
async def adjust_product_inventory(
    product_id: str,
    adjustment_data: InventoryAdjustment,
    api_key: str = Depends(validate_api_key)
):
    """
    Adjust product inventory by a relative amount
    
    - **adjustment**: Amount to add/subtract (can be negative)
    - **reason**: Reason for adjustment (required)
    
    Example: adjustment=-5 will decrease inventory by 5 units
    
    Triggers same webhooks as inventory update
    """
    try:
        updated_product = await InventoryService.adjust_inventory(
            product_id=product_id,
            adjustment=adjustment_data.adjustment,
            reason=adjustment_data.reason,
            created_by=api_key[:10]
        )
        
        return updated_product
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.exception(f"Error adjusting inventory: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adjusting inventory: {str(e)}"
        )

@router.get("/{product_id}/history", response_model=List[InventoryHistoryResponse])
async def get_inventory_history(
    product_id: str,
    limit: int = Query(50, ge=1, le=200, description="Number of history records"),
    api_key: str = Depends(validate_api_key)
):
    """
    Get inventory change history for a product
    
    Returns a list of all inventory changes with timestamps and reasons
    """
    try:
        # Verify product exists
        product = await ProductService.get_product_by_id(product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product {product_id} not found"
            )
        
        history = await InventoryService.get_inventory_history(product_id, limit)
        return history
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error fetching inventory history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching inventory history: {str(e)}"
        )
