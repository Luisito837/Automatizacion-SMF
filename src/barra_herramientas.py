"""Herramientas de reparto para el alimento seleccionado."""
import tkinter as tk
from tkinter import ttk

from configuracion import MODO_CAJA, MODO_UNIDAD
from lista_buscable import ListaDesplegableBuscable


class BarraHerramientas:
    def __init__(self, padre, al_cambiar_producto, al_aplicar_valor,
                 al_autorrellenar, al_limpiar, al_cambiar_modo):
        self.marco = ttk.Frame(padre, style="ToolbarCard.TFrame", padding=(22, 13, 22, 15))
        ttk.Label(self.marco, text="Herramientas de distribución", style="SectionTitle.TLabel").pack(anchor="w")

        controles = ttk.Frame(self.marco, style="Toolbar.TFrame")
        controles.pack(fill="x", pady=(10, 0))

        grupo_producto = ttk.Frame(controles, style="Toolbar.TFrame")
        grupo_producto.pack(side="left", fill="y")
        ttk.Label(grupo_producto, text="ALIMENTO SELECCIONADO", style="FieldLabel.TLabel").pack(anchor="w", pady=(0, 5))
        self.lista_productos = ListaDesplegableBuscable(
            grupo_producto, ancho=34, al_seleccionar=al_cambiar_producto
        )
        self.lista_productos.combo.pack(anchor="w")

        ttk.Separator(controles, orient="vertical").pack(side="left", fill="y", padx=18)

        grupo_valor = ttk.Frame(controles, style="Toolbar.TFrame")
        grupo_valor.pack(side="left", fill="y")
        ttk.Label(grupo_valor, text="CANTIDAD GLOBAL", style="FieldLabel.TLabel").pack(anchor="w", pady=(0, 5))
        fila_valor = ttk.Frame(grupo_valor, style="Toolbar.TFrame")
        fila_valor.pack(anchor="w")
        self.campo_valor = ttk.Entry(fila_valor, width=8, justify="right")
        self.campo_valor.pack(side="left", padx=(0, 6), ipady=1)
        self.campo_valor.bind("<Return>", lambda e: al_aplicar_valor(self.campo_valor.get()))
        ttk.Button(
            fila_valor, text="Aplicar", style="Secondary.TButton",
            command=lambda: al_aplicar_valor(self.campo_valor.get())
        ).pack(side="left")

        ttk.Separator(controles, orient="vertical").pack(side="left", fill="y", padx=18)

        grupo_acciones = ttk.Frame(controles, style="Toolbar.TFrame")
        grupo_acciones.pack(side="left", fill="y")
        ttk.Label(grupo_acciones, text="ACCIONES RÁPIDAS", style="FieldLabel.TLabel").pack(anchor="w", pady=(0, 5))
        fila_acciones = ttk.Frame(grupo_acciones, style="Toolbar.TFrame")
        fila_acciones.pack(anchor="w")
        ttk.Button(
            fila_acciones, text="Autorrellenar", style="Accent.TButton", command=al_autorrellenar
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            fila_acciones, text="Limpiar", style="Danger.TButton", command=al_limpiar
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            fila_acciones, text="Todo en caja", style="Secondary.TButton",
            command=lambda: al_cambiar_modo(MODO_CAJA)
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            fila_acciones, text="Todo en unidad", style="Secondary.TButton",
            command=lambda: al_cambiar_modo(MODO_UNIDAD)
        ).pack(side="left")

    def poner_productos(self, productos) -> None:
        self.lista_productos.poner_opciones(productos)

    def producto_seleccionado(self) -> str:
        return self.lista_productos.valor()

    def seleccionar_producto(self, producto: str) -> None:
        self.lista_productos.elegir(producto)
