# app/routes.py
import pandas as pd
import io
import os 
from flask import (
    Blueprint, render_template, redirect, url_for, flash, request, jsonify, Response, current_app, send_from_directory
)
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.utils import secure_filename
from .models import db, User, Student, Exit, Role, Door
from .forms import LoginForm, RegistrationForm, StudentForm, ImportForm, SettingsForm, DoorForm, ReportForm, ChangePasswordForm
from .decorators import admin_required
import qrcode
import base64
import json
from datetime import datetime, timedelta, date, time
from .models import db, User, Student, Exit, Role, Setting # <--- Añadir Setting
from sqlalchemy import func
import pytz

bp = Blueprint('routes', __name__)
# --- Ruta para servir el Service Worker desde la raíz ---
@bp.route('/sw.js')
def service_worker():
    return send_from_directory('static', 'sw.js')
# --- Rutas de Autenticación ---
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('routes.dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Usuario o contraseña inválidos', 'danger')
            return redirect(url_for('routes.login'))
        login_user(user, remember=form.remember_me.data)
        return redirect(url_for('routes.dashboard'))
    return render_template('auth/login.html', title='Iniciar Sesión', form=form)

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('routes.login'))

# El registro está disponible para administradores
@bp.route('/register', methods=['GET', 'POST'])
@login_required
@admin_required
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, role=Role(form.role.data))
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('El usuario ha sido registrado exitosamente.', 'success')
        return redirect(url_for('routes.list_users'))
    return render_template('auth/register.html', title='Registrar Usuario', form=form)

# --- Rutas Principales ---
@bp.route('/')
@login_required
def dashboard():
    # --- Lógica de cálculo de estadísticas del día ---

    # 1. Cargar la zona horaria local
    try:
        local_tz = pytz.timezone(current_app.config.get('LOCAL_TIMEZONE', 'UTC'))
    except pytz.UnknownTimeZoneError:
        local_tz = pytz.utc

    # 2. Definir el rango del día actual en la zona horaria local y convertirlo a UTC
    today_local = datetime.now(local_tz).date()
    start_of_day_local = local_tz.localize(datetime.combine(today_local, time.min))
    end_of_day_local = local_tz.localize(datetime.combine(today_local, time.max))
    
    start_of_day_utc = start_of_day_local.astimezone(pytz.utc)
    end_of_day_utc = end_of_day_local.astimezone(pytz.utc)

    # 3. Consultar las salidas del día y agrupar por puerta
    # Usamos una consulta de SQLAlchemy para que la base de datos haga el trabajo pesado.
    exits_by_door = db.session.query(
        Door.name,
        func.count(Exit.id)
    ).join(Door, Exit.door_id == Door.id).filter(
        Exit.timestamp >= start_of_day_utc,
        Exit.timestamp <= end_of_day_utc
    ).group_by(Door.name).all()

    # Formatear los resultados en un diccionario más fácil de usar en la plantilla
    # ej: {'Puerta A': 15, 'Puerta B': 10}
    daily_stats = {door_name: count for door_name, count in exits_by_door}
    
    # Calcular el total de salidas del día
    total_exits_today = sum(daily_stats.values())
    
    # 4. Obtener el total de estudiantes (como antes)
    student_count = Student.query.count()

    return render_template(
        'main/dashboard.html',
        student_count=student_count,
        total_exits_today=total_exits_today,
        daily_stats=daily_stats
    )

@bp.route('/scan')
@login_required
def scan():
    # Cargar solo las puertas activas para el selector
    active_doors = Door.query.filter_by(is_active=True).order_by(Door.name).all()
    return render_template('main/scan.html', doors=active_doors)

@bp.route('/exits')
@login_required
def list_exits():
    page = request.args.get('page', 1, type=int)
    exits = Exit.query.order_by(Exit.timestamp.desc()).paginate(page=page, per_page=15)
    return render_template('main/exits.html', exits=exits)

# app/routes.py

@bp.route('/api/scan', methods=['POST'])
@login_required
def api_scan():
    # --- Obtener el intervalo de cooldown desde la DB ---
    cooldown_setting = Setting.query.filter_by(key='exit_cooldown_minutes').first()
    # Valor por defecto de 60 minutos si no está configurado
    cooldown_minutes = int(cooldown_setting.value) if cooldown_setting else 60

    data = request.get_json()
    if not data or 'student_id' not in data or 'door' not in data:
        return jsonify({'success': False, 'message': 'Datos incompletos.'}), 400

    try:
        student_id = int(data['student_id'])
        # --- CAMBIO AQUÍ: Ahora recibimos un door_id ---
        door_id = int(data['door'])
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'ID de estudiante o puerta inválido.'}), 400

    # Validar que la puerta exista y esté activa
    door = Door.query.filter_by(id=door_id, is_active=True).first()
    if not door:
        return jsonify({'success': False, 'message': 'Puerta no válida o inactiva.'}), 400

    student = Student.query.get(student_id)
    if not student:
        return jsonify({'success': False, 'message': f'Estudiante con ID {student_id} no encontrado.'}), 404
    
    if not student.authorized:
        return jsonify({'success': False, 'message': f'Salida no autorizada para {student.name}.'}), 403

    # --- NUEVA VALIDACIÓN DE COOLDOWN ---
    last_exit = Exit.query.filter_by(student_id=student.id).order_by(Exit.timestamp.desc()).first()
    if last_exit:
        time_since_last_exit = datetime.utcnow() - last_exit.timestamp
        if time_since_last_exit < timedelta(minutes=cooldown_minutes):
            minutes_remaining = cooldown_minutes - int(time_since_last_exit.total_seconds() / 60)
            message = f'Salida ya registrada. Intente de nuevo en {minutes_remaining} min.'
            return jsonify({'success': False, 'message': message}), 429 # 429: Too Many Requests

    new_exit = Exit(
        student_id=student.id,
        student_name=student.name,
        course=student.course,
        door_id=door.id,
        operator_id=current_user.id
    )
    db.session.add(new_exit)
    db.session.commit()
    photo_url = None
    if student.photo_filename:
        photo_url = url_for('routes.student_photo', filename=student.photo_filename, _external=True)

    return jsonify({
        'success': True,
        'message': f'Salida registrada para {student.name}.',
        'student': {'name': student.name, 'course': student.course, 'photo_url': photo_url }
    })

# --- CRUD de Estudiantes ---
@bp.route('/students')
@login_required
@admin_required
def list_students():
    page = request.args.get('page', 1, type=int)
    students = Student.query.order_by(Student.name).paginate(page=page, per_page=15)
    return render_template('students/students.html', students=students)

@bp.route('/students/new', methods=['GET', 'POST'])
@login_required
@admin_required
def create_student():
    form = StudentForm()
    if form.validate_on_submit():
        if Student.query.get(form.id.data):
            flash('Ya existe un estudiante con ese ID.', 'danger')
        else:
            student = Student(id=form.id.data, name=form.name.data, course=form.course.data, authorized=form.authorized.data)
            # --- LÓGICA DE SUBIDA DE FOTO ---
            if form.photo.data:
                photo_file = form.photo.data
                # Guardar el archivo como {student.id}.jpg
                filename = f"{student.id}.jpg"
                photo_path = os.path.join(current_app.root_path, current_app.config['STUDENT_PHOTOS_FOLDER'], filename)
                photo_file.save(photo_path)
                student.photo_filename = filename
            db.session.add(student)
            db.session.commit()
            flash('Estudiante creado exitosamente.', 'success')
            return redirect(url_for('routes.list_students'))
    return render_template('students/student_form.html', form=form, title="Nuevo Estudiante")

@bp.route('/students/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_student(id):
    student = Student.query.get_or_404(id)
    form = StudentForm(obj=student)
    if form.validate_on_submit():
        student.name = form.name.data
        student.course = form.course.data
        student.authorized = form.authorized.data
        # --- LÓGICA DE SUBIDA DE FOTO ---
        if form.photo.data:
            photo_file = form.photo.data
            filename = f"{student.id}.jpg"
            photo_path = os.path.join(current_app.root_path, current_app.config['STUDENT_PHOTOS_FOLDER'], filename)
            photo_file.save(photo_path)
            student.photo_filename = filename
        db.session.commit()
        flash('Estudiante actualizado exitosamente.', 'success')
        return redirect(url_for('routes.list_students'))
    return render_template('students/student_form.html', form=form, title="Editar Estudiante", student=student)

@bp.route('/students/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_student(id):
    student = Student.query.get_or_404(id)
    db.session.delete(student)
    db.session.commit()
    flash('Estudiante eliminado exitosamente.', 'success')
    return redirect(url_for('routes.list_students'))


# --- Importación de Estudiantes ---
@bp.route('/students/import', methods=['GET', 'POST'])
@login_required
@admin_required
def import_students():
    form = ImportForm()
    if form.validate_on_submit():
        file = form.file.data
        filename = secure_filename(file.filename)
        if filename != '':
            file_ext = os.path.splitext(filename)[1]
            if file_ext not in current_app.config['UPLOAD_EXTENSIONS']:
                flash('Extensión de archivo no válida.', 'danger')
                return redirect(url_for('routes.import_students'))
            
            try:
                df = pd.read_excel(file)
                required_columns = ['id', 'name', 'course', 'authorized']
                if not all(col in df.columns for col in required_columns):
                    flash(f'El archivo debe contener las columnas: {", ".join(required_columns)}', 'danger')
                    return redirect(url_for('routes.import_students'))
                
                # Proceso de importación
                added_count = 0
                updated_count = 0
                errors = []
                for index, row in df.iterrows():
                    student_id = row['id']
                    student = Student.query.get(student_id)
                    if student: # Actualizar
                        student.name = row['name']
                        student.course = row['course']
                        student.authorized = bool(row['authorized'])
                        updated_count += 1
                    else: # Añadir
                        new_student = Student(
                            id=student_id,
                            name=row['name'],
                            course=row['course'],
                            authorized=bool(row['authorized'])
                        )
                        db.session.add(new_student)
                        added_count += 1
                db.session.commit()
                flash(f'Importación completa. {added_count} estudiantes añadidos, {updated_count} actualizados.', 'success')
                return redirect(url_for('routes.list_students'))

            except Exception as e:
                flash(f'Ocurrió un error al procesar el archivo: {e}', 'danger')

    return render_template('students/import.html', form=form)


@bp.route('/students/import/template')
@login_required
@admin_required
def download_template():
    data = {
        'id': [1001, 1002],
        'name': ['Juan Perez', 'Maria Garcia'],
        'course': ['5to A', '6to B'],
        'authorized': [1, 0]
    }
    df = pd.DataFrame(data)
    
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')
    df.to_excel(writer, index=False, sheet_name='Estudiantes')
    writer.close()
    output.seek(0)
    
    return Response(output, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": "attachment;filename=plantilla_estudiantes.xlsx"})


# --- CRUD de Usuarios (Solo Admin) ---
@bp.route('/users')
@login_required
@admin_required
def list_users():
    users = User.query.all()
    return render_template('users/users.html', users=users)

# La creación se hace via /register
# Edición y eliminación
@bp.route('/users/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(id):
    # Lógica para editar usuario (similar a estudiantes)
    # ...
    return "Not implemented yet"

@bp.route('/users/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(id):
    if id == current_user.id:
        flash('No puedes eliminar tu propio usuario.', 'danger')
        return redirect(url_for('routes.list_users'))
    user = User.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    flash('Usuario eliminado.', 'success')
    return redirect(url_for('routes.list_users'))

@bp.route('/users/<int:id>/change-password', methods=['GET', 'POST'])
@login_required
@admin_required
def change_user_password(id):
    user = User.query.get_or_404(id)
    # Un admin no puede cambiar la contraseña de otro admin
    if user.role == Role.ADMIN and current_user.id != user.id:
        flash('No puedes cambiar la contraseña de otro administrador.', 'danger')
        return redirect(url_for('routes.list_users'))

    form = ChangePasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash(f'La contraseña para el usuario {user.username} ha sido actualizada.', 'success')
        return redirect(url_for('routes.list_users'))
    
    return render_template('users/change_password.html', title="Cambiar Contraseña", form=form, user=user)

# --- Manejadores de Errores ---
@bp.app_errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@bp.app_errorhandler(403)
def forbidden_error(error):
    return render_template('403.html'), 403

@bp.route('/students/qrs')
@login_required
@admin_required
def generate_qrs():
    """Genera una página imprimible con los QR de todos los estudiantes."""
    students = Student.query.order_by(Student.name).all()
    students_with_qrs = []

    for student in students:
        # 1. Crear el payload del QR en formato JSON
        qr_payload = json.dumps({"id": student.id})

        # 2. Generar la imagen del QR en memoria
        qr_img = qrcode.make(qr_payload)
        
        # 3. Convertir la imagen a base64 para insertarla en el HTML
        buffered = io.BytesIO()
        qr_img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

        students_with_qrs.append({
            'id': student.id,
            'name': student.name,
            'course': student.course,
            'qr_code': img_str
        })

    return render_template('students/qrs.html', students_with_qrs=students_with_qrs)

# app/routes.py
# ... (después de las otras rutas)

@bp.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def app_settings():
    form = SettingsForm()
    if form.validate_on_submit():
        cooldown_setting = Setting.query.filter_by(key='exit_cooldown_minutes').first()
        if not cooldown_setting:
            cooldown_setting = Setting(key='exit_cooldown_minutes', value=str(form.exit_cooldown_minutes.data))
            db.session.add(cooldown_setting)
        else:
            cooldown_setting.value = str(form.exit_cooldown_minutes.data)
        
        db.session.commit()
        flash('Configuración guardada exitosamente.', 'success')
        return redirect(url_for('routes.app_settings'))
    
    # Cargar el valor actual en el formulario para mostrarlo
    cooldown_setting = Setting.query.filter_by(key='exit_cooldown_minutes').first()
    if cooldown_setting:
        form.exit_cooldown_minutes.data = int(cooldown_setting.value)
    else:
        form.exit_cooldown_minutes.data = 60 # Valor por defecto si no existe

    return render_template('main/settings.html', title="Configuración", form=form)


# --- CRUD de Puertas ---

@bp.route('/doors')
@login_required
@admin_required
def list_doors():
    doors = Door.query.order_by(Door.name).all()
    return render_template('doors/doors.html', doors=doors, title="Gestionar Puertas")

@bp.route('/doors/new', methods=['GET', 'POST'])
@login_required
@admin_required
def create_door():
    form = DoorForm()
    if form.validate_on_submit():
        new_door = Door(name=form.name.data, is_active=form.is_active.data)
        db.session.add(new_door)
        db.session.commit()
        flash('Puerta creada exitosamente.', 'success')
        return redirect(url_for('routes.list_doors'))
    return render_template('doors/door_form.html', form=form, title="Nueva Puerta")

@bp.route('/doors/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_door(id):
    door = Door.query.get_or_404(id)
    form = DoorForm(obj=door)
    if form.validate_on_submit():
        door.name = form.name.data
        door.is_active = form.is_active.data
        db.session.commit()
        flash('Puerta actualizada exitosamente.', 'success')
        return redirect(url_for('routes.list_doors'))
    return render_template('doors/door_form.html', form=form, title="Editar Puerta", door=door)

@bp.route('/doors/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_door(id):
    door = Door.query.get_or_404(id)
    if door.exits:
        flash('No se puede eliminar una puerta que tiene registros de salida asociados.', 'danger')
        return redirect(url_for('routes.list_doors'))
    db.session.delete(door)
    db.session.commit()
    flash('Puerta eliminada exitosamente.', 'success')
    return redirect(url_for('routes.list_doors'))


@bp.route('/report', methods=['GET', 'POST'])
@login_required
def daily_report():
    form = ReportForm()
    selected_date = date.today() # Valor por defecto

    if form.validate_on_submit():
        selected_date = form.report_date.data
    
    # --- LÓGICA DE ZONA HORARIA MEJORADA ---

    # 1. Cargar la zona horaria local desde la configuración de la app
    try:
        local_tz = pytz.timezone(current_app.config.get('LOCAL_TIMEZONE', 'UTC'))
    except pytz.UnknownTimeZoneError:
        local_tz = pytz.utc

    # 2. Crear el inicio y fin del día en la zona horaria LOCAL
    start_of_day_local = local_tz.localize(datetime.combine(selected_date, time.min))
    end_of_day_local = local_tz.localize(datetime.combine(selected_date, time.max))
    
    # 3. Convertir ese rango a UTC para la consulta en la base de datos
    start_of_day_utc = start_of_day_local.astimezone(pytz.utc)
    end_of_day_utc = end_of_day_local.astimezone(pytz.utc)
    
    # 4. Realizar la consulta con el rango UTC correcto
    exits_for_date = Exit.query.filter(
        Exit.timestamp >= start_of_day_utc,
        Exit.timestamp <= end_of_day_utc
    ).order_by(Exit.timestamp.asc()).all()

    # --- FIN DE LA LÓGICA MEJORADA ---
    
    # El resto de la función (manejo de exportación) no necesita cambios,
    # ya que opera sobre `exits_for_date`, que ahora contiene los datos correctos.
    if 'export' in request.form:
        # (El código de exportación a Excel se mantiene igual)
        data = {
            'Fecha y Hora': [(pytz.utc.localize(e.timestamp).astimezone(local_tz)).strftime('%Y-%m-%d %H:%M:%S') for e in exits_for_date],
            'ID Estudiante': [e.student_id for e in exits_for_date],
            'Nombre Estudiante': [e.student_name for e in exits_for_date],
            'Curso': [e.course for e in exits_for_date],
            'Puerta': [e.door.name for e in exits_for_date],
            'Operador': [e.operator.username for e in exits_for_date]
        }
        df = pd.DataFrame(data)
        output = io.BytesIO()
        # ... (resto del código de exportación)
        writer = pd.ExcelWriter(output, engine='openpyxl')
        df.to_excel(writer, index=False, sheet_name=f'Salidas_{selected_date.strftime("%Y-%m-%d")}')
        writer.close()
        output.seek(0)
        
        return Response(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment;filename=reporte_salidas_{selected_date.strftime('%Y-%m-%d')}.xlsx"}
        )
    
    form.report_date.data = selected_date

    return render_template('main/report.html', 
                           form=form, 
                           exits=exits_for_date, 
                           selected_date=selected_date,
                           title="Reporte Diario de Salidas")

# --- Ruta para servir las fotos de los estudiantes ---
@bp.route('/student_photo/<filename>')
def student_photo(filename):
    directory = os.path.join(current_app.root_path, current_app.config['STUDENT_PHOTOS_FOLDER'])
    return send_from_directory(directory, filename)
