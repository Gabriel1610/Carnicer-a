import flet as ft
import random
import smtplib
from smtplib import SMTPRecipientsRefused, SMTPException
import os
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
        # 1. Recuperamos los usuarios y filtramos para mostrar solo Cajeros o sin rol
        usuarios_totales = self.bd.obtener_usuarios()
        usuarios_visibles = [u for u in usuarios_totales if u["rol_nombre"] != "Administrador"]

        def abrir_modal_gestion(e, usuario_actual):
            txt_nombre = ft.TextField(label="Empleado", value=usuario_actual["nombre"], read_only=True, width=300)
            
            dd_rol = ft.Dropdown(
                label="Asignar Rol", width=300,
                options=[
                    ft.dropdown.Option("1", "Administrador"),
                    ft.dropdown.Option("2", "Cajero")
                ],
                value=str(usuario_actual["rolID"]) if usuario_actual["rolID"] else None
            )

            dd_estado = ft.Dropdown(
                label="Estado de Acceso", width=300,
                options=[
                    ft.dropdown.Option("1", "Activo (Aprobado)"),
                    ft.dropdown.Option("0", "Inactivo / Suspendido")
                ],
                value="1" if usuario_actual["activo"] == 1 else "0"
            )

            def controlar_bloqueo_admin(e):
                if dd_rol.value == "1":
                    dd_estado.value = "1"
                    dd_estado.disabled = True
                else:
                    dd_estado.disabled = False
                dd_estado.update()

            dd_rol.on_change = controlar_bloqueo_admin
            
            if dd_rol.value == "1":
                dd_estado.value = "1"
                dd_estado.disabled = True

            # Creamos una función dedicada y limpia para cerrar este modal
            def cerrar_modal(e=None):
                dialogo_gestion.open = False
                self.page.update()

            def guardar_permisos(e):
                nuevo_rol_id = int(dd_rol.value) if dd_rol.value else None
                nuevo_estado = int(dd_estado.value) if dd_estado.value else 0

                if nuevo_estado == 1 and nuevo_rol_id is None:
                    self.mostrar_alerta("Atención", "Asigná un rol antes de aprobar el acceso.", "error")
                    return

                # ¡EL GRAN CAMBIO! Cerramos la ventana de edición INMEDIATAMENTE
                cerrar_modal()

                nombre_rol = "Administrador" if nuevo_rol_id == 1 else "Cajero"
                nombre_estado = "ACTIVO / APROBADO" if nuevo_estado == 1 else "INACTIVO / SUSPENDIDO"

                # Al estar la pantalla limpia, el loader toma el control sin chocar con otra ventana
                loader = GestorMensajes.mostrar_cargando(self.page, "Conectando al servidor y notificando...")

                def tarea_notificar_y_guardar():
                    try:
                        # Envío del correo (Es normal que demore entre 3 y 6 segundos)
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

                        # Si se envió, guardamos en la base
                        exito_bd, msj_bd = self.bd.actualizar_permisos_usuario(
                            usuario_actual["id"], nuevo_rol_id, nuevo_estado
                        )

                        GestorMensajes.cerrar_cargando(self.page, loader)

                        if exito_bd:
                            self.contenedor_principal.content = self.seccion_usuarios()
                            self.contenedor_principal.update()
                            self.mostrar_alerta("Éxito", "Cambios aplicados y empleado notificado.", "exito")
                        else:
                            self.mostrar_alerta("Error Interno", msj_bd, "error")

                    except (SMTPException, OSError) as err:
                        GestorMensajes.cerrar_cargando(self.page, loader)
                        print(f">>> ERROR DE RED/SMTP: {err}")
                        self.mostrar_alerta(
                            "Error de Conexión", 
                            "No se pudieron modificar los accesos sin internet, ya que es obligatorio notificar al empleado por correo.", 
                            "error"
                        )
                    except Exception as ex:
                        GestorMensajes.cerrar_cargando(self.page, loader)
                        self.mostrar_alerta("Error Inesperado", str(ex), "error")

                threading.Thread(target=tarea_notificar_y_guardar).start()

            dialogo_gestion = ft.AlertDialog(
                modal=True,
                title=ft.Row([ft.Icon(ft.Icons.SECURITY, color=ft.Colors.BLUE_700), ft.Text("Seguridad de Cuenta")]),
                content=ft.Column([txt_nombre, dd_rol, dd_estado], tight=True),
                actions=[
                    # Conectamos el botón Cancelar con la misma función limpia
                    ft.TextButton("Cancelar", on_click=cerrar_modal),
                    ft.Button("Guardar", bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE, on_click=guardar_permisos) 
                ],
                actions_alignment=ft.MainAxisAlignment.END
            )

            self.page.overlay.append(dialogo_gestion)
            dialogo_gestion.open = True
            self.page.update()

        # Construcción de la tabla
        filas = []
        for u in usuarios_visibles:
            filas.append(
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

        return ft.Column([
            ft.Text("Gestión de Cajeros", size=24, weight=ft.FontWeight.BOLD),
            ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("ID")), 
                    ft.DataColumn(ft.Text("Nombre")), 
                    ft.DataColumn(ft.Text("Email")),
                    ft.DataColumn(ft.Text("Rol")), 
                    ft.DataColumn(ft.Text("Estado")), 
                    ft.DataColumn(ft.Text("Acción"))
                ],
                rows=filas
            )
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