import flet as ft

# ==========================================
# CLASE PARA GESTIÓN DE MENSAJES (MODALES)
# ==========================================
class GestorMensajes:
    """Clase estática para mostrar mensajes modales."""
    
    @staticmethod
    def mostrar(page: ft.Page, titulo: str, mensaje: str, tipo: str = "info"):
        """
        Tipos disponibles: 'info', 'error', 'exito'
        """
        if tipo == "error":
            icono = ft.Icons.ERROR_OUTLINE
            color_icono = ft.Colors.RED_600
            titulo_color = ft.Colors.RED_700
        elif tipo == "exito":
            icono = ft.Icons.CHECK_CIRCLE_OUTLINE
            color_icono = ft.Colors.GREEN_600
            titulo_color = ft.Colors.GREEN_700
        else: # info
            icono = ft.Icons.INFO_OUTLINE
            color_icono = ft.Colors.BLUE_600
            titulo_color = ft.Colors.BLUE_700

        # Creamos la ventana de diálogo base
        dialogo = ft.AlertDialog(
            modal=True,
            title_padding=0,
            content_padding=0,
            bgcolor=ft.Colors.TRANSPARENT,
        )

        # SOLUCIÓN: Solo cambiamos el estado a False y actualizamos. 
        # Dejamos que Flet haga su animación tranquilo sin borrar el objeto a la fuerza.
        def cerrar_dialogo(e):
            dialogo.open = False
            page.update()

        boton = ft.Button(
            content=ft.Text("Aceptar", color=ft.Colors.WHITE),
            bgcolor=color_icono, 
            on_click=cerrar_dialogo
        )

        # Contenido visual del mensaje
        contenido = ft.Column(
            tight=True, 
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(icono, color=color_icono, size=40),
                        ft.Text(titulo, size=20, weight=ft.FontWeight.BOLD, color=titulo_color)
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER
                ),
                ft.Divider(color=ft.Colors.GREY_300),
                ft.Text(mensaje, size=16, color=ft.Colors.BLACK87),
                ft.Container(height=15), # Espaciador
                ft.Row(
                    controls=[boton],
                    alignment=ft.MainAxisAlignment.END
                )
            ]
        )

        # Envolvemos el contenido en un contenedor para darle bordes redondeados y fondo blanco
        dialogo.content = ft.Container(
            content=contenido,
            width=450,
            bgcolor=ft.Colors.WHITE,
            border_radius=15,
            padding=25
        )

        # Usar la capa superpuesta (overlay)
        page.overlay.append(dialogo)
        dialogo.open = True
        page.update()

    @staticmethod
    def mostrar_cargando(page: ft.Page, texto: str):
        """Muestra un círculo de progreso con un mensaje."""
        dialogo = ft.AlertDialog(
            modal=True,
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.ProgressRing(width=40, height=40, stroke_width=4, color=ft.Colors.ORANGE_700),
                        ft.Text(texto, size=16, weight=ft.FontWeight.W_500),
                    ],
                    tight=True,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=30,
                bgcolor=ft.Colors.WHITE,
                border_radius=10,
            ),
            bgcolor=ft.Colors.TRANSPARENT,
        )
        
        page.overlay.append(dialogo)
        dialogo.open = True
        page.update()
        return dialogo # Lo devolvemos para poder cerrarlo luego

    @staticmethod
    def cerrar_cargando(page: ft.Page, dialogo: ft.AlertDialog):
        """Cierra el diálogo de carga y lo remueve del overlay."""
        dialogo.open = False
        page.update()
        if dialogo in page.overlay:
            page.overlay.remove(dialogo)
            page.update()