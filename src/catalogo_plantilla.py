"""Datos de apoyo que vienen de la plantilla: productos (LISTA) y clientes por día."""
import re
from dataclasses import dataclass

from lector_excel import LectorExcel
from utilidades import normalizar_codigo, normalizar_texto


@dataclass
class InfoProducto:
    descripcion: str
    categoria: str
    unidades_por_caja: int  # 0 cuando no se conoce


class CatalogoProductos:
    """Busca la categoría y las unidades por caja de un producto por su código."""

    def __init__(self, productos=None):
        self._productos = productos or {}

    def buscar(self, codigo):
        return self._productos.get(normalizar_codigo(codigo))

    def cantidad(self) -> int:
        return len(self._productos)


@dataclass
class Cliente:
    codigo_sistema: str
    cep: str
    dia: str
    nombre: str
    puertas: int = 0  # puertas de la nevera ADC ("1 PUERTA" -> 1); 0 si no tiene


class CatalogoClientes:
    """Lista de clientes que se puede filtrar por día de la semana."""

    def __init__(self, clientes=None):
        self._clientes = clientes or []

    def del_dia(self, dia) -> list:
        dia_normalizado = normalizar_texto(dia)
        return [c for c in self._clientes if normalizar_texto(c.dia) == dia_normalizado]

    def cantidad_del_dia(self, dia) -> int:
        return len(self.del_dia(dia))


class LectorPlantilla:
    """Lee de la plantilla FACTURACION_SMF las hojas de productos y de clientes."""

    def __init__(self, lector_excel: LectorExcel):
        self.lector_excel = lector_excel

    def leer_productos(self, ruta) -> CatalogoProductos:
        hoja = self.lector_excel.buscar_hoja_con_encabezados(
            ruta, ("Material", "Categoría", "UD por CJ"))
        if hoja is None:
            return CatalogoProductos()
        col = hoja.columnas
        productos = {}
        for fila in hoja.filas[hoja.fila_encabezados + 1:]:
            codigo = fila[col["MATERIAL"]] if col["MATERIAL"] < len(fila) else None
            if codigo is None or str(codigo).strip() == "":
                continue
            clave = normalizar_codigo(codigo)
            if clave in productos:
                continue
            productos[clave] = InfoProducto(
                descripcion=self._texto(fila, col.get("DESCRIPCION")),
                categoria=self._texto(fila, col["CATEGORIA"]),
                unidades_por_caja=self._entero(fila, col["UD POR CJ"]),
            )
        return CatalogoProductos(productos)

    def leer_clientes(self, ruta) -> CatalogoClientes:
        hoja = self.lector_excel.buscar_hoja_con_encabezados(ruta, ("DIA", "CLIENTE"))
        if hoja is None:
            return CatalogoClientes()
        col = hoja.columnas
        clientes = []
        for fila in hoja.filas[hoja.fila_encabezados + 1:]:
            nombre = self._texto(fila, col["CLIENTE"])
            dia = self._texto(fila, col["DIA"])
            if not nombre or not dia:
                continue
            adc = re.search(r"\d+", self._texto(fila, col.get("CLIENTES DE ADC")))
            clientes.append(Cliente(
                codigo_sistema=self._texto(fila, col.get("CODIGO SISTEMA")),
                cep=self._texto(fila, col.get("CEP")),
                dia=dia,
                nombre=nombre,
                puertas=int(adc.group()) if adc else 0,
            ))
        return CatalogoClientes(clientes)

    @staticmethod
    def _texto(fila, indice) -> str:
        if indice is None or indice >= len(fila) or fila[indice] is None:
            return ""
        return str(fila[indice]).strip()

    @staticmethod
    def _entero(fila, indice) -> int:
        try:
            return int(float(fila[indice]))
        except (TypeError, ValueError, IndexError):
            return 0
