import flet as ft
import random
from base_de_datos import BaseDeDatos

class Carniceria:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Fuego & Fierro - Gestión"
        
        # CONFIGURACIÓN DE VENTANA:
        # Inicia la aplicación maximizada para aprovechar todo el monitor
        self.page.window.maximized = True
        # Deshabilita el botón de maximizar/restaurar de la esquina superior derecha
        self.page.window.maximizable = False
        
        # Mantenemos el modo claro y quitamos los márgenes por defecto de la página
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.padding = 0
        
        # Instanciamos la base de datos
        self.bd = BaseDeDatos()
        
        # Variables temporales para el registro
        self.codigo_generado = ""
        self.datos_temporales_registro = {}

        # Configuración del enrutador
        self.page.on_route_change = self.cambio_de_ruta
        
        # Iniciamos la app yendo al login
        self.navegar("/login")

    def navegar(self, ruta):
        """Método seguro y síncrono para cambiar de pantalla en Flet 0.84+"""
        self.page.route = ruta
        self.cambio_de_ruta(None)

    def mostrar_alerta(self, mensaje, color=ft.Colors.RED_600):
        """Muestra un mensaje flotante (SnackBar) de forma 100% compatible."""
        # Asignamos el snackbar directamente a la propiedad de la página
        self.page.snack_bar = ft.SnackBar(content=ft.Text(mensaje), bgcolor=color)
        self.page.snack_bar.open = True
        self.page.update()

    def cambio_de_ruta(self, route_event):
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
        txt_email = ft.TextField(label="Correo Electrónico", width=300, prefix_icon=ft.Icons.EMAIL)
        txt_pass = ft.TextField(label="Contraseña", password=True, can_reveal_password=True, width=300, prefix_icon=ft.Icons.LOCK)

        def intentar_login(e):
            if not txt_email.value or not txt_pass.value:
                self.mostrar_alerta("Completá todos los campos.")
                return
            
            exito, mensaje = self.bd.verificar_login(txt_email.value, txt_pass.value)
            if exito:
                self.mostrar_alerta("¡Ingreso exitoso!", color=ft.Colors.GREEN_600)
            else:
                self.mostrar_alerta(mensaje)

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
        # NUEVO CAMPO: Confirmación de contraseña
        txt_pass_conf = ft.TextField(label="Confirmar Contraseña", password=True, can_reveal_password=True, width=300)

        def enviar_codigo(e):
            # 1. Validar que TODOS los campos estén completos, incluyendo la confirmación
            if not all([txt_nombre.value, txt_apellido.value, txt_email.value, txt_pass.value, txt_pass_conf.value]):
                self.mostrar_alerta("Completá todos los campos.")
                return
            
            # 2. NUEVA VALIDACIÓN: Verificar que ambas contraseñas sean exactamente iguales
            if txt_pass.value != txt_pass_conf.value:
                self.mostrar_alerta("Las contraseñas no coinciden.")
                return
            
            # 3. Generamos un código de 6 dígitos
            self.codigo_generado = str(random.randint(100000, 999999))
            
            # 4. Guardamos temporalmente los datos en memoria
            self.datos_temporales_registro = {
                "nombre": txt_nombre.value,
                "apellido": txt_apellido.value,
                "email": txt_email.value,
                "password": txt_pass.value # Solo hace falta guardar una, ya sabemos que son iguales
            }
            
            # 5. Simulación de email en la consola
            print(f"\n--- SIMULACIÓN DE EMAIL ---")
            print(f"Enviando a {txt_email.value} el código: {self.codigo_generado}")
            print(f"---------------------------\n")
            
            self.mostrar_alerta(f"Código enviado a {txt_email.value}", color=ft.Colors.BLUE_600)
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
                            txt_pass_conf, # AGREGADO A LA INTERFAZ VISUAL
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
                    self.mostrar_alerta(msj, color=ft.Colors.GREEN_600)
                    self.navegar("/login")
                else:
                    self.mostrar_alerta(msj)
            else:
                self.mostrar_alerta("Código incorrecto. Intentá nuevamente.")

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
    app = Carniceria(page)

if __name__ == "__main__":
    ft.run(main)