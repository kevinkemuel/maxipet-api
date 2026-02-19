# V1 Routers package
from .products import router as products_router
from .webhooks import router as webhooks_router
from .inventory import router as inventory_router
from .health import router as health_router

__all__ = [
    'products_router',
    'webhooks_router',
    'inventory_router',
    'health_router'
]
