# config.py
import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'una-clave-secreta-muy-dificil-de-adivinar'
    LOCAL_TIMEZONE = 'America/Bogota' # <--- CAMBIA ESTO A TU ZONA HORARIA
    # --- Configuración de Base de Datos ---
    # SQLite (por defecto)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'app.db')
    
    # MySQL (ejemplo, descomentar para usar)
    # SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://user:password@host/db_name'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Configuración de Uploads ---
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB
    UPLOAD_EXTENSIONS = ['.xlsx', '.xls']