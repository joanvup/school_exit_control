# app/models.py
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
import enum

db = SQLAlchemy()

class Role(enum.Enum):
    ADMIN = 'admin'
    OPERATOR = 'operator'

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.Enum(Role), default=Role.OPERATOR, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True) # Este ID debe coincidir con el del QR
    name = db.Column(db.String(120), nullable=False)
    course = db.Column(db.String(80), nullable=True)
    authorized = db.Column(db.Boolean, default=False, nullable=False)
    photo_filename = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    exits = db.relationship('Exit', backref='student', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Student {self.id}: {self.name}>'

# app/models.py

class Exit(db.Model):
    __tablename__ = 'exits'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    student_name = db.Column(db.String(120), nullable=False)
    course = db.Column(db.String(80), nullable=True)
    
    # --- CAMBIO AQUÍ ---
    # Reemplazamos el campo 'door' de tipo Enum por una Foreign Key
    door_id = db.Column(db.Integer, db.ForeignKey('doors.id'), nullable=False)
    
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    operator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    operator = db.relationship('User', backref='exits_recorded')
    # Añadimos la relación para poder acceder a los datos de la puerta fácilmente
    door = db.relationship('Door', backref='exits')

    def __repr__(self):
        return f'<Exit for student {self.student_id} at {self.timestamp}>'

class Setting(db.Model):
    __tablename__ = 'settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        return f'<Setting {self.key}>'
    
# app/models.py
# ... (puede ir antes o después de la clase Exit)

class Door(db.Model):
    __tablename__ = 'doors'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f'<Door {self.name}>'