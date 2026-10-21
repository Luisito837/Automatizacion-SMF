"""Escritura de celdas directamente en el XML de una hoja de Excel.

Así se modifica solo lo necesario y el resto del archivo (tabla dinámica, segmentaciones,
fórmulas, estilos) queda intacto; guardar con openpyxl borraría las segmentaciones.
"""
import re
from xml.sax.saxutils import escape

from openpyxl.utils import column_index_from_string, get_column_letter

_FILA = re.compile(r'<row r="(\d+)"([^>]*?)(?:/>|>(.*?)</row>)', re.S)
_CELDA = re.compile(r'<c r="([A-Z]+)\d+"[^>]*?(?:/>|>.*?</c>)', re.S)


def escribir_celdas(xml: str, celdas_por_fila: dict) -> str:
    """Escribe valores en un XML de hoja. 'celdas_por_fila' es {fila: {columna: valor}}.

    El valor puede ser texto, número o None (None deja la celda vacía conservando su estilo).
    Las celdas que ya existían conservan su estilo; el resto de la fila no se toca.
    """
    def reemplazar(coincidencia):
        fila = int(coincidencia.group(1))
        nuevas = celdas_por_fila.get(fila)
        if not nuevas:
            return coincidencia.group(0)
        atributos = re.sub(r'\sspans="[^"]*"', "", coincidencia.group(2))
        celdas = {column_index_from_string(c.group(1)): c.group(0)
                  for c in _CELDA.finditer(coincidencia.group(3) or "")}
        for columna, valor in nuevas.items():
            anterior = celdas.get(columna, "")
            estilo = re.search(r'\ss="(\d+)"', anterior.split(">")[0])
            celdas[columna] = _celda(f"{get_column_letter(columna)}{fila}", estilo.group(1) if estilo else "", valor)
        return f'<row r="{fila}"{atributos}>' + "".join(celdas[k] for k in sorted(celdas)) + "</row>"

    return _FILA.sub(reemplazar, xml)


def _celda(referencia: str, estilo: str, valor) -> str:
    atributo_estilo = f' s="{estilo}"' if estilo else ""
    if valor is None or valor == "":
        return f'<c r="{referencia}"{atributo_estilo}/>'
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return f'<c r="{referencia}"{atributo_estilo}><v>{valor!r}</v></c>'
    texto = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(valor))
    return (f'<c r="{referencia}"{atributo_estilo} t="inlineStr">'
            f'<is><t xml:space="preserve">{escape(texto)}</t></is></c>')
