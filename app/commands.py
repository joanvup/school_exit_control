# app/commands.py
import click
from flask.cli import with_appcontext
from .models import db, User, Role

@click.command('init-db')
@with_appcontext
def init_db_command():
    """Crea un usuario administrador inicial y las tablas."""
    db.create_all()
    if User.query.filter_by(username='admin').first() is None:
        admin_user = User(username='admin', role=Role.ADMIN)
        admin_user.set_password('admin123')
        db.session.add(admin_user)
        db.session.commit()
        click.echo('Base de datos inicializada y usuario "admin" creado.')
        click.echo('Usuario: admin')
        click.echo('Contraseña: admin123')
    else:
        click.echo('El usuario "admin" ya existe.')

def init_app(app):
    """Registra los comandos de la CLI en la aplicación Flask."""
    app.cli.add_command(init_db_command)