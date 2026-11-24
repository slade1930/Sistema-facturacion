
"""
Conversión de números a letras para facturas panameñas.
Fase 1-2: Conversión del monto total a letras.
"""

def numero_a_letras(numero):
    """
    Convierte un número decimal a texto para factura.
    Formato: "Mil doscientos cincuenta con 50/100"
    
    Args:
        numero: decimal (ej: 1250.50)
    
    Returns:
        str: monto en letras
    """
    if numero < 0:
        return "Error: monto negativo"
    
    enteros = int(numero)
    decimales = int(round((numero - enteros) * 100))
    
    unidades = [
        "", "un", "dos", "tres", "cuatro", "cinco", "seis", "siete",
        "ocho", "nueve", "diez", "once", "doce", "trece", "catorce",
        "quince", "dieciséis", "diecisiete", "dieciocho", "diecinueve"
    ]
    
    decenas = [
        "", "diez", "veinte", "treinta", "cuarenta", "cincuenta",
        "sesenta", "setenta", "ochenta", "noventa"
    ]
    
    centenas = [
        "", "cien", "doscientos", "trescientos", "cuatrocientos",
        "quinientos", "seiscientos", "setecientos", "ochocientos",
        "novecientos"
    ]
    
    def _convertir_grupo(n):
        """Convierte un número de 0-999 a letras."""
        resultado = ""
        
        if n == 100:
            return "cien"
        
        if n >= 100:
            resultado += centenas[n // 100] + " "
            n %= 100
        
        if n >= 20:
            resultado += decenas[n // 10]
            if n % 10 > 0:
                resultado += " y "
                resultado += unidades[n % 10]
        elif n > 0:
            resultado += unidades[n]
        
        return resultado.strip()
    
    def _numero_a_letras_completo(n):
        """Convierte cualquier entero a letras."""
        if n == 0:
            return "cero"
        
        partes = []
        
        if n >= 1000000000:
            millones = n // 1000000000
            resto = n % 1000000000
            if millones == 1:
                partes.append("mil millones")
            else:
                partes.append(_convertir_grupo(millones) + " millones")
            n = resto
        
        if n >= 1000000:
            millones = n // 1000000
            resto = n % 1000000
            partes.append(_convertir_grupo(millones) + " millones")
            n = resto
        elif n >= 1000:
            miles = n // 1000
            resto = n % 1000
            if miles == 1:
                partes.append("mil")
            else:
                partes.append(_convertir_grupo(miles) + " mil")
            n = resto
        
        if n > 0:
            partes.append(_convertir_grupo(n))
        
        return " ".join(partes)
    
    entero_texto = _numero_a_letras_completo(enteros)
    decimal_str = f"{decimales:02d}/100"
    
    return f"{entero_texto} {decimal_str}"
