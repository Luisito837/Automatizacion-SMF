"""Lógica de distribución de productos entre clientes, sin interfaz gráfica."""
from dataclasses import dataclass

from configuracion import CUOTA_REFRESCOS_POR_PUERTAS, MINIMO_CAJAS_REFRESCO_ADC, MODO_CAJA
from inventario import Inventario, Producto
from utilidades import formatear_cantidad, normalizar_texto


@dataclass
class ClienteDistribucion:
    """Cliente del catálogo preparado para recibir asignaciones durante la sesión."""
    identificador: int
    nombre: str
    cep: str
    dia: str
    codigo_sistema: str
    clave: tuple
    puertas: int = 0  # puertas de la nevera ADC; 0 si no tiene


@dataclass
class Asignacion:
    """Lo que se le asignó a un cliente de un producto, tal como se exporta."""
    cliente: "ClienteDistribucion"
    producto: Producto
    cantidad: int
    modo: str

    def texto(self) -> str:
        """Formato de exportación: codigo_producto + espacio + numero + und/cj. Ej.: 'F07103 5 cj'."""
        sufijo = "cj" if self.modo == MODO_CAJA else "und"
        return f"{self.producto.codigo} {self.cantidad} {sufijo}"


@dataclass
class EstadoNevera:
    """Cómo va un cliente con nevera ADC respecto a la regla de refrescos (en cajas)."""
    puertas: int
    cuota_cajas: int  # cuota de prioridad; 0 si no hay cuota definida para esas puertas
    asignadas_cajas: float
    incumple_minimo: bool

    @property
    def hay_alerta(self) -> bool:
        return self.incumple_minimo

    def texto(self) -> str:
        asignadas = f"{self.asignadas_cajas:.1f}".rstrip("0").rstrip(".")
        progreso = f"{asignadas}/{self.cuota_cajas} cj" if self.cuota_cajas else f"{asignadas} cj"
        texto = f"{self.puertas} puerta{'s' if self.puertas != 1 else ''} · {progreso}"
        if self.incumple_minimo:
            texto += f"  ⚠ mín. {MINIMO_CAJAS_REFRESCO_ADC} cj"
        return texto


@dataclass
class ResumenStock:
    """Todo se calcula en unidades; restantes puede ser negativo si hay exceso."""
    disponibles: int
    asignadas: int

    @property
    def restantes(self) -> int:
        return self.disponibles - self.asignadas


@dataclass
class FilaStock:
    """Una fila ya preparada para mostrarse en el panel de stock."""
    descripcion: str
    disponibles: str
    asignadas: str
    restantes: str
    restantes_unidades: int


class Distribucion:
    """Guarda la cantidad y el modo de reporte de cada cliente para cada producto.

    La cantidad escrita se interpreta como CAJA (número x unidades por caja) o UNIDAD.
    Tanto la cantidad como el modo se guardan por cliente y código de producto.
    """

    def __init__(self, inventario: Inventario):
        self.inventario = inventario
        self.clientes = []  # clientes del día actualmente seleccionado
        self._clientes_por_clave = {}
        self._cantidades = {}  # (id_cliente, codigo_producto) -> cantidad escrita
        self._modos = {}       # (id_cliente, codigo_producto) -> CAJA o UNIDAD
        self._siguiente_identificador = 1

    # ---------- inventario y clientes ----------
    def cargar_inventario(self, inventario: Inventario) -> None:
        """Reemplaza el stock del reporte y reinicia las asignaciones de esta sesión."""
        self.inventario = inventario
        self._cantidades.clear()
        self._modos.clear()

    def reemplazar_clientes(self, clientes) -> None:
        """Activa los clientes de un día y conserva asignaciones si ya se habían cargado.

        La clave incorpora el día y prefiere código del sistema, después CEP y finalmente
        nombre. Si hay duplicados en la plantilla, se agrega un ordinal para distinguirlos.
        """
        nuevos = []
        ocurrencias = {}
        for origen in clientes:
            dia = normalizar_texto(getattr(origen, "dia", ""))
            codigo = normalizar_texto(getattr(origen, "codigo_sistema", ""))
            cep = normalizar_texto(getattr(origen, "cep", ""))
            nombre = " ".join(str(getattr(origen, "nombre", "")).split())
            identidad = ("CODIGO", codigo) if codigo else (
                ("CEP", cep) if cep else ("NOMBRE", normalizar_texto(nombre))
            )
            base = (dia, *identidad)
            ordinal = ocurrencias.get(base, 0)
            ocurrencias[base] = ordinal + 1
            clave = (*base, ordinal)

            cliente = self._clientes_por_clave.get(clave)
            if cliente is None:
                cliente = ClienteDistribucion(
                    identificador=self._siguiente_identificador,
                    nombre=nombre,
                    cep=cep,
                    dia=dia,
                    codigo_sistema=codigo,
                    clave=clave,
                    puertas=int(getattr(origen, "puertas", 0) or 0),
                )
                self._siguiente_identificador += 1
                self._clientes_por_clave[clave] = cliente
            else:
                # Mantiene el identificador, pero refresca los datos visibles del catálogo.
                cliente.nombre = nombre
                cliente.cep = cep
                cliente.dia = dia
                cliente.codigo_sistema = codigo
                cliente.puertas = int(getattr(origen, "puertas", 0) or 0)
            nuevos.append(cliente)
        self.clientes = nuevos

    # ---------- modo caja / unidad ----------
    def modo_de(self, cliente: ClienteDistribucion, producto: Producto) -> str:
        return self._modos.get((cliente.identificador, producto.codigo), MODO_CAJA)

    def fijar_modo(self, cliente: ClienteDistribucion, producto: Producto, modo: str) -> None:
        self._modos[(cliente.identificador, producto.codigo)] = modo

    def fijar_modo_a_todos(self, producto: Producto, modo: str) -> None:
        for cliente in self.clientes:
            self.fijar_modo(cliente, producto, modo)

    # ---------- cantidades ----------
    def cantidad_de(self, cliente: ClienteDistribucion, codigo: str) -> int:
        return self._cantidades.get((cliente.identificador, codigo), 0)

    def establecer_cantidad(self, cliente: ClienteDistribucion, codigo: str, cantidad: int) -> None:
        clave = (cliente.identificador, codigo)
        if cantidad > 0:
            self._cantidades[clave] = cantidad
        else:
            self._cantidades.pop(clave, None)

    def unidades_asignadas(self, cliente: ClienteDistribucion, producto: Producto) -> int:
        cantidad = self.cantidad_de(cliente, producto.codigo)
        return cantidad * self._unidades_por_paso(cliente, producto)

    def _unidades_por_paso(self, cliente: ClienteDistribucion, producto: Producto) -> int:
        if self.modo_de(cliente, producto) == MODO_CAJA:
            return max(1, int(producto.unidades_por_caja or 1))
        return 1

    # ---------- herramientas para el producto seleccionado ----------
    def establecer_valor_global(self, producto: Producto, valor: int) -> int:
        """Aplica el mismo número a todos los clientes si el producto tiene stock."""
        if producto is None or producto.stock_unidades <= 0:
            return 0
        for cliente in self.clientes:
            self.establecer_cantidad(cliente, producto.codigo, valor)
        return 1

    def limpiar(self, producto: Producto) -> None:
        if producto is None:
            return
        for cliente in self.clientes:
            self.establecer_cantidad(cliente, producto.codigo, 0)

    def autorrellenar(self, producto: Producto) -> None:
        """Distribuye el stock del producto entre los clientes respetando CAJA/UNIDAD."""
        if producto is not None:
            self._repartir_producto(producto)

    def _repartir_producto(self, producto: Producto) -> None:
        """Reparte el stock en partes iguales. En refrescos aplica la regla de neveras ADC:

        1. el cliente con nevera reporta en CAJA y recibe primero como mínimo
           MINIMO_CAJAS_REFRESCO_ADC cajas de ese producto (o nada, si no alcanza el stock);
        2. luego se le da prioridad hasta completar su cuota de refrescos (25 cajas con
           1 puerta, 60 con 2), contando lo que ya tiene de los otros refrescos;
        3. lo que quede se reparte en partes iguales entre todos. La cuota NO es un límite:
           un cliente con nevera puede terminar con más de su cuota.
        """
        if not self.clientes:
            return
        pasos, minimos, objetivos = {}, {}, {}
        for cliente in self.clientes:
            if producto.es_refresco and cliente.puertas > 0:
                self.fijar_modo(cliente, producto, MODO_CAJA)  # la regla se expresa en cajas
                minimos[cliente.identificador] = MINIMO_CAJAS_REFRESCO_ADC * self._por_caja(producto)
                objetivos[cliente.identificador] = self._cuota_pendiente(cliente, producto)
            pasos[cliente.identificador] = self._unidades_por_paso(cliente, producto)

        recibido = {cliente.identificador: 0 for cliente in self.clientes}
        restante = max(0, int(producto.stock_unidades or 0))
        excluidos = set()  # clientes con nevera a quienes no les alcanza para el mínimo
        for cliente in self.clientes:
            identificador = cliente.identificador
            if identificador not in minimos:
                continue
            if restante >= minimos[identificador]:
                recibido[identificador] = minimos[identificador]
                restante -= minimos[identificador]
            else:
                excluidos.add(identificador)

        # Prioridad: los clientes con nevera se acercan a su cuota antes que el resto.
        hubo_reparto = True
        while hubo_reparto:
            hubo_reparto = False
            for cliente in self.clientes:
                identificador = cliente.identificador
                paso = pasos[identificador]
                if identificador not in objetivos or identificador in excluidos or restante < paso:
                    continue
                if recibido[identificador] + paso > objetivos[identificador]:
                    continue
                recibido[identificador] += paso
                restante -= paso
                hubo_reparto = True

        # Reparto parejo de lo que queda, sin tope.
        hubo_reparto = True
        while hubo_reparto:
            hubo_reparto = False
            for cliente in self.clientes:
                identificador = cliente.identificador
                paso = pasos[identificador]
                if identificador in excluidos or restante < paso:
                    continue
                recibido[identificador] += paso
                restante -= paso
                hubo_reparto = True
        for cliente in self.clientes:
            paso = pasos[cliente.identificador]
            self.establecer_cantidad(cliente, producto.codigo, recibido[cliente.identificador] // paso)

    @staticmethod
    def _por_caja(producto: Producto) -> int:
        return max(1, int(producto.unidades_por_caja or 1))

    def _refrescos(self) -> list:
        return [p for p in self.inventario.todos() if p.es_refresco]

    def _cajas_de_refrescos(self, cliente: ClienteDistribucion, excepto: Producto = None) -> float:
        return sum(
            self.unidades_asignadas(cliente, p) / self._por_caja(p)
            for p in self._refrescos() if excepto is None or p.codigo != excepto.codigo
        )

    def _cuota_pendiente(self, cliente: ClienteDistribucion, producto: Producto) -> int:
        """Unidades de este producto que le faltan para completar su cuota de refrescos (0 si no hay cuota)."""
        cuota = CUOTA_REFRESCOS_POR_PUERTAS.get(cliente.puertas)
        if cuota is None:
            return 0
        libres = cuota - self._cajas_de_refrescos(cliente, excepto=producto)
        return max(0, int(libres * self._por_caja(producto) + 1e-9))

    def estado_nevera(self, cliente: ClienteDistribucion):
        """Estado de la regla para un cliente con nevera ADC; None si no tiene."""
        if cliente.puertas <= 0:
            return None
        cuota = CUOTA_REFRESCOS_POR_PUERTAS.get(cliente.puertas, 0)
        total = self._cajas_de_refrescos(cliente)
        incumple = any(
            0 < self.unidades_asignadas(cliente, p) < MINIMO_CAJAS_REFRESCO_ADC * self._por_caja(p)
            for p in self._refrescos()
        )
        return EstadoNevera(cliente.puertas, cuota, total, incumple)

    # ---------- exportación ----------
    def asignaciones(self) -> list:
        """Todas las asignaciones mayores a 0 de todos los días que se han visitado en la sesión."""
        productos = {p.codigo: p for p in self.inventario.todos()}
        clientes = {c.identificador: c for c in self._clientes_por_clave.values()}
        resultado = []
        for (id_cliente, codigo), cantidad in self._cantidades.items():
            cliente, producto = clientes.get(id_cliente), productos.get(codigo)
            if cliente and producto and cantidad > 0:
                resultado.append(Asignacion(cliente, producto, cantidad, self.modo_de(cliente, producto)))
        return sorted(resultado, key=lambda a: (a.cliente.identificador, a.producto.descripcion))

    # ---------- stock ----------
    def resumen_de(self, producto: Producto) -> ResumenStock:
        asignadas = sum(self.unidades_asignadas(c, producto) for c in self.clientes)
        return ResumenStock(int(producto.stock_unidades or 0), asignadas)

    def totales_de_categoria(self, categoria: str) -> ResumenStock:
        disponibles = asignadas = 0
        for producto in self.inventario.productos_de_categoria(categoria):
            resumen = self.resumen_de(producto)
            disponibles += resumen.disponibles
            asignadas += resumen.asignadas
        return ResumenStock(disponibles, asignadas)

    def filas_de_stock(self, categoria: str) -> list:
        filas = []
        for producto in self.inventario.productos_de_categoria(categoria):
            resumen = self.resumen_de(producto)
            por_caja = max(1, int(producto.unidades_por_caja or 1))
            filas.append(FilaStock(
                descripcion=producto.descripcion,
                disponibles=formatear_cantidad(resumen.disponibles, por_caja),
                asignadas=formatear_cantidad(resumen.asignadas, por_caja),
                restantes=formatear_cantidad(resumen.restantes, por_caja),
                restantes_unidades=resumen.restantes,
            ))
        return filas
