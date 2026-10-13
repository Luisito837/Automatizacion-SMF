"""Exporta la distribución a la hoja de clientes de la plantilla (cliente x categoría).

Cada celda lleva lo asignado con el formato: codigo_producto + espacio + numero + und/cj.
Ejemplo: 'F07103 5 cj'. Si un cliente recibe varios productos de la misma categoría,
van en la misma celda separados por SEPARADOR.
Como al cargar el reporte, solo se modifica el XML de esa hoja dentro del .xlsx.
"""
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape

from openpyxl.utils import column_index_from_string, get_column_letter

from escritor_plantilla import parte_xml_de_la_hoja
from lector_excel import LectorExcel
from utilidades import normalizar_texto

SEPARADOR = ", "

# Categoría de la hoja LISTA -> cómo se llama su columna en la hoja de clientes (sin el %).
EQUIVALENCIAS_DE_CATEGORIA = {
    "COLAS NEGRAS": ("COLA NEGRA",),
    "COLAS BLANCAS": ("COLA BLANCA",),
    "SABORES": ("SAB",),
    "MALTA": ("MAL",),
    "JUGOS": ("JUG",),
    "TE": ("TE",),
    "BEBIDAS DEPORTIVAS": ("BEB.DEPOR.",),
    "TRADICIONAL": ("CER",),
    "LIGHT": ("CER",),
    "PREMIUN": ("CER",),
    "SANGRIA": ("SANG",),
    "VINO NACIONAL": ("VINOS",),
}


@dataclass
class ResultadoExportacion:
    ruta_salida: Path
    clientes_escritos: int = 0
    entradas_escritas: int = 0
    productos_sin_columna: list = field(default_factory=list)
    clientes_sin_fila: list = field(default_factory=list)

    def resumen(self) -> str:
        lineas = [
            f"Clientes con datos exportados: {self.clientes_escritos}",
            f"Productos escritos: {self.entradas_escritas}",
            "",
            f"Archivo:\n{self.ruta_salida}",
        ]
        if self.productos_sin_columna:
            lineas += ["", "No se exportaron (la plantilla no tiene columna para su categoría):",
                       *[f"   · {nombre}" for nombre in self.productos_sin_columna]]
        if self.clientes_sin_fila:
            lineas += ["", "Clientes que no se encontraron en la hoja de clientes:",
                       *[f"   · {nombre}" for nombre in self.clientes_sin_fila]]
        return "\n".join(lineas)


class ExportadorPlantilla:
    def __init__(self, lector_excel: LectorExcel):
        self.lector_excel = lector_excel

    def exportar(self, ruta_base, asignaciones, ruta_salida) -> ResultadoExportacion:
        """Copia 'ruta_base' a 'ruta_salida' con las asignaciones escritas en la hoja de clientes."""
        ruta_base, ruta_salida = Path(ruta_base), Path(ruta_salida)
        if ruta_base.resolve() == ruta_salida.resolve():
            raise ValueError("Elija un nombre distinto al del archivo de origen para no sobrescribirlo.")
        hoja = self.lector_excel.buscar_hoja_con_encabezados(ruta_base, ("DIA", "CLIENTE"))
        if hoja is None:
            raise ValueError("La plantilla no tiene una hoja de clientes (con las columnas DIA y CLIENTE).")

        filas_de_clientes = self._filas_de_clientes(hoja)
        columnas = self._columnas_de_categoria(hoja)
        resultado = ResultadoExportacion(ruta_salida)
        celdas = self._agrupar_en_celdas(asignaciones, filas_de_clientes, columnas, resultado)

        parte_xml = parte_xml_de_la_hoja(ruta_base, hoja.nombre)
        with zipfile.ZipFile(ruta_base) as origen, \
                zipfile.ZipFile(ruta_salida, "w", zipfile.ZIP_DEFLATED) as destino:
            for parte in origen.infolist():
                contenido = origen.read(parte.filename)
                if parte.filename == parte_xml:
                    contenido = self._escribir_celdas(contenido.decode("utf-8"), celdas).encode("utf-8")
                destino.writestr(parte, contenido)
        return resultado

    # ---------- ubicar filas y columnas ----------
    @staticmethod
    def _filas_de_clientes(hoja) -> dict:
        """{(día, cliente): número de fila de Excel}."""
        indice_dia, indice_cliente = hoja.columnas["DIA"], hoja.columnas["CLIENTE"]
        filas = {}
        for numero, fila in enumerate(hoja.filas):
            if numero <= hoja.fila_encabezados or max(indice_dia, indice_cliente) >= len(fila):
                continue
            clave = (normalizar_texto(fila[indice_dia]), normalizar_texto(fila[indice_cliente]))
            if clave[0] and clave[1]:
                filas[clave] = numero + 1
        return filas

    @staticmethod
    def _columnas_de_categoria(hoja) -> dict:
        """Lee la fila de encabezados de categorías (la fila justo encima de DIA/CLIENTE).

        Devuelve {texto limpio: (número de columna, es_columna_de_producto)}.
        """
        if hoja.fila_encabezados == 0:
            return {}
        columnas = {}
        for indice, valor in enumerate(hoja.filas[hoja.fila_encabezados - 1]):
            texto = normalizar_texto(valor)
            if texto:
                columnas[texto.lstrip("%").strip()] = (indice + 1, not texto.startswith("%"))
        return columnas

    @staticmethod
    def _columna_para(producto, columnas):
        """Primero busca una columna con el nombre del producto (p. ej. ROCKSTAR); luego por categoría."""
        descripcion = normalizar_texto(producto.descripcion)
        for texto, (numero, es_producto) in columnas.items():
            if es_producto and texto in descripcion:
                return numero
        categoria = normalizar_texto(producto.categoria)
        for candidato in (*EQUIVALENCIAS_DE_CATEGORIA.get(categoria, ()), categoria):
            if candidato in columnas and not columnas[candidato][1]:
                return columnas[candidato][0]
        return None

    def _agrupar_en_celdas(self, asignaciones, filas_de_clientes, columnas, resultado) -> dict:
        """{fila: {columna: texto}} con los productos de cada celda unidos por SEPARADOR."""
        textos = {}
        clientes_escritos, sin_fila, sin_columna = set(), set(), set()
        for asignacion in asignaciones:
            cliente = asignacion.cliente
            fila = filas_de_clientes.get((normalizar_texto(cliente.dia), normalizar_texto(cliente.nombre)))
            if fila is None:
                sin_fila.add(cliente.nombre)
                continue
            columna = self._columna_para(asignacion.producto, columnas)
            if columna is None:
                sin_columna.add(asignacion.producto.descripcion)
                continue
            textos.setdefault((fila, columna), []).append(asignacion.texto())
            clientes_escritos.add(fila)
            resultado.entradas_escritas += 1
        resultado.clientes_escritos = len(clientes_escritos)
        resultado.productos_sin_columna = sorted(sin_columna)
        resultado.clientes_sin_fila = sorted(sin_fila)
        celdas = {}
        for (fila, columna), lista in textos.items():
            celdas.setdefault(fila, {})[columna] = SEPARADOR.join(lista)
        return celdas

    # ---------- escribir en el XML de la hoja ----------
    @staticmethod
    def _escribir_celdas(xml, celdas_por_fila) -> str:
        patron_fila = re.compile(r'<row r="(\d+)"([^>]*?)(?:/>|>(.*?)</row>)', re.S)
        patron_celda = re.compile(r'<c r="([A-Z]+)\d+"[^>]*?(?:/>|>.*?</c>)', re.S)

        def reemplazar(coincidencia):
            fila = int(coincidencia.group(1))
            nuevas = celdas_por_fila.get(fila)
            if not nuevas:
                return coincidencia.group(0)
            atributos = re.sub(r'\sspans="[^"]*"', "", coincidencia.group(2))
            celdas = {column_index_from_string(c.group(1)): c.group(0)
                      for c in patron_celda.finditer(coincidencia.group(3) or "")}
            for columna, texto in nuevas.items():
                anterior = celdas.get(columna, "")
                estilo = re.search(r'\ss="(\d+)"', anterior.split(">")[0])
                atributo_estilo = f' s="{estilo.group(1)}"' if estilo else ""
                limpio = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", texto)
                celdas[columna] = (
                    f'<c r="{get_column_letter(columna)}{fila}"{atributo_estilo} t="inlineStr">'
                    f'<is><t xml:space="preserve">{escape(limpio)}</t></is></c>')
            return f'<row r="{fila}"{atributos}>' + "".join(celdas[k] for k in sorted(celdas)) + "</row>"

        return patron_fila.sub(reemplazar, xml)
