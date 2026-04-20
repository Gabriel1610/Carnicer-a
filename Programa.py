import flet as ft
import random
import smtplib
from smtplib import SMTPException
import os
import datetime
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import asyncio
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
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
        self.ticket_actual = [] # <--- NUEVA VARIABLE GLOBAL PARA EL CARRITO

    def navegar(self, ruta):
        self.page.route = ruta
        self.cambio_de_ruta(None)

    def mostrar_alerta(self, titulo, mensaje, tipo="info"):
        GestorMensajes.mostrar(self.page, titulo, mensaje, tipo)

    def cerrar_sesion(self, e=None):
        """Limpia los datos del usuario en memoria y redirige al Login."""
        self.usuario_actual = None
        self.ticket_actual.clear()
        self.navegar("/login")

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
        elif ruta_actual == "/cajero":
            self.page.views.append(self.vista_cajero())
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
                # ACÁ GUARDAMOS LA SESIÓN DEL USUARIO
                self.usuario_actual = mensaje 
                
                # Ruteo dinámico según el Rol: 1 = Admin, 2 = Cajero
                if self.usuario_actual["rolID"] == 1:
                    self.navegar("/admin")
                else:
                    self.navegar("/cajero")
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

        async def enviar_codigo(e):
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
            cuerpo_mensaje = f"Hola {nombre_limpio},\n\nGracias por registrarte en Fuego & Fierro. Tu código de verificación es: {self.codigo_generado}"
            msg.attach(MIMEText(cuerpo_mensaje, 'plain', 'utf-8'))

            # 1. Empaquetamos el trabajo pesado (Bloqueante) sin tocar la UI
            def tarea_envio_correo():
                try:
                    server = smtplib.SMTP('smtp.gmail.com', 587, timeout=10)
                    server.starttls()
                    server.login(REMITENTE, PASSWORD)
                    server.send_message(msg)
                    server.quit()
                    return True
                except Exception as err:
                    print(f">>> ERROR DE ENVÍO: {err}")
                    return False

            # 2. Enviamos la tarea a procesar sin congelar la pantalla visual
            exito_envio = await asyncio.to_thread(tarea_envio_correo)

            # 3. Volvemos al Primer Plano: Ahora sí podemos actualizar la UI sin fallas
            GestorMensajes.cerrar_cargando(self.page, loader)

            if exito_envio:
                self.mostrar_alerta("Código Enviado", f"Revisá tu bandeja en {email_limpio}", "exito")
                self.navegar("/validacion")
            else:
                self.mostrar_alerta(
                    "Error de Envío", 
                    "No se pudo conectar con el servidor de correo. Verificá tu conexión.", 
                    "error"
                )

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
                    padding=ft.Padding.only(top=10, bottom=10),
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
    
    def seccion_reportes(self):

        # ---------------------------------------------------------
        # EL TRUCO PRO: Reemplazamos el Dropdown por un RadioGroup
        # ---------------------------------------------------------
        dd_filtro = ft.RadioGroup(
            content=ft.Row([
                ft.Radio(value="Hoy", label="Hoy", active_color=ft.Colors.ORANGE_700),
                ft.Radio(value="Esta Semana", label="Semana", active_color=ft.Colors.ORANGE_700),
                ft.Radio(value="Mes en Curso", label="Mes", active_color=ft.Colors.ORANGE_700),
                ft.Radio(value="Histórico", label="Histórico", active_color=ft.Colors.ORANGE_700),
                ft.Radio(value="Personalizado", label="Personalizado", active_color=ft.Colors.ORANGE_700)
            ], alignment=ft.MainAxisAlignment.END),
            value="Mes en Curso"
        )

        # ==========================================
        # LÓGICA DE CALENDARIOS (DATE PICKERS)
        # ==========================================
        estado_fechas = {
            "inicio": datetime.datetime.now(), 
            "fin": datetime.datetime.now()
        }

        # Limpiamos Pickers anteriores del overlay eliminándolos uno por uno
        pickers_viejos = [ctrl for ctrl in self.page.overlay if isinstance(ctrl, ft.DatePicker)]
        for p in pickers_viejos:
            self.page.overlay.remove(p)

        # Capturamos la fecha actual exacta
        hoy = datetime.datetime.now()

        # Creamos los calendarios aplicando el límite máximo (last_date)
        dp_inicio = ft.DatePicker(last_date=hoy)
        dp_fin = ft.DatePicker(last_date=hoy)
        
        self.page.overlay.extend([dp_inicio, dp_fin])

        lbl_inicio = ft.Text(f"Desde: {estado_fechas['inicio'].strftime('%d/%m/%Y')}")
        lbl_fin = ft.Text(f"Hasta: {estado_fechas['fin'].strftime('%d/%m/%Y')}")

        def actualizar_fecha(tipo, e):
            if e.control.value:
                estado_fechas[tipo] = e.control.value
                if tipo == "inicio":
                    lbl_inicio.value = f"Desde: {estado_fechas['inicio'].strftime('%d/%m/%Y')}"
                else:
                    lbl_fin.value = f"Hasta: {estado_fechas['fin'].strftime('%d/%m/%Y')}"
                
                # Forzamos la actualización de los gráficos al elegir una fecha
                actualizar_pantalla(e="Forzar_Actualizacion")

        dp_inicio.on_change = lambda e: actualizar_fecha("inicio", e)
        dp_fin.on_change = lambda e: actualizar_fecha("fin", e)

        def abrir_dp_inicio(e):
            dp_inicio.open = True
            self.page.update()

        def abrir_dp_fin(e):
            dp_fin.open = True
            self.page.update()

        btn_inicio = ft.TextButton(
            content=ft.Row([ft.Icon(ft.Icons.CALENDAR_TODAY), lbl_inicio], tight=True),
            on_click=abrir_dp_inicio
        )
        btn_fin = ft.TextButton(
            content=ft.Row([ft.Icon(ft.Icons.CALENDAR_TODAY), lbl_fin], tight=True),
            on_click=abrir_dp_fin
        )

        # La fila de los calendarios nace oculta
        fila_fechas = ft.Row([btn_inicio, btn_fin], visible=False)
        col_filtros = ft.Column([dd_filtro, fila_fechas], horizontal_alignment=ft.CrossAxisAlignment.END)

        # 2. Tarjetas de Resumen (KPIs)
        lbl_ingresos = ft.Text("$ 0.00", size=30, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700)
        lbl_tickets = ft.Text("0", size=30, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700)
        lbl_promedio = ft.Text("$ 0.00", size=30, weight=ft.FontWeight.BOLD, color=ft.Colors.ORANGE_700)

        def crear_tarjeta(titulo, icono, color_icono, label_valor):
            return ft.Card(
                elevation=2,
                content=ft.Container(
                    padding=20, width=280,
                    content=ft.Column([
                        ft.Row([ft.Icon(icono, color=color_icono), ft.Text(titulo, size=16, color=ft.Colors.GREY_700)]),
                        label_valor
                    ])
                )
            )

        row_kpis = ft.Row([
            crear_tarjeta("Ingresos Totales", ft.Icons.ATTACH_MONEY, ft.Colors.GREEN_600, lbl_ingresos),
            crear_tarjeta("Tickets Emitidos", ft.Icons.RECEIPT_LONG, ft.Colors.BLUE_600, lbl_tickets),
            crear_tarjeta("Ticket Promedio", ft.Icons.ANALYTICS, ft.Colors.ORANGE_600, lbl_promedio),
        ], spacing=20)

        # 3. Contenedores de Listas
        col_ranking = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=15)
        
        tabla_cajeros = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Empleado", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Tickets", weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("Recaudación", weight=ft.FontWeight.BOLD), numeric=True),
            ],
            rows=[]
        )

        # 4. El Motor de Actualización
        def actualizar_pantalla(e=None):
            filtro = dd_filtro.value
            
            # --- Encender/Apagar los calendarios ---
            fila_fechas.visible = (filtro == "Personalizado")
            
            str_inicio = estado_fechas["inicio"].strftime('%Y-%m-%d')
            str_fin = estado_fechas["fin"].strftime('%Y-%m-%d')
            
            # --- Actualizar KPIs ---
            kpis = self.bd.obtener_kpis_reporte(filtro, str_inicio, str_fin)
            lbl_ingresos.value = f"$ {kpis['ingresos']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            lbl_tickets.value = str(kpis['tickets'])
            lbl_promedio.value = f"$ {kpis['promedio']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

            # --- Actualizar Ranking ---
            ranking = self.bd.obtener_ranking_productos(filtro, str_inicio, str_fin)
            col_ranking.controls.clear()
            if not ranking:
                col_ranking.controls.append(ft.Text("No hay ventas en este periodo.", color=ft.Colors.GREY_500))
            else:
                max_cantidad = max([p["cantidad"] for p in ranking]) if ranking else 1
                for item in ranking:
                    porcentaje = item["cantidad"] / max_cantidad
                    
                    # --- Formateo Español (3 decimales opcionales) ---
                    # 1. Forzamos 3 decimales fijos (ej: 1,500.500) y traducimos los separadores (ej: 1.500,500)
                    cantidad_fmt = f"{item['cantidad']:,.3f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    
                    # 2. Si tiene una coma, le limpiamos los ceros inútiles de la derecha
                    if "," in cantidad_fmt:
                        cantidad_fmt = cantidad_fmt.rstrip("0").rstrip(",") # Si queda "1.500," le saca la coma también

                    col_ranking.controls.append(
                        ft.Column([
                            ft.Row([
                                ft.Text(item["nombre"], width=150, weight=ft.FontWeight.W_500),
                                ft.Text(f"{cantidad_fmt} kg/un", color=ft.Colors.GREY_700) # Usamos la variable formateada
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.ProgressBar(value=porcentaje, color=ft.Colors.ORANGE_600, bgcolor=ft.Colors.ORANGE_50, height=8)
                        ], spacing=2)
                    )

            # --- Actualizar Auditoría ---
            auditoria = self.bd.obtener_auditoria_cajeros(filtro, str_inicio, str_fin)
            tabla_cajeros.rows.clear()
            for c in auditoria:
                recaudado_formateado = f"$ {c['recaudado']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                tabla_cajeros.rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(c['empleado'])),
                        ft.DataCell(ft.Text(str(c['tickets']))),
                        ft.DataCell(ft.Text(recaudado_formateado, color=ft.Colors.GREEN_700, weight=ft.FontWeight.BOLD))
                    ])
                )
            
            if e: 
                # Actualizamos la columna específica y la página completa
                if col_filtros.page:
                    col_filtros.update()
                self.page.update()

        # ¡Le inyectamos el evento directo al control que sí funciona!
        dd_filtro.on_change = actualizar_pantalla
        actualizar_pantalla()

        # 5. Estructura y Maquetación Final
        return ft.Column([
            ft.Row([
                ft.Text("Reportes y Estadísticas", size=32, weight=ft.FontWeight.BOLD), 
                col_filtros  
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            row_kpis,
            ft.Divider(height=40, color=ft.Colors.TRANSPARENT),
            
            ft.Row([
                # Panel Izquierdo: Ranking
                ft.Container(
                    expand=1,
                    padding=20, 
                    border=ft.Border.all(1, ft.Colors.GREY_300),
                    border_radius=10,
                    content=ft.Column([
                        ft.Row([ft.Icon(ft.Icons.LEADERBOARD, color=ft.Colors.ORANGE_700), ft.Text("Ranking de Productos (Top Salida)", size=18, weight=ft.FontWeight.W_600)]),
                        ft.Divider(),
                        col_ranking
                    ])
                ),
                # Panel Derecho: Auditoría
                ft.Container(
                    expand=1,
                    padding=20, 
                    border=ft.Border.all(1, ft.Colors.GREY_300),
                    border_radius=10,
                    content=ft.Column([
                        ft.Row([ft.Icon(ft.Icons.POINT_OF_SALE, color=ft.Colors.GREEN_700), ft.Text("Auditoría por Cajero", size=18, weight=ft.FontWeight.W_600)]),
                        ft.Divider(),
                        ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, controls=[tabla_cajeros])
                    ])
                )
            ], expand=True, spacing=20)
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
        # Creamos la etiqueta separada y le ponemos un texto temporal amigable
        lbl_ventas_dia = ft.Text("Calculando...", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700)
        
        tarjeta_ventas = ft.Card(
            content=ft.Container(
                padding=20, width=250,
                content=ft.Column([
                    ft.Text("Ventas del día", size=16, color=ft.Colors.GREY_700),
                    lbl_ventas_dia,
                    ft.Text("Actualizado recién", size=12, color=ft.Colors.GREY_500)
                ])
            )
        )

        async def cargar_ventas_dia():
            # 1. Esperamos (de forma asíncrona) a que la pantalla se termine de dibujar
            montado = False
            for _ in range(50): 
                try:
                    _ = lbl_ventas_dia.page
                    montado = True
                    break
                except Exception:
                    await asyncio.sleep(0.1) # Clave: Usamos asyncio.sleep en vez de time.sleep
                
            if not montado:
                return
                
            # 2. Buscamos los datos sin congelar la ventana
            try:
                def consulta():
                    return self.bd.obtener_kpis_reporte(filtro="Hoy")
                    
                kpis = await asyncio.to_thread(consulta)
                ingresos_hoy = kpis["ingresos"]
                
                # Formato español
                lbl_ventas_dia.value = f"$ {ingresos_hoy:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            except Exception:
                lbl_ventas_dia.value = "$ 0,00"
            
            # 3. Ordenamos repintar (Al estar en run_task, Flet obedece inmediatamente)
            try:
                lbl_ventas_dia.update()
            except Exception:
                pass

        # USAMOS EL MOTOR NATIVO DE FLET PARA TAREAS EN SEGUNDO PLANO
        self.page.run_task(cargar_ventas_dia)

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

        # 3. Consultar TODAS las ventas reales
        
        ventas_bd = self.bd.obtener_todas_las_ventas()
        
        filas_ventas = []
        for v in ventas_bd:
            # Formateamos el precio con el estándar español
            total_formateado = f"$ {v['total']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            
            # --- NUEVO: FORMATEO DE FECHA ---
            try:
                # SQLite devuelve 'YYYY-MM-DD HH:MM:SS', lo convertimos a objeto de Python
                fecha_obj = datetime.datetime.strptime(v["fecha"], "%Y-%m-%d %H:%M:%S")
                # Lo reescribimos al formato solicitado: HH:MM:SS dd/mm/aaaa
                fecha_formateada = fecha_obj.strftime("%H:%M:%S %d/%m/%Y")
            except Exception:
                # Si llega a haber algún error de lectura, usamos el original como respaldo
                fecha_formateada = v["fecha"]
            
            filas_ventas.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(f"#{v['id']}")),
                    ft.DataCell(ft.Text(fecha_formateada)), # <-- Usamos la fecha formateada
                    ft.DataCell(ft.Text(v["cajero"])),
                    ft.DataCell(ft.Text(total_formateado, color=ft.Colors.GREEN_700, weight=ft.FontWeight.BOLD)),
                ])
            )
            
        # Si la base de datos está vacía, mostramos un mensaje amigable
        if not filas_ventas:
            filas_ventas.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text("-")),
                    ft.DataCell(ft.Text("No hay ventas registradas aún")),
                    ft.DataCell(ft.Text("-")),
                    ft.DataCell(ft.Text("-")),
                ])
            )

        tabla_actividad = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Venta ID", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Fecha y Hora", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Cajero", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Total", weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.RIGHT)),
            ],
            rows=filas_ventas,
        )

        return ft.Column([
            ft.Text("Panel de Control", size=32, weight=ft.FontWeight.BOLD),
            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            ft.Row([tarjeta_ventas, tarjeta_alertas], spacing=20),
            ft.Divider(height=40, color=ft.Colors.TRANSPARENT),
            ft.Text("Historial Completo de Ventas", size=20, weight=ft.FontWeight.W_600),
            
            # TRUCO: Envolvemos la tabla en una columna scrolleable para que no se desborde la pantalla
            ft.Container(
                expand=True,
                content=ft.Column(
                    expand=True,
                    scroll=ft.ScrollMode.AUTO,
                    controls=[tabla_actividad]
                )
            )
        ], expand=True)
    
    def seccion_inventario(self):
        # Filtro global para permitir solo números, puntos y comas en los campos
        filtro_numeros = ft.InputFilter(allow=True, regex_string=r"^[0-9.,]*$", replacement_string="")

        # ==========================================
        # LÓGICA DEL MODAL "NUEVO PRODUCTO"
        # ==========================================
        def abrir_modal_alta(e):
            txt_nombre_prod = ft.TextField(label="Nombre del Producto", width=400)
            txt_precio = ft.TextField(label="Precio Unitario ($)", width=190, prefix_icon="$ ", input_filter=filtro_numeros)
            txt_stock = ft.TextField(label="Stock Inicial (kg/un)", width=190, input_filter=filtro_numeros)
            txt_critico = ft.TextField(label="Stock Crítico (Alerta)", width=190, input_filter=filtro_numeros)

            def cerrar_modal(e):
                dialogo_alta.open = False
                self.page.update()

            def guardar_producto(e):
                nombre = (txt_nombre_prod.value or "").strip()
                # TRADUCCIÓN DE FORMATO: Quitamos los puntos de mil y cambiamos la coma decimal por un punto
                precio_str = (txt_precio.value or "").strip().replace(".", "").replace(",", ".")
                stock_str = (txt_stock.value or "").strip().replace(".", "").replace(",", ".")
                critico_str = (txt_critico.value or "").strip().replace(".", "").replace(",", ".")

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
                    self.mostrar_alerta("Error de Formato", "Revisá los números ingresados. Usá la coma para los decimales.", "error")

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
            # Formateamos los valores iniciales para que se vean con coma al abrir la ventana
            precio_fmt = f"{producto_actual['precio']:g}".replace(".", ",")
            stock_fmt = f"{producto_actual['stock']:g}".replace(".", ",")
            critico_fmt = f"{producto_actual['critico']:g}".replace(".", ",")

            txt_nombre_prod = ft.TextField(label="Nombre del Producto", width=400, value=producto_actual["nombre"])
            txt_precio = ft.TextField(label="Precio Unitario ($)", width=190, prefix_icon="$ ", value=precio_fmt, input_filter=filtro_numeros)
            txt_stock = ft.TextField(label="Stock Actual (kg/un)", width=190, value=stock_fmt, input_filter=filtro_numeros)
            txt_critico = ft.TextField(label="Stock Crítico (Alerta)", width=190, value=critico_fmt, input_filter=filtro_numeros)

            def cerrar_modal_edicion(e):
                dialogo_edicion.open = False
                self.page.update()

            def guardar_edicion(e):
                nombre = (txt_nombre_prod.value or "").strip()
                # TRADUCCIÓN DE FORMATO
                precio_str = (txt_precio.value or "").strip().replace(".", "").replace(",", ".")
                stock_str = (txt_stock.value or "").strip().replace(".", "").replace(",", ".")
                critico_str = (txt_critico.value or "").strip().replace(".", "").replace(",", ".")

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
                    self.mostrar_alerta("Error de Formato", "Revisá los números ingresados. Usá la coma para los decimales.", "error")

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

                    # APLICAMOS EL FORMATO ESPAÑOL A LA TABLA
                    precio_tabla = f"$ {p['precio']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    stock_tabla = f"{p['stock']:g}".replace(".", ",") + " kg"
                    critico_tabla = f"{p['critico']:g}".replace(".", ",") + " kg"

                    filas_actualizadas.append(
                        ft.DataRow(
                            cells=[
                                ft.DataCell(ft.Text(str(p["id"]))),
                                ft.DataCell(ft.Text(p["nombre"], weight=grosor_texto, color=color_texto)),
                                ft.DataCell(ft.Text(precio_tabla)),
                                ft.DataCell(ft.Text(stock_tabla, color=color_texto, weight=grosor_texto)),
                                ft.DataCell(ft.Text(critico_tabla, color=ft.Colors.GREY_700)),
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
                border=ft.Border.all(1, ft.Colors.GREY_300),
                border_radius=10,
                padding=10
            )
        ], expand=True)

    def seccion_mi_perfil(self):
        usuario = self.usuario_actual
        
        # --- PANEL 1: DATOS PERSONALES ---
        txt_nombre = ft.TextField(label="Nombre", value=usuario['nombre'], width=350)
        txt_apellido = ft.TextField(label="Apellido", value=usuario['apellido'], width=350)
        
        # 1. Desbloqueamos el campo de correo electrónico
        txt_email = ft.TextField(
            label="Correo Electrónico", 
            value=usuario['email'], 
            width=350
        )

        # Variable para almacenar temporalmente el código generado
        codigo_verificacion_perfil = [""]

        # ==========================================
        # MODAL PARA VERIFICACIÓN DE NUEVO CORREO
        # ==========================================
        def cerrar_modal_correo(e=None):
            dialogo_codigo.open = False
            self.page.update()

        def confirmar_cambio_correo(e):
            codigo_ingresado = (txt_codigo.value or "").strip()
            
            if codigo_ingresado == codigo_verificacion_perfil[0]:
                # Si el código es correcto, guardamos finalmente los datos
                nvo_nombre = (txt_nombre.value or "").strip()
                nvo_apellido = (txt_apellido.value or "").strip()
                nvo_email = (txt_email.value or "").strip()
                
                exito, msj = self.bd.actualizar_perfil(usuario['userID'], nvo_nombre, nvo_apellido, nvo_email)
                if exito:
                    self.usuario_actual['nombre'] = nvo_nombre
                    self.usuario_actual['apellido'] = nvo_apellido
                    self.usuario_actual['email'] = nvo_email
                    cerrar_modal_correo()
                    self.mostrar_alerta("¡Éxito!", "Tus datos y tu nuevo correo han sido actualizados.", "exito")
                else:
                    self.mostrar_alerta("Error", msj, "error")
            else:
                self.mostrar_alerta("Validación Fallida", "El código ingresado es incorrecto.", "error")

        txt_codigo = ft.TextField(label="Código de 6 dígitos", width=200, text_align=ft.TextAlign.CENTER)
        
        dialogo_codigo = ft.AlertDialog(
            modal=True,
            title=ft.Row([ft.Icon(ft.Icons.MARK_EMAIL_READ, color=ft.Colors.BLUE_600), ft.Text("Verificar Nuevo Correo")]),
            content=ft.Column([
                ft.Text("Ingresá el código que enviamos a tu nueva dirección de correo.", text_align=ft.TextAlign.CENTER),
                txt_codigo
            ], tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            actions=[
                ft.TextButton("Cancelar", on_click=cerrar_modal_correo),
                ft.Button("Confirmar Cambio", bgcolor=ft.Colors.GREEN_600, color=ft.Colors.WHITE, on_click=confirmar_cambio_correo)
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        self.page.overlay.append(dialogo_codigo)

        # ==========================================
        # LÓGICA DEL BOTÓN GUARDAR (ASÍNCRONA)
        # ==========================================

        async def guardar_datos_personales(e):
            nvo_nombre = (txt_nombre.value or "").strip()
            nvo_apellido = (txt_apellido.value or "").strip()
            nvo_email = (txt_email.value or "").strip()
            
            if not nvo_nombre or not nvo_apellido or not nvo_email:
                self.mostrar_alerta("Campos vacíos", "Ningún campo personal puede quedar vacío.", "error")
                return
            
            # Validación de formato de correo
            patron_correo = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)+$"
            if not re.match(patron_correo, nvo_email):
                self.mostrar_alerta("Correo Inválido", "El formato del correo no es válido.", "error")
                return

            # CASO A: El usuario no cambió su correo, solo su nombre o apellido
            if nvo_email == usuario['email']:
                exito, msj = self.bd.actualizar_perfil(usuario['userID'], nvo_nombre, nvo_apellido, nvo_email)
                if exito:
                    self.usuario_actual['nombre'] = nvo_nombre
                    self.usuario_actual['apellido'] = nvo_apellido
                    self.mostrar_alerta("¡Éxito!", "Datos personales actualizados.", "exito")
                else:
                    self.mostrar_alerta("Error", msj, "error")
                return

            # CASO B: El usuario intenta cambiar su correo.
            # Primero verificamos si el correo está libre
            if self.bd.verificar_correo_existente(nvo_email):
                self.mostrar_alerta("Correo en uso", "Ese correo ya está registrado por otro empleado.", "error")
                return

            # Si está libre, iniciamos el proceso de envío de código
            loader = GestorMensajes.mostrar_cargando(self.page, "Enviando código de seguridad...")
            codigo_verificacion_perfil[0] = str(random.randint(100000, 999999))

            msg = MIMEMultipart()
            msg['From'] = REMITENTE
            msg['To'] = nvo_email
            msg['Subject'] = "Cambio de Correo - Fuego & Fierro"
            cuerpo_mensaje = f"Hola {nvo_nombre},\n\nSolicitaste cambiar tu correo en el sistema Fuego & Fierro. Tu código de verificación es: {codigo_verificacion_perfil[0]}\n\nSi no fuiste vos, ignorá este mensaje."
            msg.attach(MIMEText(cuerpo_mensaje, 'plain', 'utf-8'))

            # 1. Empaquetamos el trabajo pesado (Bloqueante)
            def tarea_envio_correo():
                try:
                    server = smtplib.SMTP('smtp.gmail.com', 587, timeout=10)
                    server.starttls()
                    server.login(REMITENTE, PASSWORD)
                    server.send_message(msg)
                    server.quit()
                    return True
                except Exception:
                    return False

            # 2. Enviamos la tarea a procesar sin congelar la pantalla visual
            exito_envio = await asyncio.to_thread(tarea_envio_correo)

            # 3. Volvemos al Primer Plano: Ahora sí podemos actualizar la UI sin fallas
            GestorMensajes.cerrar_cargando(self.page, loader)

            if exito_envio:
                txt_codigo.value = "" # Limpiamos el campo por seguridad
                dialogo_codigo.open = True
                self.page.update()
            else:
                self.mostrar_alerta("Error", "No se pudo enviar el correo de verificación. Revisá tu conexión a internet.", "error")

        btn_guardar_perfil = ft.Button(
            "Guardar Datos", 
            icon=ft.Icons.SAVE, 
            style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE), 
            on_click=guardar_datos_personales
        )
        
        tarjeta_datos = ft.Card(
            elevation=2,
            content=ft.Container(
                padding=30,
                content=ft.Column([
                    ft.Row([ft.Icon(ft.Icons.PERSON, color=ft.Colors.BLUE_700), ft.Text("Datos Personales", size=20, weight=ft.FontWeight.BOLD)]),
                    ft.Divider(color=ft.Colors.GREY_300),
                    txt_nombre,
                    txt_apellido,
                    txt_email,
                    ft.Container(height=10),
                    btn_guardar_perfil
                ])
            )
        )

        # --- PANEL 2: SEGURIDAD ---
        txt_pass_actual = ft.TextField(label="Contraseña Actual", password=True, can_reveal_password=True, width=350)
        txt_pass_nueva = ft.TextField(label="Nueva Contraseña", password=True, can_reveal_password=True, width=350)
        txt_pass_conf = ft.TextField(label="Confirmar Nueva Contraseña", password=True, can_reveal_password=True, width=350)

        def guardar_seguridad(e):
            p_actual = (txt_pass_actual.value or "").strip()
            p_nueva = (txt_pass_nueva.value or "").strip()
            p_conf = (txt_pass_conf.value or "").strip()

            if not p_actual or not p_nueva or not p_conf:
                self.mostrar_alerta("Campos vacíos", "Completá todas las contraseñas para poder aplicar el cambio.", "error")
                return

            if p_nueva != p_conf:
                self.mostrar_alerta("Error", "La nueva contraseña y su confirmación no coinciden.", "error")
                return
                
            if p_actual == p_nueva:
                self.mostrar_alerta("Sin cambios", "La nueva contraseña debe ser distinta a la que ya usás.", "info")
                return

            exito, msj = self.bd.cambiar_contrasena(usuario['userID'], p_actual, p_nueva)
            if exito:
                txt_pass_actual.value = ""
                txt_pass_nueva.value = ""
                txt_pass_conf.value = ""
                self.page.update()
                self.mostrar_alerta("¡Contraseña Actualizada!", msj, "exito")
            else:
                self.mostrar_alerta("Alerta de Seguridad", msj, "error")

        btn_guardar_pass = ft.Button(
            "Actualizar Contraseña", 
            icon=ft.Icons.LOCK_RESET, 
            style=ft.ButtonStyle(bgcolor=ft.Colors.ORANGE_700, color=ft.Colors.WHITE), 
            on_click=guardar_seguridad
        )

        tarjeta_seguridad = ft.Card(
            elevation=2,
            content=ft.Container(
                padding=30,
                content=ft.Column([
                    ft.Row([ft.Icon(ft.Icons.SECURITY, color=ft.Colors.ORANGE_700), ft.Text("Seguridad de la Cuenta", size=20, weight=ft.FontWeight.BOLD)]),
                    ft.Divider(color=ft.Colors.GREY_300),
                    txt_pass_actual,
                    txt_pass_nueva,
                    txt_pass_conf,
                    ft.Container(height=10),
                    btn_guardar_pass
                ])
            )
        )

        # ----------------------------------------
        # Maquetación Final de Mi Perfil
        # ----------------------------------------
        return ft.Column([
            ft.Text("Mi Perfil - Autogestión", size=32, weight=ft.FontWeight.BOLD),
            # Actualizamos el texto descriptivo
            ft.Text("Gestioná tu información personal, correo electrónico y los accesos a tu cuenta. Los cambios de correo requerirán validación.", color=ft.Colors.GREY_700),
            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            ft.Row([
                ft.Container(content=tarjeta_datos, expand=1),
                ft.Container(content=tarjeta_seguridad, expand=1)
            ], vertical_alignment=ft.CrossAxisAlignment.START, spacing=30)
        ], expand=True, scroll=ft.ScrollMode.AUTO)

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
                self.contenedor_principal.content = self.seccion_usuarios()
            elif idx == 3:
                self.contenedor_principal.content = self.seccion_reportes()
            elif idx == 4:
                self.contenedor_principal.content = self.seccion_mi_perfil()
            
            self.contenedor_principal.update()

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
            # EL NUEVO BOTÓN DE CERRAR SESIÓN SEPARADO ABAJO
            trailing=ft.Container(
                expand=True,
                alignment=ft.Alignment(0, 1), # <--- TRUCO INFALIBLE: x=0 (centro), y=1 (abajo)
                padding=ft.Padding.only(bottom=20),
                content=ft.Column(
                    alignment=ft.MainAxisAlignment.END,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.IconButton(
                            icon=ft.Icons.LOGOUT, # Ícono de la puerta y la flecha
                            icon_color=ft.Colors.RED_600,
                            icon_size=28,
                            tooltip="Cerrar Sesión Segura",
                            on_click=self.cerrar_sesion
                        ),
                        ft.Text("Salir", size=12, color=ft.Colors.RED_600, weight=ft.FontWeight.BOLD)
                    ]
                )
            ),
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
    # VISTAS DE CAJERO (PUNTO DE VENTA)
    # ==========================================

    def seccion_punto_venta(self):
        # ===================================================
        # ESTADO DEL TICKET Y BASE DE DATOS
        # ===================================================
        # Ya no creamos la lista acá, usamos la global: self.ticket_actual
        productos_bd = self.bd.obtener_productos()

        # Componentes que necesitan actualizarse dinámicamente
        lista_ticket = ft.ListView(expand=True, spacing=10)
        lbl_total_cobrar = ft.Text("$ 0,00", size=38, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700)
        grilla_productos = ft.GridView(
            expand=True, runs_count=3, max_extent=220, child_aspect_ratio=1.5, spacing=15, run_spacing=15
        )

        # ===================================================
        # LÓGICA DEL TICKET (PANEL DERECHO)
        # ===================================================
        def recalcular_total():
            total = sum(item["precio"] * item["cantidad"] for item in self.ticket_actual)
            lbl_total_cobrar.value = f"$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            
            # Atrapamos el error si la etiqueta aún no se pegó en la pantalla
            try:
                lbl_total_cobrar.update()
            except Exception:
                pass

        def dibujar_ticket():
            lista_ticket.controls.clear()
            
            for item in self.ticket_actual:
                sub = item["precio"] * item["cantidad"]
                sub_formateado = f"$ {sub:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                
                lbl_subtotal = ft.Text(sub_formateado, expand=2, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.RIGHT)
                
                def cambiar_cantidad(e, it=item, lbl=lbl_subtotal):
                    # Traducimos la coma visual del usuario al punto matemático de Python
                    texto_ingresado = e.control.value.strip().replace(",", ".")
                    try:
                        valor = float(texto_ingresado) if texto_ingresado else 0.0
                    except ValueError:
                        valor = 0.0 
                    
                    it["cantidad"] = valor
                    nuevo_subtotal = it["precio"] * valor
                    
                    lbl.value = f"$ {nuevo_subtotal:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    try:
                        lbl.update()
                    except Exception:
                        pass
                    recalcular_total()

                txt_cantidad = ft.TextField(
                    # Al dibujar el ticket, mostramos la cantidad formateada con coma
                    value=f"{item['cantidad']:g}".replace(".", ","),
                    expand=2,
                    text_align=ft.TextAlign.CENTER,
                    on_change=cambiar_cantidad,
                    content_padding=5,
                    # EL FILTRO ACTUALIZADO: Solo números y una única COMA opcional (prohíbe el punto)
                    input_filter=ft.InputFilter(allow=True, regex_string=r"^[0-9]*\,?[0-9]*$", replacement_string="")
                )

                def eliminar_item(e, it=item):
                    self.ticket_actual.remove(it)
                    dibujar_ticket()

                btn_eliminar = ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE, 
                    icon_color=ft.Colors.RED_500, 
                    on_click=eliminar_item
                )

                fila = ft.Row([
                    ft.Text(item["nombre"], expand=3, weight=ft.FontWeight.W_500),
                    txt_cantidad,
                    lbl_subtotal,
                    btn_eliminar
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                
                lista_ticket.controls.append(fila)
            
            recalcular_total()
            try:
                lista_ticket.update()
            except Exception:
                pass

        def agregar_al_ticket(producto):
            for item in self.ticket_actual:
                if item["id"] == producto["id"]:
                    item["cantidad"] += 1.0 
                    dibujar_ticket()
                    return
            
            self.ticket_actual.append({
                "id": producto["id"],
                "nombre": producto["nombre"],
                "precio": producto["precio"],
                "cantidad": 1.0 
            })
            dibujar_ticket()

        def cancelar_ticket(e):
            self.ticket_actual.clear()
            dibujar_ticket()

        async def confirmar_venta(e):
            if not self.ticket_actual:
                self.mostrar_alerta("Ticket Vacío", "No hay productos en el carrito para cobrar.", "error")
                return
            
            for item in self.ticket_actual:
                if item["cantidad"] <= 0:
                    self.mostrar_alerta("Cantidad Inválida", f"El producto '{item['nombre']}' tiene cantidad 0 (cero). Modificalo o eliminalo del ticket para poder cobrar.", "error")
                    return
            
            # ===================================================
            # NUEVA LÓGICA: AUDITORÍA DE TIEMPO Y CONEXIÓN
            # ===================================================
            loader = GestorMensajes.mostrar_cargando(self.page, "Verificando hora oficial y conexión...")

            def obtener_hora_web():
                import urllib.request
                import datetime
                import email.utils
                
                try:
                    # TRUCO PROFESIONAL: Consultamos la hora atómica directamente a las cabeceras de Google.
                    # Usamos method="HEAD" para que sea ultra rápido (no descarga la página, solo los datos técnicos).
                    req = urllib.request.Request("https://google.com", method="HEAD")
                    
                    with urllib.request.urlopen(req, timeout=4) as response:
                        # Extraemos la hora exacta en la que Google recibió nuestra petición
                        fecha_http = response.headers['Date']
                        
                        # Esa hora viene en huso horario GMT (Mundial). La convertimos a objeto Python:
                        tupla_fecha = email.utils.parsedate_tz(fecha_http)
                        if tupla_fecha:
                            fecha_utc = datetime.datetime(*tupla_fecha[:6])
                            
                            # Argentina está en UTC-3, así que le restamos 3 horas exactas
                            fecha_arg = fecha_utc - datetime.timedelta(hours=3)
                            
                            # Retornamos el formato exacto que SQLite necesita (YYYY-MM-DD HH:MM:SS)
                            return fecha_arg.strftime('%Y-%m-%d %H:%M:%S')
                except Exception as e:
                    print(f">>> Error de conexión: {e}")
                    return None

            # Mandamos la verificación al fondo para no congelar la pantalla de Flet
            hora_oficial = await asyncio.to_thread(obtener_hora_web)
            GestorMensajes.cerrar_cargando(self.page, loader)

            if not hora_oficial:
                self.mostrar_alerta(
                    "Fallo de Seguridad", 
                    "No se pudo validar la hora oficial. Por políticas de auditoría, no se pueden registrar ventas sin conexión a internet activa.", 
                    "error"
                )
                return
            
            # Si hay internet y la hora es correcta, procedemos a registrar pasando la hora oficial
            exito, msj = self.bd.registrar_venta(self.usuario_actual["userID"], self.ticket_actual, hora_oficial)
            
            if exito:
                self.ticket_actual.clear() 
                dibujar_ticket()      
                txt_buscar_pos.value = "" 
                generar_tarjetas()    
                self.mostrar_alerta("¡Venta Exitosa!", msj, "exito")
            else:
                self.mostrar_alerta("Error en la Venta", msj, "error")

        # ===================================================
        # LÓGICA DEL CATÁLOGO Y BÚSQUEDA (PANEL IZQUIERDO)
        # ===================================================
        def generar_tarjetas(termino=""):
            grilla_productos.controls.clear()
            termino = termino.lower()
            
            for p in productos_bd:
                if termino in p["nombre"].lower() or termino in str(p["id"]):
                    precio_formateado = f"$ {p['precio']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    
                    tarjeta = ft.Card(
                        elevation=2,
                        content=ft.Container(
                            padding=15,
                            on_click=lambda e, prod=p: agregar_al_ticket(prod), 
                            ink=True, 
                            content=ft.Column([
                                ft.Text(p["nombre"], size=16, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                                ft.Text(precio_formateado, size=18, color=ft.Colors.GREEN_700, weight=ft.FontWeight.W_600)
                            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                        )
                    )
                    grilla_productos.controls.append(tarjeta)
            
            try:
                grilla_productos.update()
            except Exception:
                pass 

        txt_buscar_pos = ft.TextField(
            label="Buscar producto por nombre o código...", 
            prefix_icon=ft.Icons.SEARCH,
            border_color=ft.Colors.ORANGE_700,
            expand=True,
            on_change=lambda e: generar_tarjetas(txt_buscar_pos.value) 
        )

        generar_tarjetas()
        dibujar_ticket() # <--- Añadimos esto para que dibuje el ticket si venimos de otra pestaña

        # ---------------------------------------------------
        # MAQUETACIÓN VISUAL (PANELES 60/40)
        # ---------------------------------------------------
        panel_izquierdo = ft.Container(
            expand=6, 
            padding=20,
            content=ft.Column([
                ft.Row([txt_buscar_pos]),
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                ft.Text("Catálogo de Productos", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_700),
                grilla_productos
            ])
        )

        encabezados_ticket = ft.Row([
            ft.Text("Producto", expand=3, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_700),
            ft.Text("Cant.", expand=2, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_700, text_align=ft.TextAlign.CENTER),
            ft.Text("Subtotal", expand=2, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_700, text_align=ft.TextAlign.RIGHT),
            ft.Container(width=40) 
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        panel_derecho = ft.Container(
            expand=4, 
            padding=25,
            bgcolor=ft.Colors.GREY_50,
            border=ft.Border(left=ft.BorderSide(1, ft.Colors.GREY_300)), 
            content=ft.Column([
                ft.Row([ft.Icon(ft.Icons.RECEIPT_LONG, color=ft.Colors.BLUE_600), ft.Text("Ticket en Curso", size=22, weight=ft.FontWeight.BOLD)]),
                ft.Divider(color=ft.Colors.GREY_300),
                encabezados_ticket,
                ft.Divider(color=ft.Colors.GREY_300),
                lista_ticket, 
                ft.Divider(color=ft.Colors.GREY_400, thickness=2),
                ft.Row([ft.Text("TOTAL A COBRAR:", size=18, weight=ft.FontWeight.W_600), lbl_total_cobrar], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Container(height=10),
                ft.Row([
                    ft.Button("Cancelar", icon=ft.Icons.DELETE_OUTLINE, style=ft.ButtonStyle(color=ft.Colors.RED_600, bgcolor=ft.Colors.RED_50), expand=1, on_click=cancelar_ticket),
                    ft.Button("Confirmar Venta", icon=ft.Icons.CHECK, style=ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.GREEN_600), height=50, expand=2, on_click=confirmar_venta)
                ])
            ])
        )

        return ft.Row([panel_izquierdo, panel_derecho], expand=True, spacing=0)

    def vista_cajero(self):
        # 1. Contenedor principal de la vista
        self.contenedor_cajero = ft.Container(expand=True, content=self.seccion_punto_venta())

        # ===================================================
        # LÓGICA DE ALERTA AL SALIR CON TICKET ACTIVO
        # ===================================================
        def intentar_cerrar_sesion(e):
            if len(self.ticket_actual) > 0:
                dialogo_salida.open = True
                self.page.update()
            else:
                self.cerrar_sesion()

        def confirmar_salida(e):
            dialogo_salida.open = False
            self.page.update()
            self.cerrar_sesion() # Esto llamará a la función que limpia el carrito y redirige

        def cancelar_salida(e):
            dialogo_salida.open = False
            self.page.update()

        dialogo_salida = ft.AlertDialog(
            modal=True,
            title=ft.Row([ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=ft.Colors.RED_600), ft.Text("Ticket en curso")]),
            content=ft.Text("Tenés productos en el carrito actualmente. Si cerrás sesión ahora, se descartará todo y se perderá la venta.\n\n¿Estás seguro de que querés salir?"),
            actions=[
                ft.TextButton("No, Quedarme", on_click=cancelar_salida),
                ft.Button("Sí, Descartar y Salir", bgcolor=ft.Colors.RED_600, color=ft.Colors.WHITE, on_click=confirmar_salida)
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.overlay.append(dialogo_salida)

        # 2. Ruteo interno del menú lateral del Cajero
        def cambiar_tab_cajero(e):
            idx = e.control.selected_index
            if idx == 0:
                self.contenedor_cajero.content = self.seccion_punto_venta()
            elif idx == 1:
                self.contenedor_cajero.content = self.seccion_mi_perfil()
            
            self.contenedor_cajero.update()

        # 3. Menú Lateral adaptado
        menu_lateral_cajero = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100, min_extended_width=200,
            leading=ft.Column(
                controls=[
                    ft.Icon(ft.Icons.LOCAL_FIRE_DEPARTMENT, size=40, color=ft.Colors.ORANGE_700),
                    ft.Text("CAJERO", weight=ft.FontWeight.BOLD)
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            group_alignment=-0.9,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.POINT_OF_SALE_OUTLINED, 
                    selected_icon=ft.Icons.POINT_OF_SALE, 
                    label="Punto de Venta"
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.PERSON_OUTLINE, 
                    selected_icon=ft.Icons.PERSON, 
                    label="Mi Perfil"
                ),
            ],
            trailing=ft.Container(
                expand=True,
                alignment=ft.Alignment(0, 1), 
                padding=ft.Padding.only(bottom=20),
                content=ft.Column(
                    alignment=ft.MainAxisAlignment.END,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.IconButton(
                            icon=ft.Icons.LOGOUT,
                            icon_color=ft.Colors.RED_600,
                            icon_size=28,
                            tooltip="Cerrar Sesión Segura",
                            # AHORA LLAMA A LA FUNCIÓN QUE VERIFICA EL CARRITO
                            on_click=intentar_cerrar_sesion 
                        ),
                        ft.Text("Salir", size=12, color=ft.Colors.RED_600, weight=ft.FontWeight.BOLD)
                    ]
                )
            ),
            on_change=cambiar_tab_cajero
        )

        return ft.View(
            route="/cajero",
            padding=0,
            controls=[
                ft.Row(
                    expand=True,
                    controls=[
                        menu_lateral_cajero,
                        ft.VerticalDivider(width=1),
                        self.contenedor_cajero
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