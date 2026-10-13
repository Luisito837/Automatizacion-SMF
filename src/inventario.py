"""Inventario: lo comprado (stock) agrupado por producto y por categoría."""
import re
from dataclasses import dataclass, field

from catalogo_plantilla import CatalogoProductos
from configuracion import CATEGORIA_REFRESCOS
from utilidades import normalizar_codigo, normalizar_texto

UNIDADES_DE_COMPRA_EN_CAJAS = {"CAJ", "CJ", "CJA", "CAJA"}


@dataclass
class Producto:
    codigo: str
    descripcion: str
    categoria: str
    unidades_por_caja: int
    stock_unidades: int = 0
    categoria_reporte: str = ""  # DescrCategoría tal como viene en el reporte de compras

    @property
    def es_refresco(self) -> bool:
        return normalizar_texto(self.categoria_reporte) == CATEGORIA_REFRESCOS


class Inventario:
    """Guarda los productos comprados. El stock siempre se maneja en unidades."""

    def __init__(self):
        self._productos = {}

    def sumar_compra(self, producto: Producto, unidades: int) -> None:
        clave = normalizar_codigo(producto.codigo)
        existente = self._productos.setdefault(clave, producto)
        existente.stock_unidades += unidades

    def quitar_productos_sin_stock(self) -> None:
        self._productos = {k: p for k, p in self._productos.items() if p.stock_unidades > 0}

    def categorias(self) -> list:
        return sorted({p.categoria for p in self._productos.values()})

    def productos_de_categoria(self, categoria) -> list:
        productos = [p for p in self._productos.values() if p.categoria == categoria]
        return sorted(productos, key=lambda p: p.descripcion)

    def todos(self) -> list:
        return list(self._productos.values())

    def cantidad_de_productos(self) -> int:
        return len(self._productos)


@dataclass
class ResultadoInventario:
    inventario: Inventario
    productos_sin_unidades_por_caja: list = field(default_factory=list)


class ConstructorInventario:
    """Convierte las filas de compras ya filtradas en un inventario.

    Suma las compras repetidas de un mismo producto y pasa todo a unidades
    usando las unidades por caja de la hoja LISTA de la plantilla.
    """

    def __init__(self, catalogo: CatalogoProductos):
        self.catalogo = catalogo

    def construir(self, filas_filtradas) -> ResultadoInventario:
        inventario = Inventario()
        sin_unidades = {}
        for fila in filas_filtradas:
            cantidad = self._leer_cantidad(fila.get("Cantidad"))
            codigo = str(fila.get("CodProducto") or "").strip()
            if cantidad is None or not codigo:
                continue
            producto = self._crear_producto(codigo, fila)
            if producto.unidades_por_caja == 1 and self._es_compra_por_caja(fila):
                sin_unidades[codigo] = producto.descripcion
            unidades = cantidad * producto.unidades_por_caja if self._es_compra_por_caja(fila) else cantidad
            inventario.sumar_compra(producto, unidades)
        inventario.quitar_productos_sin_stock()
        return ResultadoInventario(inventario, sorted(sin_unidades.values()))

    def _crear_producto(self, codigo, fila) -> Producto:
        info = self.catalogo.buscar(codigo)
        descripcion = str(fila.get("DescrProducto") or "").strip()
        categoria = (info.categoria if info and info.categoria else str(fila.get("DescrCategoría") or "SIN CATEGORIA"))
        unidades = info.unidades_por_caja if info and info.unidades_por_caja > 0 else self._unidades_desde_descripcion(descripcion)
        return Producto(
            codigo=codigo,
            descripcion=descripcion or (info.descripcion if info else codigo),
            categoria=categoria.strip().upper(),
            unidades_por_caja=unidades,
            categoria_reporte=str(fila.get("DescrCategoría") or "").strip(),
        )

    @staticmethod
    def _unidades_desde_descripcion(descripcion) -> int:
        """Plan B: lee 'x24UN' o 'X 6U' de la descripción. Devuelve 1 si no encuentra nada."""
        coincidencia = re.search(r"[xX]\s*(\d+)\s*U", descripcion)
        return int(coincidencia.group(1)) if coincidencia else 1

    @staticmethod
    def _es_compra_por_caja(fila) -> bool:
        return normalizar_texto(fila.get("UnidadCompra")) in UNIDADES_DE_COMPRA_EN_CAJAS

    @staticmethod
    def _leer_cantidad(valor):
        try:
            return int(round(float(valor)))
        except (TypeError, ValueError):
            return None
