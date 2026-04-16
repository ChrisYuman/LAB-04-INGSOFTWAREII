"""
Script de backup de base de datos
==================================
Crea un respaldo completo de la base de datos SQLite antes de un despliegue.

Uso: python scripts/backup_db.py [ruta_db]
"""

import shutil
import os
import sys
from datetime import datetime


def create_backup(db_path):
    """Crea un backup con timestamp de la base de datos."""
    if not os.path.exists(db_path):
        print(f"[ERROR] Base de datos no encontrada: {db_path}")
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(os.path.dirname(db_path), "backups")
    os.makedirs(backup_dir, exist_ok=True)

    db_name = os.path.basename(db_path)
    backup_name = f"{os.path.splitext(db_name)[0]}_backup_{timestamp}.db"
    backup_path = os.path.join(backup_dir, backup_name)

    try:
        shutil.copy2(db_path, backup_path)
        size_mb = os.path.getsize(backup_path) / (1024 * 1024)
        print(f"[SUCCESS] Backup creado exitosamente:")
        print(f"  📁 Archivo: {backup_path}")
        print(f"  📊 Tamaño: {size_mb:.2f} MB")
        print(f"  🕐 Fecha:  {timestamp}")
        return backup_path
    except Exception as e:
        print(f"[ERROR] No se pudo crear el backup: {e}")
        return None


def restore_backup(backup_path, db_path):
    """Restaura un backup previamente creado."""
    if not os.path.exists(backup_path):
        print(f"[ERROR] Backup no encontrado: {backup_path}")
        return False

    try:
        shutil.copy2(backup_path, db_path)
        print(f"[SUCCESS] Base de datos restaurada desde: {backup_path}")
        return True
    except Exception as e:
        print(f"[ERROR] No se pudo restaurar: {e}")
        return False


def list_backups(db_path):
    """Lista todos los backups disponibles."""
    backup_dir = os.path.join(os.path.dirname(db_path), "backups")
    if not os.path.exists(backup_dir):
        print("No hay backups disponibles.")
        return []

    backups = sorted(
        [f for f in os.listdir(backup_dir) if f.endswith(".db")],
        reverse=True
    )
    print(f"\n📦 Backups disponibles ({len(backups)}):")
    for b in backups:
        size = os.path.getsize(os.path.join(backup_dir, b)) / 1024
        print(f"  - {b} ({size:.1f} KB)")
    return backups


if __name__ == "__main__":
    if len(sys.argv) > 1:
        db = sys.argv[1]
    else:
        db = os.path.join(os.path.dirname(__file__), "..", "inventario_ventas.db")

    if len(sys.argv) > 2 and sys.argv[2] == "--restore":
        restore_backup(sys.argv[3] if len(sys.argv) > 3 else "", db)
    elif len(sys.argv) > 2 and sys.argv[2] == "--list":
        list_backups(db)
    else:
        create_backup(db)
