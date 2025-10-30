# app/commands.py
import click
import os
from flask.cli import with_appcontext
from flask import current_app
from .models import db, User, Role, Student

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

@click.command('sync-photos')
@with_appcontext
def sync_photos_command():
    """
    Escanea la carpeta de fotos y actualiza la base de datos.
    Nombra las fotos como {student_id}.jpg para que funcione.
    """
    click.echo("Iniciando sincronización de fotos...")
    
    # 1. Obtener la ruta a la carpeta de fotos
    photo_folder_path = os.path.join(current_app.root_path, current_app.config['STUDENT_PHOTOS_FOLDER'])
    
    if not os.path.isdir(photo_folder_path):
        click.echo(f"Error: La carpeta de fotos '{photo_folder_path}' no existe. Por favor, créala.")
        return

    # 2. Listar todos los archivos en la carpeta
    try:
        all_files = os.listdir(photo_folder_path)
    except OSError as e:
        click.echo(f"Error al leer la carpeta de fotos: {e}")
        return

    updated_count = 0
    not_found_count = 0
    skipped_count = 0
    
    # 3. Iterar sobre cada archivo
    with click.progressbar(all_files, label="Procesando fotos") as bar:
        for filename in bar:
            # Asegurarse de que sea un archivo JPG
            if filename.lower().endswith(('.jpg', '.jpeg')):
                # Extraer el ID del estudiante del nombre del archivo
                student_id_str = os.path.splitext(filename)[0]
                
                if student_id_str.isdigit():
                    student_id = int(student_id_str)
                    
                    # 4. Buscar al estudiante en la base de datos
                    student = Student.query.get(student_id)
                    
                    if student:
                        # 5. Actualizar el campo si ha cambiado
                        if student.photo_filename != filename:
                            student.photo_filename = filename
                            updated_count += 1
                        else:
                            skipped_count += 1
                    else:
                        not_found_count += 1
                else:
                    skipped_count += 1 # Archivos con nombres no numéricos
            else:
                skipped_count += 1 # Archivos que no son JPG

    # 6. Guardar todos los cambios en la base de datos de una sola vez
    if updated_count > 0:
        db.session.commit()
        click.echo(f"\nCambios guardados en la base de datos.")

    # 7. Mostrar un resumen
    click.echo("\n--- Resumen de la Sincronización ---")
    click.echo(f"Estudiantes actualizados con foto: {updated_count}")
    click.echo(f"Fotos donde no se encontró el estudiante: {not_found_count}")
    click.echo(f"Archivos omitidos (ya sincronizados o formato incorrecto): {skipped_count}")
    click.echo("------------------------------------")
    click.echo("Sincronización completada.")

def init_app(app):
    """Registra los comandos de la CLI en la aplicación Flask."""
    app.cli.add_command(init_db_command)
    app.cli.add_command(sync_photos_command)