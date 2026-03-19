from typing import Optional, Dict, Any
from app.services.product_service import ProductService
from app.services.catalog_service import CatalogService
from app.services.webhook_service import WebhookService
from app.services.supabase_service import SupabaseService
from app.config import settings
from app.utils.logger import logger
from datetime import datetime


class InventoryService:
    """
    Gestión de inventario sobre productos_catalogo.
    - Lee/escribe el campo 'inventario' (TEXT) del catálogo.
    - El historial de cambios se registra en la tabla inventory_history del ERP.
    - Dispara webhooks stock.updated y stock.low.
    """

    @staticmethod
    async def update_inventory(
        product_id: str,
        new_count: int,
        reason: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Actualiza el inventario de un producto del catálogo.

        Args:
            product_id: ID entero del producto (como string).
            new_count:  Nuevo valor de inventario.
            reason:     Razón del cambio.
            created_by: Identificador del solicitante.

        Returns:
            dict: Producto actualizado.
        """
        # ── Obtener producto actual ──
        current_product = await ProductService.get_product_by_id(product_id)
        if not current_product:
            raise ValueError(f"Producto {product_id} no encontrado")

        # inventario es TEXT en el catálogo
        previous_count = int(current_product.get("inventario") or 0)

        # ── Actualizar en catálogo ──
        try:
            pid = int(product_id)
        except (ValueError, TypeError):
            raise ValueError(f"ID de producto inválido: {product_id}")

        updated_product = await CatalogService.update_producto(
            pid, {"inventario": str(new_count)}
        )

        # ── Registrar historial en ERP ──
        try:
            history_record = {
                "product_id": product_id,
                "previous_count": previous_count,
                "new_count": new_count,
                "adjustment": new_count - previous_count,
                "reason": reason,
                "created_by": created_by,
                "created_at": datetime.utcnow().isoformat(),
            }
            await SupabaseService.insert("inventory_history", history_record)
        except Exception as e:
            logger.error(f"No se pudo registrar historial de inventario: {e}")

        # ── Webhooks ──
        if previous_count != new_count:
            await WebhookService.dispatch_to_all_subscribers(
                event_type="stock.updated",
                payload={
                    "product_id": product_id,
                    "product_nombre": current_product.get("nombre"),
                    "previous_count": previous_count,
                    "new_count": new_count,
                    "adjustment": new_count - previous_count,
                },
            )

            # Umbral: si bajo_inventario existe en el producto, úsalo; si no, settings
            bajo_inv = current_product.get("bajo_inventario")
            threshold = int(bajo_inv) if bajo_inv else settings.low_stock_threshold

            if new_count < threshold and previous_count >= threshold:
                await WebhookService.dispatch_to_all_subscribers(
                    event_type="stock.low",
                    payload={
                        "product_id": product_id,
                        "product_nombre": current_product.get("nombre"),
                        "inventario": new_count,
                        "threshold": threshold,
                    },
                )
                logger.warning(
                    f"Bajo inventario — producto {product_id}: {new_count} unidades "
                    f"(umbral: {threshold})"
                )

        return updated_product or current_product

    @staticmethod
    async def adjust_inventory(
        product_id: str,
        adjustment: int,
        reason: str,
        created_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Ajusta el inventario de forma relativa (+/-).

        Args:
            product_id: ID del producto.
            adjustment: Cantidad a sumar (puede ser negativa).
            reason:     Razón del ajuste (requerida).
            created_by: Identificador del solicitante.
        """
        current_product = await ProductService.get_product_by_id(product_id)
        if not current_product:
            raise ValueError(f"Producto {product_id} no encontrado")

        current_count = int(current_product.get("inventario") or 0)
        new_count = max(0, current_count + adjustment)  # nunca negativo

        return await InventoryService.update_inventory(
            product_id=product_id,
            new_count=new_count,
            reason=reason,
            created_by=created_by,
        )

    @staticmethod
    async def get_inventory_history(product_id: str, limit: int = 50):
        """Obtiene el historial de cambios de inventario de un producto."""
        try:
            return await SupabaseService.select(
                "inventory_history",
                filters={"product_id": product_id},
                order="created_at.desc",
                limit=limit,
            )
        except Exception as e:
            logger.error(f"Error obteniendo historial de inventario: {e}")
            return []
