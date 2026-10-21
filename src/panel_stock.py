"""Panel lateral: cada producto muestra existencias en cajas/unidades o bultos."""
from tkinter import ttk


COLUMNAS = (
    ("producto", "Producto", 215, "w"),
    ("disponibles", "Comprado", 155, "e"),
    ("asignadas", "Asignado", 155, "e"),
    ("restantes", "Restante", 155, "e"),
)


class PanelStock:
    def __init__(self, padre):
        self.marco = ttk.LabelFrame(
            padre, text="  Stock de compras · resumen semanal  ", padding=(12, 14), style="Stock.TLabelframe"
        )
        self.marco.columnconfigure(0, weight=1)
        self.marco.rowconfigure(0, weight=1)
        zona_tabla = ttk.Frame(self.marco, style="Card.TFrame")
        zona_tabla.grid(row=0, column=0, sticky="nsew")
        zona_tabla.columnconfigure(0, weight=1)
        zona_tabla.rowconfigure(0, weight=1)
        self.tabla = ttk.Treeview(
            zona_tabla, columns=[c[0] for c in COLUMNAS], show="headings", height=16, selectmode="none"
        )
        barra_v = ttk.Scrollbar(zona_tabla, orient="vertical", command=self.tabla.yview, style="Vertical.TScrollbar")
        barra_h = ttk.Scrollbar(zona_tabla, orient="horizontal", command=self.tabla.xview, style="Horizontal.TScrollbar")
        self.tabla.configure(yscrollcommand=barra_v.set, xscrollcommand=barra_h.set)
        for nombre, titulo, ancho, alineacion in COLUMNAS:
            self.tabla.heading(nombre, text=titulo)
            self.tabla.column(nombre, width=ancho, minwidth=85, anchor=alineacion, stretch=(nombre == "producto"))
        self.tabla.tag_configure("alterno", background="#F8FAFD")
        self.tabla.tag_configure("exceso", background="#FFF1F0", foreground="#B42318")
        self.tabla.tag_configure("completo", background="#ECFDF3", foreground="#067647")
        self.tabla.grid(row=0, column=0, sticky="nsew")
        barra_v.grid(row=0, column=1, sticky="ns")
        barra_h.grid(row=1, column=0, sticky="ew")
        self._barra_vertical = barra_v
        self._barra_horizontal = barra_h
        ttk.Separator(self.marco, orient="horizontal").grid(row=1, column=0, sticky="ew", pady=(12, 10))
        self.etiqueta_totales = ttk.Label(
            self.marco, text="Cargue un reporte para ver las existencias.",
            justify="left", wraplength=510, style="StockSummary.TLabel"
        )
        self.etiqueta_totales.grid(row=2, column=0, sticky="ew")

    def mostrar(self, filas, totales) -> None:
        self.tabla.delete(*self.tabla.get_children())
        for indice, fila in enumerate(filas):
            if fila.restantes_unidades < 0:
                etiqueta = ("exceso",)
            elif fila.restantes_unidades == 0:
                etiqueta = ("completo",)
            elif indice % 2:
                etiqueta = ("alterno",)
            else:
                etiqueta = ()
            self.tabla.insert(
                "", "end", tags=etiqueta,
                values=(fila.descripcion, fila.disponibles, fila.asignadas, fila.restantes)
            )
        if len(filas) > 16:
            self._barra_vertical.grid()
        else:
            self._barra_vertical.grid_remove()
        self._barra_horizontal.grid()

        if not filas or totales is None:
            self.etiqueta_totales.config(text="Cargue un reporte para ver las existencias.")
            return
        def medida(detalle):
            partes = []
            if detalle.get("cajas"):
                partes.append(f"{detalle['cajas']:,} cj completas")
            if detalle.get("unidades"):
                partes.append(f"{detalle['unidades']:,} und sueltas")
            if detalle.get("bultos"):
                partes.append(f"{detalle['bultos']:,} bultos")
            if detalle.get("exceso_bultos"):
                partes.append(f"exceso de {detalle['exceso_bultos']:,} bultos")
            if detalle.get("exceso_unidades"):
                partes.append(f"exceso de {detalle['exceso_unidades']:,} und")
            return " · ".join(partes) if partes else "0"
        self.etiqueta_totales.config(
            text=(f"{totales.productos} productos en esta categoría\n"
                  f"Comprado: {medida(totales.detalle_disponibles)}\n"
                  f"Asignado: {medida(totales.detalle_asignadas)}\n"
                  f"Restante: {medida(totales.detalle_restantes)}\n"
                  "Factor = 1: bulto sin conversión · rojo: exceso asignado · verde: saldo cero.")
        )
