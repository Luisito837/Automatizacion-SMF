"""Ventana principal de ROCO; distribución por cliente, con búsqueda y recuperación de guardados."""
import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from barra_herramientas import BarraHerramientas
from barra_superior import BarraSuperior
from catalogo_plantilla import CatalogoClientes, LectorPlantilla
from configuracion import RUTA_FACTORES, RUTA_LOGO, RUTA_PLANTILLA, MODO_BULTO, MODO_CAJA, MODO_UNIDAD
from distribucion import Distribucion
from exportador_plantilla import ExportadorPlantilla
from inventario import ConstructorInventario, Inventario
from panel_stock import PanelStock
from procesador_reporte import ProcesadorReporte
from tabla_distribucion import TablaDistribucion
from utilidades import normalizar_codigo, normalizar_texto, obtener_dia_actual, texto_a_entero


class VentanaPrincipal:
    def __init__(self, raiz, procesador: ProcesadorReporte, lector_plantilla: LectorPlantilla,
                 exportador: ExportadorPlantilla):
        self.raiz = raiz
        self.procesador = procesador
        self.lector_plantilla = lector_plantilla
        self.exportador = exportador
        self.ruta_plantilla_generada = None
        self.distribucion = Distribucion(Inventario())
        self.catalogo_clientes = CatalogoClientes()
        self.ruta_plantilla = RUTA_PLANTILLA if RUTA_PLANTILLA.exists() else None
        self._productos_por_opcion = {}
        self._productos_globales_por_opcion = {}
        self._categoria_activa = None

        raiz.title("ROCO · Distribución de compras por cliente")
        raiz.geometry("1480x900")
        raiz.minsize(1080, 700)
        try:
            raiz.state("zoomed")
        except tk.TclError:
            pass
        self._armar_pantalla()
        self._vincular_teclas_de_producto()
        self._cargar_clientes()
        recuperado = False
        if self.ruta_plantilla and self.ruta_plantilla.exists():
            recuperado = self._recuperar_plantilla(self.ruta_plantilla, silencioso=True)
        if not recuperado:
            self._cargar_lista_productos()
        self.tabla.mostrar_producto(self._producto_seleccionado())
        self._actualizar_stock()

    # ---------- armado de la interfaz ----------
    def _armar_pantalla(self) -> None:
        self.raiz.columnconfigure(0, weight=1)
        self.raiz.rowconfigure(2, weight=1)
        self.barra_superior = BarraSuperior(
            self.raiz, RUTA_LOGO, obtener_dia_actual(), self._al_cambiar_dia,
            self._cargar_reporte, self._abrir_guardado, self._recargar_clientes,
            self._ver_clientes, self._exportar_plantilla
        )
        self.barra_herramientas = BarraHerramientas(
            self.raiz, self._al_cambiar_categoria, self._al_cambiar_producto,
            self._aplicar_valor_global, self._autorrellenar, self._autorrellenar_categoria,
            self._limpiar_todo, self._reportar_todo_como, self._editar_factores,
            self._resumen_semanal
        )

        cuerpo = ttk.Frame(self.raiz, padding=(16, 12, 16, 8))
        cuerpo.columnconfigure(0, weight=1)
        cuerpo.columnconfigure(1, weight=0)
        cuerpo.rowconfigure(0, weight=1)
        self.tabla = TablaDistribucion(cuerpo, self.distribucion, self._actualizar_stock)
        self.panel_stock = PanelStock(cuerpo)
        self.tabla.marco.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self.panel_stock.marco.grid(row=0, column=1, sticky="nsew")

        self.barra_superior.marco.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 0))
        self.barra_herramientas.marco.grid(row=1, column=0, sticky="ew", padx=16, pady=(10, 0))
        cuerpo.grid(row=2, column=0, sticky="nsew")

        pie = ttk.Frame(self.raiz, style="Footer.TFrame", padding=(18, 2, 18, 10))
        ttk.Label(pie, text="ROCO  ·  Distribución por cliente", style="Footer.TLabel").pack(side="left")
        ttk.Label(pie, text="El stock y las asignaciones reflejan toda la semana", style="Footer.TLabel").pack(side="right")
        pie.grid(row=3, column=0, sticky="ew")

    # ---------- compras e inventario ----------
    def _cargar_reporte(self) -> None:
        ruta_reporte = filedialog.askopenfilename(
            title="Seleccione el Reporte General de Compras",
            filetypes=[("Excel", "*.xlsx *.xlsm"), ("Todos los archivos", "*.*")],
        )
        if not ruta_reporte:
            return
        ruta_plantilla = self._obtener_ruta_plantilla()
        if not ruta_plantilla:
            return
        self.raiz.config(cursor="watch")
        self.raiz.update_idletasks()
        try:
            resultado = self.procesador.procesar(ruta_reporte, ruta_plantilla)
        except Exception as error:
            messagebox.showerror("No se pudo procesar el reporte", str(error))
            return
        finally:
            self.raiz.config(cursor="")

        self.ruta_plantilla_generada = resultado.ruta_salida
        self.distribucion.cargar_inventario(resultado.inventario)
        self._cargar_clientes()
        self._cargar_lista_productos()
        messagebox.showinfo("Reporte cargado", resultado.resumen())

    def _obtener_ruta_plantilla(self):
        if self.ruta_plantilla and self.ruta_plantilla.exists():
            return self.ruta_plantilla
        seleccion = filedialog.askopenfilename(
            title="Seleccione la plantilla FACTURACION SMF.xlsx",
            filetypes=[("Excel", "*.xlsx *.xlsm"), ("Todos los archivos", "*.*")],
        )
        if seleccion:
            self.ruta_plantilla = Path(seleccion)
        return self.ruta_plantilla

    def _cargar_lista_productos(self) -> None:
        """Genera categorías desde DescrCategoría del reporte y productos buscables por nombre/SKU."""
        producto_anterior = self._producto_seleccionado()
        codigo_anterior = normalizar_codigo(producto_anterior.codigo) if producto_anterior else ""
        categoria_anterior = self._categoria_activa
        productos = self.distribucion.inventario.todos()
        self._productos_globales_por_opcion = {}
        for producto in productos:
            descripcion = (producto.descripcion or str(producto.codigo)).strip()
            opcion = f"{descripcion} — {normalizar_codigo(producto.codigo)}"
            base = opcion
            contador = 2
            while opcion in self._productos_globales_por_opcion:
                opcion = f"{base} ({contador})"
                contador += 1
            self._productos_globales_por_opcion[opcion] = producto

        categorias = self.distribucion.inventario.categorias()
        self.barra_herramientas.poner_categorias(categorias, seleccionar=categoria_anterior)
        objetivo = self.barra_herramientas.categoria_seleccionada()
        self._al_cambiar_categoria(objetivo, enfocar=False, codigo_preferido=codigo_anterior)

    # ---------- búsqueda y filtros ----------
    def _al_cambiar_categoria(self, categoria, enfocar: bool = True, codigo_preferido: str = "") -> None:
        self._categoria_activa = categoria
        productos = (self.distribucion.inventario.todos() if categoria is None
                     else self.distribucion.inventario.productos_de_categoria(categoria))
        opciones = {}
        for opcion, producto in self._productos_globales_por_opcion.items():
            if any(producto is p for p in productos):
                opciones[opcion] = producto
        self._productos_por_opcion = opciones
        self.barra_herramientas.poner_productos(list(opciones))
        elegida = ""
        if codigo_preferido:
            elegida = next((op for op, prod in opciones.items()
                            if normalizar_codigo(prod.codigo) == codigo_preferido), "")
        if not elegida:
            elegida = next(iter(opciones), "")
        self.barra_herramientas.seleccionar_producto(elegida)
        self._al_cambiar_producto(elegida, enfocar=enfocar)

    def _producto_seleccionado(self):
        return self._productos_por_opcion.get(self.barra_herramientas.producto_seleccionado())

    def _al_cambiar_producto(self, opcion: str, enfocar: bool = True) -> None:
        producto = self._productos_por_opcion.get(opcion)
        self.tabla.mostrar_producto(producto)
        modos = (MODO_CAJA, MODO_UNIDAD, MODO_BULTO)
        if producto is not None:
            if producto.es_bulto:
                modos = (MODO_BULTO,)
            elif producto.solo_cajas:
                modos = (MODO_CAJA,)
            elif self.distribucion.clientes:
                modos = self.distribucion.modos_permitidos(self.distribucion.clientes[0], producto)
            else:
                modos = (MODO_CAJA, MODO_UNIDAD)
        self.barra_herramientas.actualizar_modos_permitidos(modos)
        self._actualizar_stock()
        if enfocar:
            self.tabla.enfocar_primera_celda()

    # ---------- clientes y día ----------
    def _cargar_clientes(self) -> None:
        if self.ruta_plantilla and self.ruta_plantilla.exists():
            try:
                self.catalogo_clientes = self.lector_plantilla.leer_clientes(self.ruta_plantilla)
            except Exception as error:
                self.catalogo_clientes = CatalogoClientes()
                messagebox.showwarning("Clientes", f"No se pudieron leer los clientes de la plantilla.\n{error}")
        self.distribucion.reemplazar_clientes(self.catalogo_clientes.todos())
        self._al_cambiar_dia(self.barra_superior.dia_seleccionado())

    def _recargar_clientes(self) -> None:
        self._cargar_clientes()

    def _al_cambiar_dia(self, dia: str) -> None:
        self.distribucion.seleccionar_dia(dia)
        self.barra_superior.mostrar_cantidad_de_clientes(len(self.distribucion.clientes))
        if hasattr(self, "tabla"):
            self.tabla.mostrar_producto(self._producto_seleccionado())
            self._actualizar_stock()

    def _ver_clientes(self) -> None:
        dia = self.barra_superior.dia_seleccionado()
        clientes = self.catalogo_clientes.del_dia(dia)
        ventana = tk.Toplevel(self.raiz)
        ventana.title(f"Clientes del {dia.lower()} ({len(clientes)})")
        ventana.geometry("720x500")
        ventana.minsize(560, 360)
        contenedor = ttk.Frame(ventana, padding=16)
        contenedor.pack(fill="both", expand=True)
        ttk.Label(contenedor, text=f"Clientes del {dia.lower()}", style="SectionTitle.TLabel").pack(anchor="w")
        ttk.Label(contenedor, text=f"{len(clientes)} clientes registrados en la plantilla", style="Muted.TLabel").pack(anchor="w", pady=(4, 12))
        tabla = ttk.Treeview(contenedor, columns=("cep", "cliente", "adc"), show="headings")
        for col, titulo, ancho in (("cep", "CEP", 100), ("cliente", "Cliente", 420), ("adc", "ADC", 90)):
            tabla.heading(col, text=titulo)
            tabla.column(col, width=ancho, anchor="w", stretch=(col == "cliente"))
        for cliente in clientes:
            adc = f"{cliente.puertas} PUERTA" if cliente.puertas else "—"
            tabla.insert("", "end", values=(cliente.cep, cliente.nombre, adc))
        tabla.pack(fill="both", expand=True)

    # ---------- abrir una plantilla ya guardada ----------
    def _abrir_guardado(self) -> None:
        ruta = filedialog.askopenfilename(
            title="Abrir una plantilla con compras y distribución guardadas",
            initialdir=str(self.ruta_plantilla.parent if self.ruta_plantilla else Path.cwd()),
            filetypes=[("Excel", "*.xlsx *.xlsm"), ("Todos los archivos", "*.*")],
        )
        if not ruta:
            return
        self.ruta_plantilla = Path(ruta)
        self._cargar_clientes()
        if not self._recuperar_plantilla(self.ruta_plantilla, silencioso=False):
            messagebox.showwarning(
                "No se encontró un guardado recuperable",
                "La plantilla no contiene compras válidas en su hoja de compras, o no hay productos que pasen el filtro."
            )

    def _recuperar_plantilla(self, ruta, silencioso: bool = False) -> bool:
        """Reconstruye inventario y asignaciones desde la plantilla exportada."""
        try:
            tabla_compras = self.procesador.lector_reporte.leer(ruta)
        except Exception:
            return False
        if not tabla_compras.filas:
            return False
        resultado_filtro = self.procesador.filtro.filtrar(tabla_compras)
        catalogo = self.lector_plantilla.leer_productos(ruta)
        resultado_inventario = ConstructorInventario(catalogo).construir(resultado_filtro.filas_conservadas)
        inventario = resultado_inventario.inventario
        if not inventario.todos():
            return False
        self.distribucion.cargar_inventario(inventario)
        self.ruta_plantilla_generada = Path(ruta)
        self._cargar_lista_productos()
        registros = self.exportador.leer_asignaciones_guardadas(ruta, inventario.todos())
        restauradas = self.distribucion.restaurar_asignaciones(registros)
        self.tabla.mostrar_producto(self._producto_seleccionado())
        self._actualizar_stock()
        if not silencioso:
            messagebox.showinfo(
                "Guardado recuperado",
                f"Compras leídas: {len(tabla_compras.filas)}\n"
                f"Productos en inventario: {inventario.cantidad_de_productos()}\n"
                f"Asignaciones recuperadas: {restauradas}\n\n"
                "Puede continuar desde este punto y volver a guardar el Excel."
            )
        return True

    # ---------- avanzar/retroceder rápidamente por producto ----------
    def _vincular_teclas_de_producto(self) -> None:
        for secuencia, paso in (("<Control-Right>", 1), ("<Next>", 1),
                                ("<Control-Left>", -1), ("<Prior>", -1)):
            self.raiz.bind_all(secuencia, lambda e, p=paso: self._mover_producto(p))

    def _mover_producto(self, paso: int) -> None:
        try:
            if isinstance(self.raiz.focus_get(), ttk.Combobox):
                return
        except (KeyError, tk.TclError):
            pass
        opciones = list(self._productos_por_opcion)
        actual = self.barra_herramientas.producto_seleccionado()
        indice = opciones.index(actual) if actual in opciones else -1
        nuevo = indice + paso
        if not opciones or nuevo < 0 or nuevo >= len(opciones):
            self.raiz.bell()
            return
        self.tabla.confirmar_celdas()
        self.barra_herramientas.seleccionar_producto(opciones[nuevo])
        self._al_cambiar_producto(opciones[nuevo])

    # ---------- guardar Excel ----------
    def _exportar_plantilla(self) -> None:
        self.tabla.confirmar_celdas()
        if not self.distribucion.inventario.todos():
            messagebox.showinfo("Sin compras", "Cargue un reporte de compras antes de guardar el Excel.")
            return
        asignaciones = self.distribucion.asignaciones()
        base = self.ruta_plantilla_generada
        if not (base and Path(base).exists()):
            base = self._obtener_ruta_plantilla()
        if not base:
            return
        base = Path(base)
        ruta = filedialog.asksaveasfilename(
            title="Guardar la plantilla con la distribución", defaultextension=".xlsx",
            initialdir=str(base.parent), initialfile=f"{base.stem}_distribucion.xlsx",
            filetypes=[("Excel", "*.xlsx")],
        )
        if not ruta:
            return
        try:
            resultado = self.exportador.exportar(base, asignaciones, Path(ruta))
        except Exception as error:
            messagebox.showerror("No se pudo guardar el Excel", str(error))
            return
        self.ruta_plantilla_generada = Path(ruta)
        messagebox.showinfo("Excel guardado", resultado.resumen())

    # ---------- operación diaria ----------
    def _listo_para_operar(self, exigir_producto: bool = True) -> bool:
        if exigir_producto and self._producto_seleccionado() is None:
            messagebox.showinfo("Falta el alimento", "Cargue el reporte general y elija una categoría/producto.")
            return False
        if not self.distribucion.clientes:
            messagebox.showinfo("No hay clientes", "No hay clientes para el día seleccionado en la plantilla.")
            return False
        if not self.distribucion.inventario.todos():
            messagebox.showinfo("No hay compras", "Cargue un reporte general de compras primero.")
            return False
        return True

    def _aplicar_valor_global(self, texto: str) -> None:
        if not self._listo_para_operar():
            return
        valor = texto_a_entero(texto)
        if valor is None:
            messagebox.showwarning("Valor no válido", "Escriba un número entero mayor o igual a 0.")
            return
        producto = self._producto_seleccionado()
        modificados = self.distribucion.establecer_valor_global(producto, valor)
        if modificados == 0:
            messagebox.showinfo("Sin stock", "El alimento seleccionado no tiene stock disponible.")
        self._refrescar_todo()

    def _autorrellenar(self) -> None:
        if self._listo_para_operar():
            self.distribucion.autorrellenar(self._producto_seleccionado())
            self._refrescar_todo()

    def _autorrellenar_categoria(self) -> None:
        if not self._listo_para_operar(exigir_producto=False):
            return
        categoria = self.barra_herramientas.categoria_seleccionada()
        if categoria is None and not messagebox.askyesno(
            "Completar todas las categorías", "¿Repartir el stock restante de todos los productos para los clientes de este día?"
        ):
            return
        if categoria is None:
            total = sum(self.distribucion.autorrellenar_categoria(cat) for cat in self.distribucion.inventario.categorias())
        else:
            total = self.distribucion.autorrellenar_categoria(categoria)
        self._refrescar_todo()
        messagebox.showinfo("Categoría completada", f"Se procesaron {total} productos, descontando lo ya asignado a otros días.")

    def _limpiar_todo(self) -> None:
        if not self._listo_para_operar():
            return
        producto = self._producto_seleccionado()
        nombre = producto.descripcion or str(producto.codigo)
        if messagebox.askyesno("Limpiar el día", f"¿Borrar la asignación de {nombre} para todos los clientes del día seleccionado?"):
            self.distribucion.limpiar(producto)
            self._refrescar_todo()

    def _reportar_todo_como(self, modo: str) -> None:
        if self._listo_para_operar():
            self.distribucion.fijar_modo_a_todos(self._producto_seleccionado(), modo)
            self._refrescar_todo()
            self.tabla.mostrar_producto(self._producto_seleccionado())

    def _refrescar_todo(self) -> None:
        self.tabla.refrescar()
        self._actualizar_stock()

    def _actualizar_stock(self) -> None:
        if not hasattr(self, "panel_stock"):
            return
        producto = self._producto_seleccionado()
        if producto is not None:
            categoria = producto.categoria_filtro
            filas = self.distribucion.filas_de_stock(categoria)
            totales = self.distribucion.totales_de_categoria(categoria)
        else:
            filas, totales = [], None
        self.panel_stock.mostrar(filas, totales)

    # ---------- factores de conversión editables ----------
    def _editar_factores(self) -> None:
        productos = self.distribucion.inventario.todos()
        if not productos:
            messagebox.showinfo("Factores de conversión", "Cargue un reporte de compras primero.")
            return
        ventana = tk.Toplevel(self.raiz)
        ventana.title("Factores de conversión · catálogo de alimentos")
        ventana.geometry("920x590")
        ventana.minsize(760, 450)
        ventana.transient(self.raiz)
        contenedor = ttk.Frame(ventana, padding=16)
        contenedor.pack(fill="both", expand=True)
        ttk.Label(contenedor, text="Factores de conversión", style="SectionTitle.TLabel").pack(anchor="w")
        ttk.Label(
            contenedor, text="El factor se carga de LISTA → UD por CJ. Doble clic sobre Factor para corregirlo; 1 significa bulto.",
            style="Muted.TLabel"
        ).pack(anchor="w", pady=(4, 10))
        variable_busqueda = tk.StringVar()
        fila_busqueda = ttk.Frame(contenedor)
        fila_busqueda.pack(fill="x", pady=(0, 8))
        ttk.Label(fila_busqueda, text="Buscar alimento o SKU:").pack(side="left", padx=(0, 8))
        buscador = ttk.Entry(fila_busqueda, textvariable=variable_busqueda)
        buscador.pack(side="left", fill="x", expand=True)
        columnas = ("codigo", "producto", "categoria", "factor", "tipo")
        tabla = ttk.Treeview(contenedor, columns=columnas, show="headings", height=18)
        for col, titulo, ancho, anchor in (
            ("codigo", "Código", 105, "w"), ("producto", "Producto", 380, "w"),
            ("categoria", "Categoría reporte", 155, "w"), ("factor", "Factor", 70, "center"),
            ("tipo", "Tratamiento", 110, "w"),
        ):
            tabla.heading(col, text=titulo)
            tabla.column(col, width=ancho, anchor=anchor, stretch=(col == "producto"))
        tabla.pack(fill="both", expand=True)
        producto_por_id = {}

        def llenar(*_args):
            tabla.delete(*tabla.get_children())
            producto_por_id.clear()
            busqueda = normalizar_texto(variable_busqueda.get())
            for indice, producto in enumerate(productos):
                etiqueta = f"{producto.codigo} {producto.descripcion} {producto.categoria_filtro}"
                if busqueda and busqueda not in normalizar_texto(etiqueta):
                    continue
                iid = f"p{indice}"
                tipo = "BULTO" if producto.es_bulto else ("SOLO CAJA" if producto.solo_cajas else "CAJA / UNIDAD")
                tabla.insert("", "end", iid=iid, values=(producto.codigo, producto.descripcion,
                              producto.categoria_filtro, producto.factor, tipo))
                producto_por_id[iid] = producto

        def editar_factor(evento):
            region = tabla.identify("region", evento.x, evento.y)
            columna = tabla.identify_column(evento.x)
            iid = tabla.identify_row(evento.y)
            if region != "cell" or columna != "#4" or not iid or iid not in producto_por_id:
                return
            producto = producto_por_id[iid]
            factor = simpledialog.askinteger(
                "Editar factor", f"Unidades por caja para {producto.descripcion}\n\n1 = bulto sin conversión",
                parent=ventana, initialvalue=producto.factor, minvalue=1, maxvalue=999
            )
            if factor is None or factor == producto.factor:
                return
            try:
                self.distribucion.inventario.cambiar_factor(producto.codigo, factor)
                guardados = {}
                if Path(RUTA_FACTORES).exists():
                    try:
                        guardados = json.loads(Path(RUTA_FACTORES).read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        guardados = {}
                guardados[normalizar_codigo(producto.codigo)] = factor
                Path(RUTA_FACTORES).write_text(json.dumps(guardados, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception as error:
                messagebox.showerror("No se pudo cambiar el factor", str(error), parent=ventana)
                return
            llenar()
            self._cargar_lista_productos()
            self.tabla.mostrar_producto(self._producto_seleccionado())
            self._actualizar_stock()

        variable_busqueda.trace_add("write", llenar)
        tabla.bind("<Double-Button-1>", editar_factor)
        ttk.Button(contenedor, text="Cerrar", style="Secondary.TButton", command=ventana.destroy).pack(anchor="e", pady=(10, 0))
        llenar()
        buscador.focus_set()

    # ---------- control de cierre semanal ----------
    def _resumen_semanal(self) -> None:
        filas = self.distribucion.resumen_semanal()
        if not filas:
            messagebox.showinfo("Resumen semanal", "Cargue un reporte de compras primero.")
            return
        ventana = tk.Toplevel(self.raiz)
        ventana.title("Resumen semanal · avance hacia saldo cero")
        ventana.geometry("1160x620")
        ventana.minsize(900, 480)
        marco = ttk.Frame(ventana, padding=16)
        marco.pack(fill="both", expand=True)
        ttk.Label(marco, text="Resumen semanal de inventario", style="SectionTitle.TLabel").pack(anchor="w")
        ttk.Label(marco, text="Las cantidades asignadas incluyen todos los días, no solo el día visible.", style="Muted.TLabel").pack(anchor="w", pady=(3, 10))
        columnas = ("categoria", "codigo", "producto", "disponible", "asignado", "restante")
        tabla = ttk.Treeview(marco, columns=columnas, show="headings", height=20)
        for col, title, width, anchor in (
            ("categoria", "Categoría", 125, "w"), ("codigo", "SKU", 95, "w"),
            ("producto", "Producto", 270, "w"), ("disponible", "Comprado", 160, "e"),
            ("asignado", "Asignado", 160, "e"), ("restante", "Saldo", 160, "e"),
        ):
            tabla.heading(col, text=title)
            tabla.column(col, width=width, minwidth=70, anchor=anchor, stretch=(col == "producto"))
        tabla.tag_configure("cero", background="#ECFDF3", foreground="#067647")
        tabla.tag_configure("pendiente", background="#FFFAEB", foreground="#92400E")
        tabla.tag_configure("exceso", background="#FFF1F0", foreground="#B42318")
        tabla.pack(fill="both", expand=True)
        for fila in filas:
            restante = fila["restantes_base"]
            tag = "cero" if restante == 0 else ("exceso" if restante < 0 else "pendiente")
            tabla.insert("", "end", tags=(tag,), values=(fila["categoria"], fila["codigo"], fila["producto"],
                          fila["disponible"], fila["asignado"], fila["restante"]))
        cero = sum(1 for f in filas if f["restantes_base"] == 0)
        pendiente = sum(1 for f in filas if f["restantes_base"] > 0)
        exceso = sum(1 for f in filas if f["restantes_base"] < 0)
        ttk.Label(
            marco, text=f"Saldo cero: {cero} SKU   ·   Con remanente: {pendiente}   ·   Sobreasignados: {exceso}",
            style="StockSummary.TLabel"
        ).pack(anchor="w", pady=(10, 0))
