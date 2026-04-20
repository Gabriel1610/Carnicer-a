import sqlite3
import os
import sys
import bcrypt

class BaseDeDatos:
    def __init__(self):
        if getattr(sys, 'frozen', False):
            carpeta_actual = os.path.dirname(sys.executable)
        else:
            carpeta_actual = os.path.dirname(os.path.abspath(__file__))
            
        self.db_path = os.path.join(carpeta_actual, "fuego_y_fierro.db")
        self.crear_tablas_si_no_existen()

    def abrir(self):
        try:
            conexion = sqlite3.connect(self.db_path)
            conexion.row_factory = sqlite3.Row 
            cursor = conexion.cursor()
            cursor.execute("PRAGMA foreign_keys = ON;")
            return conexion
        except sqlite3.Error as err:
            raise Exception(f"Error de Conexión a SQLite: {err}")

    def crear_tablas_si_no_existen(self):
        """Crea el esquema completo de la base de datos respetando las dependencias."""
        conexion = None
        cursor = None
        try:
            conexion = self.abrir()
            cursor = conexion.cursor()
            
            # 1. Tabla rol
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rol (
                    rolID INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre_rol TEXT NOT NULL,
                    activo INTEGER NOT NULL DEFAULT 1,
                    CONSTRAINT chk_rol_nombre_no_vacio CHECK (TRIM(nombre_rol) <> ''),
                    CONSTRAINT chk_rol_activo_booleano CHECK (activo IN (0, 1))
                )
            """)

            # 2. Tabla usuario (Default activo=0 para que el admin lo apruebe)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usuario (
                    userID INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL UNIQUE,
                    nombre TEXT NOT NULL,
                    apellido TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    rolID INTEGER,
                    activo INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (rolID) REFERENCES rol(rolID) ON DELETE RESTRICT,
                    CONSTRAINT chk_usuario_nombre_no_vacio CHECK (TRIM(nombre) <> ''),
                    CONSTRAINT chk_usuario_apellido_no_vacio CHECK (TRIM(apellido) <> ''),
                    CONSTRAINT chk_usuario_pass_no_vacio CHECK (TRIM(password_hash) <> ''),
                    CONSTRAINT chk_usuario_activo_booleano CHECK (activo IN (0, 1)),
                    CONSTRAINT chk_email_formato CHECK (
                        email LIKE '_%@_%._%' AND TRIM(email) <> '' AND email NOT LIKE '%@%@%' 
                        AND email NOT LIKE '.%' AND email NOT LIKE '%.@%' 
                        AND email NOT LIKE '%@-%' AND email NOT LIKE '%-' 
                        AND email NOT LIKE '%@%-.%' AND email NOT LIKE '%@%.-%' AND email NOT LIKE '% %'
                    )
                )
            """)

            # 3. Tabla producto
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS producto (
                    productoID INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    precio_unitario REAL NOT NULL,
                    stock_actual REAL NOT NULL,
                    stock_critico REAL NOT NULL,
                    activo INTEGER NOT NULL DEFAULT 1,
                    CONSTRAINT chk_producto_nombre_no_vacio CHECK (TRIM(nombre) <> ''),
                    CONSTRAINT chk_precio_positivo CHECK (precio_unitario > 0),
                    CONSTRAINT chk_stock_actual_positivo CHECK (stock_actual >= 0),
                    CONSTRAINT chk_stock_critico_positivo CHECK (stock_critico >= 0),
                    CONSTRAINT chk_producto_activo_booleano CHECK (activo IN (0, 1))
                )
            """)

            # 4. Tabla venta
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS venta (
                    ventaID INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
                    userID INTEGER,
                    FOREIGN KEY (userID) REFERENCES usuario(userID) ON DELETE RESTRICT
                )
            """)

            # 5. Tabla detalleVentas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS detalleVentas (
                    detalleID INTEGER PRIMARY KEY AUTOINCREMENT,
                    ventaID INTEGER,
                    productoID INTEGER,
                    cantidad REAL NOT NULL,
                    subtotal REAL NOT NULL,
                    FOREIGN KEY (ventaID) REFERENCES venta(ventaID) ON DELETE CASCADE,
                    FOREIGN KEY (productoID) REFERENCES producto(productoID) ON DELETE RESTRICT,
                    CONSTRAINT chk_cantidad_positiva CHECK (cantidad > 0),
                    CONSTRAINT chk_subtotal_positivo CHECK (subtotal > 0)
                )
            """)

            # Insertar roles básicos si la tabla está vacía
            cursor.execute("SELECT COUNT(*) FROM rol")
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO rol (nombre_rol) VALUES ('Administrador')")
                cursor.execute("INSERT INTO rol (nombre_rol) VALUES ('Cajero')")

            conexion.commit()
        except Exception as e:
            print(f"Error crítico al inicializar la base de datos: {e}")
        finally:
            if cursor: cursor.close()
            if conexion: conexion.close()

    def registrar_usuario(self, nombre, apellido, email, password_plana):
        """Hashea la contraseña y guarda el usuario. El primero será Administrador activo automáticamente."""
        conexion = None
        cursor = None
        try:
            # Encriptar contraseña
            salt = bcrypt.gensalt()
            password_hash = bcrypt.hashpw(password_plana.encode('utf-8'), salt).decode('utf-8')
            
            conexion = self.abrir()
            cursor = conexion.cursor()
            
            # 1. Verificamos si ya existen usuarios en el sistema
            cursor.execute("SELECT COUNT(*) FROM usuario")
            cantidad_usuarios = cursor.fetchone()[0]
            
            if cantidad_usuarios == 0:
                # ES EL PRIMER USUARIO: Lo hacemos Administrador y lo activamos
                # Primero buscamos cuál es el rolID del Administrador
                cursor.execute("SELECT rolID FROM rol WHERE nombre_rol = 'Administrador'")
                resultado_rol = cursor.fetchone()
                rol_admin_id = resultado_rol['rolID'] if resultado_rol else 1 # Por defecto 1 si algo falla
                
                sql = """INSERT INTO usuario (nombre, apellido, email, password_hash, rolID, activo) 
                         VALUES (?, ?, ?, ?, ?, 1)"""
                cursor.execute(sql, (nombre, apellido, email, password_hash, rol_admin_id))
                mensaje = "¡Registro exitoso! Al ser el primer usuario, se te ha asignado el rol de Administrador."
                
            else:
                # USUARIOS POSTERIORES: Entran sin rol y con activo = 0 (esperando aprobación)
                sql = """INSERT INTO usuario (nombre, apellido, email, password_hash) 
                         VALUES (?, ?, ?, ?)"""
                cursor.execute(sql, (nombre, apellido, email, password_hash))
                mensaje = "Registro exitoso. Esperando aprobación del Administrador."
                
            conexion.commit()
            return True, mensaje
            
        except sqlite3.IntegrityError:
            return False, "Ese correo electrónico ya está registrado."
        except Exception as e:
            return False, str(e)
        finally:
            if cursor: cursor.close()
            if conexion: conexion.close()
    
    def obtener_usuarios(self):
        """Recupera la lista de todos los usuarios registrados junto con su rol."""
        try:
            conexion = self.abrir()
            cursor = conexion.cursor()
            consulta = """
                SELECT u.userID, u.nombre, u.apellido, u.email, u.activo, u.rolID, r.nombre_rol
                FROM usuario u
                LEFT JOIN rol r ON u.rolID = r.rolID
            """
            cursor.execute(consulta)
            usuarios = cursor.fetchall()
            cursor.close()
            conexion.close()
            
            # Formateamos los datos para la interfaz
            return [{
                "id": u[0], 
                "nombre": f"{u[1]} {u[2]}", 
                "email": u[3], 
                "activo": u[4], 
                "rolID": u[5], 
                "rol_nombre": u[6] or "Sin Asignar"
            } for u in usuarios]
        except Exception as e:
            print(f"Error al obtener usuarios: {e}")
            return []

    def actualizar_permisos_usuario(self, user_id, rol_id, activo):
        """Actualiza el rol y el estado de acceso de un empleado."""
        try:
            conexion = self.abrir()
            cursor = conexion.cursor()
            consulta = "UPDATE usuario SET rolID = ?, activo = ? WHERE userID = ?"
            cursor.execute(consulta, (rol_id, activo, user_id))
            conexion.commit()
            cursor.close()
            conexion.close()
            return True, "Permisos del usuario actualizados correctamente."
        except Exception as e:
            return False, f"Error al actualizar permisos: {e}"
    
    def archivar_producto(self, producto_id):
        """Realiza una baja lógica cambiando el estado del producto a inactivo (0)."""
        try:
            conexion = self.abrir()
            cursor = conexion.cursor()
            
            consulta = "UPDATE producto SET activo = 0 WHERE productoID = ?"
            cursor.execute(consulta, (producto_id,))
            
            conexion.commit()
            cursor.close()
            conexion.close()
            return True, "El producto fue archivado y retirado del catálogo."
        except Exception as e:
            return False, f"Error al archivar: {e}"
    
    def agregar_producto(self, nombre, precio, stock, critico):
        """Inserta un nuevo producto en la base de datos local."""
        try:
            conexion = self.abrir() # Asegurate que este nombre coincida con tu método de conexión
            cursor = conexion.cursor()
            consulta = """INSERT INTO producto (nombre, precio_unitario, stock_actual, stock_critico) 
                          VALUES (?, ?, ?, ?)"""
            cursor.execute(consulta, (nombre, precio, stock, critico))
            conexion.commit()
            cursor.close()
            conexion.close()
            return True, "Producto agregado correctamente."
        except Exception as e:
            return False, f"Error al guardar: {e}"
    
    def editar_producto(self, producto_id, nombre, precio, stock, critico):
        """Actualiza los datos de un producto existente en la base de datos."""
        try:
            conexion = self.abrir()
            cursor = conexion.cursor()
            consulta = """UPDATE producto 
                          SET nombre = ?, precio_unitario = ?, stock_actual = ?, stock_critico = ?
                          WHERE productoID = ?"""
            cursor.execute(consulta, (nombre, precio, stock, critico, producto_id))
            conexion.commit()
            cursor.close()
            conexion.close()
            return True, "Producto actualizado correctamente."
        except Exception as e:
            return False, f"Error al actualizar: {e}"

    def obtener_productos(self):
        """Recupera la lista de todos los productos activos."""
        try:
            conexion = self.abrir()
            cursor = conexion.cursor()
            # Seleccionamos solo los productos con activo = 1 según RF02
            cursor.execute("SELECT productoID, nombre, precio_unitario, stock_actual, stock_critico FROM producto WHERE activo = 1")
            productos = cursor.fetchall()
            cursor.close()
            conexion.close()
            # Convertimos a lista de diccionarios para que sea fácil de leer en Flet
            return [{"id": p[0], "nombre": p[1], "precio": p[2], "stock": p[3], "critico": p[4]} for p in productos]
        except Exception as e:
            print(f"Error al obtener productos: {e}")
            return []
    
    def verificar_correo_existente(self, email):
        """
        Busca en la tabla de usuarios si el correo ingresado ya está registrado.
        Retorna True si el correo existe, y False si está libre.
        """
        try:
            # 1. Abrimos la conexión (Ajustá 'self.abrir()' al método que uses en tu clase)
            conexion = self.abrir()
            cursor = conexion.cursor()

            # 2. Preparamos la consulta segura. 
            # NOTA: Si usás SQLite, cambiá el '%s' por un '?'
            consulta = "SELECT COUNT(*) FROM usuario WHERE email = ?"
            
            # 3. Ejecutamos pasando el email como tupla de un solo elemento
            cursor.execute(consulta, (email,))

            # 4. Obtenemos el resultado (fetchone devuelve una tupla, ej: (1,) o (0,))
            resultado = cursor.fetchone()

            # 5. Cerramos la conexión para no saturar la base de datos
            cursor.close()
            conexion.close()

            # 6. Evaluamos la respuesta
            cantidad = resultado[0]
            if cantidad > 0:
                return True  # El correo YA EXISTE
            else:
                return False # El correo ESTÁ LIBRE

        except Exception as e:
            print(f">>> ERROR EN BD (verificar_correo_existente): {e}")
            # Por seguridad, si la base de datos falla, devolvemos True para bloquear 
            # el registro y evitar posibles duplicados accidentales o caídas del sistema.
            return True

    def verificar_login(self, email, password_plana):
        """Verifica credenciales y si el usuario está activo."""
        conexion = None
        cursor = None
        try:
            conexion = self.abrir()
            cursor = conexion.cursor()
            # 1. CAMBIAR EL SELECT PARA TRAER MÁS DATOS:
            cursor.execute("SELECT userID, email, nombre, apellido, password_hash, rolID, activo FROM usuario WHERE email = ?", (email,))
            usuario = cursor.fetchone()
            
            if usuario:
                if not bcrypt.checkpw(password_plana.encode('utf-8'), usuario['password_hash'].encode('utf-8')):
                    return False, "Contraseña incorrecta."
                
                if usuario['activo'] == 0:
                    return False, "Tu cuenta aún no ha sido aprobada por el Administrador o está inhabilitada."
                
                # 2. CONVERTIR LA FILA EN DICCIONARIO PARA QUE SEA EDITABLE:
                return True, dict(usuario)
            return False, "Usuario no encontrado."
        except Exception as e:
            return False, str(e)
        finally:
            if cursor: cursor.close()
            if conexion: conexion.close()
    
    # ==========================================
    # MÓDULO DE REPORTES Y ESTADÍSTICAS
    # ==========================================

    def _obtener_filtro_fecha(self, filtro, fecha_inicio=None, fecha_fin=None):
        """Genera la condición SQL según el filtro de tiempo seleccionado."""
        if filtro == "Hoy":
            return "DATE(v.fecha_hora, 'localtime') = DATE('now', 'localtime')"
        elif filtro == "Esta Semana":
            return "DATE(v.fecha_hora, 'localtime') >= DATE('now', '-7 days', 'localtime')"
        elif filtro == "Mes en Curso":
            return "strftime('%Y-%m', v.fecha_hora, 'localtime') = strftime('%Y-%m', 'now', 'localtime')"
        elif filtro == "Personalizado" and fecha_inicio and fecha_fin:
            # Filtro exacto entre dos fechas (YYYY-MM-DD)
            return f"DATE(v.fecha_hora, 'localtime') BETWEEN '{fecha_inicio}' AND '{fecha_fin}'"
        else:
            return "1=1" # Histórico (Sin límite)

    def obtener_kpis_reporte(self, filtro="Mes en Curso", fecha_inicio=None, fecha_fin=None):
        """Calcula Ingresos, Tickets y Promedio según la fecha."""
        condicion = self._obtener_filtro_fecha(filtro, fecha_inicio, fecha_fin)
        try:
            conexion = self.abrir()
            cursor = conexion.cursor()
            sql = f"""
                SELECT 
                    COUNT(DISTINCT v.ventaID) as total_tickets,
                    SUM(d.subtotal) as total_ingresos
                FROM venta v
                LEFT JOIN detalleVentas d ON v.ventaID = d.ventaID
                WHERE {condicion}
            """
            cursor.execute(sql)
            resultado = cursor.fetchone()
            
            tickets = resultado['total_tickets'] or 0
            ingresos = resultado['total_ingresos'] or 0.0
            promedio = ingresos / tickets if tickets > 0 else 0.0
            
            cursor.close()
            conexion.close()
            return {"ingresos": ingresos, "tickets": tickets, "promedio": promedio}
        except Exception as e:
            print(f"Error en KPIs: {e}")
            return {"ingresos": 0.0, "tickets": 0, "promedio": 0.0}

    def obtener_ranking_productos(self, filtro="Mes en Curso", fecha_inicio=None, fecha_fin=None):
        """Devuelve los 5 productos más vendidos en el periodo."""
        condicion = self._obtener_filtro_fecha(filtro, fecha_inicio, fecha_fin)
        try:
            conexion = self.abrir()
            cursor = conexion.cursor()
            sql = f"""
                SELECT p.nombre, SUM(d.cantidad) as total_cantidad
                FROM detalleVentas d
                JOIN venta v ON d.ventaID = v.ventaID
                JOIN producto p ON d.productoID = p.productoID
                WHERE {condicion}
                GROUP BY p.productoID
                ORDER BY total_cantidad DESC
                LIMIT 5
            """
            cursor.execute(sql)
            ranking = [{"nombre": f[0], "cantidad": f[1]} for f in cursor.fetchall()]
            cursor.close()
            conexion.close()
            return ranking
        except Exception as e:
            print(f"Error en Ranking: {e}")
            return []

    def obtener_auditoria_cajeros(self, filtro="Mes en Curso", fecha_inicio=None, fecha_fin=None):
        """Devuelve el rendimiento agrupado por empleado."""
        condicion = self._obtener_filtro_fecha(filtro, fecha_inicio, fecha_fin)
        try:
            conexion = self.abrir()
            cursor = conexion.cursor()
            sql = f"""
                SELECT u.nombre, u.apellido, COUNT(DISTINCT v.ventaID) as tickets, SUM(d.subtotal) as recaudado
                FROM venta v
                JOIN usuario u ON v.userID = u.userID
                JOIN detalleVentas d ON v.ventaID = d.ventaID
                WHERE {condicion}
                GROUP BY u.userID
                ORDER BY recaudado DESC
            """
            cursor.execute(sql)
            auditoria = [{"empleado": f"{f[0]} {f[1]}", "tickets": f[2], "recaudado": f[3] or 0.0} for f in cursor.fetchall()]
            cursor.close()
            conexion.close()
            return auditoria
        except Exception as e:
            print(f"Error en Auditoría: {e}")
            return []
    
    def actualizar_perfil(self, user_id, nombre, apellido, email):
        """Actualiza nombre, apellido y correo del usuario."""
        try:
            conexion = self.abrir()
            cursor = conexion.cursor()
            cursor.execute("UPDATE usuario SET nombre = ?, apellido = ?, email = ? WHERE userID = ?", (nombre, apellido, email, user_id))
            conexion.commit()
            return True, "Datos personales actualizados con éxito."
        except sqlite3.IntegrityError:
            # Captura el error si la base de datos detecta que el email ya existe (campo UNIQUE)
            return False, "Ese correo electrónico ya está registrado por otro usuario."
        except Exception as e:
            return False, f"Error al actualizar perfil: {e}"
        finally:
            if 'cursor' in locals() and cursor: cursor.close()
            if 'conexion' in locals() and conexion: conexion.close()

    def cambiar_contrasena(self, user_id, pass_actual, pass_nueva):
        """Verifica la contraseña actual y aplica el hash a la nueva."""
        try:
            conexion = self.abrir()
            cursor = conexion.cursor()
            
            cursor.execute("SELECT password_hash FROM usuario WHERE userID = ?", (user_id,))
            resultado = cursor.fetchone()
            if not resultado:
                return False, "Usuario no encontrado en la base de datos."
                
            hash_actual = resultado['password_hash']
            if not bcrypt.checkpw(pass_actual.encode('utf-8'), hash_actual.encode('utf-8')):
                return False, "La contraseña actual que ingresaste es incorrecta."
                
            salt = bcrypt.gensalt()
            nuevo_hash = bcrypt.hashpw(pass_nueva.encode('utf-8'), salt).decode('utf-8')
            
            cursor.execute("UPDATE usuario SET password_hash = ? WHERE userID = ?", (nuevo_hash, user_id))
            conexion.commit()
            return True, "Contraseña actualizada de forma segura."
        except Exception as e:
            return False, f"Error al cambiar contraseña: {e}"
        finally:
            if 'cursor' in locals() and cursor: cursor.close()
            if 'conexion' in locals() and conexion: conexion.close()
    
    def registrar_venta(self, user_id, ticket):
        """Registra la venta y descuenta el stock de forma transaccional."""
        conexion = None
        cursor = None
        try:
            conexion = self.abrir()
            cursor = conexion.cursor()
            
            # Iniciamos la transacción (si algo falla, no se guarda nada)
            cursor.execute("BEGIN TRANSACTION;")
            
            # 1. Crear cabecera de la venta
            cursor.execute("INSERT INTO venta (userID) VALUES (?)", (user_id,))
            venta_id = cursor.lastrowid
            
            # 2. Procesar cada línea del ticket
            for item in ticket:
                prod_id = item["id"]
                cant = item["cantidad"]
                subtotal = item["precio"] * cant
                
                # Verificar que haya stock suficiente
                cursor.execute("SELECT stock_actual FROM producto WHERE productoID = ?", (prod_id,))
                resultado = cursor.fetchone()
                stock_bd = resultado['stock_actual'] if resultado else 0
                
                if stock_bd < cant:
                    # Aplicamos el formato español inteligente (hasta 3 decimales, limpiando ceros y con separador de miles)
                    stock_fmt = f"{stock_bd:,.3f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    if "," in stock_fmt:
                        stock_fmt = stock_fmt.rstrip("0").rstrip(",")
                        
                    raise Exception(f"Stock insuficiente para {item['nombre']}. Solo quedan {stock_fmt} kg/un.")

                # Insertar el detalle de la venta
                cursor.execute("""
                    INSERT INTO detalleVentas (ventaID, productoID, cantidad, subtotal)
                    VALUES (?, ?, ?, ?)
                """, (venta_id, prod_id, cant, subtotal))
                
                # Descontar el stock del catálogo
                cursor.execute("""
                    UPDATE producto 
                    SET stock_actual = stock_actual - ? 
                    WHERE productoID = ?
                """, (cant, prod_id))
                
            # Si todo salió perfecto, aplicamos los cambios
            conexion.commit()
            return True, f"Ticket #{venta_id} cobrado y registrado con éxito."
            
        except Exception as e:
            if conexion:
                conexion.rollback() # Deshacemos todo si hubo un error (Ej: falta de stock)
            return False, str(e)
        finally:
            if 'cursor' in locals() and cursor: cursor.close()
            if 'conexion' in locals() and conexion: conexion.close()
    
    def obtener_todas_las_ventas(self):
        """Recupera el historial completo de ventas con su total y cajero."""
        try:
            conexion = self.abrir()
            cursor = conexion.cursor()
            sql = """
                SELECT 
                    v.ventaID, 
                    v.fecha_hora, 
                    u.nombre, 
                    u.apellido, 
                    SUM(d.subtotal) as total_venta
                FROM venta v
                JOIN usuario u ON v.userID = u.userID
                JOIN detalleVentas d ON v.ventaID = d.ventaID
                GROUP BY v.ventaID
                ORDER BY v.fecha_hora DESC
            """
            cursor.execute(sql)
            ventas = cursor.fetchall()
            cursor.close()
            conexion.close()
            
            return [{
                "id": v["ventaID"],
                "fecha": v["fecha_hora"],
                "cajero": f"{v['nombre']} {v['apellido']}",
                "total": v["total_venta"]
            } for v in ventas]
        except Exception as e:
            print(f"Error al obtener el historial de ventas: {e}")
            return []