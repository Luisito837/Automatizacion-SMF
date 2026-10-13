"""Recuerda los nombres de los vendedores entre una sesión y otra."""
from pathlib import Path


class ArchivoVendedores:
    def __init__(self, ruta):
        self.ruta = Path(ruta)

    def leer(self) -> list:
        if not self.ruta.exists():
            return []
        return [linea.strip() for linea in self.ruta.read_text(encoding="utf-8").splitlines() if linea.strip()]

    def guardar(self, nombres) -> None:
        self.ruta.write_text("\n".join(nombres), encoding="utf-8")
