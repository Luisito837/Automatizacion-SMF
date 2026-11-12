"""Fase 1: filtrado inicial de las compras."""
from dataclasses import dataclass, field

from lector_excel import TablaCompras
from utilidades import normalizar_codigo, normalizar_texto


@dataclass(frozen=True)
class ReglasFiltro:
    """Reglas de la fase 1. Se pueden cambiar sin tocar el resto del programa."""

    # DescrCategoría: se EXCLUYEN las filas con exactamente estas categorías.
    categorias_excluidas: tuple = ("MATERIALES",)
    # CodTipoInv: lista cerrada según la regla de negocio. En el reporte real, cerveza
    # aparece como "CERVECERIA POLAR_C.A", por eso se acepta como alias explícito.
    tipos_inventario_permitidos: tuple = (
        "CERVEZA", "CERVECERIA POLAR_C.A", "PEPSI-COLA", "ALIMENTOS POLAR")
    # Patrones para detectar obsequios, regalos o promociones no reportables por palabra clave
    patrones_obsequio: tuple = ("OBSEQUI", "REGALO", "BONIFICACI", "MUESTRA")
    # Comentario Cabecera: se EXCLUYEN las filas cuyo comentario contenga estos textos.
    comentarios_excluidos: tuple = (
        "RECONOCIMIENTO DE UTILIDAD",
        "RECONOCIMIENTO DESCUENTO",
    )
    # CodProducto: se EXCLUYEN estos códigos sin importar el resto de las columnas.
    # 1001-BC: obsequio de cerveza para clientes (no debe sumarse al inventario).
    codigos_excluidos: tuple = ("1001-BC",)


@dataclass
class ResultadoFiltro:
    total_leidas: int = 0
    filas_conservadas: list = field(default_factory=list)
    descartadas_por_obsequio: int = 0
    descartadas_por_categoria: int = 0
    descartadas_por_tipo_inventario: int = 0
    descartadas_por_comentario: int = 0
    descartadas_por_codigo: int = 0

    def total_descartadas(self) -> int:
        return (self.descartadas_por_obsequio
                + self.descartadas_por_categoria
                + self.descartadas_por_tipo_inventario
                + self.descartadas_por_comentario
                + self.descartadas_por_codigo)

    def resumen(self) -> str:
        return (
            f"Filas leídas: {self.total_leidas}\n"
            f"Filas conservadas: {len(self.filas_conservadas)}\n"
            f"Filas descartadas: {self.total_descartadas()}\n"
            f"   · Obsequios o bonificaciones descartadas: {self.descartadas_por_obsequio}\n"
            f"   · Categoría excluida (MATERIALES): {self.descartadas_por_categoria}\n"
            f"   · Tipo de inventario no permitido: {self.descartadas_por_tipo_inventario}\n"
            f"   · Comentario de cabecera excluido: {self.descartadas_por_comentario}\n"
            f"   · Código de producto excluido: {self.descartadas_por_codigo}"
        )


class FiltroCompras:
    """Aplica las reglas de la fase 1. Cada fila se cuenta una sola vez, en el
    orden: obsequios, código, categoría, tipo de inventario, comentario de cabecera."""

    def __init__(self, reglas: ReglasFiltro):
        self.reglas = reglas

    def filtrar(self, tabla: TablaCompras) -> ResultadoFiltro:
        resultado = ResultadoFiltro(total_leidas=len(tabla.filas))
        for fila in tabla.filas:
            if self._es_obsequio(fila):
                resultado.descartadas_por_obsequio += 1
            elif self._codigo_excluido(fila):
                resultado.descartadas_por_codigo += 1
            elif self._categoria_excluida(fila):
                resultado.descartadas_por_categoria += 1
            elif not self._tipo_inventario_permitido(fila):
                resultado.descartadas_por_tipo_inventario += 1
            elif self._comentario_excluido(fila):
                resultado.descartadas_por_comentario += 1
            else:
                resultado.filas_conservadas.append(fila)
        return resultado

    def _es_obsequio(self, fila) -> bool:
        """Detecta si la fila corresponde a un obsequio, muestra o regalo por palabra clave."""
        # 1. Chequeo en campos principales de texto y comentarios
        campos_clave = (
            "Comentario Cabecera", "Comentario Detalle", "DescrProducto",
            "Tipo de compra (Nombre)", "Tipo de compra", "DescrCategoría"
        )
        for campo in campos_clave:
            valor = fila.get(campo)
            if valor:
                texto = normalizar_texto(str(valor))
                if any(p in texto for p in self.reglas.patrones_obsequio):
                    return True

        # 2. Chequeo general en el resto de los valores de texto de la fila (excluyendo CodProducto)
        for clave, v in fila.items():
            if clave == "CodProducto" or v is None:
                continue
            texto = normalizar_texto(str(v))
            if any(p in texto for p in self.reglas.patrones_obsequio):
                return True

        return False

    def _codigo_excluido(self, fila) -> bool:
        codigo = normalizar_codigo(fila.get("CodProducto"))
        return codigo in {normalizar_codigo(c) for c in self.reglas.codigos_excluidos}

    def _categoria_excluida(self, fila) -> bool:
        categoria = normalizar_texto(fila.get("DescrCategoría"))
        return categoria in {normalizar_texto(c) for c in self.reglas.categorias_excluidas}

    def _tipo_inventario_permitido(self, fila) -> bool:
        tipo = normalizar_texto(fila.get("CodTipoInv"))
        permitidos = {normalizar_texto(valor) for valor in self.reglas.tipos_inventario_permitidos}
        return bool(tipo) and tipo in permitidos

    def _comentario_excluido(self, fila) -> bool:
        comentario = normalizar_texto(fila.get("Comentario Cabecera"))
        return any(normalizar_texto(e) in comentario for e in self.reglas.comentarios_excluidos)
