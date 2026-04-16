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
    
    def seccion_inventario(self):
        # 1. Buscador y Botón de Alta
        txt_buscar = ft.TextField(
            label="Buscar por nombre o ID...",
            expand=True,
            prefix_icon=ft.Icons.SEARCH,
            on_change=lambda e: print(f"Buscando: {e.control.value}")
        )
        
        btn_nuevo = ft.Button(
            content=ft.Row([
                ft.Icon(ft.Icons.ADD, color=ft.Colors.WHITE),
                ft.Text("Nuevo Producto", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD)
            ], tight=True),
            # Utilizamos ButtonStyle para asegurar la compatibilidad con las versiones modernas de Flet
            style=ft.ButtonStyle(bgcolor=ft.Colors.ORANGE_700),
            on_click=lambda _: print("Abriendo modal de Alta...")
        )

        # 2. Datos simulados
        productos = [
            {"id": 1, "nombre": "Costilla de Novillo", "precio": 8500, "stock": 45.5, "critico": 20},
            {"id": 2, "nombre": "Vacio", "precio": 9200, "stock": 12.0, "critico": 25}, # ALERTA
            {"id": 3, "nombre": "Leña de Quebracho", "precio": 450, "stock": 5.0, "critico": 10}, # ALERTA
        ]

        filas = []
        for p in productos:
            es_critico = p["stock"] <= p["critico"]
            color_texto = ft.Colors.RED_700 if es_critico else ft.Colors.BLACK
            # Evitamos pasar "None" al weight para no generar excepciones en la interfaz gráfica
            grosor_texto = ft.FontWeight.BOLD if es_critico else ft.FontWeight.NORMAL

            filas.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(p["id"]))),
                        ft.DataCell(ft.Text(p["nombre"], weight=grosor_texto, color=color_texto)),
                        ft.DataCell(ft.Text(f"$ {p['precio']:.2f}")),
                        ft.DataCell(ft.Text(f"{p['stock']} kg", color=color_texto, weight=grosor_texto)),
                        ft.DataCell(
                            ft.Row([
                                ft.IconButton(icon=ft.Icons.EDIT_OUTLINED, tooltip="Editar"),
                                ft.IconButton(icon=ft.Icons.ARCHIVE_OUTLINED, icon_color=ft.Colors.GREY_600, tooltip="Archivar")
                            ])
                        ),
                    ]
                )
            )

        return ft.Column([
            ft.Row([txt_buscar, btn_nuevo], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            ft.Text("Listado de Productos y Suministros", size=20, weight=ft.FontWeight.W_600),
            
            # SOLUCIÓN: Container expandido + Columna con Scroll
            ft.Container(
                expand=True, # Este parámetro salva a la aplicación del colapso "Working..."
                content=ft.Column(
                    expand=True,
                    scroll=ft.ScrollMode.AUTO, # Permite deslizar si hay muchos productos
                    controls=[
                        ft.DataTable(
                            columns=[
                                ft.DataColumn(ft.Text("ID")),
                                ft.DataColumn(ft.Text("Producto")),
                                ft.DataColumn(ft.Text("Precio Unitario")),
                                ft.DataColumn(ft.Text("Stock Actual")),
                                ft.DataColumn(ft.Text("Acciones")),
                            ],
                            rows=filas
                        )
                    ]
                ),
                border=ft.border.all(1, ft.Colors.GREY_300),
                border_radius=10,
                padding=10
            )
        ], expand=True)

    # ==========================================
    # VISTAS DE ADMINISTRADOR
    # ==========================================

    def seccion_dashboard(self):
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

        tarjeta_alertas = ft.Card(
            content=ft.Container(
                padding=20, width=250,
                content=ft.Column([
                    ft.Text("Alertas activas", size=16, color=ft.Colors.GREY_700),
                    ft.Text("3 productos", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_700),
                    ft.Text("Requieren reposición", size=12, color=ft.Colors.GREY_500)
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
                self.contenedor_principal.content = ft.Text("Sección de Usuarios en construcción...")
            elif idx == 3:
                self.contenedor_principal.content = ft.Text("Sección de Reportes en construcción...")
            
            # Solo actualizamos el contenedor, no toda la página
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