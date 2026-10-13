"""Valores fijos del programa: rutas, días de la semana, modos de reporte y colores."""
from pathlib import Path

CARPETA_BASE = Path(__file__).resolve().parent
RUTA_PLANTILLA = CARPETA_BASE / "FACTURACION_SMF.xlsx"
RUTA_LOGO = CARPETA_BASE / "LOGO_ROCO_3.jpg"
RUTA_VENDEDORES = CARPETA_BASE / "vendedores.txt"

DIAS_SEMANA = ("LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES")

MODO_CAJA = "CAJA"
MODO_UNIDAD = "UNIDAD"
MODOS = (MODO_CAJA, MODO_UNIDAD)

# Regla de neveras (solo refrescos): clientes con "CLIENTES DE ADC" en la plantilla.
# Cuota de refrescos (en cajas) según las puertas de la nevera. Es una PRIORIDAD, no un límite:
# se les asigna primero a ellos, pero pueden recibir más. (3 puertas: sin cuota definida).
CUOTA_REFRESCOS_POR_PUERTAS = {1: 25, 2: 60}
# Con nevera ADC, cada refresco asignado no puede ser menor a estas cajas.
MINIMO_CAJAS_REFRESCO_ADC = 6
# DescrCategoría del reporte de compras que identifica a los refrescos.
CATEGORIA_REFRESCOS = "REFRESCO"

COLOR_ROJO_ROCO = "#E60000"
COLOR_AZUL_ROCO = "#1E5BFF"
COLOR_ENCABEZADO = "#E8EEF9"
