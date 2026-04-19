import flet as ft
import random
import smtplib
from smtplib import SMTPRecipientsRefused, SMTPException
import os
import time
import re
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading 
from base_de_datos import BaseDeDatos
from ventana_mensaje import GestorMensajes

load_dotenv(override=True)

REMITENTE = os.getenv("EMAIL_REMITENTE")
PASSWORD = os.getenv("EMAIL_PASSWORD")

class Carniceria:
    def __init__(self, page: ft.Page):
        self.page = page
        
        self.bd = BaseDeDatos()
        self.codigo_generado = ""
        self.datos_temporales_registro = {}

    def navegar(self, ruta):
        self.page.route = ruta
        self.cambio_de_ruta(None)

    def mostrar_alerta(self, titulo, mensaje, tipo="info"):
        GestorMensajes.mostrar(self.page, titulo, mensaje, tipo)

    def cambio_de_ruta(self, route_event=None):
        ruta_actual = self.page.route
        print(f">>> FLET: Dibujando pantalla -> {ruta_actual}")
        
        self.page.views.clear()
        
        if ruta_actual == "/registro":
            self.page.views.append(self.vista_registro())
        elif ruta_actual == "/validacion":
            self.page.views.append(self.vista_validacion())
        elif ruta_actual == "/admin":
            self.page.views.append(self.vista_admin())
        else:
            self.page.views.append(self.vista_login())
            
        self.page.update()

    # ==========================================
    # VISTAS DE AUTENTICACIÓN
    # ==========================================

    def vista_login(self):
        txt_email = ft.TextField(label="Correo Electrónico", width=300, prefix_icon=ft.Icons.EMAIL)
        txt_pass = ft.TextField(label="Contraseña", password=True, can_reveal_password=True, width=300, prefix_icon=ft.Icons.LOCK)

        def intentar_login(e):
            email_limpio = (txt_email.value or "").strip()
            pass_limpia = (txt_pass.value or "").strip()

            if not email_limpio or not pass_limpia:
                self.mostrar_alerta("Campos Incompletos", "Por favor, completá tu correo y contraseña.", "error")
                return
            
            exito, mensaje = self.bd.verificar_login(email_limpio, pass_limpia)
            if exito:
                # Si el login es exitoso, navegamos al panel de administrador
                self.navegar("/admin")
            else:
                self.mostrar_alerta("Error de Acceso", mensaje, "error")

        return ft.View(
            route="/login",
            vertical_alignment=ft.MainAxisAlignment.START,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    padding=ft.Padding.only(top=120),
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Icon(ft.Icons.LOCAL_FIRE_DEPARTMENT, size=80, color=ft.Colors.ORANGE_700),
                            ft.Text("FUEGO & FIERRO", size=30, weight=ft.FontWeight.BOLD),
                            ft.Text("Ingreso al Sistema", size=16, color=ft.Colors.GREY_700),
                            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                            txt_email,
                            txt_pass,
                            ft.Button(
                                content=ft.Text("Ingresar", color=ft.Colors.WHITE), 
                                on_click=intentar_login, 
                                width=300, 
                                bgcolor=ft.Colors.ORANGE_700
                            ),
                            ft.TextButton("¿No tenés cuenta? Registrate acá", on_click=lambda _: self.navegar("/registro"))
                        ]
                    )
                )
            ]
        )

    def vista_registro(self):
        txt_nombre = ft.TextField(label="Nombre", width=300)
        txt_apellido = ft.TextField(label="Apellido", width=300)
        txt_email = ft.TextField(label="Correo Electrónico", width=300)
        txt_pass = ft.TextField(label="Contraseña", password=True, can_reveal_password=True, width=300)
        txt_pass_conf = ft.TextField(label="Confirmar Contraseña", password=True, can_reveal_password=True, width=300)

        def enviar_codigo(e):
            nombre_limpio = (txt_nombre.value or "").strip()
            apellido_limpio = (txt_apellido.value or "").strip()
            email_limpio = (txt_email.value or "").strip()
            pass_limpia = (txt_pass.value or "").strip()
            pass_conf_limpia = (txt_pass_conf.value or "").strip()

            if not all([nombre_limpio, apellido_limpio, email_limpio, pass_limpia, pass_conf_limpia]):
                self.mostrar_alerta("Campos Incompletos", "Completá todos los datos para poder registrarte.", "error")
                return
            
            patron_correo = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)+$"
            if not re.match(patron_correo, email_limpio):
                self.mostrar_alerta(
                    "Correo Inválido", 
                    "El formato del correo no es válido. Revisá que no tenga dobles puntos ni símbolos extraños.", 
                    "error"
                )
                return

            if pass_limpia != pass_conf_limpia:
                self.mostrar_alerta("Contraseñas", "Las contraseñas no coinciden.", "error")
                return
            
            if self.bd.verificar_correo_existente(email_limpio):
                self.mostrar_alerta(
                    "Usuario Existente", 
                    "Ya existe una cuenta registrada con este correo electrónico. Por favor, iniciá sesión.", 
                    "error"
                )
                return  

            loader = GestorMensajes.mostrar_cargando(self.page, "Corroborando y enviando todo...")

            self.codigo_generado = str(random.randint(100000, 999999))
            self.datos_temporales_registro = {
                "nombre": nombre_limpio, "apellido": apellido_limpio,
                "email": email_limpio, "password": pass_limpia 
            }
            
            msg = MIMEMultipart()
            msg['From'] = REMITENTE
            msg['To'] = email_limpio
            msg['Subject'] = "Código de Verificación - Fuego & Fierro"
            cuerpo_mensaje = f"Hola {nombre_limpio}, tu código es: {self.codigo_generado}"
            msg.attach(MIMEText(cuerpo_mensaje, 'plain', 'utf-8'))

            def tarea_envio_correo():
                try:
                    server = smtplib.SMTP('smtp.gmail.com', 587)
                    server.starttls()
                    server.login(REMITENTE, PASSWORD)
                    server.send_message(msg)
                    server.quit()
                    
                    GestorMensajes.cerrar_cargando(self.page, loader)
                    self.mostrar_alerta("Código Enviado", f"Revisá tu bandeja en {email_limpio}", "exito")
                    self.navegar("/validacion")
                    
                except Exception as err:
                    GestorMensajes.cerrar_cargando(self.page, loader)
                    print(f">>> ERROR DE ENVÍO: {err}")
                    self.mostrar_alerta(
                        "Error de Envío", 
                        "No se pudo conectar con el servidor de correo. Verificá tu conexión.", 
                        "error"
                    )

            threading.Thread(target=tarea_envio_correo).start()

        return ft.View(
            route="/registro",
            vertical_alignment=ft.MainAxisAlignment.START,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    padding=ft.Padding.only(top=80),
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Text("Registro de Empleado", size=25, weight=ft.FontWeight.BOLD),
                            txt_nombre, txt_apellido, txt_email, txt_pass, txt_pass_conf,
                            ft.Button(
                                content=ft.Text("Solicitar Código"), 
                                on_click=enviar_codigo, 
                                width=300
                            ),
                            ft.TextButton("Volver al Login", on_click=lambda _: self.navegar("/login"))
                        ]
                    )
                )
            ]
        )

    def vista_validacion(self):
        txt_codigo = ft.TextField(label="Ingresá el código de 6 dígitos", width=300, text_align=ft.TextAlign.CENTER)

        def confirmar_registro(e):
            codigo_limpio = (txt_codigo.value or "").strip()

            if codigo_limpio == self.codigo_generado:
                datos = self.datos_temporales_registro
                exito, msj = self.bd.registrar_usuario(
                    datos["nombre"], datos["apellido"], datos["email"], datos["password"]
                )
                if exito:
                    self.mostrar_alerta("¡Cuenta Creada!", msj, "exito")
                    self.navegar("/login")
                else:
                    self.mostrar_alerta("Fallo en el Registro", msj, "error")
            else:
                self.mostrar_alerta("Validación Fallida", "El código es incorrecto.", "error")

        return ft.View(
            route="/validacion",
            vertical_alignment=ft.MainAxisAlignment.START,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    padding=ft.Padding.only(top=120),
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Icon(ft.Icons.MARK_EMAIL_READ, size=60, color=ft.Colors.BLUE_600),
                            ft.Text("Verificación de Correo", size=25, weight=ft.FontWeight.BOLD),
                            txt_codigo,
                            ft.Button(
                                content=ft.Text("Confirmar y Registrar", color=ft.Colors.WHITE), 
                                on_click=confirmar_registro, 
                                width=300, 
                                bgcolor=ft.Colors.GREEN_600
                            ),
                            ft.TextButton("Cancelar", on_click=lambda _: self.navegar("/registro"))
                        ]
                    )
                )
            ]
        )
    
    def seccion_usuarios(self):
        import asyncio # Importamos la librería nativa para tareas en segundo plano
        
        tabla_usuarios = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ID")), ft.DataColumn(ft.Text("Nombre")), 
                ft.DataColumn(ft.Text("Email")), ft.DataColumn(ft.Text("Rol")), 
                ft.DataColumn(ft.Text("Estado")), ft.DataColumn(ft.Text("Acción"))
            ],
            rows=[]
        )

        def cargar_filas():
            usuarios_totales = self.bd.obtener_usuarios()
            usuarios_visibles = [u for u in usuarios_totales if u["rol_nombre"] != "Administrador"]
            filas_nuevas = []
            for u in usuarios_visibles:
                filas_nuevas.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(str(u["id"]))),
                        ft.DataCell(ft.Text(u["nombre"], weight=ft.FontWeight.BOLD)),
                        ft.DataCell(ft.Text(u["email"], color=ft.Colors.GREY_700)),
                        ft.DataCell(ft.Text(u["rol_nombre"] if u["rol_nombre"] else "Pendiente")),
                        ft.DataCell(ft.Text("Activo" if u["activo"] == 1 else "Inactivo", 
                                           color=ft.Colors.GREEN_700 if u["activo"] == 1 else ft.Colors.RED_700)),
                        ft.DataCell(ft.IconButton(ft.Icons.MANAGE_ACCOUNTS, on_click=lambda e, user=u: abrir_modal_gestion(e, user)))
                    ])
                )
            return filas_nuevas

        tabla_usuarios.rows = cargar_filas()

        def abrir_modal_gestion(e, usuario_actual):
            self.page.overlay.clear()
            
            txt_nombre = ft.TextField(label="Empleado", value=usuario_actual["nombre"], read_only=True, width=300)
            
            # 1. El menú de Estado sigue siendo Dropdown
            dd_estado = ft.Dropdown(
                label="Estado de Acceso", width=300,
                options=[ft.dropdown.Option("1", "Activo (Aprobado)"), ft.dropdown.Option("0", "Inactivo / Suspendido")],
                value="1" if usuario_actual["activo"] == 1 else "0"
            )

            # 2. La función de bloqueo se mantiene intacta
            def controlar_bloqueo_admin(e):
                if dd_rol.value == "1":  # Si selecciona Administrador
                    dd_estado.value = "1"
                    dd_estado.disabled = True
                else:  # Si selecciona Cajero
                    dd_estado.disabled = False
                dd_estado.update()

            # 3. EL TRUCO: Reemplazamos el Dropdown rebelde por un RadioGroup elegante.
            # Al inyectar el on_change acá adentro, el evento funcionará de forma instantánea.
            dd_rol = ft.RadioGroup(
                content=ft.Container(
                    width=300,
                    padding=ft.padding.only(top=10, bottom=10),
                    content=ft.Row([
                        ft.Text("Rol Asignado:", color=ft.Colors.GREY_700, weight=ft.FontWeight.BOLD),
                        ft.Radio(value="1", label="Admin", active_color=ft.Colors.BLUE_600),
                        ft.Radio(value="2", label="Cajero", active_color=ft.Colors.BLUE_600)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                ),
                value=str(usuario_actual["rolID"]) if usuario_actual["rolID"] else None,
                on_change=controlar_bloqueo_admin
            )
            
            # 4. Bloqueo visual inicial al abrir la ventana si el usuario ya era Administrador
            if dd_rol.value == "1":
                dd_estado.value = "1"
                dd_estado.disabled = True

            # Botón Cancelar ahora también es asíncrono para cerrarse limpiamente
            async def cerrar_modal(e=None):
                dialogo_gestion.open = False
                self.page.update()
                await asyncio.sleep(0.3) # Espera visual sin congelar
                if dialogo_gestion in self.page.overlay:
                    self.page.overlay.remove(dialogo_gestion)
                self.page.update()

            btn_cancelar = ft.TextButton("Cancelar", on_click=cerrar_modal)
            btn_guardar = ft.Button("Guardar", bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE)

            # ========================================================
            # FUNCIÓN ACTUALIZADA: Cierre previo a la advertencia
            # ========================================================
            async def guardar_permisos(e):
                nuevo_rol_id = int(dd_rol.value) if dd_rol.value else None
                nuevo_estado = int(dd_estado.value) if dd_estado.value else 0

                # 1. Validación de seguridad básica
                if nuevo_estado == 1 and nuevo_rol_id is None:
                    self.mostrar_alerta("Atención", "Asigná un rol antes de aprobar el acceso.", "error")
                    return

                # 2. VALIDACIÓN DE CAMBIOS: Cierre y luego alerta
                if nuevo_rol_id == usuario_actual["rolID"] and nuevo_estado == usuario_actual["activo"]:
                    # Primero cerramos la ventana de edición
                    dialogo_gestion.open = False
                    self.page.update()
                    
                    # Pausa necesaria para que la animación de cierre termine en primer plano
                    await asyncio.sleep(0.4)
                    
                    # Limpiamos el overlay para asegurar que no queden rastros visuales
                    if dialogo_gestion in self.page.overlay:
                        self.page.overlay.remove(dialogo_gestion)
                        self.page.update()
                    
                    # Ahora mostramos la advertencia sobre la pantalla limpia
                    self.mostrar_alerta(
                        "Sin modificaciones", 
                        "No se realizaron cambios porque el rol y el estado son idénticos a los actuales. El proceso se canceló y no se envió ningún correo.", 
                        "info"
                    )
                    return

                # 3. Si hay cambios, procedemos con el bloqueo y el envío (Primer Plano)
                btn_guardar.content = ft.Row([
                    ft.ProgressRing(width=16, height=16, color=ft.Colors.WHITE, stroke_width=2),
                    ft.Text("Notificando...", color=ft.Colors.WHITE)
                ], tight=True)
                
                btn_guardar.disabled = True
                btn_cancelar.disabled = True
                dd_rol.disabled = True
                dd_estado.disabled = True
                self.page.update()

                nombre_rol = "Administrador" if nuevo_rol_id == 1 else "Cajero"
                nombre_estado = "ACTIVO / APROBADO" if nuevo_estado == 1 else "INACTIVO / SUSPENDIDO"

                # Función que empaqueta el trabajo en segundo plano
                def trabajo_pesado_en_segundo_plano():
                    try:
                        # (Mantenemos la lógica de smtplib y BD igual...)
                        import smtplib
                        from email.mime.text import MIMEText
                        from email.mime.multipart import MIMEMultipart
                        
                        msg = MIMEMultipart()
                        msg['From'] = REMITENTE
                        msg['To'] = usuario_actual["email"]
                        msg['Subject'] = "Actualización de Permisos - Fuego & Fierro"
                        
                        cuerpo = (
                            f"Hola {usuario_actual['nombre']},\n\n"
                            f"Te informamos que se han actualizado tus permisos en el sistema:\n"
                            f"- Nuevo Rol: {nombre_rol}\n"
                            f"- Estado de Acceso: {nombre_estado}\n\n"
                            f"Si tu estado es ACTIVO, ya podés ingresar con tus credenciales habituales.\n"
                            f"Saludos, Equipo de Fuego & Fierro."
                        )
                        msg.attach(MIMEText(cuerpo, 'plain', 'utf-8'))

                        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=10)
                        server.starttls()
                        server.login(REMITENTE, PASSWORD)
                        server.send_message(msg)
                        server.quit()

                        exito_bd, msj_bd = self.bd.actualizar_permisos_usuario(
                            usuario_actual["id"], nuevo_rol_id, nuevo_estado
                        )
                        return exito_bd, msj_bd
                    
                    except (SMTPException, OSError):
                        return False, "No se pudo enviar el correo. Verificá tu internet."
                    except Exception as ex:
                        return False, str(ex)

                # Ejecutamos el envío sin bloquear la interfaz
                exito, msj_resultado = await asyncio.to_thread(trabajo_pesado_en_segundo_plano)

                if exito:
                    dialogo_gestion.open = False
                    self.page.update()
                    await asyncio.sleep(0.4)
                    
                    if dialogo_gestion in self.page.overlay:
                        self.page.overlay.remove(dialogo_gestion)
                        
                    tabla_usuarios.rows = cargar_filas()
                    self.page.update()
                    self.mostrar_alerta("Éxito", "Cambios aplicados y empleado notificado.", "exito")
                else:
                    # Restauramos el estado si el envío falla
                    btn_guardar.content = ft.Text("Guardar", color=ft.Colors.WHITE)
                    btn_guardar.disabled = False
                    btn_cancelar.disabled = False
                    dd_rol.disabled = False
                    if dd_rol.value != "1":
                        dd_estado.disabled = False
                    
                    self.page.update()
                    self.mostrar_alerta("Error", msj_resultado, "error")

            btn_guardar.on_click = guardar_permisos

            dialogo_gestion = ft.AlertDialog(
                modal=True,
                title=ft.Row([ft.Icon(ft.Icons.SECURITY, color=ft.Colors.BLUE_700), ft.Text("Seguridad de Cuenta")]),
                content=ft.Column([txt_nombre, dd_rol, dd_estado], tight=True),
                actions=[btn_cancelar, btn_guardar], 
                actions_alignment=ft.MainAxisAlignment.END
            )

            self.page.overlay.append(dialogo_gestion)
            dialogo_gestion.open = True
            self.page.update()

        return ft.Column([
            ft.Text("Gestión de Cajeros", size=24, weight=ft.FontWeight.BOLD),
            tabla_usuarios
        ], expand=True)
    
    # ==========================================
    # VISTAS DE ADMINISTRADOR
    # ==========================================

    def seccion_dashboard(self):
        # 1. Consultamos la base de datos para calcular las alertas reales
        productos_reales = self.bd.obtener_productos()
        
        # Contamos cuántos productos tienen el stock actual menor o igual al crítico
        cantidad_alertas = sum(1 for p in productos_reales if p["stock"] <= p["critico"])

        # 2. Tarjetas de KPI
        tarjeta_ventas = ft.Card(
            content=ft.Container(
                padding=20, width=250,
                content=ft.Column([
                    ft.Text("Ventas del día", size=16, color=ft.Colors.GREY_700),
                    ft.Text("$ 145.500,00", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700),
                    ft.Text("Actualizado recién", size=12, color=ft.Colors.GREY_500)
                ])
            )
        )

        # Lógica visual: Si hay 0 alertas, se pone verde y cambia el mensaje
        color_alerta = ft.Colors.RED_700 if cantidad_alertas > 0 else ft.Colors.GREEN_700
        texto_alerta = "Requieren reposición" if cantidad_alertas > 0 else "Stock saludable"

        tarjeta_alertas = ft.Card(
            content=ft.Container(
                padding=20, width=250,
                content=ft.Column([
                    ft.Text("Alertas activas", size=16, color=ft.Colors.GREY_700),
                    ft.Text(f"{cantidad_alertas} productos", size=28, weight=ft.FontWeight.BOLD, color=color_alerta),
                    ft.Text(texto_alerta, size=12, color=ft.Colors.GREY_500)
                ])
            )
        )

        tabla_actividad = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Venta ID")),
                ft.DataColumn(ft.Text("Hora")),
                ft.DataColumn(ft.Text("Cajero")),
                ft.DataColumn(ft.Text("Total", text_align=ft.TextAlign.RIGHT)),
            ],
            rows=[
                ft.DataRow(cells=[ft.DataCell(ft.Text("#1042")), ft.DataCell(ft.Text("12:45")), ft.DataCell(ft.Text("Juan R.")), ft.DataCell(ft.Text("$12.500"))]),
                ft.DataRow(cells=[ft.DataCell(ft.Text("#1041")), ft.DataCell(ft.Text("12:30")), ft.DataCell(ft.Text("Juan R.")), ft.DataCell(ft.Text("$8.900"))]),
                ft.DataRow(cells=[ft.DataCell(ft.Text("#1040")), ft.DataCell(ft.Text("12:15")), ft.DataCell(ft.Text("Ana Gomez")), ft.DataCell(ft.Text("$25.000"))]),
            ],
        )

        return ft.Column([
            ft.Text("Panel de Control", size=32, weight=ft.FontWeight.BOLD),
            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            ft.Row([tarjeta_ventas, tarjeta_alertas], spacing=20),
            ft.Divider(height=40, color=ft.Colors.TRANSPARENT),
            ft.Text("Actividad reciente", size=20, weight=ft.FontWeight.W_600),
            tabla_actividad
        ], expand=True)

    def seccion_inventario(self):
        # ==========================================
        # LÓGICA DEL MODAL "NUEVO PRODUCTO"
        # ==========================================
        def abrir_modal_alta(e):
            txt_nombre_prod = ft.TextField(label="Nombre del Producto", width=400)
            txt_precio = ft.TextField(label="Precio Unitario ($)", width=190, prefix_icon="$ ")
            txt_stock = ft.TextField(label="Stock Inicial (kg/un)", width=190)
            txt_critico = ft.TextField(label="Stock Crítico (Alerta)", width=190)

            def cerrar_modal(e):
                dialogo_alta.open = False
                self.page.update()

            def guardar_producto(e):
                nombre = (txt_nombre_prod.value or "").strip()
                precio_str = (txt_precio.value or "").strip()
                stock_str = (txt_stock.value or "").strip()
                critico_str = (txt_critico.value or "").strip()

                if not all([nombre, precio_str, stock_str, critico_str]):
                    self.mostrar_alerta("Campos Incompletos", "Por favor, completá todos los datos.", "error")
                    return

                try:
                    precio = float(precio_str)
                    stock = float(stock_str)
                    critico = float(critico_str)

                    if precio <= 0 or stock < 0 or critico < 0:
                        self.mostrar_alerta("Valores Inválidos", "No se permiten precios nulos ni stocks negativos.", "error")
                        return

                    exito, msj = self.bd.agregar_producto(nombre, precio, stock, critico)

                    if exito:
                        cerrar_modal(e)
                        self.contenedor_principal.content = self.seccion_inventario()
                        self.contenedor_principal.update()
                        self.mostrar_alerta("Producto Registrado", msj, "exito")
                    else:
                        self.mostrar_alerta("Error en Base de Datos", msj, "error")

                except ValueError:
                    self.mostrar_alerta("Error de Formato", "El precio y los niveles de stock deben ser números válidos.", "error")

            dialogo_alta = ft.AlertDialog(
                modal=True,
                title=ft.Row([ft.Icon(ft.Icons.ADD_BOX, color=ft.Colors.ORANGE_700), ft.Text("Alta de Nuevo Producto")]),
                content=ft.Column([
                    txt_nombre_prod,
                    ft.Row([txt_precio, txt_stock], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    txt_critico
                ], tight=True), 
                actions=[
                    ft.TextButton("Cancelar", on_click=cerrar_modal),
                    ft.Button(content=ft.Text("Guardar Producto", color=ft.Colors.WHITE), style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_600), on_click=guardar_producto)
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )

            self.page.overlay.append(dialogo_alta)
            dialogo_alta.open = True
            self.page.update()

        # ==========================================
        # LÓGICA DEL MODAL "EDITAR PRODUCTO"
        # ==========================================
        def abrir_modal_edicion(e, producto_actual):
            txt_nombre_prod = ft.TextField(label="Nombre del Producto", width=400, value=producto_actual["nombre"])
            txt_precio = ft.TextField(label="Precio Unitario ($)", width=190, prefix_icon="$ ", value=str(producto_actual["precio"]))
            txt_stock = ft.TextField(label="Stock Actual (kg/un)", width=190, value=str(producto_actual["stock"]))
            txt_critico = ft.TextField(label="Stock Crítico (Alerta)", width=190, value=str(producto_actual["critico"]))

            def cerrar_modal_edicion(e):
                dialogo_edicion.open = False
                self.page.update()

            def guardar_edicion(e):
                nombre = (txt_nombre_prod.value or "").strip()
                precio_str = (txt_precio.value or "").strip()
                stock_str = (txt_stock.value or "").strip()
                critico_str = (txt_critico.value or "").strip()

                if not all([nombre, precio_str, stock_str, critico_str]):
                    self.mostrar_alerta("Campos Incompletos", "Completá todos los datos.", "error")
                    return

                try:
                    precio = float(precio_str)
                    stock = float(stock_str)
                    critico = float(critico_str)

                    if precio <= 0 or stock < 0 or critico < 0:
                        self.mostrar_alerta("Valores Inválidos", "No se permiten valores negativos.", "error")
                        return

                    exito, msj = self.bd.editar_producto(producto_actual["id"], nombre, precio, stock, critico)

                    if exito:
                        cerrar_modal_edicion(e)
                        self.contenedor_principal.content = self.seccion_inventario()
                        self.contenedor_principal.update()
                        self.mostrar_alerta("Producto Actualizado", msj, "exito")
                    else:
                        self.mostrar_alerta("Error en Base de Datos", msj, "error")

                except ValueError:
                    self.mostrar_alerta("Error de Formato", "El precio y los niveles de stock deben ser números válidos.", "error")

            dialogo_edicion = ft.AlertDialog(
                modal=True,
                title=ft.Row([ft.Icon(ft.Icons.EDIT, color=ft.Colors.BLUE_700), ft.Text(f"Editar Producto #{producto_actual['id']}")]),
                content=ft.Column([
                    txt_nombre_prod,
                    ft.Row([txt_precio, txt_stock], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    txt_critico
                ], tight=True), 
                actions=[
                    ft.TextButton("Cancelar", on_click=cerrar_modal_edicion),
                    ft.Button(content=ft.Text("Guardar Cambios", color=ft.Colors.WHITE), style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_600), on_click=guardar_edicion)
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )

            self.page.overlay.append(dialogo_edicion)
            dialogo_edicion.open = True
            self.page.update()
        
        # ==========================================
        # LÓGICA DEL MODAL "ARCHIVAR PRODUCTO"
        # ==========================================
        def abrir_modal_archivo(e, producto_actual):
            def cerrar_modal_archivo(e):
                dialogo_archivo.open = False
                self.page.update()

            def confirmar_archivo(e):
                exito, msj = self.bd.archivar_producto(producto_actual["id"])
                if exito:
                    cerrar_modal_archivo(e)
                    self.contenedor_principal.content = self.seccion_inventario()
                    self.contenedor_principal.update()
                    self.mostrar_alerta("Producto Archivado", msj, "exito")
                else:
                    self.mostrar_alerta("Error", msj, "error")

            dialogo_archivo = ft.AlertDialog(
                modal=True,
                title=ft.Row([
                    ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=ft.Colors.RED_600), 
                    ft.Text("Confirmar Acción")
                ]),
                content=ft.Text(f"¿Estás seguro de que querés archivar '{producto_actual['nombre']}'?\nYa no aparecerá en el inventario ni podrá ser vendido."),
                actions=[
                    ft.TextButton("Cancelar", on_click=cerrar_modal_archivo),
                    ft.Button(
                        content=ft.Text("Archivar Producto", color=ft.Colors.WHITE), 
                        style=ft.ButtonStyle(bgcolor=ft.Colors.RED_600), 
                        on_click=confirmar_archivo
                    )
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )

            self.page.overlay.append(dialogo_archivo)
            dialogo_archivo.open = True
            self.page.update()

        # ==========================================
        # INTERFAZ PRINCIPAL DEL INVENTARIO
        # ==========================================
        
        productos_reales = self.bd.obtener_productos()

        estado_filtro = {"solo_criticos": False}

        def generar_filas(termino=""):
            termino = termino.lower() 
            filas_actualizadas = []
            
            for p in productos_reales:
                es_critico = p["stock"] <= p["critico"]
                
                if estado_filtro["solo_criticos"] and not es_critico:
                    continue

                if termino in str(p["id"]).lower() or termino in p["nombre"].lower():
                    color_texto = ft.Colors.RED_700 if es_critico else ft.Colors.BLACK
                    grosor_texto = ft.FontWeight.BOLD if es_critico else ft.FontWeight.NORMAL

                    filas_actualizadas.append(
                        ft.DataRow(
                            cells=[
                                ft.DataCell(ft.Text(str(p["id"]))),
                                ft.DataCell(ft.Text(p["nombre"], weight=grosor_texto, color=color_texto)),
                                ft.DataCell(ft.Text(f"$ {p['precio']:.2f}")),
                                ft.DataCell(ft.Text(f"{p['stock']} kg", color=color_texto, weight=grosor_texto)),
                                ft.DataCell(ft.Text(f"{p['critico']} kg", color=ft.Colors.GREY_700)),
                                ft.DataCell(
                                    ft.Row([
                                        ft.IconButton(
                                            icon=ft.Icons.EDIT_OUTLINED, 
                                            tooltip="Editar", 
                                            on_click=lambda e, prod=p: abrir_modal_edicion(e, prod)
                                        ),
                                        ft.IconButton(
                                            icon=ft.Icons.ARCHIVE_OUTLINED, 
                                            icon_color=ft.Colors.GREY_600, 
                                            tooltip="Archivar",
                                            on_click=lambda e, prod=p: abrir_modal_archivo(e, prod)
                                        )
                                    ])
                                ),
                            ]
                        )
                    )
            return filas_actualizadas

        def realizar_busqueda(e):
            texto = txt_buscar.value or ""
            tabla_inventario.rows = generar_filas(texto)
            self.page.update()

        txt_buscar = ft.TextField(
            label="Buscar por nombre o ID...",
            expand=True,
            prefix_icon=ft.Icons.SEARCH,
            on_change=realizar_busqueda  
        )
        
        icono_filtro = ft.Icon(ft.Icons.FILTER_ALT_OUTLINED, color=ft.Colors.GREY_700)
        texto_filtro = ft.Text("Solo Reposición", color=ft.Colors.GREY_700, weight=ft.FontWeight.BOLD)

        def alternar_filtro_criticos(e):
            estado_filtro["solo_criticos"] = not estado_filtro["solo_criticos"]
            
            if estado_filtro["solo_criticos"]:
                btn_filtro.style = ft.ButtonStyle(bgcolor=ft.Colors.RED_50)
                icono_filtro.name = ft.Icons.FILTER_ALT 
                icono_filtro.color = ft.Colors.RED_700
                texto_filtro.color = ft.Colors.RED_700
            else:
                btn_filtro.style = ft.ButtonStyle(bgcolor=ft.Colors.TRANSPARENT)
                icono_filtro.name = ft.Icons.FILTER_ALT_OUTLINED 
                icono_filtro.color = ft.Colors.GREY_700
                texto_filtro.color = ft.Colors.GREY_700
                
            texto_actual = txt_buscar.value or ""
            tabla_inventario.rows = generar_filas(texto_actual)
            self.page.update()

        btn_filtro = ft.Button(
            content=ft.Row([icono_filtro, texto_filtro], tight=True),
            style=ft.ButtonStyle(bgcolor=ft.Colors.TRANSPARENT),
            on_click=alternar_filtro_criticos
        )
        
        btn_nuevo = ft.Button(
            content=ft.Row([
                ft.Icon(ft.Icons.ADD, color=ft.Colors.WHITE),
                ft.Text("Nuevo Producto", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD)
            ], tight=True),
            style=ft.ButtonStyle(bgcolor=ft.Colors.ORANGE_700),
            on_click=abrir_modal_alta 
        )

        def ordenar_tabla(e, llave):
            tabla_inventario.sort_column_index = e.column_index
            tabla_inventario.sort_ascending = e.ascending
            productos_reales.sort(key=lambda x: x[llave], reverse=not e.ascending)
            
            texto_actual = txt_buscar.value or ""
            tabla_inventario.rows = generar_filas(texto_actual)
            self.page.update()

        tabla_inventario = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ID"), numeric=True, on_sort=lambda e: ordenar_tabla(e, "id")),
                ft.DataColumn(ft.Text("Producto"), on_sort=lambda e: ordenar_tabla(e, "nombre")),
                ft.DataColumn(ft.Text("Precio Unitario"), numeric=True, on_sort=lambda e: ordenar_tabla(e, "precio")),
                ft.DataColumn(ft.Text("Stock Actual"), numeric=True, on_sort=lambda e: ordenar_tabla(e, "stock")),
                ft.DataColumn(ft.Text("Stock Crítico"), numeric=True, on_sort=lambda e: ordenar_tabla(e, "critico")),
                ft.DataColumn(ft.Text("Acciones")),
            ],
            rows=generar_filas(), 
            sort_column_index=0,
            sort_ascending=True
        )

        return ft.Column([
            ft.Row([txt_buscar, btn_filtro, btn_nuevo], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, spacing=15),
            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            ft.Text("Listado de Productos y Suministros", size=20, weight=ft.FontWeight.W_600),
            
            ft.Container(
                expand=True, 
                content=ft.Column(
                    expand=True,
                    scroll=ft.ScrollMode.AUTO, 
                    controls=[tabla_inventario]
                ),
                border=ft.border.all(1, ft.Colors.GREY_300),
                border_radius=10,
                padding=10
            )
        ], expand=True)

    def vista_admin(self):
        # 1. Creamos el contenedor que va a alojar las secciones, arrancando con el Dashboard
        self.contenedor_principal = ft.Container(expand=True, padding=40, content=self.seccion_dashboard())

        # 2. Función que cambia el contenido del contenedor según qué botón se toque
        def cambiar_tab(e):
            idx = e.control.selected_index
            if idx == 0:
                self.contenedor_principal.content = self.seccion_dashboard()
            elif idx == 1:
                self.contenedor_principal.content = self.seccion_inventario()
            elif idx == 2:
                # ACÁ CONECTAMOS LA NUEVA SECCIÓN DE USUARIOS
                self.contenedor_principal.content = self.seccion_usuarios()
            elif idx == 3:
                self.contenedor_principal.content = ft.Text("Sección de Reportes en construcción...")
            
            self.contenedor_principal.update()

        # 3. El menú lateral que dispara la función de arriba
        # 3. El menú lateral con etiquetas en español
        menu_lateral = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100, min_extended_width=200,
            leading=ft.Column(
                controls=[
                    ft.Icon(ft.Icons.LOCAL_FIRE_DEPARTMENT, size=40, color=ft.Colors.ORANGE_700),
                    ft.Text("ADMIN", weight=ft.FontWeight.BOLD)
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            group_alignment=-0.9,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.DASHBOARD_OUTLINED, 
                    selected_icon=ft.Icons.DASHBOARD, 
                    label="Panel de Control"
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.INVENTORY_2_OUTLINED, 
                    selected_icon=ft.Icons.INVENTORY_2, 
                    label="Inventario"
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.PEOPLE_OUTLINE, 
                    selected_icon=ft.Icons.PEOPLE, 
                    label="Usuarios"
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.BAR_CHART_OUTLINED, 
                    selected_icon=ft.Icons.BAR_CHART, 
                    label="Reportes"
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.PERSON_OUTLINE, 
                    selected_icon=ft.Icons.PERSON, 
                    label="Mi Perfil"
                ),
            ],
            on_change=cambiar_tab
        )

        return ft.View(
            route="/admin",
            padding=0,
            controls=[
                ft.Row(
                    expand=True,
                    controls=[
                        menu_lateral,
                        ft.VerticalDivider(width=1),
                        self.contenedor_principal
                    ]
                )
            ]
        )

# ==========================================
# PUNTO DE ENTRADA PRINCIPAL
# ==========================================
def main(page: ft.Page):
    print(">>> PYTHON: Iniciando sistema Fuego & Fierro...")
    
    page.title = "Fuego & Fierro - Gestión"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0

    app = Carniceria(page)
    page.on_route_change = app.cambio_de_ruta
    
    app.navegar("/login")

    page.window.maximized = True
    page.update()

if __name__ == "__main__":
    ft.run(main)