"""Orquesta la fase 1: leer el reporte, filtrar, copiar a la plantilla y armar el inventario."""
import datetime
from dataclasses import dataclass, field
from pathlib import Path

from catalogo_plantilla import LectorPlantilla
from escritor_plantilla import EscritorPlantilla
from filtro_compras import FiltroCompras, ResultadoFiltro
from inventario import ConstructorInventario, Inventario
from lector_excel import LectorReporteCompras


@dataclass
class ResultadoProceso:
    ruta_salida: Path
    resultado_filtro: ResultadoFiltro
    inventario: Inventario
    productos_sin_unidades_por_caja: list = field(default_factory=list)

    def resumen(self) -> str:
        lineas = [
            self.resultado_filtro.resumen(),
            "",
            f"Productos con stock para distribuir: {self.inventario.cantidad_de_productos()}",
            f"Categorías: {len(self.inventario.categorias())}",
            "",
            f"Plantilla con las compras copiadas:\n{self.ruta_salida}",
        ]
        if self.productos_sin_unidades_por_caja:
            lineas += [
                "",
                "Aviso: no se encontraron las unidades por caja de estos productos "
                "(se tomó 1 unidad por caja):",
                *[f"   · {descripcion}" for descripcion in self.productos_sin_unidades_por_caja],
            ]
        return "\n".join(lineas)


class ProcesadorReporte:
    """Junta las piezas de la fase 1 (se arma por composición)."""

    def __init__(self, lector_reporte: LectorReporteCompras, filtro: FiltroCompras,
                 escritor: EscritorPlantilla, lector_plantilla: LectorPlantilla):
        self.lector_reporte = lector_reporte
        self.filtro = filtro
        self.escritor = escritor
        self.lector_plantilla = lector_plantilla

    def procesar(self, ruta_reporte, ruta_plantilla) -> ResultadoProceso:
        tabla = self.lector_reporte.leer(ruta_reporte)
        resultado_filtro = self.filtro.filtrar(tabla)
        ruta_salida = self._ruta_de_salida(Path(ruta_plantilla))
        self.escritor.volcar_compras(ruta_plantilla, resultado_filtro.filas_conservadas, ruta_salida)
        catalogo = self.lector_plantilla.leer_productos(ruta_plantilla)
        resultado_inventario = ConstructorInventario(catalogo).construir(resultado_filtro.filas_conservadas)
        return ResultadoProceso(
            ruta_salida=ruta_salida,
            resultado_filtro=resultado_filtro,
            inventario=resultado_inventario.inventario,
            productos_sin_unidades_por_caja=resultado_inventario.productos_sin_unidades_por_caja,
        )

    @staticmethod
    def _ruta_de_salida(ruta_plantilla: Path) -> Path:
        """Crea un nombre nuevo cada vez; evita pisar el estado de un reporte previo."""
        fecha = datetime.date.today().strftime("%Y-%m-%d")
        candidato = ruta_plantilla.with_name(f"{ruta_plantilla.stem}_{fecha}{ruta_plantilla.suffix}")
        secuencia = 2
        while candidato.exists():
            candidato = ruta_plantilla.with_name(
                f"{ruta_plantilla.stem}_{fecha}_{secuencia}{ruta_plantilla.suffix}"
            )
            secuencia += 1
        return candidato
