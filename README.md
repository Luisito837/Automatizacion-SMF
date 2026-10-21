# Automatización SMF · ROCO

# Automatización SMF · ROCO

Aplicación de escritorio en Python/Tkinter para distribuir entre los clientes por día de la semana lo que se compró, usando el Reporte General de Compras y la plantilla FACTURACION SMF.

## Características principales

- Filtrado estricto de compras: excluye `MATERIALES`, conserva solo los tipos permitidos y excluye los comentarios `OBSEQUIOS DE CLIENTES` y `RECONOCIMIENTO DE UTILIDAD`.
- Categorías generadas a partir de `DescrCategoría` del reporte. Se pueden filtrar con botones; el selector de producto permite buscar por nombre o SKU y queda limitado a la categoría seleccionada.
- Un producto visible a la vez, con cantidad editable por cliente y selector individual para reportar por caja, unidad o bulto cuando corresponda.
- Conversión desde compras: `Cantidad` en `UnidadCompra=CAJ` se convierte a unidades multiplicando por el factor; `UNI` se mantiene en unidades. El factor principal sale de `INVENTARIO → UND`; si el SKU no está en esa hoja, se usa `LISTA → UD por CJ` como respaldo. Un factor `1` significa bulto y no se multiplica.
- Pepsi-Cola se reporta solo por caja. Para productos con factor `1`, el modo es bulto, sin conversión.
- Reglas ADC en productos de categoría `REFRESCO`: `1 PUERTA` tiene cuota individual de 25 cajas, `2 PUERTA` de 60 cajas y cualquier asignación no vacía tiene mínimo de 6 cajas. La cuota por SKU se implementa temporalmente de manera individual, a la espera de la definición del equipo. `3 PUERTA` no tiene una cuota fija definida, pero conserva el mínimo de 6 cajas.
- Editor para consultar y corregir factores de conversión. Las correcciones se guardan localmente en `src/factores_conversion.json` y prevalecen sobre los valores leídos del Excel hasta que se modifiquen.
- Herramientas rápidas: cantidad global, repartir el restante del producto, completar la categoría, limpiar las asignaciones del día, fijar un modo permitido y resumen semanal por SKU para localizar los saldos pendientes o excesos.
- Botón `Guardar Excel`: copia la plantilla con compras y asignaciones de todos los días que estén guardadas, sin sobrescribir el archivo origen. Una plantilla con compras y asignaciones previamente exportadas puede abrirse con `Abrir guardado` o recuperarse automáticamente si está configurada como plantilla por defecto.
- Copia de las compras filtradas a la plantilla, conservando tablas dinámicas, segmentaciones, fórmulas y estilos.
- Clientes filtrados por día de la semana (lunes a viernes), tomados de la plantilla; cada cliente puede reportarse por caja o unidad.
- Navegación con teclado pensada para capturar rápido.

## Requisitos

- Python 3.10 o superior con Tkinter (incluido en la instalación oficial de Python para Windows).
- Dependencias:

```bash
pip install -r requisitos.txt
```

`openpyxl` es obligatorio; `Pillow` es opcional: sin él se muestra el nombre `ROCO` en lugar del logo.

## Instalación

1. Descomprime el proyecto completo; conserva `resources/` y `src/`.
2. Instala las dependencias, desde `src/`:

   ```bash
   pip install -r requisitos.txt
   ```

3. Ejecuta `python principal.py` desde la carpeta `src/`.

Requiere Python 3.10 o superior con Tkinter. `openpyxl` es obligatorio; `Pillow` solo se utiliza para mostrar el logo.

## Uso y flujo de trabajo

1. Carga el Reporte General de Compras. ROCO filtra las filas y crea una copia de la plantilla con las compras incluidas.
2. Selecciona el día de reparto; se cargan los clientes del día.
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

### Fase 1: filtrado de las compras

Se aplican en este orden (cada fila se cuenta una sola vez) y se pueden cambiar en `ReglasFiltro` (`filtro_compras.py`):

| Columna del reporte | Regla |
|---|---|
| `DescrCategoría` | Se **excluye** `MATERIALES` |
| `CodTipoInv` | Se **conservan** solo los tipos de la lista permitida (cerveza, Pepsi-Cola, Alimentos Polar, etc.) |
| `Comentario Cabecera` | Se **excluyen** `OBSEQUIOS DE CLIENTES` y `RECONOCIMIENTO DE UTILIDAD` |

En este reporte la cerveza viene en `CodTipoInv` como "CERVECERIA POLAR_C.A". Solo se distribuye lo que queda con stock mayor a 0.

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

### Atajos de teclado

| Tecla | Acción |
|---|---|
| `Enter` / `↓` | Bajar a la celda de cantidad del siguiente cliente |
| `↑` | Subir al cliente anterior |
| `Ctrl+D` | Copiar la cantidad del cliente de arriba |
| `Ctrl+V` | Pegar una columna de cantidades copiada desde Excel |
| `Ctrl+→` o `Av Pág` | Siguiente alimento |
| `Ctrl+←` o `Re Pág` | Alimento anterior |
| `C` / `U` / `Espacio` | En el desplegable "Reportar por": CAJA / UNIDAD / alternar |

Al entrar en una celda su contenido queda seleccionado, así que escribir reemplaza el valor. Dentro de una lista desplegable, `Ctrl+←/→` y `Av Pág`/`Re Pág` conservan su función normal.

### Regla de neveras ADC (solo refrescos)

Los refrescos son los productos con categoría `REFRESCO` en el reporte. La plantilla indica en la columna **CLIENTES DE ADC** si el cliente tiene nevera (`1 PUERTA`, `2 PUERTA`, `3 PUERTA` o vacío). Para esos clientes:

- **Cuota de prioridad:** 1 puerta = 25 cajas y 2 puertas = 60 cajas de refrescos en total. La cuota **no es un límite**: un cliente con nevera puede recibir más. 3 puertas no tiene cuota definida.
- **Mínimo:** cada refresco asignado a un cliente con nevera no puede ser menor a **6 cajas**.
- **Autorrellenar un refresco:** el cliente con nevera pasa a CAJA y recibe primero su mínimo; luego se le da prioridad hasta completar su cuota (descontando lo que ya tiene de otros refrescos) y lo que queda se reparte en partes iguales entre todos. Si el stock no alcanza para todos los clientes con nevera, los demás reciben menos o nada de ese producto.
- La columna **NEVERA (ADC)** muestra las puertas y lo asignado frente a la cuota (por ejemplo `1 puerta · 11/25 cj`) y marca en rojo si un cliente queda por debajo del mínimo. La entrada manual y el valor global no se bloquean: solo se avisa.

Los valores se cambian en `configuracion.py` (`CUOTA_REFRESCOS_POR_PUERTAS`, `MINIMO_CAJAS_REFRESCO_ADC`, `CATEGORIA_REFRESCOS`).

## Exportación

**Guardar Excel** parte de la plantilla generada al cargar el reporte (con las compras ya incluidas) y la guarda con otro nombre; nunca sobrescribe el original.

- Cada celda lleva `codigo_producto + espacio + número + und/cj`, por ejemplo `0178392 5 cj` o `80626 3 und`.
- Se escribe en la hoja de clientes, en la fila de cada cliente (por día y nombre) y en la columna de la categoría del producto (`%Cola Negra`, `%Sab`, `%Agua`, `%Cer`…). Los productos con columna propia (por ejemplo ROCKSTAR) van a esa columna.
- Si un cliente recibe varios productos de la misma categoría, comparten celda separados por `, `.
- Se exporta lo asignado en todos los días que se hayan visitado durante la sesión.
- Lo que no tenga columna en la plantilla, o los clientes que no se encuentren, no se escriben y el mensaje final los lista.

La equivalencia categoría → columna está en `EQUIVALENCIAS_DE_CATEGORIA` y el separador en `SEPARADOR` (`exportador_plantilla.py`).

## Archivos de entrada esperados

**Reporte General de Compras** (`.xlsx`): columnas `CodProducto`, `DescrProducto`, `Cantidad`, `UnidadCompra`, `DescrCategoría`, `CodTipoInv` y `Comentario Cabecera`. Las columnas se buscan por nombre, no por posición.

**Plantilla `FACTURACION_SMF.xlsx`**, con estas hojas (se detectan por sus encabezados, no por el nombre):

| Hoja | Encabezados que necesita |
|---|---|
| Productos (`LISTA`) | `Material`, `Categoría`, `UD por CJ` |
| Compras | `CódigoCompra`, `FechaCompra`, `CodProducto` (la columna `RUC` del reporte no se copia) |
| Clientes | `DIA`, `CLIENTE`, `CEP`, `CODIGO SISTEMA`, `CLIENTES DE ADC`; los encabezados de categorías están en la fila inmediatamente superior |

## Estructura del proyecto

El código usa **composición** (clases pequeñas que se combinan, sin herencia), con nombres y funciones en español. `principal.py` arma todas las piezas.

| Módulo | Responsabilidad |
|---|---|
| `principal.py` | Punto de entrada, tema visual y armado de las piezas |
| `ventana_principal.py` | Conecta la interfaz con la lógica |
| `barra_superior.py`, `barra_herramientas.py`, `tabla_distribucion.py`, `panel_stock.py`, `lista_buscable.py` | Componentes de la interfaz |
| `procesador_reporte.py` | Orquesta la fase 1 |
| `lector_excel.py` | Lectura del reporte y localización de hojas por encabezados |
| `filtro_compras.py` | Reglas de filtrado |
| `escritor_plantilla.py` | Copia las compras a la hoja de compras de la plantilla |
| `catalogo_plantilla.py` | Productos (categoría, unidades por caja) y clientes por día |
| `inventario.py` | Stock comprado, por producto y categoría |
| `distribucion.py` | Reparto entre clientes, modo caja/unidad, regla de neveras y stock |
| `exportador_plantilla.py` | Exporta la distribución a la hoja de clientes |
| `configuracion.py`, `utilidades.py` | Constantes y funciones de apoyo |
| `archivo_vendedores.py` | Sin uso en la versión por cliente |

## Notas

- **Los archivos Excel se editan a nivel XML.** Guardar la plantilla con `openpyxl` eliminaría las segmentaciones de la tabla dinámica; por eso solo se reescribe la hoja necesaria dentro del `.xlsx`. La tabla dinámica se actualiza sola al abrir el archivo en Excel.
- En Windows, si el archivo de salida está abierto en Excel, no se puede sobrescribir: ciérralo antes de volver a cargar el reporte o exportar con el mismo nombre.
- Los Excel de la empresa (plantilla y reportes) y el logo no deberían subirse a un repositorio público; el `.gitignore` incluido excluye los Excel de la empresa (plantilla, reportes y archivos generados).
- La aplicación se usa para capturar distribuciones por día y luego exportarlas a la plantilla para su revisión en Excel.

