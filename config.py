# config.py
import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'una-clave-secreta-muy-dificil-de-adivinar'

    # --- Configuración de la Base de Datos (Dinámica) ---
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    print(SQLALCHEMY_DATABASE_URI)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    LOCAL_TIMEZONE = 'America/Bogota' # <--- CAMBIA ESTO A TU ZONA HORARIA

    # --- Configuración de Uploads ---
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB
    UPLOAD_EXTENSIONS = ['.xlsx', '.xls']
    # Carpeta para guardar las fotos de los estudiantes
    STUDENT_PHOTOS_FOLDER = 'student_photos'