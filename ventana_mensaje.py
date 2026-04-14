import flet as ft

# ==========================================
# CLASE PARA GESTIÓN DE MENSAJES (MODALES)
# ==========================================
class GestorMensajes:
    """Clase estática para mostrar mensajes modales adaptada a Flet 0.84+ y Modo Claro."""
    
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

        def cerrar_dialogo(e):
            page.close(dialogo)

        # Botón dinámico según el color del tipo de mensaje
        boton = ft.Button(
            text="Aceptar", 
            bgcolor=color_icono, 
            color=ft.Colors.WHITE,
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

        # Disparamos el modal en la pantalla
        page.open(dialogo)