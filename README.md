# Automatización SMF · ROCO

Aplicación de escritorio en Python/Tkinter para distribuir las compras entre los clientes por día de la semana, usando la plantilla FACTURACION SMF y el Reporte General de Compras.

## Funciones principales

- Filtrado estricto de compras: excluye `MATERIALES`, conserva solo los tipos permitidos y excluye los comentarios `OBSEQUIOS DE CLIENTES` y `RECONOCIMIENTO DE UTILIDAD`.
- Categorías generadas a partir de `DescrCategoría` del reporte. Se pueden filtrar con botones; el selector de producto permite buscar por nombre o SKU y queda limitado a la categoría seleccionada.
- Un producto visible a la vez, con cantidad editable por cliente y selector individual para reportar por caja, unidad o bulto cuando corresponda.
- Conversión desde compras: `Cantidad` en `UnidadCompra=CAJ` se convierte a unidades multiplicando por el factor; `UNI` se mantiene en unidades. El factor principal sale de `INVENTARIO → UND`; si el SKU no está en esa hoja, se usa `LISTA → UD por CJ` como respaldo. Un factor `1` significa bulto y no se multiplica.
- Pepsi-Cola se reporta solo por caja. Para productos con factor `1`, el modo es bulto, sin conversión.
- Reglas ADC en los productos de categoría `REFRESCO`: `1 PUERTA` tiene cuota individual de 25 cajas, `2 PUERTA` de 60 cajas y cualquier asignación no vacía tiene mínimo de 6 cajas. La cuota por SKU se implementa temporalmente de manera individual, a la espera de la definición del equipo. `3 PUERTA` no tiene una cuota fija definida, pero conserva el mínimo de 6 cajas.
- Editor para consultar y corregir factores de conversión. Las correcciones se guardan localmente en `src/factores_conversion.json` y prevalecen sobre los valores leídos del Excel hasta que se modifiquen.
- Herramientas rápidas: cantidad global, repartir el restante del producto, completar la categoría, limpiar las asignaciones del día, fijar un modo permitido y resumen semanal por SKU para localizar los saldos pendientes o excesos.
- Botón `Guardar Excel`: copia la plantilla con compras y asignaciones de todos los días que estén guardadas, sin sobrescribir el archivo origen. Una plantilla con compras y asignaciones previamente exportadas puede abrirse con `Abrir guardado` o recuperarse automáticamente si está configurada como plantilla por defecto.

## Instalación

1. Descomprime el proyecto completo; conserva `resources/` y `src/`.
2. Instala las dependencias, desde `src/`:

   ```bash
   pip install -r requisitos.txt
   ```

3. Ejecuta `python principal.py` desde la carpeta `src/`.

Requiere Python 3.10 o superior con Tkinter. `openpyxl` es obligatorio; `Pillow` solo se utiliza para mostrar el logo.

## Flujo de trabajo

1. Carga el Reporte General de Compras. ROCO filtra las filas y crea una copia de la plantilla con las compras incluidas.
2. Selecciona el día de reparto.
3. Selecciona una categoría y busca el producto por nombre o código.
4. Edita las cantidades por cliente o utiliza las herramientas de reparto rápido.
5. Consulta `Resumen semanal` para revisar, por SKU, lo comprado, lo asignado y el saldo.
6. Pulsa `Guardar Excel` para escribir la distribución en la hoja de clientes y elegir dónde guardar el archivo.
7. Para continuar posteriormente, pulsa `Abrir guardado` y selecciona el Excel exportado.

## Reglas de filtrado

- `DescrCategoría`: excluir la categoría `MATERIALES`.
- `CodTipoInv`: conservar `CERVEZA`, `PEPSI-COLA` y `ALIMENTOS POLAR`. En el reporte incluido la cerveza aparece como `CERVECERIA POLAR_C.A`, que se admite como alias explícito.
- `Comentario Cabecera`: excluir `OBSEQUIOS DE CLIENTES` y `RECONOCIMIENTO DE UTILIDAD`.

El filtro compara los tipos de inventario como valores exactos después de normalizar mayúsculas, tildes y espacios, para no admitir tipos similares por coincidencia parcial.

## Conversión y reporte

Para productos con factor `12`, por ejemplo, `5 cajas × 12 = 60 unidades`. Cuando el factor de `INVENTARIO → UND` es `1`, la cantidad representa bultos y se conserva como tal. Los totales del panel de compras muestran cajas completas, unidades sueltas y bultos por separado; no intenta sumar bultos con unidades como si fueran la misma medida.

Cada asignación se almacena con código limpio, cantidad y sufijo de modo: por ejemplo `12345 6und`, `12345 2cj` o `12345 2bto`. Si varios productos corresponden a la misma celda de categoría, se separan por coma. Los productos sin una columna equivalente en la plantilla o los clientes no localizados se notifican al guardar.

## Atajos

- `Enter` / `↓`: siguiente cliente.
- `↑`: cliente anterior.
- `Ctrl+D`: copiar la cantidad de la fila superior.
- `Ctrl+V`: pegar una columna de cantidades copiada desde Excel.
- `Ctrl+→` o `Av Pág`: siguiente producto.
- `Ctrl+←` o `Re Pág`: producto anterior.
- En el desplegable, `C`, `U`, `B` o `Espacio`: caja, unidad, bulto o siguiente modo permitido.
