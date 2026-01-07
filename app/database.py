from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Definimos la ruta donde se guardará el archivo de la base de datos
# Usamos una ruta absoluta dentro del contenedor para evitar problemas
DB_DIR = "/code/data"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_DIR}/nexus.db"

# Aseguramos que el directorio exista (por seguridad, aunque Docker lo debería crear)
os.makedirs(DB_DIR, exist_ok=True)

# check_same_thread: False es necesario solo para SQLite en FastAPI
# porque FastAPI usa múltiples hilos para manejar las peticiones.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Creamos la fábrica de sesiones para interactuar con la BD
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base clase para nuestros modelos
Base = declarative_base()

# Dependencia: Función auxiliar para obtener una sesión de BD en cada petición
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()