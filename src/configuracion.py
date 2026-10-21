"""Rutas, días, unidades de reporte y colores de ROCO."""
from pathlib import Path

CARPETA_BASE = Path(__file__).resolve().parent
CANDIDATAS_PLANTILLA = (
    CARPETA_BASE / "FACTURACION SMF.xlsx",
    CARPETA_BASE / "FACTURACION_SMF.xlsx",
    CARPETA_BASE.parent / "resources" / "FACTURACION SMF.xlsx",
)
RUTA_PLANTILLA = next((ruta for ruta in CANDIDATAS_PLANTILLA if ruta.exists()), CANDIDATAS_PLANTILLA[0])
RUTA_LOGO = CARPETA_BASE / "LOGO_ROCO_3.jpg"
RUTA_VENDEDORES = CARPETA_BASE / "vendedores.txt"  # Compatibilidad con instalaciones anteriores.
RUTA_FACTORES = CARPETA_BASE / "factores_conversion.json"

DIAS_SEMANA = ("LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES")

MODO_CAJA = "CAJA"
MODO_UNIDAD = "UNIDAD"
MODO_BULTO = "BULTO"
MODOS = (MODO_CAJA, MODO_UNIDAD, MODO_BULTO)

# Cuotas de refrescos para ADC. La regla se aplica ahora por producto hasta recibir
# una definición diferente del equipo.
CUOTA_REFRESCOS_POR_PUERTAS = {1: 25, 2: 60}
MINIMO_CAJAS_REFRESCO_ADC = 6
CATEGORIA_REFRESCOS = "REFRESCO"
TIPO_PEPSI = "PEPSI-COLA"

COLOR_ROJO_ROCO = "#E60000"
COLOR_AZUL_ROCO = "#1E5BFF"
COLOR_ENCABEZADO = "#E8EEF9"
