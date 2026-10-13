"""Ventana principal de ROCO; la distribución se gestiona por cliente, nunca por vendedor."""
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from barra_herramientas import BarraHerramientas
from barra_superior import BarraSuperior
from catalogo_plantilla import CatalogoClientes, LectorPlantilla
from configuracion import RUTA_LOGO, RUTA_PLANTILLA
from distribucion import Distribucion
from exportador_plantilla import ExportadorPlantilla
from inventario import Inventario
from panel_stock import PanelStock
from procesador_reporte import ProcesadorReporte
from tabla_distribucion import TablaDistribucion
from utilidades import obtener_dia_actual, texto_a_entero


class VentanaPrincipal:
    """Conecta la interfaz, el catálogo de clientes, el inventario y la distribución."""

    def __init__(self, raiz, procesador: ProcesadorReporte, lector_plantilla: LectorPlantilla,
                 exportador: ExportadorPlantilla):
        self.raiz = raiz
        self.procesador = procesador
        self.lector_plantilla = lector_plantilla
        self.exportador = exportador
        self.ruta_plantilla_generada = None  # plantilla con las compras, creada al cargar el reporte
        self.distribucion = Distribucion(Inventario())
        self.catalogo_clientes = CatalogoClientes()
        self.ruta_plantilla = RUTA_PLANTILLA if RUTA_PLANTILLA.exists() else None
        self._productos_por_opcion = {}

        raiz.title("ROCO · Distribución de compras por cliente")
        raiz.geometry("1440x840")
        raiz.minsize(1080, 660)
        try:
            raiz.state("zoomed")
        except tk.TclError:
            pass
        self._armar_pantalla()
        self._vincular_teclas_de_producto()
        self._cargar_lista_productos()
        self._cargar_clientes()
        self.tabla.mostrar_producto(self._producto_seleccionado())
        self._actualizar_stock()

    # ---------- armado de la interfaz ----------
    def _armar_pantalla(self) -> None:
        self.raiz.columnconfigure(0, weight=1)
        self.raiz.rowconfigure(2, weight=1)
        self.barra_superior = BarraSuperior(
            self.raiz, RUTA_LOGO, obtener_dia_actual(), self._al_cambiar_dia,
            self._cargar_reporte, self._recargar_clientes, self._ver_clientes,
            self._exportar_plantilla
        )
        self.barra_herramientas = BarraHerramientas(
            self.raiz, self._al_cambiar_producto, self._aplicar_valor_global,
            self._autorrellenar, self._limpiar_todo, self._reportar_todo_como
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
        ttk.Label(pie, text="Las cantidades se calculan contra el inventario cargado", style="Footer.TLabel").pack(side="right")
        pie.grid(row=3, column=0, sticky="ew")

    # ---------- fase 1: cargar compras / inventario ----------
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
        self._cargar_lista_productos()
        self._cargar_clientes()
        opciones = list(self._productos_por_opcion)
        if opciones:
            self.barra_herramientas.seleccionar_producto(opciones[0])
            self._al_cambiar_producto(opciones[0], enfocar=False)
        else:
            self._al_cambiar_producto("", enfocar=False)
        messagebox.showinfo("Reporte cargado", resultado.resumen())

    def _obtener_ruta_plantilla(self):
        if self.ruta_plantilla and self.ruta_plantilla.exists():
            return self.ruta_plantilla
        seleccion = filedialog.askopenfilename(
            title="Seleccione la plantilla FACTURACION_SMF.xlsx",
            filetypes=[("Excel", "*.xlsx"), ("Todos los archivos", "*.*")],
        )
        if seleccion:
            self.ruta_plantilla = Path(seleccion)
        return self.ruta_plantilla

    def _cargar_lista_productos(self) -> None:
        """Crea opciones legibles para elegir un único producto, distinguiendo duplicados."""
        productos = []
        vistos = set()
        for categoria in self.distribucion.inventario.categorias():
            for producto in self.distribucion.inventario.productos_de_categoria(categoria):
                if producto.codigo in vistos:
                    continue
                vistos.add(producto.codigo)
                productos.append(producto)

        bases = []
        frecuencias = {}
        for producto in productos:
            descripcion = (producto.descripcion or str(producto.codigo)).strip()
            base = f"{descripcion} — {producto.categoria}" if producto.categoria else descripcion
            bases.append(base)
            frecuencias[base] = frecuencias.get(base, 0) + 1

        self._productos_por_opcion = {}
        for base, producto in zip(bases, productos):
            opcion = f"{base} [{producto.codigo}]" if frecuencias[base] > 1 else base
            # Si dos códigos se repiten por un error en la fuente, evita que se sobrescriban.
            etiqueta = opcion
            sufijo = 2
            while etiqueta in self._productos_por_opcion:
                etiqueta = f"{opcion} ({sufijo})"
                sufijo += 1
            self._productos_por_opcion[etiqueta] = producto

        opciones = list(self._productos_por_opcion)
        self.barra_herramientas.poner_productos(opciones)
        if opciones:
            self.barra_herramientas.seleccionar_producto(opciones[0])

    # ---------- clientes y día ----------
    def _cargar_clientes(self) -> None:
        if self.ruta_plantilla and self.ruta_plantilla.exists():
            try:
                self.catalogo_clientes = self.lector_plantilla.leer_clientes(self.ruta_plantilla)
            except Exception as error:
                self.catalogo_clientes = CatalogoClientes()
                messagebox.showwarning("Clientes", f"No se pudieron leer los clientes de la plantilla.\n{error}")
        self._al_cambiar_dia(self.barra_superior.dia_seleccionado())

    def _recargar_clientes(self) -> None:
        self._cargar_clientes()

    def _al_cambiar_dia(self, dia: str) -> None:
        clientes = self.catalogo_clientes.del_dia(dia)
        self.distribucion.reemplazar_clientes(clientes)
        self.barra_superior.mostrar_cantidad_de_clientes(len(clientes))
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
        ventana.configure(background="#F3F6FC")
        contenedor = ttk.Frame(ventana, padding=16)
        contenedor.pack(fill="both", expand=True)
        ttk.Label(contenedor, text=f"Clientes del {dia.lower()}", style="SectionTitle.TLabel").pack(anchor="w")
        ttk.Label(contenedor, text=f"{len(clientes)} clientes registrados en la plantilla", style="Muted.TLabel").pack(anchor="w", pady=(4, 12))
        tabla = ttk.Treeview(contenedor, columns=("cep", "cliente"), show="headings")
        tabla.heading("cep", text="CEP")
        tabla.heading("cliente", text="Cliente")
        tabla.column("cep", width=100, anchor="w", stretch=False)
        tabla.column("cliente", width=480, anchor="w")
        for cliente in clientes:
            tabla.insert("", "end", values=(cliente.cep, cliente.nombre))
        tabla.pack(fill="both", expand=True)

    # ---------- producto seleccionado ----------
    def _producto_seleccionado(self):
        opcion = self.barra_herramientas.producto_seleccionado()
        return self._productos_por_opcion.get(opcion)

    def _al_cambiar_producto(self, opcion: str, enfocar: bool = True) -> None:
        producto = self._productos_por_opcion.get(opcion)
        self.tabla.mostrar_producto(producto)
        self._actualizar_stock()
        if enfocar:
            self.tabla.enfocar_primera_celda()

    # ---------- avanzar / retroceder de alimento con el teclado ----------
    def _vincular_teclas_de_producto(self) -> None:
        """Ctrl+Derecha o Av Pág: siguiente alimento. Ctrl+Izquierda o Re Pág: alimento anterior."""
        for secuencia, paso in (("<Control-Right>", 1), ("<Next>", 1),
                                ("<Control-Left>", -1), ("<Prior>", -1)):
            self.raiz.bind_all(secuencia, lambda e, p=paso: self._mover_producto(p))

    def _mover_producto(self, paso: int) -> None:
        try:
            if isinstance(self.raiz.focus_get(), ttk.Combobox):
                return  # dentro de una lista desplegable esas teclas conservan su función normal
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

    # ---------- exportar ----------
    def _exportar_plantilla(self) -> None:
        self.tabla.confirmar_celdas()
        asignaciones = self.distribucion.asignaciones()
        if not asignaciones:
            messagebox.showinfo("Nada que exportar", "Todavía no hay cantidades asignadas.")
            return
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
            messagebox.showerror("No se pudo exportar", str(error))
            return
        messagebox.showinfo("Plantilla exportada", resultado.resumen())

    # ---------- herramientas para un solo producto ----------
    def _listo_para_operar(self) -> bool:
        if self._producto_seleccionado() is None:
            messagebox.showinfo("Falta el alimento", "Cargue el reporte general y elija un alimento.")
            return False
        if not self.distribucion.clientes:
            messagebox.showinfo(
                "No hay clientes", "No hay clientes para el día seleccionado en la plantilla."
            )
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

    def _limpiar_todo(self) -> None:
        if not self._listo_para_operar():
            return
        producto = self._producto_seleccionado()
        nombre = producto.descripcion or str(producto.codigo)
        if messagebox.askyesno("Limpiar", f"¿Borrar la asignación de {nombre} para todos los clientes del día?"):
            self.distribucion.limpiar(producto)
            self._refrescar_todo()

    def _reportar_todo_como(self, modo: str) -> None:
        if self._listo_para_operar():
            self.distribucion.fijar_modo_a_todos(self._producto_seleccionado(), modo)
            self._refrescar_todo()

    def _refrescar_todo(self) -> None:
        self.tabla.refrescar()
        self._actualizar_stock()

    def _actualizar_stock(self) -> None:
        if not hasattr(self, "panel_stock"):
            return
        producto = self._producto_seleccionado()
        if producto is not None:
            categoria = producto.categoria
            filas = self.distribucion.filas_de_stock(categoria)
            totales = self.distribucion.totales_de_categoria(categoria)
        else:
            filas, totales = [], None
        self.panel_stock.mostrar(filas, totales)
