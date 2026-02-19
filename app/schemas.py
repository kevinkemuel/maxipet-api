from pydantic import BaseModel, Field, HttpUrl, validator
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

# ============= Product Schemas =============

class ProductBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    image_link: HttpUrl
    link: HttpUrl
    price: Decimal = Field(..., gt=0)
    currency: str = Field(default="USD", max_length=3)
    availability: str = Field(default="in stock")
    brand: Optional[str] = None
    inventory_count: int = Field(default=0, ge=0)

class ProductCreate(ProductBase):
    external_id: str = Field(..., min_length=1, max_length=255)

class ProductUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    image_link: Optional[HttpUrl] = None
    link: Optional[HttpUrl] = None
    price: Optional[Decimal] = Field(None, gt=0)
    currency: Optional[str] = Field(None, max_length=3)
    availability: Optional[str] = None
    brand: Optional[str] = None
    inventory_count: Optional[int] = Field(None, ge=0)

class ProductResponse(ProductBase):
    id: str
    external_id: str
    updated_at: datetime

    class Config:
        from_attributes = True

# ============= Webhook Schemas =============

class WebhookSubscriptionCreate(BaseModel):
    url: HttpUrl
    event_types: List[str] = Field(..., min_items=1)
    description: Optional[str] = None
    
    @validator('event_types')
    def validate_event_types(cls, v):
        valid_events = ['stock.updated', 'stock.low', 'product.created', 'product.updated', 'product.deleted']
        for event in v:
            if event not in valid_events:
                raise ValueError(f'Invalid event type: {event}. Valid types: {valid_events}')
        return v

class WebhookSubscriptionUpdate(BaseModel):
    url: Optional[HttpUrl] = None
    event_types: Optional[List[str]] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None

class WebhookSubscriptionResponse(BaseModel):
    id: str
    url: str
    event_types: List[str]
    secret_key: str
    is_active: bool
    description: Optional[str]
    retry_count: int
    last_triggered: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class WebhookLogResponse(BaseModel):
    id: str
    subscription_id: str
    event_type: str
    payload: dict
    response_status: Optional[int]
    response_body: Optional[str]
    delivered_at: Optional[datetime]
    attempts: int
    created_at: datetime

    class Config:
        from_attributes = True

class WebhookTestResponse(BaseModel):
    success: bool
    status_code: Optional[int]
    response_body: Optional[str]
    error: Optional[str]

# ============= Pagination Schemas =============

class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)

class PaginatedResponse(BaseModel):
    items: List[dict]
    total: int
    page: int
    limit: int
    pages: int

# ============= Inventory Schemas =============

class InventoryUpdate(BaseModel):
    inventory_count: int = Field(..., ge=0)
    reason: Optional[str] = None

class InventoryAdjustment(BaseModel):
    adjustment: int  # Can be negative
    reason: str = Field(..., min_length=1)

class InventoryHistoryResponse(BaseModel):
    id: str
    product_id: str
    previous_count: int
    new_count: int
    adjustment: int
    reason: Optional[str]
    created_at: datetime
    created_by: Optional[str]

    class Config:
        from_attributes = True

# ============= Search & Filter Schemas =============

class ProductSearchParams(BaseModel):
    q: Optional[str] = None  # Search query
    brand: Optional[str] = None
    min_price: Optional[Decimal] = Field(None, ge=0)
    max_price: Optional[Decimal] = Field(None, ge=0)
    availability: Optional[str] = None
    sort_by: str = Field(default="updated_at")
    order: str = Field(default="desc", pattern="^(asc|desc)$")

# ============= Health Check Schemas =============

class HealthCheckResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime
    services: dict

# ============= Generic Response Schemas =============

class MessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    timestamp: datetime
