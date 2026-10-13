"""Funciones pequeñas de apoyo para texto, códigos y cantidades."""
import datetime
import unicodedata

from configuracion import DIAS_SEMANA


def normalizar_texto(texto) -> str:
    """Devuelve el texto en mayúsculas, sin tildes y sin espacios repetidos.

    Ejemplo: ' Categoría  ' -> 'CATEGORIA'. Si el valor es None devuelve ''.
    """
    if texto is None:
        return ""
    descompuesto = unicodedata.normalize("NFKD", str(texto))
    sin_tildes = "".join(c for c in descompuesto if not unicodedata.combining(c))
    return " ".join(sin_tildes.upper().split())


def normalizar_codigo(codigo) -> str:
    """Devuelve el código sin espacios ni ceros a la izquierda.

    Ejemplo: '0178392' y 178392 -> '178392'. Así el código del reporte
    coincide con el de la plantilla aunque uno tenga ceros de más.
    """
    if isinstance(codigo, float) and codigo.is_integer():
        codigo = int(codigo)
    return normalizar_texto(codigo).lstrip("0")


def texto_a_entero(texto):
    """Convierte lo escrito en una celda a un entero >= 0.

    Devuelve 0 si está vacío y None si no es un entero válido.
    """
    limpio = str(texto).strip().replace(",", ".")
    if limpio == "":
        return 0
    try:
        numero = float(limpio)
    except ValueError:
        return None
    if numero < 0 or not numero.is_integer():
        return None
    return int(numero)


def formatear_cantidad(unidades: int, unidades_por_caja: int) -> str:
    """Muestra una cantidad en cajas y unidades sueltas.

    Ejemplo: 77 unidades con 24 por caja -> '3 cj 5 un'.
    """
    signo = "-" if unidades < 0 else ""
    absoluto = abs(unidades)
    if unidades_por_caja <= 1:
        return f"{signo}{absoluto} un"
    cajas, sueltas = divmod(absoluto, unidades_por_caja)
    partes = []
    if cajas or not sueltas:
        partes.append(f"{cajas} cj")
    if sueltas:
        partes.append(f"{sueltas} un")
    return signo + " ".join(partes)


def obtener_dia_actual() -> str:
    """Devuelve el día de hoy (LUNES a VIERNES). Sábado y domingo devuelven LUNES."""
    indice = datetime.date.today().weekday()
    return DIAS_SEMANA[indice] if indice < len(DIAS_SEMANA) else DIAS_SEMANA[0]
