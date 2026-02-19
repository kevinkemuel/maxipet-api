from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import List
from app.schemas import (
    WebhookSubscriptionCreate,
    WebhookSubscriptionUpdate,
    WebhookSubscriptionResponse,
    WebhookLogResponse,
    WebhookTestResponse,
    MessageResponse
)
from app.services.webhook_service import WebhookService
from app.services.supabase_service import SupabaseService
from app.utils.security import generate_secret_key
from app.auth import validate_api_key
from app.utils.logger import logger

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

@router.post("", response_model=WebhookSubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook_subscription(
    subscription: WebhookSubscriptionCreate,
    api_key: str = Depends(validate_api_key)
):
    """
    Register a new webhook subscription
    
    - **url**: Webhook endpoint URL
    - **event_types**: List of events to subscribe to
      - `stock.updated`: Triggered when inventory changes
      - `stock.low`: Triggered when stock falls below threshold
      - `product.created`: Triggered when a product is created
      - `product.updated`: Triggered when a product is updated
      - `product.deleted`: Triggered when a product is deleted
    - **description**: Optional description
    
    Returns the subscription with a `secret_key` for HMAC verification
    """
    try:
        # Generate secret key for HMAC signing
        secret_key = generate_secret_key()
        
        new_subscription = {
            "url": str(subscription.url),
            "event_types": subscription.event_types,
            "description": subscription.description,
            "secret_key": secret_key,
            "is_active": True,
            "retry_count": 0
        }
        
        result = await SupabaseService.insert("webhook_subscriptions", new_subscription)
        
        logger.info(f"Created webhook subscription {result['id']} for {subscription.url}")
        
        return result
    except Exception as e:
        logger.exception(f"Error creating webhook subscription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating webhook subscription: {str(e)}"
        )

@router.get("", response_model=List[WebhookSubscriptionResponse])
async def list_webhook_subscriptions(
    active_only: bool = Query(True, description="Show only active subscriptions"),
    api_key: str = Depends(validate_api_key)
):
    """List all webhook subscriptions"""
    try:
        filters = {"is_active": "true"} if active_only else None
        subscriptions = await SupabaseService.select(
            "webhook_subscriptions",
            filters=filters,
            order="created_at.desc"
        )
        return subscriptions
    except Exception as e:
        logger.exception(f"Error listing webhooks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing webhooks: {str(e)}"
        )

@router.get("/{subscription_id}", response_model=WebhookSubscriptionResponse)
async def get_webhook_subscription(
    subscription_id: str,
    api_key: str = Depends(validate_api_key)
):
    """Get a specific webhook subscription"""
    try:
        subscriptions = await SupabaseService.select(
            "webhook_subscriptions",
            filters={"id": subscription_id}
        )
        
        if not subscriptions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Webhook subscription {subscription_id} not found"
            )
        
        return subscriptions[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error fetching webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching webhook: {str(e)}"
        )

@router.put("/{subscription_id}", response_model=WebhookSubscriptionResponse)
async def update_webhook_subscription(
    subscription_id: str,
    update_data: WebhookSubscriptionUpdate,
    api_key: str = Depends(validate_api_key)
):
    """Update a webhook subscription"""
    try:
        # Check if exists
        existing = await SupabaseService.select(
            "webhook_subscriptions",
            filters={"id": subscription_id}
        )
        
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Webhook subscription {subscription_id} not found"
            )
        
        # Prepare update data
        update_dict = {}
        if update_data.url is not None:
            update_dict["url"] = str(update_data.url)
        if update_data.event_types is not None:
            update_dict["event_types"] = update_data.event_types
        if update_data.is_active is not None:
            update_dict["is_active"] = update_data.is_active
        if update_data.description is not None:
            update_dict["description"] = update_data.description
        
        result = await SupabaseService.update(
            "webhook_subscriptions",
            {"id": subscription_id},
            update_dict
        )
        
        logger.info(f"Updated webhook subscription {subscription_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error updating webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating webhook: {str(e)}"
        )

@router.delete("/{subscription_id}", response_model=MessageResponse)
async def delete_webhook_subscription(
    subscription_id: str,
    api_key: str = Depends(validate_api_key)
):
    """Delete a webhook subscription"""
    try:
        # Check if exists
        existing = await SupabaseService.select(
            "webhook_subscriptions",
            filters={"id": subscription_id}
        )
        
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Webhook subscription {subscription_id} not found"
            )
        
        await SupabaseService.delete("webhook_subscriptions", {"id": subscription_id})
        
        logger.info(f"Deleted webhook subscription {subscription_id}")
        return MessageResponse(
            message="Webhook subscription deleted successfully",
            detail=f"Subscription {subscription_id} has been deleted"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting webhook: {str(e)}"
        )

@router.get("/{subscription_id}/logs", response_model=List[WebhookLogResponse])
async def get_webhook_logs(
    subscription_id: str,
    limit: int = Query(50, ge=1, le=200, description="Number of logs to return"),
    api_key: str = Depends(validate_api_key)
):
    """Get delivery logs for a webhook subscription"""
    try:
        # Verify subscription exists
        subscriptions = await SupabaseService.select(
            "webhook_subscriptions",
            filters={"id": subscription_id}
        )
        
        if not subscriptions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Webhook subscription {subscription_id} not found"
            )
        
        logs = await SupabaseService.select(
            "webhook_logs",
            filters={"subscription_id": subscription_id},
            order="created_at.desc",
            limit=limit
        )
        
        return logs
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error fetching webhook logs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching webhook logs: {str(e)}"
        )

@router.post("/{subscription_id}/test", response_model=WebhookTestResponse)
async def test_webhook(
    subscription_id: str,
    api_key: str = Depends(validate_api_key)
):
    """
    Send a test webhook to verify the endpoint
    
    This will send a test payload to the webhook URL and return the result
    """
    try:
        subscriptions = await SupabaseService.select(
            "webhook_subscriptions",
            filters={"id": subscription_id}
        )
        
        if not subscriptions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Webhook subscription {subscription_id} not found"
            )
        
        result = await WebhookService.test_webhook(subscriptions[0])
        return WebhookTestResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error testing webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error testing webhook: {str(e)}"
        )
