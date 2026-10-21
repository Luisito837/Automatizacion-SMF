"""Punto de entrada de ROCO y tema visual inspirado en Windows 11."""
import tkinter as tk
from tkinter import ttk

from catalogo_plantilla import LectorPlantilla
from escritor_plantilla import EscritorPlantilla
from exportador_plantilla import ExportadorPlantilla
from filtro_compras import FiltroCompras, ReglasFiltro
from lector_excel import LectorExcel, LectorReporteCompras
from procesador_reporte import ProcesadorReporte
from ventana_principal import VentanaPrincipal


# Paleta clara y sobria, con azul ROCO como color de acento.
COLORES = {
    "fondo": "#F3F6FC",
    "superficie": "#FFFFFF",
    "borde": "#DCE4F0",
    "texto": "#172033",
    "secundario": "#627089",
    "azul": "#2563EB",
    "azul_hover": "#1D4ED8",
    "azul_suave": "#EAF1FF",
    "rojo": "#B42318",
    "rojo_suave": "#FFF1F0",
    "verde": "#067647",
    "verde_suave": "#ECFDF3",
    "fila_alterna": "#F8FAFD",
    "encabezado_tabla": "#EFF4FB",
}


def configurar_tema_roco(raiz: tk.Tk) -> None:
    """Configura ttk con una apariencia moderna y consistente tipo Windows 11."""
    estilo = ttk.Style(raiz)
    try:
        estilo.theme_use("clam")
    except tk.TclError:
        pass

    raiz.configure(background=COLORES["fondo"])
    fuente = ("Segoe UI", 10)
    estilo.configure(".", font=fuente, foreground=COLORES["texto"])
    estilo.configure("TFrame", background=COLORES["fondo"])
    estilo.configure("TLabel", background=COLORES["fondo"], foreground=COLORES["texto"])
    estilo.configure("TSeparator", background=COLORES["borde"])

    # Superficies y jerarquía de texto.
    estilo.configure("Card.TFrame", background=COLORES["superficie"])
    estilo.configure("CardBorder.TFrame", background=COLORES["superficie"],
                     borderwidth=1, relief="solid", bordercolor=COLORES["borde"])
    estilo.configure("HeaderCard.TFrame", background=COLORES["superficie"],
                     borderwidth=1, relief="solid", bordercolor=COLORES["borde"])
    estilo.configure("ToolbarCard.TFrame", background=COLORES["superficie"],
                     borderwidth=1, relief="solid", bordercolor=COLORES["borde"])
    estilo.configure("Header.TFrame", background=COLORES["superficie"])
    estilo.configure("Header.TLabel", background=COLORES["superficie"], foreground=COLORES["texto"])
    estilo.configure("Toolbar.TFrame", background=COLORES["superficie"])
    estilo.configure("Inner.TFrame", background=COLORES["superficie"])
    estilo.configure("Footer.TFrame", background=COLORES["fondo"])
    estilo.configure("HeaderTitle.TLabel", background=COLORES["superficie"],
                     foreground=COLORES["texto"], font=("Segoe UI", 19, "bold"))
    estilo.configure("HeaderSubtitle.TLabel", background=COLORES["superficie"],
                     foreground=COLORES["secundario"], font=("Segoe UI", 9))
    estilo.configure("SectionTitle.TLabel", background=COLORES["superficie"],
                     foreground=COLORES["texto"], font=("Segoe UI", 12, "bold"))
    estilo.configure("Muted.TLabel", background=COLORES["superficie"],
                     foreground=COLORES["secundario"], font=("Segoe UI", 9))
    estilo.configure("Pill.TLabel", background=COLORES["azul_suave"],
                     foreground=COLORES["azul"], padding=(10, 6),
                     font=("Segoe UI", 9, "bold"))
    estilo.configure("Footer.TLabel", background=COLORES["fondo"],
                     foreground=COLORES["secundario"], font=("Segoe UI", 9))
    estilo.configure("FieldLabel.TLabel", background=COLORES["superficie"],
                     foreground=COLORES["secundario"], font=("Segoe UI", 9, "bold"))

    # Controles: bordes discretos, buen espacio interno y foco azul.
    estilo.configure("TEntry", fieldbackground=COLORES["superficie"],
                     foreground=COLORES["texto"], insertcolor=COLORES["texto"],
                     padding=(9, 7), bordercolor=COLORES["borde"],
                     lightcolor=COLORES["borde"], darkcolor=COLORES["borde"],
                     focuscolor=COLORES["azul"])
    estilo.configure("Table.TEntry", fieldbackground=COLORES["superficie"],
                     foreground=COLORES["texto"], insertcolor=COLORES["texto"],
                     padding=(9, 6), bordercolor=COLORES["borde"],
                     lightcolor=COLORES["borde"], darkcolor=COLORES["borde"],
                     focuscolor=COLORES["azul"])
    estilo.configure("TCombobox", fieldbackground=COLORES["superficie"],
                     background=COLORES["superficie"], foreground=COLORES["texto"],
                     padding=(8, 6), bordercolor=COLORES["borde"],
                     lightcolor=COLORES["borde"], darkcolor=COLORES["borde"],
                     arrowcolor=COLORES["secundario"], focuscolor=COLORES["azul"])
    estilo.map("TCombobox",
               fieldbackground=[("readonly", COLORES["superficie"]), ("focus", COLORES["superficie"])],
               foreground=[("readonly", COLORES["texto"])],
               selectbackground=[("readonly", COLORES["superficie"])],
               selectforeground=[("readonly", COLORES["texto"])])
    estilo.configure("Table.TCombobox", fieldbackground=COLORES["superficie"],
                     background=COLORES["superficie"], foreground=COLORES["texto"],
                     padding=(7, 5), bordercolor=COLORES["borde"],
                     lightcolor=COLORES["borde"], darkcolor=COLORES["borde"],
                     arrowcolor=COLORES["secundario"], focuscolor=COLORES["azul"])

    # Botones principales y secundarios.
    estilo.configure("TButton", background=COLORES["superficie"], foreground=COLORES["texto"],
                     padding=(12, 8), borderwidth=1, relief="flat",
                     bordercolor=COLORES["borde"], focusthickness=1,
                     focuscolor=COLORES["azul"])
    estilo.map("TButton", background=[("pressed", "#E8EEF7"), ("active", "#F4F7FC")],
               bordercolor=[("focus", COLORES["azul"])])
    estilo.configure("Accent.TButton", background=COLORES["azul"], foreground="#FFFFFF",
                     padding=(15, 9), borderwidth=0, relief="flat",
                     font=("Segoe UI", 10, "bold"))
    estilo.map("Accent.TButton",
               background=[("disabled", "#A9BFF5"), ("pressed", COLORES["azul_hover"]),
                           ("active", COLORES["azul_hover"])],
               foreground=[("disabled", "#F4F7FF"), ("!disabled", "#FFFFFF")])
    estilo.configure("Secondary.TButton", background="#F7F9FC", foreground=COLORES["texto"],
                     padding=(11, 8), bordercolor=COLORES["borde"], borderwidth=1)
    estilo.map("Secondary.TButton", background=[("pressed", "#E8EEF7"), ("active", "#EFF4FB")])
    estilo.configure("Quiet.TButton", background=COLORES["superficie"], foreground=COLORES["azul"],
                     padding=(10, 8), borderwidth=0)
    estilo.map("Quiet.TButton", background=[("pressed", COLORES["azul_suave"]), ("active", "#F5F8FF")])
    estilo.configure("Danger.TButton", background=COLORES["rojo_suave"], foreground=COLORES["rojo"],
                     padding=(11, 8), borderwidth=0)
    estilo.map("Danger.TButton", background=[("pressed", "#FEE4E2"), ("active", "#FEE4E2")])
    estilo.configure("Category.TButton", background="#F7F9FC", foreground=COLORES["texto"],
                     padding=(10, 6), bordercolor=COLORES["borde"], borderwidth=1,
                     font=("Segoe UI", 9))
    estilo.map("Category.TButton", background=[("pressed", "#E8EEF7"), ("active", "#EFF4FB")])
    estilo.configure("CategorySelected.TButton", background=COLORES["azul"], foreground="#FFFFFF",
                     padding=(10, 6), borderwidth=0, font=("Segoe UI", 9, "bold"))
    estilo.map("CategorySelected.TButton", background=[("pressed", COLORES["azul_hover"]),
                    ("active", COLORES["azul_hover"])], foreground=[("!disabled", "#FFFFFF")])

    # Tabla y desplazamiento.
    estilo.configure("Treeview", background=COLORES["superficie"],
                     fieldbackground=COLORES["superficie"], foreground=COLORES["texto"],
                     rowheight=31, borderwidth=0, font=("Segoe UI", 9))
    estilo.map("Treeview", background=[("selected", COLORES["azul_suave"])],
               foreground=[("selected", COLORES["texto"])])
    estilo.configure("Treeview.Heading", background=COLORES["encabezado_tabla"],
                     foreground="#34435D", font=("Segoe UI", 9, "bold"),
                     padding=(8, 9), borderwidth=0, relief="flat")
    estilo.map("Treeview.Heading", background=[("active", "#E5ECF7")])
    estilo.configure("Vertical.TScrollbar", background="#E2E8F0", troughcolor=COLORES["superficie"],
                     bordercolor=COLORES["superficie"], arrowcolor=COLORES["secundario"], width=12)
    estilo.configure("Horizontal.TScrollbar", background="#E2E8F0", troughcolor=COLORES["superficie"],
                     bordercolor=COLORES["superficie"], arrowcolor=COLORES["secundario"], width=12)

    # Panel de stock con apariencia de tarjeta.
    estilo.configure("Stock.TLabelframe", background=COLORES["superficie"],
                     bordercolor=COLORES["borde"], relief="solid", borderwidth=1)
    estilo.configure("Stock.TLabelframe.Label", background=COLORES["superficie"],
                     foreground=COLORES["texto"], font=("Segoe UI", 11, "bold"))
    estilo.configure("StockSummary.TLabel", background=COLORES["superficie"],
                     foreground=COLORES["secundario"], font=("Segoe UI", 9))
    estilo.configure("TableCell.TLabel", background=COLORES["superficie"], foreground=COLORES["texto"])
    estilo.configure("TableCellAlt.TLabel", background=COLORES["fila_alterna"], foreground=COLORES["texto"])


def iniciar_programa() -> None:
    lector_excel = LectorExcel()
    lector_plantilla = LectorPlantilla(lector_excel)
    procesador = ProcesadorReporte(
        LectorReporteCompras(lector_excel), FiltroCompras(ReglasFiltro()),
        EscritorPlantilla(), lector_plantilla
    )

    raiz = tk.Tk()
    configurar_tema_roco(raiz)
    VentanaPrincipal(raiz, procesador, lector_plantilla, ExportadorPlantilla(lector_excel))
    raiz.mainloop()


if __name__ == "__main__":
    iniciar_programa()
