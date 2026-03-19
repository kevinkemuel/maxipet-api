from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Supabase ERP (mvyshricuovdufooldzz.supabase.co — schema maxipet)
    supabase_url: str
    supabase_key: str

    # Supabase Catálogo (db.maxipetonline.com — schema public)
    supabase_catalog_url: str
    supabase_catalog_key: str
    
    # API Security
    api_key_token: str
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Database
    database_url: str = ""
    
    # API Configuration
    api_version: str = "v1"
    api_title: str = "MaxiPet API"
    api_description: str = "API para gestión de productos y webhooks de MaxiPet"
    
    # CORS
    cors_origins: str = "*"  # Changed to string, will be split in main.py
    
    # Rate Limiting
    rate_limit_per_minute: int = 60
    
    # Webhooks
    webhook_retry_attempts: int = 3
    webhook_timeout: int = 10  # seconds
    webhook_retry_delays: List[int] = [1, 5, 15]  # Delays between retries in seconds
    
    # Inventory
    low_stock_threshold: int = 10
    
    # Logging
    log_level: str = "INFO"

    class Config:
        env_file = ".env"

settings = Settings()
