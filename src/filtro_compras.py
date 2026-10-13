"""Fase 1: filtrado inicial de las compras."""
from dataclasses import dataclass, field

from lector_excel import TablaCompras
from utilidades import normalizar_texto


@dataclass(frozen=True)
class ReglasFiltro:
    """Reglas de la fase 1. Se pueden cambiar sin tocar el resto del programa."""

    # DescrCategoría: se EXCLUYEN las filas con exactamente estas categorías.
    categorias_excluidas: tuple = ("MATERIALES",)
    # CodTipoInv: se CONSERVAN solo las filas cuyo tipo contenga alguno de estos textos.
    # "CERVECERIA POLAR" es como el sistema nombra a la cerveza en este reporte.
    tipos_inventario_permitidos: tuple = (
        "CERVEZA", "CERVECERIA POLAR", "PEPSI", "ALIMENTOS POLAR", "MALTA", "REFRESCO", "SOLERA", "POLAR")
    # Comentario Cabecera: se EXCLUYEN las filas cuyo comentario contenga estos textos.
    comentarios_excluidos: tuple = ("OBSEQUIOS DE CLIENTES", "RECONOCIMIENTO DE UTILIDAD")


@dataclass
class ResultadoFiltro:
    total_leidas: int = 0
    filas_conservadas: list = field(default_factory=list)
    descartadas_por_categoria: int = 0
    descartadas_por_tipo_inventario: int = 0
    descartadas_por_comentario: int = 0

    def total_descartadas(self) -> int:
        return (self.descartadas_por_categoria
                + self.descartadas_por_tipo_inventario
                + self.descartadas_por_comentario)

    def resumen(self) -> str:
        return (
            f"Filas leídas: {self.total_leidas}\n"
            f"Filas conservadas: {len(self.filas_conservadas)}\n"
            f"Filas descartadas: {self.total_descartadas()}\n"
            f"   · Categoría excluida (MATERIALES): {self.descartadas_por_categoria}\n"
            f"   · Tipo de inventario no permitido: {self.descartadas_por_tipo_inventario}\n"
            f"   · Comentario de cabecera excluido: {self.descartadas_por_comentario}"
        )


class FiltroCompras:
    """Aplica las reglas de la fase 1. Cada fila se cuenta una sola vez, en el
    orden: categoría, tipo de inventario, comentario de cabecera."""

    def __init__(self, reglas: ReglasFiltro):
        self.reglas = reglas

    def filtrar(self, tabla: TablaCompras) -> ResultadoFiltro:
        resultado = ResultadoFiltro(total_leidas=len(tabla.filas))
        for fila in tabla.filas:
            if self._categoria_excluida(fila):
                resultado.descartadas_por_categoria += 1
            elif not self._tipo_inventario_permitido(fila):
                resultado.descartadas_por_tipo_inventario += 1
            elif self._comentario_excluido(fila):
                resultado.descartadas_por_comentario += 1
            else:
                resultado.filas_conservadas.append(fila)
        return resultado

    def _categoria_excluida(self, fila) -> bool:
        categoria = normalizar_texto(fila.get("DescrCategoría"))
        return categoria in {normalizar_texto(c) for c in self.reglas.categorias_excluidas}

    def _tipo_inventario_permitido(self, fila) -> bool:
        tipo = normalizar_texto(fila.get("CodTipoInv"))
        return any(normalizar_texto(p) in tipo for p in self.reglas.tipos_inventario_permitidos if tipo)

    def _comentario_excluido(self, fila) -> bool:
        comentario = normalizar_texto(fila.get("Comentario Cabecera"))
        return any(normalizar_texto(e) in comentario for e in self.reglas.comentarios_excluidos)
