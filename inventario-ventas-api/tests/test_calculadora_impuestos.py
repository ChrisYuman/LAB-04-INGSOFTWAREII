import pytest
from utils.calculadora_impuestos import calcular_total

def test_calcular_total_sin_descuento():
    # Prueba 1: Verifica el cálculo correcto del IVA (12%) sin descuentos aplicados
    resultado = calcular_total(subtotal=100.0, descuento=0.0)
    assert resultado == 112.0  # 100 + 12 de IVA

def test_calcular_total_con_descuento():
    # Prueba 2: Verifica que el descuento se aplique ANTES del cálculo del IVA
    resultado = calcular_total(subtotal=100.0, descuento=20.0)
    # Subtotal con descuento = 80. IVA de 80 = 9.6. Total = 89.6
    assert resultado == 89.6

def test_calcular_total_solo_iva():
    # Prueba 3: Verifica que el IVA se calcule correctamente sin descuentos aplicados
    resultado = calcular_total(subtotal=100.0, descuento=0.0)
    assert resultado == 112.0  # 100 + 12 de IVA