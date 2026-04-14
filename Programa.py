import flet as ft
import random
from base_de_datos import BaseDeDatos
from ventana_mensaje import GestorMensajes

class Carniceria:
    def __init__(self, page: ft.Page):
        self.page = page
        
        # Instanciamos la base de datos
        self.bd = BaseDeDatos()
        
        # Variables temporales para el registro
        self.codigo_generado = ""
        self.datos_temporales_registro = {}

        # Configuración del enrutador
        self.page.on_route_change = self.cambio_de_ruta
        
        # Arrancamos la aplicación
        self.navegar("/login")

    def navegar(self, ruta):
        """Método seguro y síncrono para cambiar de pantalla."""
        self.page.route = ruta
        self.cambio_de_ruta(None)

    def mostrar_alerta(self, titulo, mensaje, tipo="info"):
        """Usa el GestorMensajes para mostrar notificaciones modales."""
        GestorMensajes.mostrar(self.page, titulo, mensaje, tipo)

    def cambio_de_ruta(self, route_event):
        """Maneja qué pantalla se muestra garantizando que nunca quede vacía."""
        # 1. Limpiamos la pantalla actual
        self.page.views.clear()
        
        # 2. Atrapamos la ruta (ya sea del evento automático de Flet o de la navegación manual)
        ruta_destino = route_event.route if route_event else self.page.route
        
        # 3. Dibujamos la vista correspondiente
        if ruta_destino == "/registro":
            self.page.views.append(self.vista_registro())
        elif ruta_destino == "/validacion":
            self.page.views.append(self.vista_validacion())
        else:
            # Si la ruta es "/", "/login" o cualquier basura, forzamos el Login.
            self.page.views.append(self.vista_login())
            
        # 4. Actualizamos la interfaz
        self.page.update()

    # ==========================================
    # VISTAS (PANTALLAS)
    # ==========================================

    def vista_login(self):
        txt_email = ft.TextField(label="Correo Electrónico", width=300, prefix_icon=ft.Icons.EMAIL)
        txt_pass = ft.TextField(label="Contraseña", password=True, can_reveal_password=True, width=300, prefix_icon=ft.Icons.LOCK)

        def intentar_login(e):
            if not txt_email.value or not txt_pass.value:
                self.mostrar_alerta("Campos Incompletos", "Por favor, completá tu correo y contraseña.", "error")
                return
            
            exito, mensaje = self.bd.verificar_login(txt_email.value, txt_pass.value)
            if exito:
                self.mostrar_alerta("¡Bienvenido!", "El ingreso fue exitoso.", "exito")
                # A futuro: self.navegar("/dashboard")
            else:
                self.mostrar_alerta("Error de Acceso", mensaje, "error")

        return ft.View(
            route="/login",
            controls=[
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Icon(ft.Icons.LOCAL_FIRE_DEPARTMENT, size=80, color=ft.Colors.ORANGE_700),
                            ft.Text("FUEGO & FIERRO", size=30, weight=ft.FontWeight.BOLD),
                            ft.Text("Ingreso al Sistema", size=16, color=ft.Colors.GREY_700),
                            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                            txt_email,
                            txt_pass,
                            ft.Button("Ingresar", on_click=intentar_login, width=300, bgcolor=ft.Colors.ORANGE_700, color=ft.Colors.WHITE),
                            ft.TextButton("¿No tenés cuenta? Registrate acá", on_click=lambda _: self.navegar("/registro"))
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    alignment=ft.Alignment.CENTER,
                    expand=True
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
            if not all([txt_nombre.value, txt_apellido.value, txt_email.value, txt_pass.value, txt_pass_conf.value]):
                self.mostrar_alerta("Campos Incompletos", "Completá todos los datos para poder registrarte.", "error")
                return
            
            if txt_pass.value != txt_pass_conf.value:
                self.mostrar_alerta("Contraseñas", "Las contraseñas no coinciden. Verificá lo que escribiste.", "error")
                return
            
            self.codigo_generado = str(random.randint(100000, 999999))
            
            self.datos_temporales_registro = {
                "nombre": txt_nombre.value,
                "apellido": txt_apellido.value,
                "email": txt_email.value,
                "password": txt_pass.value 
            }
            
            print(f"\n--- SIMULACIÓN DE EMAIL ---")
            print(f"Enviando a {txt_email.value} el código: {self.codigo_generado}")
            print(f"---------------------------\n")
            
            self.mostrar_alerta("Código Enviado", f"Revisá tu bandeja de entrada en {txt_email.value}", "info")
            self.navegar("/validacion")

        return ft.View(
            route="/registro",
            controls=[
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text("Registro de Empleado", size=25, weight=ft.FontWeight.BOLD),
                            txt_nombre,
                            txt_apellido,
                            txt_email,
                            txt_pass,
                            txt_pass_conf,
                            ft.Button("Solicitar Código de Verificación", on_click=enviar_codigo, width=300),
                            ft.TextButton("Volver al Login", on_click=lambda _: self.navegar("/login"))
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    alignment=ft.Alignment.CENTER,
                    expand=True
                )
            ]
        )

    def vista_validacion(self):
        txt_codigo = ft.TextField(label="Ingresá el código de 6 dígitos", width=300, text_align=ft.TextAlign.CENTER)

        def confirmar_registro(e):
            if txt_codigo.value == self.codigo_generado:
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
                self.mostrar_alerta("Validación Fallida", "El código ingresado es incorrecto. Intentá nuevamente.", "error")

        return ft.View(
            route="/validacion",
            controls=[
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Icon(ft.Icons.MARK_EMAIL_READ, size=60, color=ft.Colors.BLUE_600),
                            ft.Text("Verificación de Correo", size=25, weight=ft.FontWeight.BOLD),
                            ft.Text(f"Se envió un código a {self.datos_temporales_registro.get('email', '')}", text_align=ft.TextAlign.CENTER),
                            txt_codigo,
                            ft.Button("Confirmar y Registrar", on_click=confirmar_registro, width=300, bgcolor=ft.Colors.GREEN_600, color=ft.Colors.WHITE),
                            ft.TextButton("Cancelar", on_click=lambda _: self.navegar("/registro"))
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    alignment=ft.Alignment.CENTER,
                    expand=True
                )
            ]
        )

def main(page: ft.Page):
    # 1. Configuración estable de la página antes de cargar la app
    page.title = "Fuego & Fierro - Gestión"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    
    # Manejo seguro de la ventana para Windows
    try:
        page.window.maximized = True
        page.window.maximizable = False
    except Exception as e:
        print(f"Aviso de ventana: {e}")
        
    # 2. Instanciamos la app
    app = Carniceria(page)
    
    # 3. Forzamos un renderizado final para evitar que quede cargando
    page.update()

if __name__ == "__main__":
    ft.run(main)