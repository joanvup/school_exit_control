# Aplicación de Control de Salidas Peatonales

Aplicación web desarrollada en Flask y JavaScript para gestionar y registrar las salidas peatonales de estudiantes en un colegio mediante la lectura de códigos QR.

## Características

-   **Roles de Usuario**: Administrador (CRUD completo) y Operador (solo escaneo y consulta).
-   **Autenticación**: Sistema de login seguro con contraseñas hasheadas.
-   **Escaneo de QR**: Lectura de QR desde la cámara del navegador (móvil o desktop) para registrar salidas.
-   **Gestión de Estudiantes**: CRUD completo para la base de datos de estudiantes.
-   **Importación Masiva**: Sube un archivo XLSX para añadir o actualizar estudiantes en lote.
-   **Historial de Salidas**: Registro detallado de todas las salidas, con filtros.
-   **Base de Datos Flexible**: Configurada para SQLite por defecto, fácilmente adaptable a MySQL o PostgreSQL.

## Instrucciones para Ejecutar Localmente

Sigue estos pasos para poner en marcha la aplicación en tu entorno de desarrollo.

### Prerrequisitos

-   Python 3.8 o superior
-   `pip` y `venv`

### 1. Crear Entorno Virtual

Clona el repositorio y crea un entorno virtual para aislar las dependencias.

```bash
git clone <url-del-repositorio>
cd school_exit_control
python -m venv venv