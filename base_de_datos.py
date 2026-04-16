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
                    CONSTRAINT chk_precio_positivo CHECK (precio_unitario >= 0),
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
    
    def verificar_correo_existente(self, email):
        """
        Busca en la tabla de usuarios si el correo ingresado ya está registrado.
        Retorna True si el correo existe, y False si está libre.
        """
        try:
            # 1. Abrimos la conexión (Ajustá 'self.conectar()' al método que uses en tu clase)
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
            cursor.execute("SELECT userID, password_hash, rolID, activo FROM usuario WHERE email = ?", (email,))
            usuario = cursor.fetchone()
            
            if usuario:
                if not bcrypt.checkpw(password_plana.encode('utf-8'), usuario['password_hash'].encode('utf-8')):
                    return False, "Contraseña incorrecta."
                
                if usuario['activo'] == 0:
                    return False, "Tu cuenta aún no ha sido aprobada por el Administrador o está inhabilitada."
                
                return True, usuario
            return False, "Usuario no encontrado."
        except Exception as e:
            return False, str(e)
        finally:
            if cursor: cursor.close()
            if conexion: conexion.close()