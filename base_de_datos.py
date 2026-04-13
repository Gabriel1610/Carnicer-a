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
        """Hashea la contraseña y guarda el usuario inactivo esperando aprobación."""
        conexion = None
        cursor = None
        try:
            # Encriptar contraseña
            salt = bcrypt.gensalt()
            password_hash = bcrypt.hashpw(password_plana.encode('utf-8'), salt).decode('utf-8')
            
            conexion = self.abrir()
            cursor = conexion.cursor()
            
            # Por defecto, entra sin rol (NULL) y activo = 0
            sql = """INSERT INTO usuario (nombre, apellido, email, password_hash) 
                     VALUES (?, ?, ?, ?)"""
            cursor.execute(sql, (nombre, apellido, email, password_hash))
            conexion.commit()
            return True, "Registro exitoso. Esperando aprobación del Administrador."
        except sqlite3.IntegrityError:
            return False, "Ese correo electrónico ya está registrado."
        except Exception as e:
            return False, str(e)
        finally:
            if cursor: cursor.close()
            if conexion: conexion.close()

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