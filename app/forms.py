# app/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, FileField
from wtforms.validators import DataRequired, EqualTo, ValidationError, Length
from .models import User
from flask_wtf.file import FileField, FileAllowed

class LoginForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired(), Length(min=4, max=80)])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    remember_me = BooleanField('Recuérdame')
    submit = SubmitField('Iniciar Sesión')

class RegistrationForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired(), Length(min=4, max=80)])
    password = PasswordField('Contraseña', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Repetir Contraseña', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Rol', choices=[('operator', 'Operador'), ('admin', 'Administrador')], validators=[DataRequired()])
    submit = SubmitField('Registrar')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Por favor, usa un nombre de usuario diferente.')

class StudentForm(FlaskForm):
    id = StringField('ID del Estudiante', validators=[DataRequired()])
    name = StringField('Nombre Completo', validators=[DataRequired()])
    course = StringField('Curso')
    authorized = BooleanField('Autorizado para Salida Peatonal')
    photo = FileField('Foto del Estudiante (JPG)', validators=[
        FileAllowed(['jpg', 'jpeg'], '¡Solo se permiten imágenes JPG!')
    ])
    submit = SubmitField('Guardar')

class ImportForm(FlaskForm):
    file = FileField('Archivo XLSX', validators=[DataRequired()])
    submit = SubmitField('Importar')


from wtforms import IntegerField
from wtforms.validators import NumberRange

class SettingsForm(FlaskForm):
    exit_cooldown_minutes = IntegerField(
        'Intervalo de Salida (minutos)',
        validators=[DataRequired(), NumberRange(min=0, max=1440)],
        description='Tiempo mínimo en minutos que debe pasar antes de que un mismo estudiante pueda registrar otra salida.'
    )
    submit = SubmitField('Guardar Cambios')


class DoorForm(FlaskForm):
    name = StringField('Nombre de la Puerta', validators=[DataRequired(), Length(max=50)])
    is_active = BooleanField('Activa', default=True)
    submit = SubmitField('Guardar')


from wtforms import DateField, SubmitField

class ReportForm(FlaskForm):
    report_date = DateField('Seleccionar Fecha', format='%Y-%m-%d', validators=[DataRequired()])
    submit = SubmitField('Generar Reporte')