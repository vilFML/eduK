'''
Formula de Heron: Para calcular el area de un triangulo dados sus lados,
area = raiz( S*(s-a)(S-b)(S-c) )
en donde a, b, c son los lados del triangulo y S es el semiperimetro del triangulo.


Siguiendo la receta de diseño implemente la función heron, que recibe como
parámetros las medidas de los lados de un triángulo y devuelve el área del
triángulo de acuerdo con lo obtenido por la Fórmula de Herón.
- Indicación: Asuma que los valores recibidos por la función efectivamente
forman un triángulo.
'''

# heron: num, num, num -> num
# Entrega el area de un triangulo dados sus tres lados
# Ej: heron(1,2,3) entrega NOSE TODAVIA

def heron(ladoA, ladoB, ladoC):
    lado1 = float(ladoA)
    lado2 = float(ladoB)
    lado3 = float(ladoC)
    semiper = (lado1 + lado2 + lado3) / 2.0

    area = (semiper * (semiper-lado1) * (semiper-lado2) * (semiper-lado3)) ** 0.5
    
    return area

# tests

assert heron(3,4,5) == 6.0
assert heron(5,12,13) == 30