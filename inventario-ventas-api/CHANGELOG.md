# Changelog

Todos los cambios notables de este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhiere a [Versionamiento Semántico](https://semver.org/lang/es/).

## [1.2.0] - 2026-05-01 (Planificado - MAJOR: Breaking Change)

### Cambiado (BREAKING)
- Modelo `Usuario`: campo `nombre` dividido en `nombre` y `apellido`
- Modelo `Producto`: nuevo campo obligatorio `categoria_id` (FK a nueva tabla `categorias`)
- Modelo `Factura`: nuevos campos `fecha_emision`, `fecha_vencimiento`, `estado_factura`
- Modelo `Venta`: nuevo campo `fecha_venta` (TIMESTAMP), campo `descuento_aplicado`

### Agregado
- Nueva entidad `Categoria` con campos `id`, `nombre`, `descripcion`, `activa`
- Nueva entidad `Proveedor` con campos `id`, `nombre`, `contacto`, `telefono`, `email`, `direccion`
- Nueva tabla `producto_proveedor` (relación muchos a muchos)
- Tabla `auditoria_cambios` para trazabilidad de operaciones
- Índices optimizados en tablas de alto tráfico

### Eliminado
- Campo redundante `ubicacion` en tabla `inventarios` (migrado a tabla `bodegas`)

## [1.1.0] - 2026-04-20 (Planificado - MINOR: Nueva Feature)

### Agregado
- Endpoint de reportes de ventas por rango de fechas
- Filtro de productos por rango de precio
- Paginación en listados de productos y ventas
- Campo `fecha_creacion` en tabla `ventas`

### Mejorado
- Validaciones de entrada en endpoints de checkout
- Mensajes de error más descriptivos

## [1.0.0] - 2026-04-10 (Actual - Release Inicial)

### Agregado
- Módulo de Ventas/Checkout completo
- Módulo de Inventario con control de stock
- Módulo de Facturación con generación de facturas
- Sistema de Autenticación con roles (Cliente, Vendedor, Bodeguero, Admin)
- Integración mock con Pasarela de Pagos
- Integración mock con Sistema de Contabilidad
- Integración mock con Servicio de Email
- Pipeline CI/CD con GitHub Actions
- Análisis estático con SonarQube y pylint
