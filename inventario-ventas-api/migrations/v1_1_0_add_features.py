"""
Migración v1.1.0 - Nuevas funcionalidades (MINOR)
==================================================
Cambios:
  - Agrega campo 'fecha_creacion' a tabla 'ventas'
  - Agrega campo 'stock_minimo' a tabla 'inventarios' para alertas
  - Crea índice en ventas.usuario_id para optimizar consultas

Tipo: MINOR (compatible hacia atrás)
Fecha: 2026-04-20
Autor: Equipo de Desarrollo
"""

import sqlite3
import sys
import os
from datetime import datetime


MIGRATION_ID = "v1_1_0"
MIGRATION_DESCRIPTION = "Agregar fecha_creacion a ventas, stock_minimo a inventarios"


def check_already_applied(cursor):
    """Verifica si la migración ya fue aplicada (idempotencia)."""
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='migration_history'
    """)
    if not cursor.fetchone():
        cursor.execute("""
            CREATE TABLE migration_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                migration_id TEXT UNIQUE NOT NULL,
                description TEXT,
                applied_at TEXT NOT NULL,
                rolled_back_at TEXT
            )
        """)
        return False

    cursor.execute(
        "SELECT id FROM migration_history WHERE migration_id = ? AND rolled_back_at IS NULL",
        (MIGRATION_ID,)
    )
    return cursor.fetchone() is not None


def migrate(db_path):
    """Ejecuta la migración hacia adelante."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        if check_already_applied(cursor):
            print(f"[SKIP] Migración {MIGRATION_ID} ya fue aplicada previamente.")
            return True

        print(f"[START] Aplicando migración {MIGRATION_ID}...")

        # 1. Agregar campo fecha_creacion a ventas
        try:
            cursor.execute("ALTER TABLE ventas ADD COLUMN fecha_creacion TEXT")
            print("  ✔ Campo 'fecha_creacion' agregado a tabla 'ventas'")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("  ⚠ Campo 'fecha_creacion' ya existe en 'ventas', omitiendo...")
            else:
                raise

        # Llenar valores existentes con fecha actual
        cursor.execute(
            "UPDATE ventas SET fecha_creacion = ? WHERE fecha_creacion IS NULL",
            (datetime.now().isoformat(),)
        )
        print(f"  ✔ Registros existentes actualizados con fecha por defecto")

        # 2. Agregar campo stock_minimo a inventarios
        try:
            cursor.execute("ALTER TABLE inventarios ADD COLUMN stock_minimo INTEGER DEFAULT 5")
            print("  ✔ Campo 'stock_minimo' agregado a tabla 'inventarios'")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("  ⚠ Campo 'stock_minimo' ya existe en 'inventarios', omitiendo...")
            else:
                raise

        # 3. Crear índice para optimizar consultas de ventas por usuario
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ventas_usuario ON ventas(usuario_id)")
            print("  ✔ Índice 'idx_ventas_usuario' creado")
        except sqlite3.OperationalError:
            print("  ⚠ Índice ya existe, omitiendo...")

        # Registrar migración
        cursor.execute(
            "INSERT INTO migration_history (migration_id, description, applied_at) VALUES (?, ?, ?)",
            (MIGRATION_ID, MIGRATION_DESCRIPTION, datetime.now().isoformat())
        )

        conn.commit()
        print(f"[SUCCESS] Migración {MIGRATION_ID} aplicada exitosamente.")
        return True

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Migración {MIGRATION_ID} falló: {e}")
        return False
    finally:
        conn.close()


def rollback(db_path):
    """Revierte la migración (rollback)."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        print(f"[ROLLBACK] Revirtiendo migración {MIGRATION_ID}...")

        # SQLite no soporta DROP COLUMN directamente en versiones antiguas
        # Para fecha_creacion y stock_minimo, se reconstruye la tabla sin las columnas

        # Nota: En SQLite >= 3.35.0 se puede usar ALTER TABLE DROP COLUMN
        # Para compatibilidad, usamos el enfoque de reconstrucción

        # Revertir ventas: quitar fecha_creacion
        cursor.execute("""
            CREATE TABLE ventas_backup AS 
            SELECT id, usuario_id, total, estado, metodo_pago FROM ventas
        """)
        cursor.execute("DROP TABLE ventas")
        cursor.execute("""
            CREATE TABLE ventas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER REFERENCES usuarios(id),
                total REAL,
                estado TEXT,
                metodo_pago TEXT
            )
        """)
        cursor.execute("INSERT INTO ventas SELECT * FROM ventas_backup")
        cursor.execute("DROP TABLE ventas_backup")
        print("  ✔ Campo 'fecha_creacion' eliminado de 'ventas'")

        # Revertir inventarios: quitar stock_minimo
        cursor.execute("""
            CREATE TABLE inventarios_backup AS _
            SELECT id, producto_id, cantidad, ubicacion FROM inventarios
        """)
        cursor.execute("DROP TABLE inventarios")
        cursor.execute("""
            CREATE TABLE inventarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                producto_id INTEGER REFERENCES productos(id),
                cantidad INTEGER DEFAULT 0,
                ubicacion TEXT DEFAULT 'Bodega Principal'
            )
        """)
        cursor.execute("INSERT INTO inventarios SELECT * FROM inventarios_backup")
        cursor.execute("DROP TABLE inventarios_backup")
        print("  ✔ Campo 'stock_minimo' eliminado de 'inventarios'")

        # Eliminar índice
        cursor.execute("DROP INDEX IF EXISTS idx_ventas_usuario")
        print("  ✔ Índice 'idx_ventas_usuario' eliminado")

        # Marcar como revertido
        cursor.execute(
            "UPDATE migration_history SET rolled_back_at = ? WHERE migration_id = ?",
            (datetime.now().isoformat(), MIGRATION_ID)
        )

        conn.commit()
        print(f"[SUCCESS] Rollback de {MIGRATION_ID} completado.")
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
