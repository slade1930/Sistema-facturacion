"""
Validaciones de integridad de datos para factura.
Fase 1-2: Validaciones de campos obligatorios.
"""

import re
from datetime import datetime


def validar_ruc(ruc):
    """
    Valida RUC panameño: formato XX-XXXXX-XXX (13 dígitos).
    
    Args:
        ruc: string con el RUC
    
    Returns:
        bool: True si es válido
    """
    if not isinstance(ruc, str):
        return False
    
    patron = r'^\d{2}-\d{5}-\d{3}$'
    return bool(re.match(patron, ruc))


def validar_monto(monto):
    """
    Valida que el monto sea positivo y dentro del rango razonable.
    
    Args:
        monto: número decimal
    
    Returns:
        bool: True si es válido
    """
    try:
        monto = float(monto)
        return 0 < monto <= 999999999.99
    except (ValueError, TypeError):
        return False


def validar_fecha(fecha_str):
    """
    Valida formato DD/MM/YYYY y que sea fecha válida.
    
    Args:
        fecha_str: string con la fecha
    
    Returns:
        bool: True si es válida
    """
    if not isinstance(fecha_str, str):
        return False
    
    patron = r'^\d{2}/\d{2}/\d{4}$'
    if not re.match(patron, fecha_str):
        return False
    
    try:
        datetime.strptime(fecha_str, '%d/%m/%Y')
        return True
    except ValueError:
        return False


def validar_nombre(nombre):
    """
    Valida que el nombre tenga al menos 2 caracteres.
    
    Args:
        nombre: string
    
    Returns:
        bool: True si es válido
    """
    if not isinstance(nombre, str):
        return False
    return len(nombre.strip()) >= 2


def validar_email(email):
    """
    Valida formato básico de email.
    
    Args:
        email: string
    
    Returns:
        bool: True si es válido
    """
    patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(patron, email))


def validar_factura_datos(datos):
    """
    Valida todos los campos requeridos de una factura.
    
    Args:
        datos: dict con keys: ruc, nombre, total, fecha
    
    Returns:
        tuple: (bool, list de errores)
    """
    errores = []
    
    if not validar_ruc(datos.get('ruc', '')):
        errores.append("RUC inválido. Formato: XX-XXXXX-XXX")
    
    if not validar_nombre(datos.get('nombre', '')):
        errores.append("Nombre inválido")
    
    if not validar_monto(datos.get('total', 0)):
        errores.append("Monto inválido")
    
    if not validar_fecha(datos.get('fecha', '')):
        errores.append("Fecha inválida. Formato: DD/MM/YYYY")
    
    return (len(errores) == 0, errores)
