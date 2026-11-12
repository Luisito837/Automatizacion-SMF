"""Menú de Inicio estilo Photoshop / Home Screen para ROCO Distribución."""
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Optional

from configuracion import (
    COLOR_AZUL_ROCO,
    COLOR_ROJO_ROCO,
    RUTA_LOGO,
    CANDIDATAS_PLANTILLA,
)
from gestor_recientes import GestorRecientes, InfoArchivoReciente, analizar_archivo_excel

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None


class DialogoNuevoReparto(tk.Toplevel):
    """Ventana modal estilo asistente guiado para iniciar un nuevo reparto."""

    def __init__(self, padre, ruta_plantilla_por_defecto: Optional[Path], al_confirmar: Callable[[Path, Path], None]):
        super().__init__(padre)
        self.al_confirmar = al_confirmar
        self.ruta_reporte = None
        self.ruta_plantilla = ruta_plantilla_por_defecto

        self.title("Iniciar Nuevo Reparto")
        self.geometry("640x480")
        self.minsize(580, 420)
        self.resizable(False, False)
        self.transient(padre)
        self.grab_set()

        self._armar_interfaz()
        self._centrar(padre)

    def _centrar(self, padre):
        self.update_idletasks()
        ancho = self.winfo_width()
        alto = self.winfo_height()
        px = padre.winfo_rootx() + (padre.winfo_width() - ancho) // 2
        py = padre.winfo_rooty() + (padre.winfo_height() - alto) // 2
        self.geometry(f"+{max(0, px)}+{max(0, py)}")

    def _armar_interfaz(self):
        contenedor = ttk.Frame(self, padding=(28, 24, 28, 20), style="TFrame")
        contenedor.pack(fill="both", expand=True)

        # Encabezado
        ttk.Label(contenedor, text="Iniciar Nuevo Reparto", style="HeaderTitle.TLabel").pack(anchor="w")
        ttk.Label(
            contenedor,
            text="Cargue el reporte de compras recibido para generar la nueva distribución semanal.",
            style="HeaderSubtitle.TLabel"
        ).pack(anchor="w", pady=(3, 18))

        # Tarjeta Paso 1: Reporte de compras
        tarjeta_reporte = ttk.LabelFrame(contenedor, text="  1. Reporte General de Compras (Obligatorio)  ", padding=14)
        tarjeta_reporte.pack(fill="x", pady=(0, 14))

        self.lbl_reporte_estado = ttk.Label(
            tarjeta_reporte,
            text="Ningún reporte seleccionado aún",
            font=("Segoe UI", 9, "italic"),
            foreground="#627089"
        )
        self.lbl_reporte_estado.pack(side="left", fill="x", expand=True)

        btn_examinar_reporte = ttk.Button(
            tarjeta_reporte,
            text="Seleccionar reporte...",
            style="Accent.TButton",
            command=self._seleccionar_reporte
        )
        btn_examinar_reporte.pack(side="right")

        # Tarjeta Paso 2: Plantilla base
        tarjeta_plantilla = ttk.LabelFrame(contenedor, text="  2. Plantilla base para rellenar  ", padding=14)
        tarjeta_plantilla.pack(fill="x", pady=(0, 14))

        self.lbl_plantilla_estado = ttk.Label(tarjeta_plantilla, text="", font=("Segoe UI", 9))
        self.lbl_plantilla_estado.pack(side="left", fill="x", expand=True)

        btn_cambiar_plantilla = ttk.Button(
            tarjeta_plantilla,
            text="Cambiar...",
            style="Secondary.TButton",
            command=self._seleccionar_plantilla
        )
        btn_cambiar_plantilla.pack(side="right")

        # Alerta o detalle (crearlo ANTES de _actualizar_etiqueta_plantilla)
        self.lbl_aviso = ttk.Label(
            contenedor,
            text="",
            wraplength=560,
            font=("Segoe UI", 9),
            foreground="#B42318"
        )
        self.lbl_aviso.pack(fill="x", pady=(4, 10))

        # Ahora sí actualizar la etiqueta de la plantilla
        self._actualizar_etiqueta_plantilla()

        # Botones de pie
        pie = ttk.Frame(contenedor)
        pie.pack(side="bottom", fill="x", pady=(10, 0))

        ttk.Button(pie, text="Cancelar", style="Secondary.TButton", command=self.destroy).pack(side="left")

        self.btn_iniciar = ttk.Button(
            pie,
            text="Comenzar Distribución ➔",
            style="Accent.TButton",
            command=self._ejecutar,
            state="disabled"
        )
        self.btn_iniciar.pack(side="right")

    def _actualizar_etiqueta_plantilla(self):
        if self.ruta_plantilla and self.ruta_plantilla.exists():
            info = analizar_archivo_excel(self.ruta_plantilla)
            if info.es_trabajo_en_progreso:
                self.lbl_plantilla_estado.config(
                    text=f"⚠ {self.ruta_plantilla.name} (¡Ya tiene trabajo a medio hacer!)",
                    foreground="#B42318"
                )
                self.lbl_aviso.config(
                    text="Aviso: La plantilla elegida ya contiene compras o asignaciones guardadas.\n"
                         "Si continúas con 'Comenzar Distribución', se generará un nuevo reparto inyectando el nuevo reporte."
                )
            else:
                self.lbl_plantilla_estado.config(
                    text=f"✔ {self.ruta_plantilla.name} (Plantilla limpia)",
                    foreground="#067647"
                )
                self.lbl_aviso.config(text="")
        else:
            self.lbl_plantilla_estado.config(
                text="❌ Plantilla no encontrada. Debe seleccionar una.",
                foreground="#B42318"
            )

    def _seleccionar_reporte(self):
        seleccion = filedialog.askopenfilename(
            parent=self,
            title="Seleccionar Reporte General de Compras",
            filetypes=[("Excel", "*.xlsx *.xlsm"), ("Todos los archivos", "*.*")]
        )
        if seleccion:
            self.ruta_reporte = Path(seleccion)
            self.lbl_reporte_estado.config(
                text=f"✔ {self.ruta_reporte.name}",
                font=("Segoe UI", 9, "bold"),
                foreground="#067647"
            )
            self._verificar_listo()

    def _seleccionar_plantilla(self):
        seleccion = filedialog.askopenfilename(
            parent=self,
            title="Seleccionar Plantilla FACTURACION SMF.xlsx",
            filetypes=[("Excel", "*.xlsx *.xlsm"), ("Todos los archivos", "*.*")]
        )
        if seleccion:
            self.ruta_plantilla = Path(seleccion)
            self._actualizar_etiqueta_plantilla()
            self._verificar_listo()

    def _verificar_listo(self):
        if self.ruta_reporte and self.ruta_plantilla and self.ruta_plantilla.exists():
            self.btn_iniciar.config(state="normal")
        else:
            self.btn_iniciar.config(state="disabled")

    def _ejecutar(self):
        if not self.ruta_reporte or not self.ruta_plantilla:
            return
        reporte, plantilla = self.ruta_reporte, self.ruta_plantilla
        self.destroy()
        self.al_confirmar(reporte, plantilla)


class PantallaInicio(ttk.Frame):
    """Vista de inicio estilo Photoshop con panel lateral de acciones y lista de archivos recientes."""

    def __init__(
        self,
        padre,
        gestor_recientes: GestorRecientes,
        al_abrir_archivo: Callable[[Path], None],
        al_nuevo_reparto: Callable[[Path, Path], None],
        ruta_plantilla_base: Optional[Path] = None,
    ):
        super().__init__(padre, style="TFrame")
        self.gestor_recientes = gestor_recientes
        self.al_abrir_archivo = al_abrir_archivo
        self.al_nuevo_reparto = al_nuevo_reparto
        self.ruta_plantilla_base = ruta_plantilla_base

        self._recientes_cargados = []
        self._imagen_logo = self._cargar_logo(RUTA_LOGO)
        self._armar_interfaz()
        self.refrescar_recientes()

    def _cargar_logo(self, ruta):
        if Image is None or not Path(ruta).exists():
            return None
        try:
            img = Image.open(ruta).convert("RGB")
            # Redimensionar conservando proporción para la barra lateral
            ancho_deseado = 160
            proporcion = ancho_deseado / float(img.size[0])
            alto_deseado = int(float(img.size[1]) * proporcion)
            img = img.resize((ancho_deseado, alto_deseado), Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(img)
        except Exception:
            return None

    def _armar_interfaz(self):
        self.columnconfigure(0, weight=0, minsize=260)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # ---------------- BARRA LATERAL (Acciones Rápidas) ----------------
        barra_lateral = ttk.Frame(self, style="CardBorder.TFrame", padding=(22, 26, 22, 26))
        barra_lateral.grid(row=0, column=0, sticky="nsew", padx=(18, 0), pady=18)
        barra_lateral.columnconfigure(0, weight=1)

        # Logo / Marca
        if self._imagen_logo is not None:
            lbl_logo = ttk.Label(barra_lateral, image=self._imagen_logo, style="Header.TLabel")
            lbl_logo.pack(anchor="w", pady=(0, 8))
        else:
            marca = tk.Frame(barra_lateral, background="#FFFFFF")
            marca.pack(anchor="w", pady=(0, 8))
            tk.Label(
                marca, text="R", font=("Segoe UI", 26, "bold"),
                fg=COLOR_ROJO_ROCO, bg="#FFFFFF"
            ).pack(side="left")
            tk.Label(
                marca, text="OCO", font=("Segoe UI", 24, "bold"),
                fg=COLOR_AZUL_ROCO, bg="#FFFFFF"
            ).pack(side="left")

        ttk.Label(barra_lateral, text="Distribución SMF", style="HeaderTitle.TLabel").pack(anchor="w")
        ttk.Label(
            barra_lateral,
            text="Control semanal de existencias y asignaciones por cliente.",
            style="HeaderSubtitle.TLabel",
            wraplength=210
        ).pack(anchor="w", pady=(2, 24))

        # Botón Acción Primaria: Nuevo reparto
        btn_nuevo = tk.Button(
            barra_lateral,
            text="＋  Nuevo reparto",
            font=("Segoe UI", 11, "bold"),
            bg=COLOR_AZUL_ROCO,
            fg="#FFFFFF",
            activebackground="#1D4ED8",
            activeforeground="#FFFFFF",
            relief="flat",
            cursor="hand2",
            padx=16,
            pady=12,
            command=self._solicitar_nuevo_reparto
        )
        btn_nuevo.pack(fill="x", pady=(0, 10))

        # Botón Acción Secundaria: Abrir guardado
        btn_abrir = tk.Button(
            barra_lateral,
            text="📂  Abrir guardado...",
            font=("Segoe UI", 10),
            bg="#F7F9FC",
            fg="#172033",
            activebackground="#EFF4FB",
            relief="groove",
            bd=1,
            cursor="hand2",
            padx=14,
            pady=9,
            command=self._examinar_guardado
        )
        btn_abrir.pack(fill="x", pady=(0, 24))

        ttk.Separator(barra_lateral, orient="horizontal").pack(fill="x", pady=(0, 18))

        # Mensaje informativo / Tips para la operadora
        tips_frame = ttk.Frame(barra_lateral, style="Card.TFrame")
        tips_frame.pack(fill="x", anchor="w")

        ttk.Label(tips_frame, text="💡 Consejo:", font=("Segoe UI", 9, "bold"), style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            tips_frame,
            text="• Si guardaste tu trabajo a medias, haz clic en el archivo dentro de 'Recientes' para continuar exactamente donde lo dejaste.\n\n"
                 "• Para empezar una nueva semana con compras nuevas, haz clic en 'Nuevo reparto'.",
            style="Muted.TLabel",
            wraplength=210,
            justify="left"
        ).pack(anchor="w", pady=(4, 0))

        # ---------------- PANEL CENTRAL (Archivos Recientes) ----------------
        panel_central = ttk.Frame(self, style="CardBorder.TFrame", padding=(26, 26, 26, 22))
        panel_central.grid(row=0, column=1, sticky="nsew", padx=18, pady=18)
        panel_central.columnconfigure(0, weight=1)
        panel_central.rowconfigure(1, weight=1)

        # Encabezado del panel
        encabezado = ttk.Frame(panel_central, style="Card.TFrame")
        encabezado.grid(row=0, column=0, sticky="ew", pady=(0, 14))

        ttk.Label(encabezado, text="Trabajos recientes", style="HeaderTitle.TLabel").pack(anchor="w")
        ttk.Label(
            encabezado,
            text="Selecciona un archivo de la lista para continuar tu trabajo o haz doble clic para abrirlo.",
            style="HeaderSubtitle.TLabel"
        ).pack(anchor="w", pady=(2, 0))

        # Contenedor de la tabla de recientes
        tabla_marco = ttk.Frame(panel_central, style="Card.TFrame")
        tabla_marco.grid(row=1, column=0, sticky="nsew")
        tabla_marco.columnconfigure(0, weight=1)
        tabla_marco.rowconfigure(0, weight=1)

        columnas = ("nombre", "fecha", "estado", "ruta")
        self.tree_recientes = ttk.Treeview(
            tabla_marco,
            columns=columnas,
            show="headings",
            selectmode="browse"
        )
        self.tree_recientes.heading("nombre", text="Nombre del archivo", anchor="w")
        self.tree_recientes.heading("fecha", text="Última modificación", anchor="w")
        self.tree_recientes.heading("estado", text="Estado del trabajo", anchor="w")
        self.tree_recientes.heading("ruta", text="Ubicación", anchor="w")

        self.tree_recientes.column("nombre", width=250, minwidth=180, stretch=False)
        self.tree_recientes.column("fecha", width=160, minwidth=140, stretch=False)
        self.tree_recientes.column("estado", width=200, minwidth=160, stretch=False)
        self.tree_recientes.column("ruta", width=340, minwidth=200, stretch=True)

        scroll_y = ttk.Scrollbar(tabla_marco, orient="vertical", command=self.tree_recientes.yview)
        self.tree_recientes.configure(yscrollcommand=scroll_y.set)

        self.tree_recientes.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")

        self.tree_recientes.bind("<Double-1>", lambda e: self._abrir_seleccionado())
        self.tree_recientes.bind("<Return>", lambda e: self._abrir_seleccionado())

        # Pie del panel central
        pie_central = ttk.Frame(panel_central, style="Card.TFrame")
        pie_central.grid(row=2, column=0, sticky="ew", pady=(14, 0))

        ttk.Button(
            pie_central,
            text="🔄 Actualizar lista",
            style="Quiet.TButton",
            command=self.refrescar_recientes
        ).pack(side="left")

        self.btn_abrir_sel = ttk.Button(
            pie_central,
            text="Continuar con este archivo ➔",
            style="Accent.TButton",
            command=self._abrir_seleccionado
        )
        self.btn_abrir_sel.pack(side="right")

    def refrescar_recientes(self) -> None:
        """Carga o actualiza la lista de archivos recientes en la vista."""
        for item in self.tree_recientes.get_children():
            self.tree_recientes.delete(item)

        self._recientes_cargados = self.gestor_recientes.obtener_lista_recientes()

        for info in self._recientes_cargados:
            icono = "📄"
            if info.es_trabajo_en_progreso:
                icono = "🔄"
            elif "Plantilla base" in info.estado:
                icono = "📋"

            self.tree_recientes.insert(
                "",
                "end",
                values=(
                    f"{icono}  {info.nombre}",
                    info.fecha_modificacion,
                    info.estado,
                    info.ruta,
                ),
            )

        # Seleccionar el primer elemento automáticamente si existe
        hijos = self.tree_recientes.get_children()
        if hijos:
            self.tree_recientes.selection_set(hijos[0])
            self.tree_recientes.focus(hijos[0])

    def _abrir_seleccionado(self) -> None:
        seleccion = self.tree_recientes.selection()
        if not seleccion:
            messagebox.showinfo("Seleccione un archivo", "Por favor haga clic en un archivo de la lista de recientes.")
            return
        indice = self.tree_recientes.index(seleccion[0])
        if 0 <= indice < len(self._recientes_cargados):
            info = self._recientes_cargados[indice]
            ruta = Path(info.ruta)
            if not ruta.exists():
                messagebox.showerror("Archivo no encontrado", f"El archivo ya no se encuentra en:\n{ruta}")
                self.refrescar_recientes()
                return
            self.al_abrir_archivo(ruta)

    def _examinar_guardado(self) -> None:
        ruta = filedialog.askopenfilename(
            title="Abrir plantilla o trabajo guardado",
            filetypes=[("Excel", "*.xlsx *.xlsm"), ("Todos los archivos", "*.*")]
        )
        if ruta:
            p = Path(ruta)
            self.gestor_recientes.guardar_reciente(p)
            self.al_abrir_archivo(p)

    def _solicitar_nuevo_reparto(self) -> None:
        DialogoNuevoReparto(
            self.winfo_toplevel(),
            self.ruta_plantilla_base,
            self.al_nuevo_reparto
        )
