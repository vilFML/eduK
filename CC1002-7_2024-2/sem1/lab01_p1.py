#VICHOX
'''P1
Crea la función formatear_monto que recibe un número entero (se puede asumir que siempre estará
entre 1000 y 999999, inclusives) y retorna un string con el mismo número que tenga un signo peso a
la izquierda y un punto decimal.
'''

# formatear_monto: int -> str
# a partir de un nro, lo entrega en formato con signo peso y separando las milesimas con puntos.
# Ej: formatear_monto(12345) entrega '12.345$'
def formatear_monto(numero):
    milenas = numero // 1000
    
    unidad = numero % 10
    decena = (numero % 100) // 10    
    centena = (numero % 1000) // 100

    # Pasar ints a str
    unidadStr = str(unidad)
    decenaStr = str(decena)
    centenaStr = str(centena)
    despuesPunto = centenaStr + decenaStr + unidadStr

    antesPunto = str(milenas)

    textoFormateado = antesPunto + '.' + despuesPunto + '$' 

    return textoFormateado

# tests
print(formatear_monto(12345))
assert formatear_monto(12345) == '12.345$'
assert formatear_monto(999999) == '999.999$'
assert formatear_monto(20000) == '20.000$'

'''
Escribe un programa interactivo en Python que calcule la propina adecuada en un restaurante. El
programa debe pedir al usuario el monto total de la cuenta y el porcentaje de propina que desea
dejar. Luego, el programa debe calcular el valor de la propina y el monto total a pagar, incluyendo
la propina. Si los valores contienen decimales, se pueden truncar. Finalmente, se debe mostrar un
mensaje con la información calculada, usando la función formatear_monto definida anteriormente.
'''

# Pedir monto total de la cuenta
consumo = input('Ingresa el monto del consumo: ')
consumoNum = int(consumo)

# Pedir porcentaje de propina
propinaPorcentaje = input('Ingresa el porcentaje (solo el numero) de propina: ')
propinaPorcentajeNum = float(propinaPorcentaje) / 100

# Calcular el valor de la propina
montoPropina = propinaPorcentajeNum * consumoNum
    # Mostrar propina
# print('El monto de la propina es: ', formatear_monto(montoPropina))

# monto total a pagar (con propina)
montoTotal = consumoNum + montoPropina
    # si hay decimal, se puede truncar
montoFinal = int(montoTotal)

# mostar monto formateado con funcion previa
finalFormateado = formatear_monto(montoFinal)
print('En total se pagaran',finalFormateado)