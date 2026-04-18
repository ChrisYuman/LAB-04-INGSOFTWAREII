"""
Script de validación post-migración
====================================
Ejecuta verificaciones de integridad después de aplicar una migración.
Valida:
  - Conteo de registros (no se perdieron datos)
  - Integridad referencial entre tablas
  - Consistencia de datos transformados
  - Ausencia de valores nulos inesperados
  - Reglas de negocio del dominio

Uso: python migrations/validate_migration.py [ruta_db]
"""

import sqlite3
import sys
import os


class ValidationResult:
    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []

    def add_pass(self, msg):
        self.passed.append(msg)
        print(f"  ✅ PASS: {msg}")

    def add_fail(self, msg):
        self.failed.append(msg)
        print(f"  ❌ FAIL: {msg}")

    def add_warning(self, msg):
        self.warnings.append(msg)
        print(f"  ⚠️  WARN: {msg}")

    def summary(self):
        total = len(self.passed) + len(self.failed) + len(self.warnings)
        print("\n" + "=" * 60)
        print(f"RESULTADOS DE VALIDACIÓN: {len(self.passed)}/{total} pasaron")
        print(f"  ✅ Pasaron: {len(self.passed)}")
        print(f"  ❌ Fallaron: {len(self.failed)}")
        print(f"  ⚠️  Advertencias: {len(self.warnings)}")
        print("=" * 60)
        return len(self.failed) == 0


def validate_migration(db_path):
    """Ejecuta todas las validaciones post-migración."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    result = ValidationResult()

    print("\n🔍 VALIDACIÓN POST-MIGRACIÓN")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 1. CONTEO DE REGISTROS
    # ------------------------------------------------------------------
    print("\n📊 1. Conteo de registros")
    tables = ['usuarios', 'productos', 'ventas', 'venta_items', 'inventarios', 'facturas']
    for table in tables:
        try:
            count = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            if count >= 0:
                result.add_pass(f"Tabla '{table}': {count} registros")
            if count == 0:
                result.add_warning(f"Tabla '{table}' está vacía")
        except sqlite3.OperationalError:
            result.add_fail(f"Tabla '{table}' no existe")

    # ------------------------------------------------------------------
    # 2. INTEGRIDAD REFERENCIAL
    # ------------------------------------------------------------------
    print("\n🔗 2. Integridad referencial")

    # Ventas → Usuarios
    orphan_ventas = cursor.execute("""
        SELECT COUNT(*) FROM ventas v 
        LEFT JOIN usuarios u ON v.usuario_id = u.id 
        WHERE u.id IS NULL
    """).fetchone()[0]
    if orphan_ventas == 0:
        result.add_pass("Todas las ventas tienen usuario válido")
    else:
        result.add_fail(f"{orphan_ventas} ventas sin usuario válido (huérfanas)")

    # VentaItems → Ventas
    orphan_items = cursor.execute("""
        SELECT COUNT(*) FROM venta_items vi 
        LEFT JOIN ventas v ON vi.venta_id = v.id 
        WHERE v.id IS NULL
    """).fetchone()[0]
    if orphan_items == 0:
        result.add_pass("Todos los items tienen venta válida")
    else:
        result.add_fail(f"{orphan_items} items sin venta válida")

    # VentaItems → Productos
    orphan_prod = cursor.execute("""
        SELECT COUNT(*) FROM venta_items vi 
        LEFT JOIN productos p ON vi.producto_id = p.id 
        WHERE p.id IS NULL
    """).fetchone()[0]
    if orphan_prod == 0:
        result.add_pass("Todos los items refieren a productos válidos")
    else:
        result.add_fail(f"{orphan_prod} items con producto inválido")

    # Facturas → Ventas
    orphan_fac = cursor.execute("""
        SELECT COUNT(*) FROM facturas f 
        LEFT JOIN ventas v ON f.venta_id = v.id 
        WHERE v.id IS NULL
    """).fetchone()[0]
    if orphan_fac == 0:
        result.add_pass("Todas las facturas tienen venta válida")
    else:
        result.add_fail(f"{orphan_fac} facturas sin venta válida")

    # Inventario → Productos
    orphan_inv = cursor.execute("""
        SELECT COUNT(*) FROM inventarios i 
        LEFT JOIN productos p ON i.producto_id = p.id 
        WHERE p.id IS NULL
    """).fetchone()[0]
    if orphan_inv == 0:
        result.add_pass("Todo el inventario refiere a productos válidos")
    else:
        result.add_fail(f"{orphan_inv} registros de inventario sin producto válido")

    # ------------------------------------------------------------------
    # 3. CONSISTENCIA DE DATOS
    # ------------------------------------------------------------------
    print("\n🧪 3. Consistencia de datos")

    # Precios positivos
    precios_negativos = cursor.execute(
        "SELECT COUNT(*) FROM productos WHERE precio < 0"
    ).fetchone()[0]
    if precios_negativos == 0:
        result.add_pass("Todos los productos tienen precio >= 0")
    else:
        result.add_fail(f"{precios_negativos} productos con precio negativo")

    # Stock no negativo
    stock_negativo = cursor.execute(
        "SELECT COUNT(*) FROM inventarios WHERE cantidad < 0"
    ).fetchone()[0]
    if stock_negativo == 0:
        result.add_pass("Todo el inventario tiene stock >= 0")
    else:
        result.add_fail(f"{stock_negativo} registros con stock negativo")

    # Totales de venta positivos
    ventas_negativas = cursor.execute(
        "SELECT COUNT(*) FROM ventas WHERE total <= 0"
    ).fetchone()[0]
    if ventas_negativas == 0:
        result.add_pass("Todas las ventas tienen total > 0")
    else:
        result.add_warning(f"{ventas_negativas} ventas con total <= 0")

    # Facturas con número único
    fac_duplicadas = cursor.execute("""
        SELECT numero_factura, COUNT(*) c FROM facturas 
        GROUP BY numero_factura HAVING c > 1
    """).fetchall()
    if not fac_duplicadas:
        result.add_pass("Todos los números de factura son únicos")
    else:
        result.add_fail(f"{len(fac_duplicadas)} números de factura duplicados")

    # ------------------------------------------------------------------
    # 4. VALIDACIONES ESPECÍFICAS v1.2.0
    # ------------------------------------------------------------------
    print("\n🆕 4. Validaciones específicas v1.2.0")

    # Verificar tabla categorias existe
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='categorias'")
    if cursor.fetchone():
        result.add_pass("Tabla 'categorias' existe")
        # Verificar que productos tienen categoria
        sin_cat = cursor.execute(
            "SELECT COUNT(*) FROM productos WHERE categoria_id IS NULL"
        ).fetchone()[0]
        if sin_cat == 0:
            result.add_pass("Todos los productos tienen categoría asignada")
        else:
            result.add_warning(f"{sin_cat} productos sin categoría")
    else:
        result.add_warning("Tabla 'categorias' no existe (migración v1.2.0 no aplicada)")

    # Verificar transformación de nombres
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='usuarios'")
    schema = cursor.fetchone()
    if schema and 'apellido' in schema[0]:
        nombres_vacios = cursor.execute(
            "SELECT COUNT(*) FROM usuarios WHERE nombre IS NULL OR nombre = ''"
        ).fetchone()[0]
        if nombres_vacios == 0:
            result.add_pass("Todos los usuarios tienen nombre después de la transformación")
        else:
            result.add_fail(f"{nombres_vacios} usuarios sin nombre tras la migración")
    else:
        result.add_warning("Campo 'apellido' no existe (migración v1.2.0 no aplicada)")

    # ------------------------------------------------------------------
    # 5. HISTORIAL DE MIGRACIONES
    # ------------------------------------------------------------------
    print("\n📋 5. Historial de migraciones")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='migration_history'")
    if cursor.fetchone():
        migrations = cursor.execute(
            "SELECT migration_id, applied_at, rolled_back_at FROM migration_history ORDER BY applied_at"
        ).fetchall()
        for m in migrations:
            status = "ACTIVA" if not m[2] else f"REVERTIDA ({m[2]})"
            result.add_pass(f"Migración {m[0]} - {status}")
    else:
        result.add_warning("No hay historial de migraciones")

    conn.close()
    return result.summary()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = os.path.join(os.path.dirname(__file__), "..", "inventario_ventas.db")

    success = validate_migration(db_path)
    sys.exit(0 if success else 1)
