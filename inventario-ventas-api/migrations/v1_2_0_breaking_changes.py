"""
Migración v1.2.0 - Breaking Changes (MAJOR)
=============================================
Cambios estructurales:
  - Divide campo 'nombre' de usuarios en 'nombre' y 'apellido'
  - Crea tabla 'categorias'
  - Agrega FK 'categoria_id' a tabla 'productos'
  - Crea tabla 'proveedores'
  - Crea tabla relacional 'producto_proveedor'
  - Agrega campos de fecha y estado a 'facturas'
  - Agrega campo 'descuento_aplicado' a 'ventas'
  - Crea tabla 'auditoria_cambios'

Tipo: MAJOR (rompe compatibilidad hacia atrás)
Fecha: 2026-05-01
Autor: Equipo de Desarrollo

ADVERTENCIA: Esta migración NO es fácilmente reversible para el campo
'nombre' → 'nombre' + 'apellido' ya que se pierde la información de
cómo estaba concatenado originalmente.
"""

import sqlite3
import sys
import os
from datetime import datetime

MIGRATION_ID = "v1_2_0"
MIGRATION_DESCRIPTION = "Breaking change: reestructuración del modelo de datos"

# -------------------------------------------------------------------
# Prerequisito: la migración v1.1.0 debe estar aplicada
# -------------------------------------------------------------------
PREREQUISITE = "v1_1_0"


def check_prerequisite(cursor):
    """Verifica que la migración prerrequisito esté aplicada."""
    cursor.execute(
        "SELECT id FROM migration_history WHERE migration_id = ? AND rolled_back_at IS NULL",
        (PREREQUISITE,)
    )
    return cursor.fetchone() is not None


def check_already_applied(cursor):
    """Verifica si la migración ya fue aplicada (idempotencia)."""
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='migration_history'
    """)
    if not cursor.fetchone():
        return False
    cursor.execute(
        "SELECT id FROM migration_history WHERE migration_id = ? AND rolled_back_at IS NULL",
        (MIGRATION_ID,)
    )
    return cursor.fetchone() is not None


def transform_nombre(nombre_completo):
    """
    Transforma 'nombre_completo' en (nombre, apellido).
    Estrategia: la primera palabra es nombre, el resto es apellido.
    Si solo hay una palabra, apellido queda vacío.
    """
    if not nombre_completo or not nombre_completo.strip():
        return ("Sin nombre", "")
    partes = nombre_completo.strip().split(" ", 1)
    nombre = partes[0]
    apellido = partes[1] if len(partes) > 1 else ""
    return (nombre, apellido)


def migrate(db_path):
    """Ejecuta la migración v1.2.0."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        if check_already_applied(cursor):
            print(f"[SKIP] Migración {MIGRATION_ID} ya fue aplicada.")
            return True

        if not check_prerequisite(cursor):
            print(f"[ERROR] Prerrequisito {PREREQUISITE} no está aplicado.")
            return False

        print(f"[START] Aplicando migración {MIGRATION_ID} (BREAKING CHANGE)...")
        print("=" * 60)

        # ============================================================
        # PASO 1: Crear tabla de categorías
        # ============================================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categorias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE,
                descripcion TEXT,
                activa INTEGER DEFAULT 1,
                fecha_creacion TEXT
            )
        """)
        # Insertar categoría por defecto para productos existentes
        cursor.execute(
            "INSERT OR IGNORE INTO categorias (nombre, descripcion, fecha_creacion) VALUES (?, ?, ?)",
            ("General", "Categoría por defecto para productos existentes", datetime.now().isoformat())
        )
        categoria_default_id = cursor.execute(
            "SELECT id FROM categorias WHERE nombre = 'General'"
        ).fetchone()[0]
        print("  ✔ Tabla 'categorias' creada con categoría por defecto")

        # ============================================================
        # PASO 2: Agregar categoria_id a productos
        # ============================================================
        try:
            cursor.execute(f"ALTER TABLE productos ADD COLUMN categoria_id INTEGER DEFAULT {categoria_default_id}")
            cursor.execute(
                f"UPDATE productos SET categoria_id = ? WHERE categoria_id IS NULL",
                (categoria_default_id,)
            )
            print("  ✔ Campo 'categoria_id' agregado a 'productos'")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("  ⚠ Campo 'categoria_id' ya existe, omitiendo...")
            else:
                raise

        # ============================================================
        # PASO 3: Dividir nombre de usuarios en nombre + apellido
        # ============================================================
        print("  → Transformando campo 'nombre' de usuarios...")
        
        # Leer datos actuales
        usuarios = cursor.execute("SELECT id, nombre FROM usuarios").fetchall()
        
        # Hacer backup antes de transformar
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS _backup_usuarios_v1_2_0 AS 
            SELECT * FROM usuarios
        """)
        print(f"  ✔ Backup de {len(usuarios)} usuarios creado en '_backup_usuarios_v1_2_0'")

        # Agregar campo apellido
        try:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN apellido TEXT DEFAULT ''")
        except sqlite3.OperationalError as e:
            if "duplicate column" not in str(e).lower():
                raise

        # Transformar datos: dividir nombre en nombre + apellido
        errores_transformacion = []
        for uid, nombre_completo in usuarios:
            try:
                nombre, apellido = transform_nombre(nombre_completo)
                cursor.execute(
                    "UPDATE usuarios SET nombre = ?, apellido = ? WHERE id = ?",
                    (nombre, apellido, uid)
                )
            except Exception as e:
                errores_transformacion.append({
                    "usuario_id": uid,
                    "nombre_original": nombre_completo,
                    "error": str(e)
                })

        if errores_transformacion:
            print(f"  ⚠ {len(errores_transformacion)} errores durante transformación de nombres")
            for err in errores_transformacion:
                print(f"    - Usuario {err['usuario_id']}: {err['error']}")
        else:
            print(f"  ✔ {len(usuarios)} usuarios transformados exitosamente")

        # ============================================================
        # PASO 4: Crear tabla de proveedores
        # ============================================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS proveedores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                contacto TEXT,
                telefono TEXT,
                email TEXT UNIQUE,
                direccion TEXT,
                activo INTEGER DEFAULT 1,
                fecha_registro TEXT
            )
        """)
        print("  ✔ Tabla 'proveedores' creada")

        # ============================================================
        # PASO 5: Crear tabla relacional producto_proveedor
        # ============================================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS producto_proveedor (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                producto_id INTEGER NOT NULL REFERENCES productos(id),
                proveedor_id INTEGER NOT NULL REFERENCES proveedores(id),
                precio_compra REAL,
                tiempo_entrega_dias INTEGER,
                UNIQUE(producto_id, proveedor_id)
            )
        """)
        print("  ✔ Tabla 'producto_proveedor' creada")

        # ============================================================
        # PASO 6: Agregar campos a facturas
        # ============================================================
        campos_factura = [
            ("fecha_emision", "TEXT"),
            ("fecha_vencimiento", "TEXT"),
            ("estado_factura", "TEXT DEFAULT 'emitida'"),
        ]
        for campo, tipo in campos_factura:
            try:
                cursor.execute(f"ALTER TABLE facturas ADD COLUMN {campo} {tipo}")
            except sqlite3.OperationalError as e:
                if "duplicate column" not in str(e).lower():
                    raise

        # Actualizar facturas existentes con fecha actual
        cursor.execute(
            "UPDATE facturas SET fecha_emision = ?, estado_factura = 'emitida' WHERE fecha_emision IS NULL",
            (datetime.now().isoformat(),)
        )
        print("  ✔ Campos de fecha y estado agregados a 'facturas'")

        # ============================================================
        # PASO 7: Agregar descuento_aplicado a ventas
        # ============================================================
        try:
            cursor.execute("ALTER TABLE ventas ADD COLUMN descuento_aplicado REAL DEFAULT 0.0")
        except sqlite3.OperationalError as e:
            if "duplicate column" not in str(e).lower():
                raise
        print("  ✔ Campo 'descuento_aplicado' agregado a 'ventas'")

        # ============================================================
        # PASO 8: Crear tabla de auditoría
        # ============================================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auditoria_cambios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tabla_afectada TEXT NOT NULL,
                registro_id INTEGER,
                tipo_operacion TEXT NOT NULL,
                datos_anteriores TEXT,
                datos_nuevos TEXT,
                usuario_id INTEGER,
                fecha TEXT NOT NULL
            )
        """)
        print("  ✔ Tabla 'auditoria_cambios' creada")

        # ============================================================
        # Registrar migración
        # ============================================================
        cursor.execute(
            "INSERT INTO migration_history (migration_id, description, applied_at) VALUES (?, ?, ?)",
            (MIGRATION_ID, MIGRATION_DESCRIPTION, datetime.now().isoformat())
        )

        conn.commit()
        print("=" * 60)
        print(f"[SUCCESS] Migración {MIGRATION_ID} aplicada exitosamente.")
        
        if errores_transformacion:
            print(f"\n[WARNING] Revisar {len(errores_transformacion)} errores de transformación.")
        
        return True

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Migración {MIGRATION_ID} falló: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()


def rollback(db_path):
    """
    Revierte la migración v1.2.0.
    
    NOTA: La reversión del campo 'nombre' de usuarios es PARCIAL.
    Se restaura desde la tabla de backup '_backup_usuarios_v1_2_0'.
    Si el backup no existe, se concatenan nombre + apellido.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        print(f"[ROLLBACK] Revirtiendo migración {MIGRATION_ID}...")
        print("=" * 60)
        print("⚠ ADVERTENCIA: Esta reversión puede causar pérdida de datos")
        print("  en registros creados después de la migración original.")
        print("=" * 60)

        # Restaurar usuarios desde backup si existe
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='_backup_usuarios_v1_2_0'
        """)
        if cursor.fetchone():
            # Restaurar datos originales
            cursor.execute("DELETE FROM usuarios")
            cursor.execute("INSERT INTO usuarios (id, nombre, email, password_hash, rol) SELECT id, nombre, email, password_hash, rol FROM _backup_usuarios_v1_2_0")
            cursor.execute("DROP TABLE _backup_usuarios_v1_2_0")
            print("  ✔ Usuarios restaurados desde backup")
        else:
            # Concatenar nombre + apellido como fallback
            cursor.execute("UPDATE usuarios SET nombre = nombre || ' ' || COALESCE(apellido, '')")
            print("  ⚠ Backup no encontrado, se concatenó nombre + apellido")

        # Eliminar tablas nuevas
        for tabla in ['producto_proveedor', 'proveedores', 'categorias', 'auditoria_cambios']:
            cursor.execute(f"DROP TABLE IF EXISTS {tabla}")
            print(f"  ✔ Tabla '{tabla}' eliminada")

        # Marcar como revertido
        cursor.execute(
            "UPDATE migration_history SET rolled_back_at = ? WHERE migration_id = ?",
            (datetime.now().isoformat(), MIGRATION_ID)
        )

        conn.commit()
        print("=" * 60)
        print(f"[SUCCESS] Rollback de {MIGRATION_ID} completado.")
        print("⚠ Datos de proveedores/categorías/auditoría creados post-migración se perdieron.")
        return True

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Rollback de {MIGRATION_ID} falló: {e}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    db = os.path.join(os.path.dirname(__file__), "..", "inventario_ventas.db")
    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        rollback(db)
    else:
        migrate(db)
