import flet as ft
import random
# Aquí importamos tu simulación de envío de correo o librería SMTP
# import smtplib 
from base_de_datos import BaseDeDatos

class Carniceria:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Fuego & Fierro - Gestión"
        self.page.window_width = 1366
        self.page.window_height = 768
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.padding = 0
        
        # Instanciamos la base de datos
        self.bd = BaseDeDatos()
        
        # Variables temporales para el registro
        self.codigo_generado = ""
        self.datos_temporales_registro = {}

        # Configuración del enrutador de Flet
        self.page.on_route_change = self.cambio_de_ruta
        self.page.go("/login") # Ruta inicial

    def mostrar_alerta(self, mensaje, color=ft.colors.RED_600):
        """Muestra un mensaje flotante (SnackBar) al usuario."""
        self.page.snack_bar = ft.SnackBar(ft.Text(mensaje), bgcolor=color)
        self.page.snack_bar.open = True
        self.page.update()

    def cambio_de_ruta(self, route):
        """Maneja qué pantalla se muestra según la ruta actual."""
        self.page.views.clear()
        
        if self.page.route == "/login":
            self.page.views.append(self.vista_login())
        elif self.page.route == "/registro":
            self.page.views.append(self.vista_registro())
        elif self.page.route == "/validacion":
            self.page.views.append(self.vista_validacion())
            
        self.page.update()

    # ==========================================
    # VISTAS (PANTALLAS)
    # ==========================================

    def vista_login(self):
        txt_email = ft.TextField(label="Correo Electrónico", width=300, prefix_icon=ft.icons.EMAIL)
        txt_pass = ft.TextField(label="Contraseña", password=True, can_reveal_password=True, width=300, prefix_icon=ft.icons.LOCK)

        def intentar_login(e):
            if not txt_email.value or not txt_pass.value:
                self.mostrar_alerta("Completá todos los campos.")
                return
            
            exito, mensaje = self.bd.verificar_login(txt_email.value, txt_pass.value)
            if exito:
                self.mostrar_alerta("¡Ingreso exitoso!", color=ft.colors.GREEN_600)
                # Acá a futuro mandarías a la pantalla del mostrador o dashboard
                # self.page.go("/dashboard")
            else:
                self.mostrar_alerta(mensaje)

        return ft.View(
            "/login",
            controls=[
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Icon(ft.icons.LOCAL_FIRE_DEPARTMENT, size=80, color=ft.colors.ORANGE_700),
                            ft.Text("FUEGO & FIERRO", size=30, weight=ft.FontWeight.BOLD),
                            ft.Text("Ingreso al Sistema", size=16, color=ft.colors.GREY_700),
                            ft.Divider(height=20, color=ft.colors.TRANSPARENT),
                            txt_email,
                            txt_pass,
                            ft.ElevatedButton("Ingresar", on_click=intentar_login, width=300, bgcolor=ft.colors.ORANGE_700, color=ft.colors.WHITE),
                            ft.TextButton("¿No tenés cuenta? Registrate acá", on_click=lambda _: self.page.go("/registro"))
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    alignment=ft.alignment.center,
                    expand=True
                )
            ]
        )

    def vista_registro(self):
        txt_nombre = ft.TextField(label="Nombre", width=300)
        txt_apellido = ft.TextField(label="Apellido", width=300)
        txt_email = ft.TextField(label="Correo Electrónico", width=300)
        txt_pass = ft.TextField(label="Contraseña", password=True, can_reveal_password=True, width=300)

        def enviar_codigo(e):
            if not all([txt_nombre.value, txt_apellido.value, txt_email.value, txt_pass.value]):
                self.mostrar_alerta("Completá todos los campos.")
                return
            
            # 1. Generamos un código de 6 dígitos
            self.codigo_generado = str(random.randint(100000, 999999))
            
            # 2. Guardamos temporalmente los datos en memoria, NO en la base de datos todavía
            self.datos_temporales_registro = {
                "nombre": txt_nombre.value,
                "apellido": txt_apellido.value,
                "email": txt_email.value,
                "password": txt_pass.value
            }
            
            # 3. Acá iría tu lógica real de envío de email (SMTP)
            print(f"--- SIMULACIÓN DE EMAIL ---")
            print(f"Enviando a {txt_email.value} el código: {self.codigo_generado}")
            print(f"---------------------------")
            
            self.mostrar_alerta(f"Código enviado a {txt_email.value}", color=ft.colors.BLUE_600)
            self.page.go("/validacion")

        return ft.View(
            "/registro",
            controls=[
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text("Registro de Empleado", size=25, weight=ft.FontWeight.BOLD),
                            txt_nombre,
                            txt_apellido,
                            txt_email,
                            txt_pass,
                            ft.ElevatedButton("Solicitar Código de Verificación", on_click=enviar_codigo, width=300),
                            ft.TextButton("Volver al Login", on_click=lambda _: self.page.go("/login"))
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    alignment=ft.alignment.center,
                    expand=True
                )
            ]
        )

    def vista_validacion(self):
        txt_codigo = ft.TextField(label="Ingresá el código de 6 dígitos", width=300, text_align=ft.TextAlign.CENTER)

        def confirmar_registro(e):
            if txt_codigo.value == self.codigo_generado:
                # Si el código es correcto, ahora SÍ guardamos en SQLite
                datos = self.datos_temporales_registro
                exito, msj = self.bd.registrar_usuario(
                    datos["nombre"], datos["apellido"], datos["email"], datos["password"]
                )
                
                if exito:
                    self.mostrar_alerta(msj, color=ft.colors.GREEN_600)
                    self.page.go("/login") # Lo mandamos a loguearse
                else:
                    self.mostrar_alerta(msj)
            else:
                self.mostrar_alerta("Código incorrecto. Intentá nuevamente.")

        return ft.View(
            "/validacion",
            controls=[
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Icon(ft.icons.MARK_EMAIL_READ, size=60, color=ft.colors.BLUE_600),
                            ft.Text("Verificación de Correo", size=25, weight=ft.FontWeight.BOLD),
                            ft.Text(f"Se envió un código a {self.datos_temporales_registro.get('email', '')}", text_align=ft.TextAlign.CENTER),
                            txt_codigo,
                            ft.ElevatedButton("Confirmar y Registrar", on_click=confirmar_registro, width=300, bgcolor=ft.colors.GREEN_600, color=ft.colors.WHITE),
                            ft.TextButton("Cancelar", on_click=lambda _: self.page.go("/registro"))
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    alignment=ft.alignment.center,
                    expand=True
                )
            ]
        )

# Punto de entrada principal
def main(page: ft.Page):
    app = Carniceria(page)

if __name__ == "__main__":
    ft.app(target=main)