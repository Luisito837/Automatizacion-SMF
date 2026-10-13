# Automatizacion SMF

Aplicación de escritorio (Python + Tkinter) para repartir entre los clientes del día lo que se compró,
a partir del **Reporte General de Compras** y de la plantilla Excel **FACTURACION_SMF**.

## Características

- Filtrado automático del reporte (categoría, tipo de inventario y comentario de cabecera).
- Copia de las compras filtradas a la plantilla (tabla dinámica,
  segmentaciones, fórmulas y estilos se conservan).
- Un alimento a la vez, con lista desplegable que.
- Clientes filtrados por **día de la semana** (lunes a viernes), tomados de la plantilla.
- Cada cliente puede reportarse **por CAJA o por UNIDAD**.
- Herramientas por alimento: valor global, autorrellenado, limpiar, todo en caja y todo en unidad.
- Navegación con teclado pensada para capturar rápido.

## Requisitos

- Python 3.10 o superior con Tkinter (viene incluido en el instalador oficial de Python para Windows).
- Dependencias:

```bash
pip install -r requisitos.txt
```

`openpyxl` es obligatorio. `pillow` es opcional: sin él se muestra el nombre "ROCO" en lugar del logo.

## Uso

1. Pulsa **Cargar reporte general** y elige el Excel del reporte de compras. Se aplica el filtrado y se
   crea una copia de la plantilla con las compras: `FACTURACION_SMF_AAAA-MM-DD.xlsx`.
2. Elige el **día** de reparto. Se cargan los clientes de ese día (**Ver clientes** muestra la lista).
3. Elige un **alimento** en la barra de herramientas y asigna cantidades en la tabla, o usa
   *Autorrellenar* / *Cantidad global*.
4. Avanza al siguiente alimento con el teclado (ver atajos) y repite.
5. Pulsa **Exportar plantilla** y elige dónde guardar el resultado.

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

Al entrar en una celda su contenido queda seleccionado, así que escribir reemplaza el valor.
Dentro de una lista desplegable, `Ctrl+←/→` y `Av Pág`/`Re Pág` conservan su función normal.

## Reglas

### Fase 1: filtrado de las compras

Se aplican en este orden (cada fila se cuenta una sola vez) y se pueden cambiar en
`ReglasFiltro` (`filtro_compras.py`):

| Columna del reporte | Regla |
|---|---|
| `DescrCategoría` | Se **excluye** `MATERIALES` |
| `CodTipoInv` | Se **conservan** solo los tipos de la lista permitida (cerveza, Pepsi-Cola, Alimentos Polar, etc.) |
| `Comentario Cabecera` | Se **excluyen** `OBSEQUIOS DE CLIENTES` y `RECONOCIMIENTO DE UTILIDAD` |

En este reporte la cerveza viene en `CodTipoInv` como "CERVECERIA POLAR_C.A". Solo se distribuye lo que
queda con stock mayor a 0.

### Regla de neveras ADC (solo refrescos)

Los refrescos son los productos con categoría `REFRESCO` en el reporte. La plantilla indica en la columna
**CLIENTES DE ADC** si el cliente tiene nevera (`1 PUERTA`, `2 PUERTA`, `3 PUERTA` o vacío). Para esos clientes:

- **Cuota de prioridad:** 1 puerta = 25 cajas y 2 puertas = 60 cajas de refrescos en total. La cuota **no es un
  límite**: un cliente con nevera puede recibir más. 3 puertas no tiene cuota definida.
- **Mínimo:** cada refresco asignado a un cliente con nevera no puede ser menor a **6 cajas**.
- **Autorrellenar un refresco:** el cliente con nevera pasa a CAJA y recibe primero su mínimo; luego se le
  da prioridad hasta completar su cuota (descontando lo que ya tiene de otros refrescos) y lo que queda se
  reparte en partes iguales entre todos. Si el stock no alcanza para todos los clientes con nevera, los
  demás reciben menos o nada de ese producto.
- La columna **NEVERA (ADC)** muestra las puertas y lo asignado frente a la cuota (por ejemplo
  `1 puerta · 11/25 cj`) y marca en rojo si un cliente queda por debajo del mínimo. La entrada manual
  y el valor global no se bloquean: solo se avisa.

Los valores se cambian en `configuracion.py` (`CUOTA_REFRESCOS_POR_PUERTAS`, `MINIMO_CAJAS_REFRESCO_ADC`,
`CATEGORIA_REFRESCOS`).

### Exportación

**Exportar plantilla** parte de la plantilla generada al cargar el reporte (con las compras ya incluidas)
y la guarda con otro nombre; nunca sobrescribe el original.

- Cada celda lleva `codigo_producto + espacio + número + und/cj`, por ejemplo `0178392 5 cj` o `80626 3 und`.
- Se escribe en la hoja de clientes, en la fila de cada cliente (por día y nombre) y en la columna de la
  categoría del producto (`%Cola Negra`, `%Sab`, `%Agua`, `%Cer`…). Los productos con columna propia
  (por ejemplo ROCKSTAR) van a esa columna.
- Si un cliente recibe varios productos de la misma categoría, comparten celda separados por `, `.
- Se exporta lo asignado en todos los días que se hayan visitado durante la sesión.
- Lo que no tenga columna en la plantilla, o los clientes que no se encuentren, no se escriben y el
  mensaje final los lista.

La equivalencia categoría → columna está en `EQUIVALENCIAS_DE_CATEGORIA` y el separador en `SEPARADOR`
(`exportador_plantilla.py`).

## Archivos de entrada esperados

**Reporte General de Compras** (`.xlsx`): columnas `CodProducto`, `DescrProducto`, `Cantidad`,
`UnidadCompra`, `DescrCategoría`, `CodTipoInv` y `Comentario Cabecera`. Las columnas se buscan por nombre,
no por posición.

**Plantilla `FACTURACION_SMF.xlsx`**, con estas hojas (se detectan por sus encabezados, no por el nombre):

| Hoja | Encabezados que necesita |
|---|---|
| Productos (`LISTA`) | `Material`, `Categoría`, `UD por CJ` |
| Compras | `CódigoCompra`, `FechaCompra`, `CodProducto` (la columna `RUC` del reporte no se copia) |
| Clientes | `DIA`, `CLIENTE`, `CEP`, `CODIGO SISTEMA`, `CLIENTES DE ADC`; los encabezados de categorías están en la fila inmediatamente superior |

## Estructura del proyecto

El código usa **composición** (clases pequeñas que se combinan, sin herencia), con nombres y funciones
en español. `principal.py` arma todas las piezas.

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

- **Los archivos Excel se editan a nivel XML.** Guardar la plantilla con `openpyxl` eliminaría las
  segmentaciones de la tabla dinámica; por eso solo se reescribe la hoja necesaria dentro del `.xlsx`.
  La tabla dinámica se actualiza sola al abrir el archivo en Excel.
- En Windows, si el archivo de salida está abierto en Excel, no se puede sobrescribir: ciérralo antes
  de volver a cargar el reporte o exportar con el mismo nombre.
- Los Excel de la empresa (plantilla y reportes) y el logo no deberían subirse a un repositorio público;
  el `.gitignore` incluido excluye los Excel de la empresa (plantilla, reportes y archivos generados).
