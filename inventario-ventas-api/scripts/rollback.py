"""
Script de rollback completo
=============================
Ejecuta el rollback de aplicación, base de datos y datos.

Uso: python scripts/rollback.py [--version VERSION] [--data-only] [--schema-only]
"""

import subprocess
import sys
import os
from datetime import datetime


def rollback_aplicacion(version_target="v1.0.0"):
    """
    Rollback de aplicación (código).
    Regresa a una versión anterior usando git tags o commits.
    """
    print("\n🔄 ROLLBACK DE APLICACIÓN")
    print("=" * 50)
    print(f"  Versión destino: {version_target}")
    print(f"  Mecanismo: git checkout + redeploy")
    print()
    print("  Comandos a ejecutar:")
    print(f"    1. git stash (guardar cambios locales)")
    print(f"    2. git checkout tags/{version_target}")
    print(f"    3. pip install -r requirements.txt")
    print(f"    4. Reiniciar servicio uvicorn")
    print()
    print("  ⚠ Nota: Asegurarse de que la BD sea compatible con esta versión")
    return True


def rollback_base_datos(db_path, migration_id):
    """
    Rollback de base de datos (estructura).
    Revierte los cambios de esquema de una migración específica.
    """
    print("\n🔄 ROLLBACK DE BASE DE DATOS")
    print("=" * 50)
    print(f"  Migración a revertir: {migration_id}")

    migration_map = {
        "v1_1_0": "v1_1_0_add_features",
        "v1_2_0": "v1_2_0_breaking_changes",
    }

    if migration_id not in migration_map:
        print(f"  ❌ Migración desconocida: {migration_id}")
        return False

    module_name = migration_map[migration_id]
    migrations_dir = os.path.join(os.path.dirname(__file__), "..", "migrations")
    
    try:
        result = subprocess.run(
            [sys.executable, os.path.join(migrations_dir, f"{module_name}.py"), "--rollback"],
            capture_output=True, text=True,
            cwd=os.path.join(os.path.dirname(__file__), "..")
        )
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return "SUCCESS" in result.stdout
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def rollback_datos(db_path):
    """
    Rollback de datos (restauración desde backup).
    Este es el nivel más crítico de rollback.
    """
    print("\n🔄 ROLLBACK DE DATOS")
    print("=" * 50)
    
    backup_dir = os.path.join(os.path.dirname(db_path), "backups")
    if not os.path.exists(backup_dir):
        print("  ❌ No hay backups disponibles")
        print("  → Alternativa: aplicar forward-fix o nueva migración correctiva")
        return False

    backups = sorted(
        [f for f in os.listdir(backup_dir) if f.endswith(".db")],
        reverse=True
    )
    
    if not backups:
        print("  ❌ No hay backups disponibles")
        return False

    print(f"  Backups disponibles:")
    for i, b in enumerate(backups[:5]):
        print(f"    {i+1}. {b}")

    latest = os.path.join(backup_dir, backups[0])
    print(f"\n  Restaurando desde: {backups[0]}")

    import shutil
    try:
        shutil.copy2(latest, db_path)
        print("  ✅ Base de datos restaurada exitosamente")
        return True
    except Exception as e:
        print(f"  ❌ Error al restaurar: {e}")
        return False


def classify_rollback_difficulty():
    """
    Clasifica la dificultad de rollback por tipo de cambio.
    """
    print("\n📊 CLASIFICACIÓN DE ROLLBACK POR CAMBIO")
    print("=" * 50)
    
    easy = [
        "Agregar columna nueva (se elimina con ALTER TABLE DROP)",
        "Crear tabla nueva (se elimina con DROP TABLE)",
        "Agregar índice (se elimina con DROP INDEX)",
        "Cambio en código de aplicación (git revert)",
    ]
    
    partial = [
        "Cambiar tipo de dato de columna (pérdida de precisión)",
        "Agregar constraint NOT NULL con datos existentes",
        "Renombrar tabla o columna (requiere actualizar código)",
    ]
    
    irreversible = [
        "Dividir campo 'nombre_completo' en 'nombre' + 'apellido'",
        "Eliminar columna con datos únicos",
        "Transformar datos con pérdida de formato original",
        "Eliminar registros (DELETE sin backup previo)",
        "Truncar datos al cambiar VARCHAR(100) a VARCHAR(50)",
    ]

    print("\n  ✅ ROLLBACK FÁCIL:")
    for item in easy:
        print(f"    → {item}")
    
    print("\n  ⚠ ROLLBACK PARCIAL:")
    for item in partial:
        print(f"    → {item}")
    
    print("\n  ❌ ROLLBACK IMPOSIBLE O MUY DIFÍCIL:")
    for item in irreversible:
        print(f"    → {item}")

    print("\n  📌 ESTRATEGIA PARA CAMBIOS IRREVERSIBLES:")
    print("    1. Forward-fix: corregir hacia adelante con nueva migración")
    print("    2. Hotfix: parche de emergencia para manejar ambos formatos")
    print("    3. Restaurar desde backup (si existe y es reciente)")
    print("    4. Migración correctiva con lógica de reconstrucción")


def main():
    db_path = os.path.join(os.path.dirname(__file__), "..", "inventario_ventas.db")

    print("=" * 60)
    print("  SISTEMA DE ROLLBACK")
    print(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    if "--classify" in sys.argv:
        classify_rollback_difficulty()
        return

    if "--data-only" in sys.argv:
        rollback_datos(db_path)
        return

    if "--schema-only" in sys.argv:
        migration = sys.argv[sys.argv.index("--schema-only") + 1] if len(sys.argv) > sys.argv.index("--schema-only") + 1 else "v1_2_0"
        rollback_base_datos(db_path, migration)
        return

    # Rollback completo
    version = "v1.0.0"
    for i, arg in enumerate(sys.argv):
        if arg == "--version" and i + 1 < len(sys.argv):
            version = sys.argv[i + 1]

    rollback_aplicacion(version)
    rollback_base_datos(db_path, "v1_2_0")
    rollback_base_datos(db_path, "v1_1_0")
    classify_rollback_difficulty()


if __name__ == "__main__":
    main()
