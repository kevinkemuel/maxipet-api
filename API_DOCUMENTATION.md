# MaxiPet API - Documentación Completa para Cliente

## 📋 Resumen Ejecutivo

MaxiPet API es una **API REST moderna y escalable** diseñada para gestionar el catálogo de productos, inventario y notificaciones de la tienda MaxiPet. La API está construida con tecnologías de vanguardia y sigue las mejores prácticas de la industria.

### Propósito Principal

Proporcionar una interfaz programática robusta y segura que permita:
- Gestionar el catálogo completo de productos para mascotas
- Controlar el inventario en tiempo real
- Recibir notificaciones automáticas sobre eventos importantes (stock bajo, cambios de productos, etc.)
- Integrar fácilmente con aplicaciones web, móviles o sistemas de terceros

---

## 🎯 Características Principales

### 1. **Gestión Completa de Productos (CRUD)**

**Propósito:** Administrar todo el catálogo de productos de la tienda.

**Funcionalidades:**
- ✅ **Crear productos nuevos** con toda su información (nombre, descripción, precio, marca, etc.)
- ✅ **Listar productos** con paginación, búsqueda y filtros avanzados
- ✅ **Actualizar información** de productos existentes
- ✅ **Eliminar productos** del catálogo
- ✅ **Búsqueda avanzada** por nombre, marca, categoría
- ✅ **Filtros** por precio, disponibilidad, marca
- ✅ **Ordenamiento** por precio, fecha de creación, nombre

**Endpoints principales:**
```
GET    /api/v1/products              - Listar productos
GET    /api/v1/products/{id}         - Ver detalle de un producto
POST   /api/v1/products              - Crear nuevo producto
PUT    /api/v1/products/{id}         - Actualizar producto
DELETE /api/v1/products/{id}         - Eliminar producto
GET    /api/v1/products/search       - Búsqueda avanzada
```

**Ejemplo de uso:**
```bash
# Listar productos con filtros
GET /api/v1/products?brand=Purina&min_price=10&max_price=100&page=1&limit=20
```

---

### 2. **Sistema de Webhooks (Notificaciones Automáticas)**

**Propósito:** Notificar automáticamente a sistemas externos cuando ocurren eventos importantes en la tienda.

**¿Qué es un Webhook?**
Un webhook es una notificación HTTP automática que se envía a una URL específica cuando ocurre un evento. Es como una "llamada telefónica" que la API hace a tu sistema para avisarte de algo importante.

**Eventos disponibles:**
- 🔔 `stock.updated` - Cuando cambia el inventario de un producto
- ⚠️ `stock.low` - Cuando un producto tiene stock bajo (configurable)
- ➕ `product.created` - Cuando se crea un nuevo producto
- ✏️ `product.updated` - Cuando se actualiza un producto
- ❌ `product.deleted` - Cuando se elimina un producto

**Características de seguridad:**
- ✅ **Firmas HMAC SHA256** - Cada notificación incluye una firma criptográfica para verificar autenticidad
- ✅ **Reintentos automáticos** - Si falla el envío, se reintenta 3 veces (1s, 5s, 15s)
- ✅ **Desactivación automática** - Después de 10 fallos consecutivos, el webhook se desactiva
- ✅ **Logs completos** - Registro de todos los intentos de envío

**Endpoints:**
```
POST   /api/v1/webhooks              - Registrar nuevo webhook
GET    /api/v1/webhooks              - Listar webhooks activos
GET    /api/v1/webhooks/{id}         - Ver detalle de webhook
PUT    /api/v1/webhooks/{id}         - Actualizar webhook
DELETE /api/v1/webhooks/{id}         - Eliminar webhook
POST   /api/v1/webhooks/{id}/test    - Probar webhook
GET    /api/v1/webhooks/{id}/logs    - Ver historial de envíos
```

**Ejemplo de registro:**
```json
POST /api/v1/webhooks
{
  "url": "https://tu-sistema.com/notificaciones",
  "event_types": ["stock.low", "product.created"],
  "description": "Notificaciones de inventario"
}
```

**Ejemplo de notificación recibida:**
```json
{
  "event_type": "stock.low",
  "timestamp": "2026-02-15T20:30:00Z",
  "data": {
    "product_id": "abc-123",
    "product_name": "Alimento Pro Plan 15kg",
    "current_stock": 3,
    "threshold": 10
  },
  "signature": "sha256=abc123..."
}
```

---

### 3. **Gestión de Inventario**

**Propósito:** Controlar las existencias de productos en tiempo real.

**Funcionalidades:**
- ✅ **Actualizar inventario** de productos individuales
- ✅ **Ajustar stock** con razón documentada
- ✅ **Historial completo** de cambios de inventario
- ✅ **Alertas automáticas** cuando el stock es bajo
- ✅ **Consultar productos** con stock bajo

**Endpoints:**
```
PATCH  /api/v1/inventory/{product_id}           - Actualizar inventario
POST   /api/v1/inventory/{product_id}/adjust    - Ajustar stock
GET    /api/v1/inventory/{product_id}/history   - Ver historial
GET    /api/v1/inventory/low-stock              - Productos con stock bajo
```

**Ejemplo de actualización:**
```json
PATCH /api/v1/inventory/{product_id}
{
  "inventory_count": 50,
  "reason": "Recepción de mercancía"
}
```

**Beneficios:**
- 📊 Trazabilidad completa de movimientos de inventario
- 🔔 Notificaciones automáticas cuando hay que reponer
- 📈 Historial para análisis y auditorías

---

### 4. **Monitoreo y Salud del Sistema**

**Propósito:** Verificar que la API esté funcionando correctamente.

**Endpoints:**
```
GET /api/v1/health/simple    - Estado básico (sin autenticación)
GET /api/v1/health           - Estado detallado (requiere API key)
```

**Respuesta de salud:**
```json
{
  "status": "healthy",
  "version": "v1",
  "timestamp": "2026-02-15T20:30:00Z",
  "services": {
    "supabase": {
      "status": "healthy",
      "type": "REST API"
    }
  }
}
```

---

## 🔒 Seguridad

### Autenticación por API Key

Todos los endpoints (excepto `/health/simple`) requieren autenticación mediante API Key.

**Cómo usar:**
```bash
curl -H "X-API-KEY: tu_api_key_secreta" https://api.maxipet.com/api/v1/products
```

### Seguridad de Webhooks

Cada webhook incluye una firma HMAC para verificar que la notificación proviene realmente de MaxiPet API:

```python
# Ejemplo de verificación en Python
import hmac
import hashlib

def verify_webhook(payload, signature, secret):
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

### Rate Limiting

La API incluye límites de tasa para prevenir abuso:
- **60 peticiones por minuto** por IP
- Respuesta `429 Too Many Requests` si se excede

---

## 📊 Versionamiento de API

La API usa versionamiento en la URL para garantizar compatibilidad:

```
/api/v1/products    ← Versión 1 (actual)
/api/v2/products    ← Futuras versiones
```

**Beneficio:** Puedes actualizar tu integración a tu ritmo sin que cambios en la API rompan tu sistema.

---

## 🚀 Arquitectura Técnica

### Stack Tecnológico

- **Framework:** FastAPI (Python) - Alto rendimiento y documentación automática
- **Base de datos:** Supabase (PostgreSQL) - Escalable y en la nube
- **Autenticación:** API Keys con validación middleware
- **Documentación:** OpenAPI/Swagger automática
- **Contenedorización:** Docker para despliegue consistente

### Características Técnicas

✅ **API RESTful** - Estándares HTTP, JSON
✅ **Documentación interactiva** - Swagger UI en `/docs`
✅ **Validación automática** - Pydantic schemas
✅ **Logging estructurado** - Trazabilidad completa
✅ **Manejo de errores** - Respuestas consistentes
✅ **CORS configurado** - Integración desde navegadores
✅ **Paginación** - Manejo eficiente de grandes datasets

---

## 📖 Documentación Interactiva

La API incluye documentación interactiva donde puedes **probar todos los endpoints directamente desde el navegador**:

```
https://tu-dominio.com/docs
```

**Características:**
- 📝 Descripción completa de cada endpoint
- 🧪 Prueba endpoints en vivo
- 📋 Ejemplos de peticiones y respuestas
- 🔍 Exploración de schemas de datos

---

## 💼 Casos de Uso Prácticos

### 1. **E-commerce / Tienda Online**
- Sincronizar catálogo de productos
- Actualizar precios y disponibilidad en tiempo real
- Recibir alertas de stock bajo para reponer

### 2. **Sistema de Punto de Venta (POS)**
- Consultar productos y precios
- Actualizar inventario al realizar ventas
- Mantener sincronización bidireccional

### 3. **Aplicación Móvil**
- Mostrar catálogo de productos
- Búsqueda y filtros avanzados
- Notificaciones push cuando hay nuevos productos

### 4. **Sistema de Gestión de Almacén**
- Recibir notificaciones de stock bajo
- Actualizar inventario al recibir mercancía
- Generar reportes de movimientos

### 5. **Integraciones con Marketplaces**
- Publicar productos en Amazon, MercadoLibre, etc.
- Sincronizar inventario automáticamente
- Actualizar precios en múltiples plataformas

---

## 📈 Beneficios para el Negocio

### Operacionales
- ⚡ **Automatización** - Reduce trabajo manual
- 🔄 **Sincronización en tiempo real** - Datos siempre actualizados
- 📊 **Trazabilidad** - Historial completo de cambios
- 🔔 **Alertas proactivas** - Previene quiebres de stock

### Técnicos
- 🚀 **Escalabilidad** - Crece con tu negocio
- 🔒 **Seguridad** - Autenticación y encriptación
- 📱 **Multi-plataforma** - Integra con cualquier sistema
- 🛠️ **Mantenibilidad** - Código modular y documentado

### Comerciales
- 💰 **Reduce costos** - Menos errores manuales
- ⏱️ **Ahorra tiempo** - Procesos automatizados
- 📈 **Mejora servicio** - Stock siempre disponible
- 🌐 **Expande canales** - Vende en más plataformas

---

## 🔧 Soporte y Mantenimiento

### Logs y Monitoreo
- Todos los eventos se registran con timestamp
- Logs estructurados para debugging
- Métricas de rendimiento disponibles

### Actualizaciones
- Versionamiento semántico
- Changelog documentado
- Notificación de cambios importantes

---

## 📞 Información de Contacto

Para soporte técnico, consultas o reportar problemas:
- **Documentación:** `/docs`
- **Health check:** `/api/v1/health/simple`

---

## 🎓 Próximos Pasos Recomendados

1. **Explorar la documentación interactiva** en `/docs`
2. **Obtener tu API Key** para comenzar a integrar
3. **Probar endpoints** con herramientas como Postman o curl
4. **Configurar webhooks** para recibir notificaciones
5. **Implementar integración** en tu sistema

---

**Versión de API:** v1  
**Última actualización:** Febrero 2026  
**Estado:** ✅ Producción
