"""Datos de apoyo que vienen de la plantilla: productos (LISTA) y clientes por día."""
import re
from dataclasses import dataclass
import json
from pathlib import Path

from configuracion import RUTA_FACTORES
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

    def aplicar_factor(self, codigo, factor: int) -> bool:
        producto = self._productos.get(normalizar_codigo(codigo))
        if producto is None or not isinstance(factor, int) or not 1 <= factor <= 999:
            return False
        producto.unidades_por_caja = factor
        return True


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

    def todos(self) -> list:
        return list(self._clientes)


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
        # Fuente prioritaria del factor: hoja INVENTARIO, columna UND. Allí el equipo
        # mantiene cuántas unidades contiene la caja; el valor 1 significa BULTO.
        # LISTA → UD por CJ se conserva como respaldo para los SKU que no estén en INVENTARIO.
        hoja_inventario = self.lector_excel.buscar_hoja_con_encabezados(ruta, ("COD", "DESC", "UND"))
        if hoja_inventario is not None:
            col_inv = hoja_inventario.columnas
            idx_codigo = col_inv["COD"]
            idx_factor = col_inv["UND"]
            idx_descripcion = col_inv["DESC"]
            idx_categoria = col_inv.get("CATEGORIA")
            for fila in hoja_inventario.filas[hoja_inventario.fila_encabezados + 1:]:
                codigo_original = fila[idx_codigo] if idx_codigo < len(fila) else None
                if codigo_original is None or not str(codigo_original).strip():
                    continue
                clave = normalizar_codigo(codigo_original)
                try:
                    factor = int(float(fila[idx_factor])) if idx_factor < len(fila) and fila[idx_factor] is not None else 0
                except (TypeError, ValueError):
                    factor = 0
                if not 1 <= factor <= 999:
                    continue
                if clave in productos:
                    productos[clave].unidades_por_caja = factor
                else:
                    # Algunos códigos solo están en INVENTARIO; se incluyen igualmente
                    # para que una compra válida no pierda su factor ni descripción.
                    descripcion = self._texto(fila, idx_descripcion)
                    categoria = self._texto(fila, idx_categoria)
                    productos[clave] = InfoProducto(
                        descripcion=descripcion or clave,
                        categoria=categoria or "SIN CATEGORIA",
                        unidades_por_caja=factor,
                    )

        # Los factores corregidos manualmente se guardan fuera del Excel y prevalecen
        # sobre ambas hojas hasta que el usuario los cambie de nuevo.
        try:
            if Path(RUTA_FACTORES).exists():
                guardados = json.loads(Path(RUTA_FACTORES).read_text(encoding="utf-8"))
                if isinstance(guardados, dict):
                    for codigo, factor in guardados.items():
                        clave = normalizar_codigo(codigo)
                        if clave in productos:
                            try:
                                valor = int(factor)
                                if 1 <= valor <= 999:
                                    productos[clave].unidades_por_caja = valor
                            except (TypeError, ValueError):
                                continue
        except (OSError, json.JSONDecodeError):
            pass
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
