"""Filtros de categoría/producto y herramientas rápidas de distribución."""
import tkinter as tk
from tkinter import ttk

from configuracion import MODO_BULTO, MODO_CAJA, MODO_UNIDAD
from lista_buscable import ListaDesplegableBuscable


class BarraHerramientas:
    def __init__(
        self, padre, al_cambiar_categoria, al_cambiar_producto, al_aplicar_valor,
        al_autorrellenar, al_autorrellenar_categoria, al_limpiar, al_cambiar_modo,
        al_editar_factores, al_resumen_semanal,
    ):
        self._al_cambiar_categoria = al_cambiar_categoria
        self._categorias = []
        self._categoria_activa = None
        self._botones_categoria = {}
        self.marco = ttk.Frame(padre, style="ToolbarCard.TFrame", padding=(20, 13, 20, 15))
        ttk.Label(self.marco, text="Buscar por categoría", style="SectionTitle.TLabel").pack(anchor="w")
        self.grilla_categorias = ttk.Frame(self.marco, style="Toolbar.TFrame")
        self.grilla_categorias.pack(fill="x", pady=(8, 12))

        ttk.Separator(self.marco, orient="horizontal").pack(fill="x", pady=(0, 10))
        controles = ttk.Frame(self.marco, style="Toolbar.TFrame")
        controles.pack(fill="x")

        grupo_producto = ttk.Frame(controles, style="Toolbar.TFrame")
        grupo_producto.pack(side="left", fill="y")
        ttk.Label(grupo_producto, text="BUSCAR PRODUCTO / SKU", style="FieldLabel.TLabel").pack(anchor="w", pady=(0, 5))
        self.lista_productos = ListaDesplegableBuscable(
            grupo_producto, ancho=38, al_seleccionar=al_cambiar_producto
        )
        self.lista_productos.combo.pack(anchor="w")

        ttk.Separator(controles, orient="vertical").pack(side="left", fill="y", padx=14)

        grupo_valor = ttk.Frame(controles, style="Toolbar.TFrame")
        grupo_valor.pack(side="left", fill="y")
        ttk.Label(grupo_valor, text="CANTIDAD GLOBAL", style="FieldLabel.TLabel").pack(anchor="w", pady=(0, 5))
        fila_valor = ttk.Frame(grupo_valor, style="Toolbar.TFrame")
        fila_valor.pack(anchor="w")
        self.campo_valor = ttk.Entry(fila_valor, width=8, justify="right")
        self.campo_valor.pack(side="left", padx=(0, 6), ipady=1)
        self.campo_valor.bind("<Return>", lambda e: al_aplicar_valor(self.campo_valor.get()))
        ttk.Button(fila_valor, text="Aplicar", style="Secondary.TButton",
                   command=lambda: al_aplicar_valor(self.campo_valor.get())).pack(side="left")

        ttk.Separator(controles, orient="vertical").pack(side="left", fill="y", padx=14)
        grupo_acciones = ttk.Frame(controles, style="Toolbar.TFrame")
        grupo_acciones.pack(side="left", fill="y", expand=True)
        ttk.Label(grupo_acciones, text="ACCIONES RÁPIDAS", style="FieldLabel.TLabel").pack(anchor="w", pady=(0, 5))
        fila_acciones = ttk.Frame(grupo_acciones, style="Toolbar.TFrame")
        fila_acciones.pack(anchor="w")
        ttk.Button(fila_acciones, text="Repartir restante", style="Accent.TButton",
                   command=al_autorrellenar).pack(side="left", padx=(0, 5))
        ttk.Button(fila_acciones, text="Completar categoría", style="Secondary.TButton",
                   command=al_autorrellenar_categoria).pack(side="left", padx=(0, 5))
        ttk.Button(fila_acciones, text="Limpiar día", style="Danger.TButton",
                   command=al_limpiar).pack(side="left", padx=(0, 5))
        self.boton_caja = ttk.Button(fila_acciones, text="Todo en caja", style="Secondary.TButton",
                                     command=lambda: al_cambiar_modo(MODO_CAJA))
        self.boton_caja.pack(side="left", padx=(0, 5))
        self.boton_unidad = ttk.Button(fila_acciones, text="Todo en unidad", style="Secondary.TButton",
                                       command=lambda: al_cambiar_modo(MODO_UNIDAD))
        self.boton_unidad.pack(side="left", padx=(0, 5))
        self.boton_bulto = ttk.Button(fila_acciones, text="Todo en bulto", style="Secondary.TButton",
                                      command=lambda: al_cambiar_modo(MODO_BULTO))
        self.boton_bulto.pack(side="left", padx=(0, 5))
        ttk.Button(fila_acciones, text="Factores", style="Quiet.TButton",
                   command=al_editar_factores).pack(side="left", padx=(0, 5))
        ttk.Button(fila_acciones, text="Resumen semanal", style="Quiet.TButton",
                   command=al_resumen_semanal).pack(side="left")

    def poner_categorias(self, categorias, seleccionar=None) -> None:
        self._categorias = list(categorias)
        for hijo in self.grilla_categorias.winfo_children():
            hijo.destroy()
        self._botones_categoria = {}
        opciones = [None, *self._categorias]  # None representa "Todas".
        columnas = 8
        for indice, categoria in enumerate(opciones):
            texto = "Todas" if categoria is None else str(categoria)
            boton = ttk.Button(
                self.grilla_categorias, text=texto,
                style="Category.TButton", command=lambda c=categoria: self._elegir_categoria(c)
            )
            boton.grid(row=indice // columnas, column=indice % columnas, sticky="ew", padx=3, pady=3)
            self._botones_categoria[categoria] = boton
        for columna in range(columnas):
            self.grilla_categorias.columnconfigure(columna, weight=1)
        objetivo = seleccionar if seleccionar in self._categorias else (None if not self._categorias else self._categorias[0])
        self._elegir_categoria(objetivo, notificar=False)

    def _elegir_categoria(self, categoria, notificar=True) -> None:
        if categoria is not None and categoria not in self._categorias:
            categoria = None
        self._categoria_activa = categoria
        for clave, boton in self._botones_categoria.items():
            try:
                boton.configure(style="CategorySelected.TButton" if clave == categoria else "Category.TButton")
            except tk.TclError:
                pass
        if notificar:
            self._al_cambiar_categoria(categoria)

    def categoria_seleccionada(self):
        return self._categoria_activa

    def poner_productos(self, productos) -> None:
        self.lista_productos.poner_opciones(productos)

    def producto_seleccionado(self) -> str:
        return self.lista_productos.valor()

    def seleccionar_producto(self, producto: str) -> None:
        self.lista_productos.elegir(producto)

    def actualizar_modos_permitidos(self, modos) -> None:
        permitidos = set(modos or ())
        for modo, boton in ((MODO_CAJA, self.boton_caja), (MODO_UNIDAD, self.boton_unidad), (MODO_BULTO, self.boton_bulto)):
            boton.configure(state="normal" if modo in permitidos else "disabled")
