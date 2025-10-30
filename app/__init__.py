# app/__init__.py
import os
from flask import Flask
from datetime import datetime
import pytz
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from .models import db, User  # Import db desde models

# --- AÑADIR ESTO ---
# Corrección del MIME Type para archivos .js en Windows
import mimetypes
mimetypes.add_type('application/javascript', '.js')
# --- FIN DE LA ADICIÓN ---

migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()

def create_app(config_class='config.Config'):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)
    # --- AÑADIR ESTA SECCIÓN PARA EL FILTRO ---
    
    # Cargar la zona horaria desde la configuración
    try:
        local_tz = pytz.timezone(app.config.get('LOCAL_TIMEZONE', 'UTC'))
    except pytz.UnknownTimeZoneError:
        print(f"ADVERTENCIA: Zona horaria '{app.config.get('LOCAL_TIMEZONE')}' no reconocida. Usando UTC por defecto.")
        local_tz = pytz.utc

    @app.template_filter('localtime')
    def localtime_filter(utc_dt):
        if not isinstance(utc_dt, datetime):
            return utc_dt # Devuelve el valor original si no es un objeto datetime
        
        # 1. Asignar la zona horaria UTC al objeto datetime (ya que viene "naive" de la DB)
        utc_dt = pytz.utc.localize(utc_dt)
        # 2. Convertir a la zona horaria local
        local_dt = utc_dt.astimezone(local_tz)
        return local_dt

    # --- FIN DE LA SECCIÓN DEL FILTRO ---
    # Asegurarse que la carpeta 'instance' exista
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Inicializar extensiones
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Configuración de Flask-Login
    login_manager.login_view = 'routes.login'
    login_manager.login_message = 'Por favor, inicia sesión para acceder a esta página.'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    with app.app_context():
        from . import routes
        app.register_blueprint(routes.bp)
        
        # --- CAMBIO AQUÍ ---
        # Registrar los comandos de la CLI
        from . import commands
        commands.init_app(app)

    return app