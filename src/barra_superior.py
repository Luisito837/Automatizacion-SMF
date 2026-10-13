"""Cabecera de ROCO: identidad, selección de día y acciones principales."""
from pathlib import Path
import tkinter as tk
from tkinter import ttk

from configuracion import COLOR_AZUL_ROCO, COLOR_ROJO_ROCO, DIAS_SEMANA

try:
    from PIL import Image, ImageTk
except ImportError:  # Pillow es opcional; sin él se muestra el nombre en vez del logo.
    Image = None
    ImageTk = None


ALTO_DEL_LOGO = 42


class BarraSuperior:
    def __init__(self, padre, ruta_logo, dia_inicial, al_cambiar_dia,
                 al_cargar_reporte, al_actualizar_clientes, al_ver_clientes, al_exportar):
        self.marco = ttk.Frame(padre, style="HeaderCard.TFrame", padding=(22, 14, 22, 16))
        self.marco.columnconfigure(0, weight=1)

        identidad = ttk.Frame(self.marco, style="Header.TFrame")
        identidad.grid(row=0, column=0, sticky="w")
        self._imagen_logo = self._cargar_logo(ruta_logo)
        self._crear_logo(identidad)
        bloque_titulo = ttk.Frame(identidad, style="Header.TFrame")
        bloque_titulo.pack(side="left", padx=(12, 0))
        ttk.Label(bloque_titulo, text="Distribución de alimentos", style="HeaderTitle.TLabel").pack(anchor="w")
        ttk.Label(
            bloque_titulo, text="Asignaciones por cliente · Control de existencias",
            style="HeaderSubtitle.TLabel"
        ).pack(anchor="w", pady=(1, 0))

        botones = ttk.Frame(self.marco, style="Header.TFrame")
        botones.grid(row=0, column=1, sticky="e", padx=(16, 0))
        ttk.Button(
            botones, text="Exportar plantilla", style="Secondary.TButton", command=al_exportar
        ).pack(side="left", padx=(0, 8))
        ttk.Button(
            botones, text="＋  Cargar reporte general", style="Accent.TButton",
            command=al_cargar_reporte
        ).pack(side="left")

        controles = ttk.Frame(self.marco, style="Header.TFrame")
        controles.grid(row=1, column=0, sticky="w", pady=(15, 0))
        ttk.Label(controles, text="DÍA DE REPARTO", style="FieldLabel.TLabel").pack(side="left", padx=(0, 9))
        self.variable_dia = tk.StringVar(value=dia_inicial)
        selector = ttk.Combobox(
            controles, values=DIAS_SEMANA, textvariable=self.variable_dia,
            state="readonly", width=13
        )
        selector.pack(side="left")
        selector.bind("<<ComboboxSelected>>", lambda e: al_cambiar_dia(self.variable_dia.get()))

        self.etiqueta_clientes = ttk.Label(controles, text="0 clientes", style="Pill.TLabel")
        self.etiqueta_clientes.pack(side="left", padx=(12, 0))

        acciones = ttk.Frame(self.marco, style="Header.TFrame")
        acciones.grid(row=1, column=1, sticky="e", pady=(15, 0), padx=(16, 0))
        ttk.Button(
            acciones, text="Ver clientes", style="Secondary.TButton", command=al_ver_clientes
        ).pack(side="left", padx=(0, 7))
        ttk.Button(
            acciones, text="Actualizar clientes", style="Quiet.TButton", command=al_actualizar_clientes
        ).pack(side="left")

    def dia_seleccionado(self) -> str:
        return self.variable_dia.get()

    def mostrar_cantidad_de_clientes(self, cantidad: int) -> None:
        sufijo = "cliente" if cantidad == 1 else "clientes"
        self.etiqueta_clientes.config(text=f"{cantidad} {sufijo}")

    def _crear_logo(self, padre) -> None:
        if self._imagen_logo is not None:
            ttk.Label(padre, image=self._imagen_logo, style="Header.TLabel").pack(side="left")
            return
        marca = tk.Frame(padre, background="#FFFFFF", width=83, height=45)
        marca.pack(side="left")
        marca.pack_propagate(False)
        tk.Label(
            marca, text="R", font=("Segoe UI", 23, "bold"),
            fg=COLOR_ROJO_ROCO, bg="#FFFFFF"
        ).pack(side="left")
        tk.Label(
            marca, text="OCO", font=("Segoe UI", 21, "bold"),
            fg=COLOR_AZUL_ROCO, bg="#FFFFFF"
        ).pack(side="left")

    @staticmethod
    def _cargar_logo(ruta):
        """Carga el logo y recorta el margen blanco. Devuelve None si no se puede."""
        if Image is None or not Path(ruta).exists():
            return None
        try:
            imagen = Image.open(ruta).convert("RGB")
            no_blanco = imagen.convert("L").point(lambda p: 255 if p < 215 else 0)
            area = no_blanco.getbbox()
            if area:
                imagen = imagen.crop(area)
            ancho = round(imagen.width * ALTO_DEL_LOGO / imagen.height)
            return ImageTk.PhotoImage(imagen.resize((ancho, ALTO_DEL_LOGO), Image.LANCZOS))
        except Exception:
            return None
