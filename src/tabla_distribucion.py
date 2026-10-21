"""Tabla moderna y editable de distribución: una fila por cliente."""
import tkinter as tk
from tkinter import ttk

from configuracion import MODO_BULTO, MODO_CAJA, MODO_UNIDAD
from utilidades import texto_a_entero


FONDO = "#FFFFFF"
FILA_ALTERNA = "#F8FAFD"
COLOR_TEXTO = "#172033"
COLOR_SECUNDARIO = "#627089"
COLOR_ENCABEZADO = "#EFF4FB"
COLOR_ALERTA = "#B42318"


class TablaDistribucion:
    COLUMNA_CLIENTE = 0
    COLUMNA_CANTIDAD = 1
    COLUMNA_MODO = 2
    COLUMNA_NEVERA = 3

    def __init__(self, padre, distribucion, al_cambiar_datos):
        self.distribucion = distribucion
        self.al_cambiar_datos = al_cambiar_datos
        self.producto = None
        self._filas = []  # dict con cliente, cantidad y variable_modo
        self._reconstruyendo = False

        self.marco = ttk.Frame(padre, style="CardBorder.TFrame", padding=0)
        self.marco.columnconfigure(0, weight=1)
        self.marco.rowconfigure(2, weight=1)

        self.cabecera = ttk.Frame(self.marco, style="Card.TFrame", padding=(17, 14, 17, 12))
        self.cabecera.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.cabecera.columnconfigure(0, weight=1)
        ttk.Label(
            self.cabecera, text="Distribución por cliente", style="SectionTitle.TLabel"
        ).grid(row=0, column=0, sticky="w")
        self.etiqueta_producto = ttk.Label(
            self.cabecera, text="Sin alimento seleccionado", style="Pill.TLabel", wraplength=360
        )
        self.etiqueta_producto.grid(row=0, column=1, sticky="e", padx=(10, 0))
        self.etiqueta_ayuda = ttk.Label(
            self.cabecera, text="Edite la cantidad y seleccione CAJA o UNIDAD para cada cliente.",
            style="Muted.TLabel"
        )
        self.etiqueta_ayuda.grid(row=1, column=0, sticky="w", pady=(5, 0))
        self.etiqueta_conteo = ttk.Label(self.cabecera, text="0 clientes", style="Muted.TLabel")
        self.etiqueta_conteo.grid(row=1, column=1, sticky="e", pady=(5, 0))
        ttk.Separator(self.marco, orient="horizontal").grid(row=1, column=0, columnspan=2, sticky="ew")

        self.lienzo = tk.Canvas(self.marco, highlightthickness=0, background=FONDO, bd=0)
        self.barra_vertical = ttk.Scrollbar(
            self.marco, orient="vertical", command=self.lienzo.yview, style="Vertical.TScrollbar"
        )
        self.barra_horizontal = ttk.Scrollbar(
            self.marco, orient="horizontal", command=self.lienzo.xview, style="Horizontal.TScrollbar"
        )
        self.lienzo.configure(yscrollcommand=self.barra_vertical.set,
                              xscrollcommand=self.barra_horizontal.set)
        self.interior = ttk.Frame(self.lienzo, style="Card.TFrame")
        self._id_interior = self.lienzo.create_window((0, 0), window=self.interior, anchor="nw")
        self.interior.bind("<Configure>", self._actualizar_region)
        self.lienzo.bind("<Configure>", self._ajustar_ancho_interior)
        self.lienzo.bind_all("<MouseWheel>", self._girar_rueda, add="+")
        self.lienzo.grid(row=2, column=0, sticky="nsew")
        self.barra_vertical.grid(row=2, column=1, sticky="ns")
        self.barra_horizontal.grid(row=3, column=0, sticky="ew")
        self.marco.columnconfigure(0, weight=1)
        self._reconstruir()

    # ---------- uso desde fuera ----------
    def mostrar_producto(self, producto) -> None:
        self.producto = producto
        self._reconstruir()

    def refrescar(self) -> None:
        """Actualiza las cantidades y modos visibles después de operaciones globales."""
        if self._reconstruyendo or self.producto is None:
            return
        for fila in self._filas:
            cliente = fila["cliente"]
            cantidad = self.distribucion.cantidad_de(cliente, self.producto.codigo)
            self._poner_texto(fila["cantidad"], str(cantidad) if cantidad else "")
            fila["variable_modo"].set(self.distribucion.modo_de(cliente, self.producto))
        self._actualizar_neveras()

    def confirmar_celdas(self) -> None:
        """Guarda lo que haya escrito en las celdas (útil antes de cambiar de alimento o exportar)."""
        for fila in self._filas:
            self._confirmar_cantidad(fila["cliente"], fila["cantidad"])

    def enfocar_primera_celda(self) -> None:
        if self._filas:
            self._filas[0]["cantidad"].focus_set()
            self._filas[0]["cantidad"].selection_range(0, "end")

    # ---------- construcción ----------
    def _reconstruir(self) -> None:
        self._reconstruyendo = True
        for hijo in self.interior.winfo_children():
            hijo.destroy()
        self._filas = []
        cantidad_clientes = len(self.distribucion.clientes)
        self.etiqueta_conteo.config(text=f"{cantidad_clientes} cliente" + ("" if cantidad_clientes == 1 else "s"))

        if self.producto is None:
            self.etiqueta_producto.config(text="Sin alimento seleccionado")
            self._mostrar_estado(
                "Seleccione un alimento",
                "Cargue el reporte general y elija un producto en la barra de herramientas."
            )
        elif not self.distribucion.clientes:
            nombre = self.producto.descripcion or str(self.producto.codigo)
            self.etiqueta_producto.config(text=nombre)
            self._mostrar_estado(
                "No hay clientes para este día",
                "Seleccione otro día o actualice la lista de clientes de la plantilla."
            )
        else:
            nombre_producto = self.producto.descripcion or str(self.producto.codigo)
            unidades_caja = max(1, int(self.producto.unidades_por_caja or 1))
            if self.producto.es_bulto:
                detalle_unidad = "bulto · sin conversión"
            elif self.producto.solo_cajas:
                detalle_unidad = f"{unidades_caja} unidades/caja · Pepsi se reporta por caja"
            else:
                detalle_unidad = f"{unidades_caja} unidades por caja"
            self.etiqueta_producto.config(text=f"{nombre_producto}  ·  {detalle_unidad}")

            self._crear_encabezado(self.COLUMNA_CLIENTE, "CLIENTE")
            self._crear_encabezado(
                self.COLUMNA_CANTIDAD, f"CANTIDAD  ·  {nombre_producto}\n({detalle_unidad})"
            )
            self._crear_encabezado(self.COLUMNA_MODO, "REPORTAR POR")
            self._crear_encabezado(self.COLUMNA_NEVERA, "NEVERA (ADC)\nrefrescos asignados / cuota")

            for numero, cliente in enumerate(self.distribucion.clientes, start=1):
                fondo_fila = FONDO if numero % 2 else FILA_ALTERNA
                etiqueta_cliente = tk.Label(
                    self.interior, text=cliente.nombre, anchor="w", justify="left",
                    font=("Segoe UI", 10), fg=COLOR_TEXTO, bg=fondo_fila,
                    padx=12, pady=8, bd=0, highlightthickness=0
                )
                etiqueta_cliente.grid(
                    row=numero, column=self.COLUMNA_CLIENTE,
                    sticky="nsew", padx=(0, 0), pady=1
                )

                valor = self.distribucion.cantidad_de(cliente, self.producto.codigo)
                entrada = ttk.Entry(self.interior, width=13, justify="right", style="Table.TEntry")
                entrada.insert(0, str(valor) if valor else "")
                entrada.bind("<FocusOut>", lambda e, c=cliente, w=entrada: self._confirmar_cantidad(c, w))
                entrada.bind("<Return>", lambda e, n=numero - 1: self._mover_cantidad(n + 1))
                entrada.bind("<Down>", lambda e, n=numero - 1: self._mover_cantidad(n + 1))
                entrada.bind("<Up>", lambda e, n=numero - 1: self._mover_cantidad(n - 1))
                entrada.bind("<Control-d>", lambda e, n=numero - 1: self._copiar_de_arriba(n))
                entrada.bind("<Control-v>", lambda e, n=numero - 1: self._pegar_columna(n))
                entrada.bind("<FocusIn>", lambda e: e.widget.after_idle(lambda w=e.widget: self._seleccionar_todo(w)))
                entrada.grid(
                    row=numero, column=self.COLUMNA_CANTIDAD,
                    sticky="nsew", padx=8, pady=4
                )

                modos_permitidos = self.distribucion.modos_permitidos(cliente, self.producto)
                variable_modo = tk.StringVar(value=self.distribucion.modo_de(cliente, self.producto))
                desplegable = ttk.Combobox(
                    self.interior, values=modos_permitidos, textvariable=variable_modo,
                    state="readonly", width=12, style="Table.TCombobox"
                )
                desplegable.bind(
                    "<<ComboboxSelected>>",
                    lambda e, c=cliente, v=variable_modo: self._cambiar_modo(c, v.get())
                )
                desplegable.bind("<Key>", lambda e, c=cliente, v=variable_modo: self._tecla_en_modo(e, c, v))
                desplegable.grid(
                    row=numero, column=self.COLUMNA_MODO,
                    sticky="ew", padx=(8, 12), pady=4
                )
                etiqueta_nevera = tk.Label(
                    self.interior, text="", anchor="w", justify="left", font=("Segoe UI", 9),
                    fg=COLOR_SECUNDARIO, bg=fondo_fila, padx=10, pady=8, bd=0, highlightthickness=0
                )
                etiqueta_nevera.grid(row=numero, column=self.COLUMNA_NEVERA, sticky="nsew", pady=1)
                self._filas.append({
                    "cliente": cliente,
                    "cantidad": entrada,
                    "variable_modo": variable_modo,
                    "desplegable": desplegable,
                    "nevera": etiqueta_nevera,
                })

            self.interior.columnconfigure(self.COLUMNA_CLIENTE, weight=1, minsize=230)
            self.interior.columnconfigure(self.COLUMNA_CANTIDAD, weight=0, minsize=180)
            self.interior.columnconfigure(self.COLUMNA_MODO, weight=0, minsize=155)
            self.interior.columnconfigure(self.COLUMNA_NEVERA, weight=0, minsize=230)
            self._actualizar_neveras()

        self._reconstruyendo = False
        self._actualizar_region()

    def _mostrar_estado(self, titulo, mensaje) -> None:
        contenedor = ttk.Frame(self.interior, style="Card.TFrame", padding=(28, 32))
        contenedor.grid(row=0, column=0, columnspan=4, sticky="nsew")
        ttk.Label(
            contenedor, text=titulo, style="SectionTitle.TLabel"
        ).pack(anchor="w")
        ttk.Label(
            contenedor, text=mensaje, style="Muted.TLabel", wraplength=600
        ).pack(anchor="w", pady=(7, 0))

    def _crear_encabezado(self, columna, texto) -> None:
        etiqueta = tk.Label(
            self.interior, text=texto, wraplength=260, justify="left" if columna == 0 else "center",
            anchor="w" if columna == 0 else "center", background=COLOR_ENCABEZADO,
            foreground="#34435D", font=("Segoe UI", 9, "bold"),
            padx=12, pady=11, borderwidth=0, highlightthickness=0
        )
        etiqueta.grid(row=0, column=columna, sticky="nsew", padx=(0, 1), pady=(0, 3))

    # ---------- datos ----------
    def _confirmar_cantidad(self, cliente, celda) -> None:
        if self._reconstruyendo or self.producto is None:
            return
        try:
            valor = texto_a_entero(celda.get())
            anterior = self.distribucion.cantidad_de(cliente, self.producto.codigo)
            if valor is None:
                self._poner_texto(celda, str(anterior) if anterior else "")
                celda.bell()
                return
            if valor != anterior:
                aplicado = self.distribucion.establecer_cantidad(cliente, self.producto.codigo, valor)
                self._actualizar_neveras()
                self.al_cambiar_datos()
            else:
                aplicado = anterior
            self._poner_texto(celda, str(aplicado) if aplicado else "")
        except tk.TclError:
            return

    def _actualizar_neveras(self) -> None:
        """Muestra, por cliente con nevera ADC, lo asignado de refrescos frente a su cuota."""
        for fila in self._filas:
            estado = self.distribucion.estado_nevera(fila["cliente"], self.producto)
            try:
                if estado is None:
                    fila["nevera"].config(text="", fg=COLOR_SECUNDARIO)
                else:
                    fila["nevera"].config(
                        text=estado.texto(), fg=COLOR_ALERTA if estado.hay_alerta else COLOR_SECUNDARIO)
            except tk.TclError:
                pass

    def _cambiar_modo(self, cliente, modo) -> None:
        if self.producto is None:
            return
        if modo not in self.distribucion.modos_permitidos(cliente, self.producto):
            modo = self.distribucion.modo_predeterminado(cliente, self.producto)
        modo_final = self.distribucion.fijar_modo(cliente, self.producto, modo)
        for fila in self._filas:
            if fila["cliente"].identificador == cliente.identificador:
                fila["variable_modo"].set(modo_final)
                break
        self._actualizar_neveras()
        self.al_cambiar_datos()

    def _tecla_en_modo(self, evento, cliente, variable):
        tecla = evento.keysym.lower()
        if tecla == "c":
            nuevo = MODO_CAJA
        elif tecla == "u":
            nuevo = MODO_UNIDAD
        elif tecla == "b":
            nuevo = MODO_BULTO
        elif tecla == "space":
            permitidos = self.distribucion.modos_permitidos(cliente, self.producto)
            indice = permitidos.index(variable.get()) if variable.get() in permitidos else 0
            nuevo = permitidos[(indice + 1) % len(permitidos)]
        else:
            return None
        if nuevo not in self.distribucion.modos_permitidos(cliente, self.producto):
            return "break"
        variable.set(nuevo)
        self._cambiar_modo(cliente, nuevo)
        return "break"

    def _mover_cantidad(self, indice):
        if self._filas:
            indice = max(0, min(indice, len(self._filas) - 1))
            self._filas[indice]["cantidad"].focus_set()
            self._filas[indice]["cantidad"].selection_range(0, "end")
        return "break"

    def _copiar_de_arriba(self, indice):
        if indice > 0 and indice < len(self._filas):
            anterior = self._filas[indice - 1]["cantidad"].get()
            actual = self._filas[indice]["cantidad"]
            self._poner_texto(actual, anterior)
            self._confirmar_cantidad(self._filas[indice]["cliente"], actual)
            self._seleccionar_todo(actual)
        return "break"

    def _pegar_columna(self, indice):
        """Permite pegar una columna de cantidades copiada desde Excel."""
        if self.producto is None or not self._filas:
            return "break"
        try:
            contenido = self.marco.clipboard_get()
        except tk.TclError:
            return "break"
        for desplazamiento, linea in enumerate(contenido.splitlines()):
            destino = indice + desplazamiento
            if destino >= len(self._filas):
                break
            texto = linea.split("\t")[0].strip()
            fila = self._filas[destino]
            self._poner_texto(fila["cantidad"], texto)
            self._confirmar_cantidad(fila["cliente"], fila["cantidad"])
        return "break"

    @staticmethod
    def _poner_texto(celda, texto) -> None:
        celda.delete(0, "end")
        celda.insert(0, texto)

    @staticmethod
    def _seleccionar_todo(celda) -> None:
        try:
            celda.selection_range(0, "end")
            celda.icursor("end")
        except tk.TclError:
            pass

    # ---------- desplazamiento ----------
    def _actualizar_region(self, _evento=None) -> None:
        try:
            self.lienzo.configure(scrollregion=self.lienzo.bbox("all"))
            self.lienzo.after_idle(self._actualizar_barras)
        except tk.TclError:
            pass

    def _actualizar_barras(self) -> None:
        """Oculta las barras que no hacen falta para evitar controles vacíos."""
        try:
            caja = self.lienzo.bbox("all")
            if not caja:
                necesita_x = necesita_y = False
            else:
                ancho_contenido = caja[2] - caja[0]
                alto_contenido = caja[3] - caja[1]
                necesita_x = ancho_contenido > self.lienzo.winfo_width() + 2
                necesita_y = alto_contenido > self.lienzo.winfo_height() + 2
            if necesita_y:
                self.barra_vertical.grid()
            else:
                self.barra_vertical.grid_remove()
            if necesita_x:
                self.barra_horizontal.grid()
            else:
                self.barra_horizontal.grid_remove()
        except tk.TclError:
            pass

    def _ajustar_ancho_interior(self, evento) -> None:
        """Hace que la tabla ocupe el ancho visible sin perder el scroll horizontal."""
        try:
            ancho_necesario = self.interior.winfo_reqwidth()
            self.lienzo.itemconfigure(self._id_interior, width=max(evento.width, ancho_necesario))
        except tk.TclError:
            pass

    def _girar_rueda(self, evento) -> None:
        try:
            if self.lienzo.winfo_exists():
                self.lienzo.yview_scroll(-1 if evento.delta > 0 else 1, "units")
        except tk.TclError:
            pass
