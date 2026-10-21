"""Lógica de distribución por cliente con existencias y asignaciones semanales."""
from dataclasses import dataclass, field

from configuracion import (
    CUOTA_REFRESCOS_POR_PUERTAS, MINIMO_CAJAS_REFRESCO_ADC,
    MODO_BULTO, MODO_CAJA, MODO_UNIDAD,
)
from inventario import Inventario, Producto
from utilidades import normalizar_codigo, normalizar_texto


@dataclass
class ClienteDistribucion:
    identificador: int
    nombre: str
    cep: str
    dia: str
    codigo_sistema: str
    clave: tuple
    puertas: int = 0


@dataclass
class Asignacion:
    cliente: "ClienteDistribucion"
    producto: Producto
    cantidad: int
    modo: str

    def texto(self) -> str:
        """Nomenclatura compacta para la plantilla: código limpio + cantidad + und/cj/bto."""
        codigo = normalizar_codigo(self.producto.codigo)
        sufijo = {MODO_CAJA: "cj", MODO_UNIDAD: "und", MODO_BULTO: "bto"}.get(self.modo, "cj")
        return f"{codigo} {self.cantidad}{sufijo}"


@dataclass
class EstadoNevera:
    puertas: int
    cuota_cajas: int
    asignadas_cajas: float
    incumple_minimo: bool
    excede_cuota: bool

    @property
    def hay_alerta(self) -> bool:
        return self.incumple_minimo or self.excede_cuota

    def texto(self) -> str:
        asignadas = f"{self.asignadas_cajas:.1f}".rstrip("0").rstrip(".")
        progreso = f"{asignadas}/{self.cuota_cajas} cj" if self.cuota_cajas else f"{asignadas} cj"
        texto = f"{self.puertas} puerta{'s' if self.puertas != 1 else ''} · {progreso}"
        if self.incumple_minimo:
            texto += f"  ⚠ mín. {MINIMO_CAJAS_REFRESCO_ADC} cj"
        if self.excede_cuota:
            texto += "  ⚠ excede"
        return texto


@dataclass
class ResumenStock:
    """Resumen agregado; cada producto conserva su propia medida (cajas/unidades/bultos)."""
    disponibles: int
    asignadas: int
    productos: int = 0
    detalle_disponibles: dict = field(default_factory=dict)
    detalle_asignadas: dict = field(default_factory=dict)
    detalle_restantes: dict = field(default_factory=dict)

    @property
    def restantes(self) -> int:
        return self.disponibles - self.asignadas


@dataclass
class FilaStock:
    descripcion: str
    disponibles: str
    asignadas: str
    restantes: str
    restantes_unidades: int


class Distribucion:
    """Mantiene cantidades por cliente-producto y modos CAJA/UNIDAD/BULTO.

    Los clientes de todos los días se mantienen cargados al mismo tiempo. El stock asignado
    y el autorrelleno consideran toda la semana, para no volver a repartir lo ya asignado
    cuando se cambia de día.
    """

    def __init__(self, inventario: Inventario):
        self.inventario = inventario
        self.clientes = []  # solo clientes del día seleccionado, visibles en la tabla
        self._clientes_por_clave = {}
        self._cantidades = {}  # (id_cliente, codigo_producto) -> cantidad expresada en su modo
        self._modos = {}       # (id_cliente, codigo_producto) -> CAJA / UNIDAD / BULTO
        self._siguiente_identificador = 1

    def cargar_inventario(self, inventario: Inventario) -> None:
        self.inventario = inventario
        self._cantidades.clear()
        self._modos.clear()

    def reemplazar_clientes(self, clientes) -> None:
        """Carga/actualiza el catálogo completo conservando IDs y asignaciones previas."""
        nuevos = []
        ocurrencias = {}
        for origen in clientes:
            dia = normalizar_texto(getattr(origen, "dia", ""))
            codigo = normalizar_texto(getattr(origen, "codigo_sistema", ""))
            cep = normalizar_texto(getattr(origen, "cep", ""))
            nombre = " ".join(str(getattr(origen, "nombre", "")).split())
            identidad = ("CODIGO", codigo) if codigo else (("CEP", cep) if cep else ("NOMBRE", normalizar_texto(nombre)))
            base = (dia, *identidad)
            ordinal = ocurrencias.get(base, 0)
            ocurrencias[base] = ordinal + 1
            clave = (*base, ordinal)
            cliente = self._clientes_por_clave.get(clave)
            if cliente is None:
                cliente = ClienteDistribucion(
                    self._siguiente_identificador, nombre, cep, dia, codigo, clave,
                    int(getattr(origen, "puertas", 0) or 0),
                )
                self._siguiente_identificador += 1
                self._clientes_por_clave[clave] = cliente
            else:
                cliente.nombre, cliente.cep, cliente.dia = nombre, cep, dia
                cliente.codigo_sistema = codigo
                cliente.puertas = int(getattr(origen, "puertas", 0) or 0)
            nuevos.append(cliente)
        self.clientes = nuevos

    def seleccionar_dia(self, dia: str) -> None:
        objetivo = normalizar_texto(dia)
        self.clientes = [c for c in self._clientes_por_clave.values() if c.dia == objetivo]

    def todos_los_clientes(self) -> list:
        return list(self._clientes_por_clave.values())

    # ---------- modos válidos para cada producto/cliente ----------
    def modos_permitidos(self, cliente: ClienteDistribucion, producto: Producto) -> tuple:
        if producto is None:
            return (MODO_CAJA, MODO_UNIDAD)
        if producto.es_bulto:
            return (MODO_BULTO,)
        if producto.solo_cajas:
            return (MODO_CAJA,)
        if producto.es_refresco and cliente.puertas > 0:
            return (MODO_CAJA,)
        return (MODO_CAJA, MODO_UNIDAD)

    def modo_predeterminado(self, cliente: ClienteDistribucion, producto: Producto) -> str:
        permitidos = self.modos_permitidos(cliente, producto)
        return permitidos[0] if len(permitidos) == 1 else MODO_CAJA

    def modo_de(self, cliente: ClienteDistribucion, producto: Producto) -> str:
        almacenado = self._modos.get((cliente.identificador, producto.codigo))
        permitidos = self.modos_permitidos(cliente, producto)
        return almacenado if almacenado in permitidos else self.modo_predeterminado(cliente, producto)

    def fijar_modo(self, cliente: ClienteDistribucion, producto: Producto, modo: str) -> str:
        permitidos = self.modos_permitidos(cliente, producto)
        modo_final = modo if modo in permitidos else self.modo_predeterminado(cliente, producto)
        self._modos[(cliente.identificador, producto.codigo)] = modo_final
        # El mínimo ADC se mide en cajas. Las asignaciones ADC de refrescos siempre van en caja.
        if producto.es_refresco and cliente.puertas > 0 and not producto.es_bulto:
            self._modos[(cliente.identificador, producto.codigo)] = MODO_CAJA
            return MODO_CAJA
        return modo_final

    def fijar_modo_a_todos(self, producto: Producto, modo: str) -> None:
        if producto is None:
            return
        for cliente in self.clientes:
            self.fijar_modo(cliente, producto, modo)

    # ---------- cantidades y conversión ----------
    def cantidad_de(self, cliente: ClienteDistribucion, codigo: str) -> int:
        return self._cantidades.get((cliente.identificador, normalizar_codigo(codigo)), 0)

    def establecer_cantidad(self, cliente: ClienteDistribucion, codigo: str, cantidad: int) -> int:
        codigo = normalizar_codigo(codigo)
        producto = next((p for p in self.inventario.todos() if normalizar_codigo(p.codigo) == codigo), None)
        valor = max(0, int(cantidad or 0))
        if producto and valor > 0 and producto.es_refresco and cliente.puertas > 0 and not producto.es_bulto:
            # Hasta confirmar otro criterio con el equipo, 6 cajas mínimo por cliente-producto.
            self.fijar_modo(cliente, producto, MODO_CAJA)
            valor = max(valor, MINIMO_CAJAS_REFRESCO_ADC)
        clave = (cliente.identificador, codigo)
        if valor > 0:
            self._cantidades[clave] = valor
        else:
            self._cantidades.pop(clave, None)
        return valor

    def unidades_asignadas(self, cliente: ClienteDistribucion, producto: Producto) -> int:
        cantidad = self.cantidad_de(cliente, producto.codigo)
        modo = self.modo_de(cliente, producto)
        if producto.es_bulto or modo == MODO_BULTO:
            return cantidad  # bultos sin conversión
        if modo == MODO_CAJA:
            return cantidad * producto.factor
        return cantidad

    # ---------- herramientas diarias/semanales ----------
    def establecer_valor_global(self, producto: Producto, valor: int) -> int:
        if producto is None or producto.stock_unidades <= 0:
            return 0
        for cliente in self.clientes:
            self.establecer_cantidad(cliente, producto.codigo, valor)
        return 1

    def limpiar(self, producto: Producto) -> None:
        if producto is None:
            return
        for cliente in self.clientes:
            self._cantidades.pop((cliente.identificador, normalizar_codigo(producto.codigo)), None)

    def limpiar_categoria(self, categoria: str) -> None:
        for producto in self.inventario.productos_de_categoria(categoria):
            self.limpiar(producto)

    def autorrellenar(self, producto: Producto) -> None:
        if producto is not None:
            self._repartir_producto(producto)

    def autorrellenar_categoria(self, categoria: str) -> int:
        productos = self.inventario.productos_de_categoria(categoria)
        for producto in productos:
            self._repartir_producto(producto)
        return len(productos)

    def _repartir_producto(self, producto: Producto) -> None:
        """Reparte solo el remanente de stock, sin borrar lo asignado a otros días."""
        if not self.clientes:
            return
        codigo = normalizar_codigo(producto.codigo)
        ids_actuales = {c.identificador for c in self.clientes}
        # Reasignar este día: se quitan sus valores del cálculo antes de repartir de nuevo.
        for cliente in self.clientes:
            self._cantidades.pop((cliente.identificador, codigo), None)

        asignadas_otros_dias = sum(
            self.unidades_asignadas(cliente, producto)
            for cliente in self.todos_los_clientes() if cliente.identificador not in ids_actuales
        )
        restante = max(0, int(producto.stock_unidades or 0) - asignadas_otros_dias)
        pasos, topes, minimos = {}, {}, {}
        for cliente in self.clientes:
            if producto.es_refresco and cliente.puertas > 0 and not producto.es_bulto:
                self.fijar_modo(cliente, producto, MODO_CAJA)
                minimos[cliente.identificador] = MINIMO_CAJAS_REFRESCO_ADC * producto.factor
                topes[cliente.identificador] = self._tope_por_nevera(cliente, producto)
            pasos[cliente.identificador] = self._unidades_por_paso(cliente, producto)

        recibido = {c.identificador: 0 for c in self.clientes}
        excluidos = set()
        for cliente in self.clientes:
            identificador = cliente.identificador
            if identificador not in minimos:
                continue
            minimo = minimos[identificador]
            tope = topes.get(identificador)
            if restante >= minimo and (tope is None or tope >= minimo):
                recibido[identificador] = minimo
                restante -= minimo
            else:
                excluidos.add(identificador)

        hubo_reparto = True
        while hubo_reparto:
            hubo_reparto = False
            for cliente in self.clientes:
                identificador = cliente.identificador
                paso = pasos[identificador]
                if identificador in excluidos or restante < paso:
                    continue
                tope = topes.get(identificador)
                if tope is not None and recibido[identificador] + paso > tope:
                    continue
                recibido[identificador] += paso
                restante -= paso
                hubo_reparto = True
        for cliente in self.clientes:
            paso = pasos[cliente.identificador]
            self.establecer_cantidad(cliente, codigo, recibido[cliente.identificador] // paso)

    def _unidades_por_paso(self, cliente: ClienteDistribucion, producto: Producto) -> int:
        modo = self.modo_de(cliente, producto)
        if producto.es_bulto or modo == MODO_BULTO:
            return 1
        return producto.factor if modo == MODO_CAJA else 1

    def _por_caja(self, producto: Producto) -> int:
        return max(1, int(producto.unidades_por_caja or 1))

    def _refrescos(self) -> list:
        return [p for p in self.inventario.todos() if p.es_refresco and not p.es_bulto]

    def _cajas_de_refrescos(self, cliente: ClienteDistribucion, excepto: Producto = None) -> float:
        return sum(
            self.unidades_asignadas(cliente, producto) / self._por_caja(producto)
            for producto in self._refrescos()
            if excepto is None or normalizar_codigo(producto.codigo) != normalizar_codigo(excepto.codigo)
        )

    def _tope_por_nevera(self, cliente: ClienteDistribucion, producto: Producto):
        cuota = CUOTA_REFRESCOS_POR_PUERTAS.get(cliente.puertas)
        if cuota is None:
            return None
        # Hasta consultar al equipo, la cuota se aplica individualmente a cada SKU.
        return max(0, int(cuota * self._por_caja(producto) + 1e-9))

    def estado_nevera(self, cliente: ClienteDistribucion, producto: Producto = None):
        if cliente.puertas <= 0 or producto is None or not producto.es_refresco or producto.es_bulto:
            return None
        cuota = CUOTA_REFRESCOS_POR_PUERTAS.get(cliente.puertas, 0)
        asignadas_cajas = self.unidades_asignadas(cliente, producto) / self._por_caja(producto)
        incumple = 0 < asignadas_cajas < MINIMO_CAJAS_REFRESCO_ADC
        excede = bool(cuota) and asignadas_cajas > cuota + 1e-9
        return EstadoNevera(cliente.puertas, cuota, asignadas_cajas, incumple, excede)

    # ---------- restaurar guardados ----------
    def restaurar_asignaciones(self, registros: list) -> int:
        """Importa valores leídos de las celdas de la plantilla. Cada registro identifica cliente/producto."""
        clientes = self.todos_los_clientes()
        productos = {normalizar_codigo(p.codigo): p for p in self.inventario.todos()}
        restauradas = 0
        for registro in registros:
            producto = productos.get(normalizar_codigo(registro.get("producto_codigo", "")))
            if producto is None:
                continue
            dia = normalizar_texto(registro.get("dia", ""))
            codigo_sistema = normalizar_texto(registro.get("codigo_sistema", ""))
            cep = normalizar_texto(registro.get("cep", ""))
            nombre = normalizar_texto(registro.get("cliente", ""))
            candidatos = [c for c in clientes if c.dia == dia]
            cliente = next((c for c in candidatos if codigo_sistema and c.codigo_sistema == codigo_sistema), None)
            if cliente is None:
                cliente = next((c for c in candidatos if cep and normalizar_texto(c.cep) == cep), None)
            if cliente is None:
                cliente = next((c for c in candidatos if normalizar_texto(c.nombre) == nombre), None)
            if cliente is None:
                continue
            modo = str(registro.get("modo", MODO_CAJA)).upper()
            self.fijar_modo(cliente, producto, modo)
            self.establecer_cantidad(cliente, producto.codigo, int(registro.get("cantidad", 0) or 0))
            if self.cantidad_de(cliente, producto.codigo) > 0:
                restauradas += 1
        return restauradas

    def asignaciones(self) -> list:
        """Devuelve el estado completo de clientes/productos para guardarlo en Excel."""
        resultado = []
        productos = {normalizar_codigo(p.codigo): p for p in self.inventario.todos()}
        clientes = sorted(self.todos_los_clientes(), key=lambda c: (c.dia, c.identificador))
        for cliente in clientes:
            for codigo, producto in productos.items():
                cantidad = self.cantidad_de(cliente, codigo)
                if cantidad <= 0:
                    continue
                resultado.append(Asignacion(
                    cliente=cliente,
                    producto=producto,
                    cantidad=cantidad,
                    modo=self.modo_de(cliente, producto),
                ))
        return resultado

    # ---------- stock agregado de toda la semana ----------
    def resumen_de(self, producto: Producto) -> ResumenStock:
        asignadas = sum(self.unidades_asignadas(c, producto) for c in self.todos_los_clientes())
        return ResumenStock(int(producto.stock_unidades or 0), asignadas, productos=1)

    @staticmethod
    def _acumular_medida(detalle: dict, producto: Producto, cantidad: int) -> None:
        if producto.es_bulto:
            clave = "bultos" if cantidad >= 0 else "exceso_bultos"
            detalle[clave] = detalle.get(clave, 0) + abs(cantidad)
            return
        if cantidad < 0:
            detalle["exceso_unidades"] = detalle.get("exceso_unidades", 0) + abs(cantidad)
            return
        cajas, sueltas = divmod(cantidad, producto.factor)
        detalle["cajas"] = detalle.get("cajas", 0) + cajas
        detalle["unidades"] = detalle.get("unidades", 0) + sueltas

    def totales_de_categoria(self, categoria: str) -> ResumenStock:
        disponibles = asignadas = 0
        detalle_disp, detalle_asig, detalle_rest = {}, {}, {}
        productos = self.inventario.productos_de_categoria(categoria)
        for producto in productos:
            resumen = self.resumen_de(producto)
            disponibles += resumen.disponibles
            asignadas += resumen.asignadas
            self._acumular_medida(detalle_disp, producto, resumen.disponibles)
            self._acumular_medida(detalle_asig, producto, resumen.asignadas)
            self._acumular_medida(detalle_rest, producto, resumen.restantes)
        return ResumenStock(disponibles, asignadas, len(productos), detalle_disp, detalle_asig, detalle_rest)

    @staticmethod
    def _formatear_stock(cantidad: int, producto: Producto) -> str:
        if producto.es_bulto:
            if cantidad < 0:
                return f"Exceso {abs(cantidad)} bulto{'s' if abs(cantidad) != 1 else ''}"
            return f"{cantidad} bulto{'s' if cantidad != 1 else ''}"
        if cantidad < 0:
            return f"Exceso {abs(cantidad):,} und"
        cajas, sueltas = divmod(cantidad, producto.factor)
        if sueltas:
            return f"{cajas} cj + {sueltas} und ({cantidad:,} und)"
        return f"{cajas} cj ({cantidad:,} und)"

    def filas_de_stock(self, categoria: str) -> list:
        filas = []
        for producto in self.inventario.productos_de_categoria(categoria):
            resumen = self.resumen_de(producto)
            filas.append(FilaStock(
                descripcion=f"{producto.descripcion} [{producto.codigo}]",
                disponibles=self._formatear_stock(resumen.disponibles, producto),
                asignadas=self._formatear_stock(resumen.asignadas, producto),
                restantes=self._formatear_stock(resumen.restantes, producto),
                restantes_unidades=resumen.restantes,
            ))
        return filas

    def resumen_semanal(self) -> list:
        """Registros de todos los productos, con las asignaciones acumuladas de los días cargados."""
        resultado = []
        for producto in self.inventario.todos():
            resumen = self.resumen_de(producto)
            resultado.append({
                "codigo": producto.codigo,
                "producto": producto.descripcion,
                "categoria": producto.categoria_filtro,
                "disponible": self._formatear_stock(resumen.disponibles, producto),
                "asignado": self._formatear_stock(resumen.asignadas, producto),
                "restante": self._formatear_stock(resumen.restantes, producto),
                "restantes_base": resumen.restantes,
            })
        return resultado
