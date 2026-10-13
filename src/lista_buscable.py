"""Lista desplegable que filtra sus opciones mientras se escribe."""
import tkinter as tk
from tkinter import ttk

from utilidades import normalizar_texto

TECLAS_QUE_NO_FILTRAN = {
    "Up", "Down", "Left", "Right", "Return", "KP_Enter", "Escape", "Tab",
    "Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R",
}


class ListaDesplegableBuscable:
    """Escriba parte del nombre, presione Enter y se elige la primera coincidencia."""

    def __init__(self, padre, ancho, al_seleccionar):
        self._opciones = []
        self._valor_confirmado = ""
        self._al_seleccionar = al_seleccionar
        self.variable = tk.StringVar()
        self.combo = ttk.Combobox(padre, textvariable=self.variable, width=ancho)
        self.combo.bind("<KeyRelease>", self._filtrar_al_escribir)
        self.combo.bind("<Return>", self._confirmar_con_enter)
        self.combo.bind("<<ComboboxSelected>>", self._al_elegir_de_la_lista)
        self.combo.bind("<FocusOut>", self._al_perder_foco)

    def poner_opciones(self, opciones) -> None:
        self._opciones = list(opciones)
        self.combo["values"] = self._opciones
        if self._valor_confirmado not in self._opciones:
            self.elegir("")

    def elegir(self, valor: str) -> None:
        """Cambia el valor mostrado sin avisar al resto del programa."""
        self._valor_confirmado = valor
        self.variable.set(valor)

    def valor(self) -> str:
        return self._valor_confirmado

    def _coincidencias(self) -> list:
        escrito = normalizar_texto(self.variable.get())
        return [o for o in self._opciones if escrito in normalizar_texto(o)]

    def _filtrar_al_escribir(self, evento) -> None:
        if evento.keysym in TECLAS_QUE_NO_FILTRAN:
            return
        coincidencias = self._coincidencias()
        self.combo["values"] = coincidencias if coincidencias else self._opciones

    def _confirmar_con_enter(self, evento):
        coincidencias = self._coincidencias()
        if coincidencias:
            self._confirmar(coincidencias[0])
        else:
            self.combo.bell()
            self.variable.set(self._valor_confirmado)
        return "break"

    def _al_elegir_de_la_lista(self, evento) -> None:
        self._confirmar(self.variable.get())

    def _confirmar(self, valor: str) -> None:
        self.elegir(valor)
        self.combo["values"] = self._opciones
        self.combo.selection_clear()
        if self._al_seleccionar:
            self._al_seleccionar(valor)

    def _al_perder_foco(self, evento) -> None:
        self.variable.set(self._valor_confirmado)
        self.combo["values"] = self._opciones
