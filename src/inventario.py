"""Inventario comprado: conversión de cajas a unidades y soporte para bultos."""
import re
from dataclasses import dataclass, field

from catalogo_plantilla import CatalogoProductos
from configuracion import CATEGORIA_REFRESCOS, MODO_BULTO, MODO_CAJA, MODO_UNIDAD, TIPO_PEPSI
from utilidades import normalizar_codigo, normalizar_texto

UNIDADES_DE_COMPRA_EN_CAJAS = {"CAJ", "CJ", "CJA", "CAJA", "CAJAS"}
UNIDADES_DE_COMPRA_EN_BULTOS = {"BUL", "BTO", "BULTO", "BULTOS"}
UNIDADES_DE_COMPRA_EN_UNIDADES = {"UNI", "UN", "UND", "UNIDAD", "UNIDADES", "PZA", "PZ"}


@dataclass
class Producto:
    codigo: str
    descripcion: str
    categoria: str                 # categoría de la plantilla LISTA; se conserva para exportación.
    unidades_por_caja: int
    stock_unidades: int = 0        # base del inventario; si factor=1, representa bultos.
    categoria_reporte: str = ""   # DescrCategoría del reporte de compras; filtro principal de la UI.
    tipo_inventario: str = ""     # CodTipoInv; Pepsi se reporta solo por caja.
    cantidad_compra_cajas: int = 0
    cantidad_compra_unidades: int = 0
    cantidad_compra_bultos: int = 0

    @property
    def es_refresco(self) -> bool:
        return normalizar_texto(self.categoria_reporte) == CATEGORIA_REFRESCOS

    @property
    def es_bulto(self) -> bool:
        # Por la regla comercial acordada, UD por CJ = 1 significa bulto,
        # no una caja de una unidad.
        return max(1, int(self.unidades_por_caja or 1)) == 1

    @property
    def solo_cajas(self) -> bool:
        return normalizar_texto(self.tipo_inventario) == TIPO_PEPSI and not self.es_bulto

    @property
    def categoria_filtro(self) -> str:
        """Categoría del reporte general, con fallback al catálogo de la plantilla."""
        return (self.categoria_reporte or self.categoria or "SIN CATEGORIA").strip()

    @property
    def factor(self) -> int:
        return max(1, int(self.unidades_por_caja or 1))

    def recalcular_stock(self) -> None:
        """Recalcula desde las compras originales, para que editar el factor sea seguro."""
        if self.es_bulto:
            # Factor=1: cada cantidad comprada cuenta como un bulto, sin multiplicación.
            self.stock_unidades = (
                self.cantidad_compra_cajas + self.cantidad_compra_unidades + self.cantidad_compra_bultos
            )
        else:
            self.stock_unidades = (
                self.cantidad_compra_cajas * self.factor
                + self.cantidad_compra_unidades
                + self.cantidad_compra_bultos
            )


class Inventario:
    """Índice de productos comprados, siempre con cantidades recalculables por producto."""

    def __init__(self):
        self._productos = {}

    def sumar_compra(self, producto: Producto, cantidad: int, unidad: str) -> None:
        clave = normalizar_codigo(producto.codigo)
        existente = self._productos.get(clave)
        if existente is None:
            existente = producto
            self._productos[clave] = existente
        cantidad = max(0, int(cantidad or 0))
        tipo_unidad = normalizar_texto(unidad)
        if tipo_unidad in UNIDADES_DE_COMPRA_EN_CAJAS:
            existente.cantidad_compra_cajas += cantidad
        elif tipo_unidad in UNIDADES_DE_COMPRA_EN_BULTOS:
            existente.cantidad_compra_bultos += cantidad
        else:
            # UNI/UND y valores no reconocidos se interpretan como unidades compradas.
            existente.cantidad_compra_unidades += cantidad
        existente.recalcular_stock()

    def cambiar_factor(self, codigo: str, factor: int) -> Producto:
        if not isinstance(factor, int) or factor < 1 or factor > 999:
            raise ValueError("El factor debe ser un entero entre 1 y 999.")
        producto = self._productos[normalizar_codigo(codigo)]
        producto.unidades_por_caja = factor
        producto.recalcular_stock()
        return producto

    def quitar_productos_sin_stock(self) -> None:
        self._productos = {k: p for k, p in self._productos.items() if p.stock_unidades > 0}

    def categorias(self) -> list:
        categorias = {}
        for producto in self._productos.values():
            etiqueta = producto.categoria_filtro
            categorias.setdefault(normalizar_texto(etiqueta), etiqueta)
        return sorted(categorias.values(), key=normalizar_texto)

    def productos_de_categoria(self, categoria) -> list:
        if categoria is None:
            return self.todos()
        objetivo = normalizar_texto(categoria)
        productos = [p for p in self._productos.values() if normalizar_texto(p.categoria_filtro) == objetivo]
        return sorted(productos, key=lambda p: (normalizar_texto(p.descripcion), normalizar_codigo(p.codigo)))

    def todos(self) -> list:
        return sorted(self._productos.values(), key=lambda p: (normalizar_texto(p.categoria_filtro), normalizar_texto(p.descripcion)))

    def cantidad_de_productos(self) -> int:
        return len(self._productos)


@dataclass
class ResultadoInventario:
    inventario: Inventario
    productos_sin_unidades_por_caja: list = field(default_factory=list)


class ConstructorInventario:
    """Agrupa compras por producto respetando UnidadCompra y UD por CJ de LISTA.

    CAJ × factor -> unidades; UNI -> unidades; factor=1 -> bultos sin conversión.
    Los componentes originales se conservan para reconstruir existencias si se edita
    manualmente el factor de conversión.
    """

    def __init__(self, catalogo: CatalogoProductos):
        self.catalogo = catalogo

    def construir(self, filas_filtradas) -> ResultadoInventario:
        inventario = Inventario()
        sin_unidades = {}
        for fila in filas_filtradas:
            cantidad = self._leer_cantidad(fila.get("Cantidad"))
            codigo_original = str(fila.get("CodProducto") or "").strip()
            codigo = normalizar_codigo(codigo_original)
            if cantidad is None or cantidad <= 0 or not codigo:
                continue
            producto = self._crear_producto(codigo, fila)
            unidad = str(fila.get("UnidadCompra") or "").strip()
            inventario.sumar_compra(producto, cantidad, unidad)
            # Factor 1 no se reporta como factor faltante: según la regla comercial,
            # significa bulto y se mantiene sin conversión.
        inventario.quitar_productos_sin_stock()
        return ResultadoInventario(inventario, sorted(sin_unidades.values()))

    def _crear_producto(self, codigo, fila) -> Producto:
        info = self.catalogo.buscar(codigo)
        descripcion_reporte = str(fila.get("DescrProducto") or "").strip()
        descripcion = (info.descripcion if info and info.descripcion else descripcion_reporte) or codigo
        categoria_plantilla = info.categoria if info and info.categoria else str(fila.get("DescrCategoría") or "SIN CATEGORIA")
        factor = info.unidades_por_caja if info and info.unidades_por_caja > 0 else self._unidades_desde_descripcion(descripcion)
        return Producto(
            codigo=codigo,
            descripcion=descripcion,
            categoria=categoria_plantilla.strip(),
            unidades_por_caja=max(1, factor),
            stock_unidades=0,
            categoria_reporte=str(fila.get("DescrCategoría") or "").strip(),
            tipo_inventario=str(fila.get("CodTipoInv") or "").strip(),
        )

    @staticmethod
    def _unidades_desde_descripcion(descripcion) -> int:
        """Fallback para descripciones tipo 'x24UN'; si no, se toma como bulto (factor 1)."""
        coincidencia = re.search(r"[xX]\s*(\d+)\s*U", descripcion)
        return int(coincidencia.group(1)) if coincidencia else 1

    @staticmethod
    def _leer_cantidad(valor):
        try:
            numero = float(str(valor).strip().replace(",", "."))
        except (TypeError, ValueError):
            return None
        if not numero.is_integer():
            return None
        return int(numero)
