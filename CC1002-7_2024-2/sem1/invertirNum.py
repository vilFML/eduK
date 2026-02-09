'''
Escriba una función de nombre invertir que recibe un número entero de dos
cifras, y lo devuelva en el orden inverso.
Por ejemplo, invertir(75) debe retornar 57.
'''

#Usar division entera por 10 y modulo por 10

'''
1. tomar numero
2. extraer unidad
3. extraer decena (eliminar unidad)
4. poner unidad en decena
5. poner decena en unidad.
6. mostrar resultado
'''

# invertir: int -> int
# Invierte los digitos de un numero de dos digitos
# Ej: invertir(72) entrega 27

def invertir(numero):
    unidadOriginal = numero % 10
    decenaOriginal = numero // 10

    unidadSalida = decenaOriginal
    decenaSalida = unidadOriginal * 10

    numeroFinal = decenaSalida + unidadSalida
    return numeroFinal

# tests

assert invertir(72) == 27
assert invertir(99) == 99