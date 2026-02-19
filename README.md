# MaxiPet API

API REST para gestión de productos de mascotas con sistema de webhooks y control de inventario.

## 🚀 Características

- **API Versionada**: Endpoints bajo `/api/v1/`
- **CRUD Completo de Productos**: Crear, leer, actualizar y eliminar productos
- **Búsqueda y Filtros**: Búsqueda por texto, filtros por precio, marca, disponibilidad
- **Paginación**: Soporte completo de paginación en listados
- **Webhooks Outbound**: Sistema de notificaciones automáticas
  - Eventos: `stock.updated`, `stock.low`, `product.created`, `product.updated`, `product.deleted`
  - Reintentos automáticos con backoff exponencial
  - Firmas HMAC para seguridad
  - Logs de entregas
- **Gestión de Inventario**: Control de stock con historial de cambios
- **Rate Limiting**: Protección contra abuso
- **Autenticación**: API Key authentication
- **Health Checks**: Monitoreo de servicios
- **Documentación**: Swagger UI automática

## 📋 Requisitos

- Python 3.8+
- PostgreSQL (via Supabase)
- Cuenta de Supabase

## 🛠️ Instalación

1. **Clonar el repositorio**
```bash
git clone <repository-url>
cd maxipet-api
```

2. **Crear entorno virtual**
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Configurar variables de entorno**
```bash
cp .env.example .env
# Editar .env con tus credenciales
```

5. **Crear tablas de base de datos**
```bash
python create_tables.py
```

6. **Ejecutar servidor**
```bash
uvicorn app.main:app --reload
```

La API estará disponible en `http://localhost:8000`

## 📚 Documentación

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔑 Autenticación

Todos los endpoints (excepto `/` y `/api/v1/health/simple`) requieren autenticación con API Key:

```bash
curl -H "X-API-KEY: your-api-key" http://localhost:8000/api/v1/products
```

## 📡 Endpoints Principales

### Productos
- `GET /api/v1/products` - Listar productos (con paginación y filtros)
- `GET /api/v1/products/{id}` - Obtener producto
- `GET /api/v1/products/search?q=query` - Buscar productos
- `POST /api/v1/products` - Crear producto
- `PUT /api/v1/products/{id}` - Actualizar producto
- `DELETE /api/v1/products/{id}` - Eliminar producto

### Webhooks
- `POST /api/v1/webhooks` - Registrar webhook
- `GET /api/v1/webhooks` - Listar webhooks
- `GET /api/v1/webhooks/{id}` - Obtener webhook
- `PUT /api/v1/webhooks/{id}` - Actualizar webhook
- `DELETE /api/v1/webhooks/{id}` - Eliminar webhook
- `GET /api/v1/webhooks/{id}/logs` - Ver logs de entregas
- `POST /api/v1/webhooks/{id}/test` - Probar webhook

### Inventario
- `GET /api/v1/inventory/low-stock` - Productos con bajo stock
- `PATCH /api/v1/inventory/{product_id}` - Actualizar inventario
- `POST /api/v1/inventory/{product_id}/adjust` - Ajustar inventario
- `GET /api/v1/inventory/{product_id}/history` - Historial de cambios

### Health
- `GET /api/v1/health` - Health check completo (requiere auth)
- `GET /api/v1/health/simple` - Health check simple (sin auth)

## 🔔 Webhooks

### Registrar un Webhook

```bash
curl -X POST http://localhost:8000/api/v1/webhooks \
  -H "X-API-KEY: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-domain.com/webhook",
    "event_types": ["stock.updated", "stock.low"],
    "description": "Notificaciones de inventario"
  }'
```

### Eventos Disponibles

- `stock.updated`: Cuando cambia el inventario de un producto
- `stock.low`: Cuando el stock cae por debajo del umbral
- `product.created`: Cuando se crea un producto
- `product.updated`: Cuando se actualiza un producto
- `product.deleted`: Cuando se elimina un producto

### Verificar Firma HMAC

Los webhooks incluyen una firma HMAC en el header `X-Webhook-Signature`:

```python
import hmac
import hashlib

def verify_webhook(payload, signature, secret):
    expected = hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

## 🔧 Configuración

Variables de entorno importantes:

```env
# Supabase
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# Seguridad
API_KEY_TOKEN=your_api_key
SECRET_KEY=your_secret_key

# Base de datos
DATABASE_URL=postgresql://user:pass@host:port/db

# Webhooks
WEBHOOK_RETRY_ATTEMPTS=3
WEBHOOK_TIMEOUT=10
LOW_STOCK_THRESHOLD=10

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
```

## 🐳 Docker

```bash
docker build -t maxipet-api .
docker run -p 8000:8000 --env-file .env maxipet-api
```

## 📝 Ejemplos de Uso

### Listar productos con filtros
```bash
curl "http://localhost:8000/api/v1/products?page=1&limit=20&brand=PetCo&min_price=10&max_price=50" \
  -H "X-API-KEY: your-api-key"
```

### Buscar productos
```bash
curl "http://localhost:8000/api/v1/products/search?q=collar" \
  -H "X-API-KEY: your-api-key"
```

### Actualizar inventario
```bash
curl -X PATCH http://localhost:8000/api/v1/inventory/product-123 \
  -H "X-API-KEY: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"inventory_count": 50, "reason": "Restock"}'
```

## 🤝 Contribuir

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT.

## 🆘 Soporte

Para soporte, abre un issue en GitHub o contacta al equipo de desarrollo.
