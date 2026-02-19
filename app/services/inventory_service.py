from typing import Optional, Dict, Any
from app.services.product_service import ProductService
from app.services.webhook_service import WebhookService
from app.services.supabase_service import SupabaseService
from app.config import settings
from app.utils.logger import logger
from datetime import datetime

class InventoryService:
    """Service for managing inventory and triggering webhooks on changes"""
    
    @staticmethod
    async def update_inventory(
        product_id: str,
        new_count: int,
        reason: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update product inventory and trigger webhooks
        
        Args:
            product_id: Product ID
            new_count: New inventory count
            reason: Reason for the change
            created_by: User/API key making the change
            
        Returns:
            dict: Updated product data
        """
        # Get current product
        current_product = await ProductService.get_product_by_id(product_id)
        if not current_product:
            raise ValueError(f"Product {product_id} not found")
        
        previous_count = current_product.get('inventory_count', 0)
        
        # Update inventory
        from app.schemas import ProductUpdate
        update_data = ProductUpdate(inventory_count=new_count)
        updated_product = await ProductService.update_product(product_id, update_data)
        
        # Record history in Supabase
        try:
            history_record = {
                "product_id": product_id,
                "previous_count": previous_count,
                "new_count": new_count,
                "adjustment": new_count - previous_count,
                "reason": reason,
                "created_by": created_by,
                "created_at": datetime.utcnow().isoformat()
            }
            await SupabaseService.insert("inventory_history", history_record)
        except Exception as e:
            logger.error(f"Failed to record inventory history: {str(e)}")
        
        # Trigger webhooks if inventory changed
        if previous_count != new_count:
            # Stock updated event
            await WebhookService.dispatch_to_all_subscribers(
                event_type="stock.updated",
                payload={
                    "product_id": product_id,
                    "product_title": current_product.get('title'),
                    "previous_count": previous_count,
                    "new_count": new_count,
                    "adjustment": new_count - previous_count
                }
            )
            
            # Low stock event
            if new_count < settings.low_stock_threshold and previous_count >= settings.low_stock_threshold:
                await WebhookService.dispatch_to_all_subscribers(
                    event_type="stock.low",
                    payload={
                        "product_id": product_id,
                        "product_title": current_product.get('title'),
                        "inventory_count": new_count,
                        "threshold": settings.low_stock_threshold
                    }
                )
                logger.warning(
                    f"Low stock alert for product {product_id}: {new_count} units "
                    f"(threshold: {settings.low_stock_threshold})"
                )
        
        return updated_product
    
    @staticmethod
    async def adjust_inventory(
        product_id: str,
        adjustment: int,
        reason: str,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Adjust inventory by a relative amount
        
        Args:
            product_id: Product ID
            adjustment: Amount to adjust (positive or negative)
            reason: Reason for adjustment
            created_by: User/API key making the change
            
        Returns:
            dict: Updated product data
        """
        # Get current product
        current_product = await ProductService.get_product_by_id(product_id)
        if not current_product:
            raise ValueError(f"Product {product_id} not found")
        
        current_count = current_product.get('inventory_count', 0)
        new_count = max(0, current_count + adjustment)  # Don't go below 0
        
        return await InventoryService.update_inventory(
            product_id=product_id,
            new_count=new_count,
            reason=reason,
            created_by=created_by
        )
    
    @staticmethod
    async def get_inventory_history(product_id: str, limit: int = 50):
        """Get inventory history for a product"""
        try:
            history = await SupabaseService.select(
                "inventory_history",
                filters={"product_id": product_id},
                order="created_at.desc",
                limit=limit
            )
            return history
        except Exception as e:
            logger.error(f"Failed to fetch inventory history: {str(e)}")
            return []
