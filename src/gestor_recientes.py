"""Gestor de archivos recientes y análisis de estado para la pantalla de inicio."""
from dataclasses import dataclass
import datetime
import json
from pathlib import Path
from typing import List, Optional

from configuracion import CARPETA_BASE, CANDIDATAS_PLANTILLA
from lector_excel import LectorExcel, LectorReporteCompras
from exportador_plantilla import PATRON_ASIGNACION


RUTA_RECIENTES_JSON = CARPETA_BASE / "recientes.json"
MAX_RECIENTES = 15


@dataclass
class InfoArchivoReciente:
    ruta: str
    nombre: str
    fecha_modificacion: str
    estado: str
    es_trabajo_en_progreso: bool
    cantidad_compras: int = 0
    cantidad_asignaciones: int = 0


def analizar_archivo_excel(ruta_archivo: Path, lector_excel: Optional[LectorExcel] = None) -> InfoArchivoReciente:
    """Inspecciona rápidamente un archivo Excel para ver si tiene compras y asignaciones."""
    ruta = Path(ruta_archivo).resolve()
    nombre = ruta.name
    
    if not ruta.exists():
        return InfoArchivoReciente(
            ruta=str(ruta),
            nombre=nombre,
            fecha_modificacion="Archivo no encontrado",
            estado="No encontrado",
            es_trabajo_en_progreso=False
        )

    try:
        timestamp = ruta.stat().st_mtime
        fecha_str = datetime.datetime.fromtimestamp(timestamp).strftime("%d/%m/%Y %I:%M %p")
    except Exception:
        fecha_str = "Desconocida"

    if lector_excel is None:
        lector_excel = LectorExcel()

    # Verificar si tiene compras
    compras_count = 0
    try:
        lector_reporte = LectorReporteCompras(lector_excel)
        tabla = lector_reporte.leer(ruta)
        compras_count = len(tabla.filas) if tabla and tabla.filas else 0
    except Exception:
        compras_count = 0

    # Verificar si tiene asignaciones escritas en hoja de clientes
    asignaciones_count = 0
    try:
        hoja_clientes = lector_excel.buscar_hoja_con_encabezados(ruta, ("DIA", "CLIENTE"))
        if hoja_clientes is not None:
            col = hoja_clientes.columnas
            idx_cliente = col.get("CLIENTE")
            idx_dia = col.get("DIA")
            for idx_fila, fila in enumerate(hoja_clientes.filas):
                if idx_fila <= hoja_clientes.fila_encabezados:
                    continue
                if idx_cliente is not None and not hoja_clientes.valor(fila, idx_cliente):
                    continue
                for valor in fila:
                    if isinstance(valor, str) and valor.strip():
                        coincidencias = len(PATRON_ASIGNACION.findall(valor))
                        asignaciones_count += coincidencias
    except Exception:
        asignaciones_count = 0

    if asignaciones_count > 0:
        estado = f"En progreso ({asignaciones_count} asignaciones)"
        en_progreso = True
    elif compras_count > 0:
        estado = f"Compras listas ({compras_count} ítems)"
        en_progreso = True
    elif "FACTURACION SMF.XLSX" in nombre.upper():
        estado = "Plantilla base limpia"
        en_progreso = False
    else:
        estado = "Archivo Excel"
        en_progreso = False

    return InfoArchivoReciente(
        ruta=str(ruta),
        nombre=nombre,
        fecha_modificacion=fecha_str,
        estado=estado,
        es_trabajo_en_progreso=en_progreso,
        cantidad_compras=compras_count,
        cantidad_asignaciones=asignaciones_count
    )


class GestorRecientes:
    def __init__(self, lector_excel: Optional[LectorExcel] = None):
        self.lector_excel = lector_excel or LectorExcel()
        self.archivo_json = RUTA_RECIENTES_JSON

    def guardar_reciente(self, ruta: Path) -> None:
        """Registra una ruta en la lista de recientes al principio."""
        try:
            ruta_str = str(Path(ruta).resolve())
            recientes = self._leer_rutas()
            if ruta_str in recientes:
                recientes.remove(ruta_str)
            recientes.insert(0, ruta_str)
            recientes = recientes[:MAX_RECIENTES]
            self.archivo_json.write_text(json.dumps(recientes, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def _leer_rutas(self) -> List[str]:
        if not self.archivo_json.exists():
            return []
        try:
            datos = json.loads(self.archivo_json.read_text(encoding="utf-8"))
            if isinstance(datos, list):
                return [str(p) for p in datos if Path(p).exists()]
        except Exception:
            pass
        return []

    def obtener_lista_recientes(self) -> List[InfoArchivoReciente]:
        """Obtiene la lista de recientes combinando el historial JSON y los archivos en resources/."""
        rutas_existentes = self._leer_rutas()
        vistos = set(rutas_existentes)

        # Autodescubrir archivos de resources y base si hay pocos en JSON
        carpetas_busqueda = [
            CARPETA_BASE.parent / "resources",
            CARPETA_BASE
        ]
        archivos_descubiertos = []
        for carpeta in carpetas_busqueda:
            if carpeta.exists() and carpeta.is_dir():
                for arch in carpeta.glob("*.xlsx"):
                    if arch.name.startswith("~$") or "REPORTEGENERALCOMPRAS" in arch.name.upper():
                        continue
                    ruta_abs = str(arch.resolve())
                    if ruta_abs not in vistos:
                        archivos_descubiertos.append(arch)
                        vistos.add(ruta_abs)

        # Ordenar los descubiertos por fecha de modificación más reciente
        archivos_descubiertos.sort(key=lambda a: a.stat().st_mtime if a.exists() else 0, reverse=True)

        todas_las_rutas = rutas_existentes + [str(a.resolve()) for a in archivos_descubiertos]
        todas_las_rutas = todas_las_rutas[:MAX_RECIENTES]

        resultados = []
        for r_str in todas_las_rutas:
            p = Path(r_str)
            if p.exists():
                info = analizar_archivo_excel(p, self.lector_excel)
                resultados.append(info)

        return resultados
