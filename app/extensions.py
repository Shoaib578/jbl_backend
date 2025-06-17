from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_jwt_extended import JWTManager
# Initialise SQLAlchemy for database operations
db = SQLAlchemy()
# Initialise Flask-Login for user authentication management
login_manager = LoginManager()
jwt = JWTManager()
