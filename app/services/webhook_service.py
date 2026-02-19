import httpx
import json
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.services.supabase_service import SupabaseService
from app.utils.security import generate_hmac_signature
from app.utils.logger import logger
from app.config import settings

class WebhookService:
    """Service for managing and dispatching webhooks using Supabase"""
    
    @staticmethod
    async def dispatch_webhook(
        subscription: Dict[str, Any],
        event_type: str,
        payload: Dict[str, Any]
    ) -> bool:
        """
        Dispatch a webhook to a subscription with retry logic
        
        Args:
            subscription: Webhook subscription dict
            event_type: Type of event (e.g., 'stock.updated')
            payload: Event payload data
            
        Returns:
            bool: True if webhook was delivered successfully
        """
        if not subscription.get('is_active'):
            logger.warning(f"Webhook {subscription['id']} is inactive, skipping")
            return False
        
        if event_type not in subscription.get('event_types', []):
            logger.debug(f"Event {event_type} not in subscription {subscription['id']} event types")
            return False
        
        # Prepare payload with metadata
        webhook_payload = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": payload
        }
        
        payload_json = json.dumps(webhook_payload)
        
        # Generate HMAC signature
        signature = generate_hmac_signature(payload_json, subscription['secret_key'])
        
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature,
            "X-Webhook-Event": event_type,
            "User-Agent": "MaxiPet-Webhook/1.0"
        }
        
        # Create webhook log
        webhook_log = {
            "subscription_id": subscription['id'],
            "event_type": event_type,
            "payload": webhook_payload,
            "attempts": 0
        }
        
        try:
            log_record = await SupabaseService.insert("webhook_logs", webhook_log)
            log_id = log_record['id'] if log_record else None
        except Exception as e:
            logger.error(f"Failed to create webhook log: {str(e)}")
            log_id = None
        
        # Attempt delivery with retries
        for attempt in range(settings.webhook_retry_attempts):
            try:
                if log_id:
                    await SupabaseService.update(
                        "webhook_logs",
                        {"id": log_id},
                        {"attempts": attempt + 1}
                    )
                
                async with httpx.AsyncClient(timeout=settings.webhook_timeout) as client:
                    response = await client.post(
                        subscription['url'],
                        content=payload_json,
                        headers=headers
                    )
                    
                    if log_id:
                        await SupabaseService.update(
                            "webhook_logs",
                            {"id": log_id},
                            {
                                "response_status": response.status_code,
                                "response_body": response.text[:1000],
                                "delivered_at": datetime.utcnow().isoformat()
                            }
                        )
                    
                    if response.status_code < 300:
                        # Success
                        await SupabaseService.update(
                            "webhook_subscriptions",
                            {"id": subscription['id']},
                            {
                                "last_triggered": datetime.utcnow().isoformat(),
                                "retry_count": 0
                            }
                        )
                        
                        logger.info(
                            f"Webhook delivered successfully to {subscription['url']} "
                            f"(event: {event_type}, attempt: {attempt + 1})"
                        )
                        return True
                    else:
                        logger.warning(
                            f"Webhook delivery failed with status {response.status_code} "
                            f"(attempt: {attempt + 1}/{settings.webhook_retry_attempts})"
                        )
                        
            except Exception as e:
                logger.error(
                    f"Webhook delivery error: {str(e)} "
                    f"(attempt: {attempt + 1}/{settings.webhook_retry_attempts})"
                )
                if log_id:
                    try:
                        await SupabaseService.update(
                            "webhook_logs",
                            {"id": log_id},
                            {"response_body": f"Error: {str(e)}"[:1000]}
                        )
                    except:
                        pass
            
            # Wait before retry (except on last attempt)
            if attempt < settings.webhook_retry_attempts - 1:
                delay = settings.webhook_retry_delays[attempt]
                logger.info(f"Retrying webhook in {delay} seconds...")
                await asyncio.sleep(delay)
        
        # All attempts failed
        current_retry_count = subscription.get('retry_count', 0) + 1
        
        # Deactivate webhook after too many failures
        if current_retry_count >= 10:
            await SupabaseService.update(
                "webhook_subscriptions",
                {"id": subscription['id']},
                {
                    "retry_count": current_retry_count,
                    "is_active": False
                }
            )
            logger.error(
                f"Webhook {subscription['id']} deactivated after {current_retry_count} failures"
            )
        else:
            await SupabaseService.update(
                "webhook_subscriptions",
                {"id": subscription['id']},
                {"retry_count": current_retry_count}
            )
        
        return False
    
    @staticmethod
    async def dispatch_to_all_subscribers(
        event_type: str,
        payload: Dict[str, Any]
    ):
        """
        Dispatch an event to all active subscribers
        
        Args:
            event_type: Type of event
            payload: Event payload
        """
        # Get all active subscriptions
        try:
            subscriptions = await SupabaseService.select(
                "webhook_subscriptions",
                filters={"is_active": "true"}
            )
        except Exception as e:
            logger.error(f"Failed to fetch webhook subscriptions: {str(e)}")
            return
        
        # Filter subscriptions that listen to this event type
        relevant_subscriptions = [
            sub for sub in subscriptions
            if event_type in sub.get('event_types', [])
        ]
        
        logger.info(
            f"Dispatching {event_type} to {len(relevant_subscriptions)} subscribers"
        )
        
        # Dispatch to all subscribers concurrently
        tasks = [
            WebhookService.dispatch_webhook(sub, event_type, payload)
            for sub in relevant_subscriptions
        ]
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    @staticmethod
    async def test_webhook(subscription: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a test webhook
        
        Args:
            subscription: Webhook subscription dict
            
        Returns:
            dict: Test result with success status and details
        """
        test_payload = {
            "message": "This is a test webhook from MaxiPet API",
            "subscription_id": subscription['id'],
            "test": True
        }
        
        try:
            success = await WebhookService.dispatch_webhook(
                subscription=subscription,
                event_type="test.webhook",
                payload=test_payload
            )
            
            # Get the latest log
            try:
                logs = await SupabaseService.select(
                    "webhook_logs",
                    filters={"subscription_id": subscription['id']},
                    order="created_at.desc",
                    limit=1
                )
                latest_log = logs[0] if logs else None
            except:
                latest_log = None
            
            return {
                "success": success,
                "status_code": latest_log.get('response_status') if latest_log else None,
                "response_body": latest_log.get('response_body') if latest_log else None,
                "error": None if success else "Webhook delivery failed"
            }
            
        except Exception as e:
            logger.exception(f"Test webhook error: {str(e)}")
            return {
                "success": False,
                "status_code": None,
                "response_body": None,
                "error": str(e)
            }
