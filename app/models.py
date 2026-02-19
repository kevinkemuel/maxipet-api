from sqlalchemy import Column, String, Text, Numeric, Integer, TIMESTAMP, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class Product(Base):
    __tablename__ = "products"
    __table_args__ = {"schema": "maxipet"}

    id = Column(String, primary_key=True, index=True, default=generate_uuid)
    external_id = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    image_link = Column(String, nullable=False)
    link = Column(String, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String, default="USD")
    availability = Column(String, default="in stock")
    brand = Column(String)
    inventory_count = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

class WebhookSubscription(Base):
    __tablename__ = "webhook_subscriptions"
    __table_args__ = {"schema": "maxipet"}

    id = Column(String, primary_key=True, index=True, default=generate_uuid)
    url = Column(String, nullable=False)
    event_types = Column(JSON, nullable=False)  # List of event types
    secret_key = Column(String, nullable=False)  # For HMAC signing
    is_active = Column(Boolean, default=True)
    description = Column(Text)
    retry_count = Column(Integer, default=0)
    last_triggered = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

class WebhookLog(Base):
    __tablename__ = "webhook_logs"
    __table_args__ = {"schema": "maxipet"}

    id = Column(String, primary_key=True, index=True, default=generate_uuid)
    subscription_id = Column(String, ForeignKey("maxipet.webhook_subscriptions.id"), nullable=False)
    event_type = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    response_status = Column(Integer)
    response_body = Column(Text)
    delivered_at = Column(TIMESTAMP)
    attempts = Column(Integer, default=1)
    created_at = Column(TIMESTAMP, server_default=func.now())

class InventoryHistory(Base):
    __tablename__ = "inventory_history"
    __table_args__ = {"schema": "maxipet"}

    id = Column(String, primary_key=True, index=True, default=generate_uuid)
    product_id = Column(String, ForeignKey("maxipet.products.id"), nullable=False)
    previous_count = Column(Integer, nullable=False)
    new_count = Column(Integer, nullable=False)
    adjustment = Column(Integer, nullable=False)
    reason = Column(Text)
    created_by = Column(String)  # API key or user ID
    created_at = Column(TIMESTAMP, server_default=func.now())