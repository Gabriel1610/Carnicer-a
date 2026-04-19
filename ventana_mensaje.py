import flet as ft

class GestorMensajes:
    """Clase estática para mostrar mensajes modales de forma segura."""
    
    @staticmethod
    def mostrar(page: ft.Page, titulo: str, mensaje: str, tipo: str = "info"):
        if tipo == "error":
            icono = ft.Icons.ERROR_OUTLINE
            color_icono = ft.Colors.RED_600
            titulo_color = ft.Colors.RED_700
        elif tipo == "exito":
            icono = ft.Icons.CHECK_CIRCLE_OUTLINE
            color_icono = ft.Colors.GREEN_600
            titulo_color = ft.Colors.GREEN_700
        else:
            icono = ft.Icons.INFO_OUTLINE
            color_icono = ft.Colors.BLUE_600
            titulo_color = ft.Colors.BLUE_700

        def limpiar_memoria(e):
            if dialogo in page.overlay:
                page.overlay.remove(dialogo)
                page.update()

        dialogo = ft.AlertDialog(
            modal=True,
            title_padding=0,
            content_padding=0,
            bgcolor=ft.Colors.TRANSPARENT,
            on_dismiss=limpiar_memoria 
        )

        def cerrar_dialogo(e):
            dialogo.open = False
            page.update()

        boton = ft.Button(
            content=ft.Text("Aceptar", color=ft.Colors.WHITE),
            bgcolor=color_icono, 
            on_click=cerrar_dialogo
        )

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
                ft.Container(height=15), 
                ft.Row(
                    controls=[boton],
                    alignment=ft.MainAxisAlignment.END
                )
            ]
        )

        dialogo.content = ft.Container(
            content=contenido, width=450, bgcolor=ft.Colors.WHITE, border_radius=15, padding=25
        )
        
        page.overlay.append(dialogo)
        dialogo.open = True
        page.update()

    @staticmethod
    def mostrar_cargando(page: ft.Page, texto: str):
        def limpiar_memoria(e):
            if dialogo in page.overlay:
                page.overlay.remove(dialogo)
                page.update()

        dialogo = ft.AlertDialog(
            modal=True,
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.ProgressRing(width=40, height=40, stroke_width=4, color=ft.Colors.ORANGE_700),
                        ft.Text(texto, size=16, weight=ft.FontWeight.W_500),
                    ],
                    tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=30, bgcolor=ft.Colors.WHITE, border_radius=10,
            ),
            bgcolor=ft.Colors.TRANSPARENT,
            on_dismiss=limpiar_memoria
        )
        
        page.overlay.append(dialogo)
        dialogo.open = True
        page.update()
        return dialogo 

    @staticmethod
    def cerrar_cargando(page: ft.Page, dialogo: ft.AlertDialog):
        dialogo.open = False
        page.update()