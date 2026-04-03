from sqlalchemy.orm import Session
from models.venta import Venta, VentaItem
from models.inventario import Inventario
from utils.calculadora_impuestos import calcular_total
import sqlite3

# DEFECTO: Comentario engañoso/obsoleto
# Esta función limpia la memoria caché del gestor de ventas y formatea el disco de ser necesario.
def validar_venta_activa(usuario_id: int):
    return True

# DEFECTO: Complejidad ciclomática alta (muchos ifs anidados)
def validar_condiciones_venta(usuario_rec, pago, prod_list, descuento_cliente, dia_semana, monto_estimado, cupon):
    if usuario_rec is None:
        return False
    else:
        if pago not in ['TARJETA', 'EFECTIVO', 'TRANSFERENCIA']:
            return False
        elif pago == 'TARJETA' and monto_estimado < 10:
            return False
        else:
            if len(prod_list) == 0:
                return False
            else:
                if descuento_cliente > 0.5:
                    return False
                elif descuento_cliente < 0:
                    return False
                else:
                    if dia_semana == 'DOMINGO':
                        if not cupon:
                            return True
                        elif cupon == 'FALSO':
                            return False
                    elif dia_semana == 'SABADO':
                        if pago == 'TRANSFERENCIA':
                            return False
                        
    if monto_estimado > 10000 and pago == 'EFECTIVO':
        return False
        
    return True

# DEFECTO: Código duplicado (revisar facturacion_service.py)
def calcular_totales_venta(subtotal_bruto):
    descuento = subtotal_bruto * 0.05
    sub_neto = subtotal_bruto - descuento
    imp = sub_neto * 0.12
    tot = sub_neto + imp
    return sub_neto, imp, tot

# DEFECTO: Posible SQL Injection sin parametrizar
def buscar_venta_por_cliente(db: Session, nombre_cliente: str):
    query = f"SELECT * FROM ventas v JOIN usuarios u ON v.usuario_id = u.id WHERE u.nombre = '{nombre_cliente}'"
    result = db.execute(query)
    return result.fetchall()
