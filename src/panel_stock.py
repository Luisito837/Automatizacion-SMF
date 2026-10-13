"""Panel lateral de existencias con jerarquía visual y estados de stock."""
from tkinter import ttk


COLUMNAS = (
    ("producto", "Producto", 160, "w"),
    ("disponibles", "Disponible", 82, "e"),
    ("asignadas", "Asignado", 82, "e"),
    ("restantes", "Restante", 82, "e"),
)


class PanelStock:
    def __init__(self, padre):
        self.marco = ttk.LabelFrame(
            padre, text="  Stock de la categoría  ", padding=(12, 14), style="Stock.TLabelframe"
        )
        self.marco.columnconfigure(0, weight=1)
        self.marco.rowconfigure(0, weight=1)

        zona_tabla = ttk.Frame(self.marco, style="Card.TFrame")
        zona_tabla.grid(row=0, column=0, sticky="nsew")
        zona_tabla.columnconfigure(0, weight=1)
        zona_tabla.rowconfigure(0, weight=1)
        self.tabla = ttk.Treeview(
            zona_tabla, columns=[c[0] for c in COLUMNAS],
            show="headings", height=16, selectmode="none"
        )
        barra = ttk.Scrollbar(
            zona_tabla, orient="vertical", command=self.tabla.yview, style="Vertical.TScrollbar"
        )
        self.tabla.configure(yscrollcommand=barra.set)
        for nombre, titulo, ancho, alineacion in COLUMNAS:
            self.tabla.heading(nombre, text=titulo)
            self.tabla.column(
                nombre, width=ancho, minwidth=60, anchor=alineacion,
                stretch=(nombre == "producto")
            )
        self.tabla.tag_configure("alterno", background="#F8FAFD")
        self.tabla.tag_configure("exceso", background="#FFF1F0", foreground="#B42318")
        self.tabla.tag_configure("completo", background="#ECFDF3", foreground="#067647")
        self.tabla.grid(row=0, column=0, sticky="nsew")
        self._barra_vertical = barra
        barra.grid(row=0, column=1, sticky="ns")
        barra.grid_remove()

        ttk.Separator(self.marco, orient="horizontal").grid(row=1, column=0, sticky="ew", pady=(12, 10))
        self.etiqueta_totales = ttk.Label(
            self.marco, text="", justify="left", wraplength=400, style="StockSummary.TLabel"
        )
        self.etiqueta_totales.grid(row=2, column=0, sticky="ew")

    def mostrar(self, filas, totales) -> None:
        """'filas' son FilaStock y 'totales' es un ResumenStock (en unidades)."""
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

        if filas:
            self.etiqueta_totales.config(
                text=(f"TOTAL EN UNIDADES\nDisponibles: {totales.disponibles:,}    "
                      f"Asignadas: {totales.asignadas:,}    Restantes: {totales.restantes:,}\n"
                      "Rojo: excedente asignado.  Verde: stock distribuido.")
            )
        else:
            self.etiqueta_totales.config(text="Cargue un reporte para ver las existencias.")
