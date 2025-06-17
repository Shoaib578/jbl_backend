import os
import csv
import logging
from flask import Flask
from flask_cors import CORS
from werkzeug.security import generate_password_hash
from sqlalchemy.exc import OperationalError
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity

from .models import User, Product
from .extensions import db, login_manager

from dotenv import load_dotenv
load_dotenv()
# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def create_app():
    """
    Application factory function to create and configure the Flask app.
    """
    logger.info("Initialising Flask application")

    # Create Flask application
    app = Flask(__name__)
    # Load configuration from environment variables
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret_key') #  Fallback if SECRET_KEY is missing
    # app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'mysql+pymysql://root:password@mysql-db:3306/jbl-db')
    app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://root:@localhost/jbl"
    app.config['JWT_SECRET_KEY'] = os.getenv("JWT_SECRET_KEY")  # Replace with a strong key
    app.config['JWT_VERIFY_SUB'] = False
    app.config['JWT_TOKEN_LOCATION'] = ['headers']

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    logger.info(f"Environment: {os.getenv('FLASK_ENV', 'production')}")
    
    # Initialise extensions
    db.init_app(app)

    login_manager.init_app(app)
    jwt = JWTManager(app)
    CORS(app)

    logger.info("Flask app initialised successfully.")

    # Configure login redirection for unauthorised users
    login_manager.login_view = 'admin_routes.admin_login'
    logger.info("Registering routes.")
    
    # Register Blueprints
    from .routes import main
    app.register_blueprint(main)

    from .admin_routes import admin_routes
    app.register_blueprint(admin_routes)

    # Set up application context to initialise database and default data
    with app.app_context():
        # Create database tables
        logger.info("Creating database tables.")
        db.create_all()
        
        # Ensure default admin user exists
        logger.info("Checking for admin user.")
        create_admin_user()

        # Load initial product data from CSV during setup
        if Product.query.count() == 0:
            logger.info("Loading initial products from CSV.")
            load_products_from_csv()

    return app

def create_admin_user():
    """
    Creates the default admin user if it doesn't exist.
    Retries if a deadlock occurs.
    """
    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            # Check if admin user already exists
            if not User.query.filter_by(username='admin',is_admin=True).first():
                # Create admin user with default password
                admin = User(
                    username='admin',
                    email='admin@example.com',
                    password_hash=generate_password_hash('admin123'),
                    is_admin=True
                )
                db.session.add(admin)
                db.session.commit()
                logger.info("Admin user created successfully.")
            else:
                logger.info("Admin user already exists. Skipping creation.")
            break
        except OperationalError as e:
            # Handle potential database deadlocks during user creation
            db.session.rollback()
            retry_count += 1
            logger.warning(f"Deadlock detected. Retrying... ({retry_count}/{max_retries})")
            if retry_count == max_retries:
                logger.error("Failed to create admin user after multiple retries.")
                raise Exception("Failed to create admin user after multiple retries.") from e

def load_products_from_csv():
    """
    Loads products from CSV file into the database.
    Handles validation and skips invalid entries.
    """
    csv_file_path = os.path.join(os.path.dirname(__file__), 'products.csv')

    # Only clear existing products in development/testing environments
    if os.getenv('FLASK_ENV') in ['development', 'testing']:
        logger.warning("Clearing all existing products from the database (development/testing environment).")
        Product.query.delete()
        db.session.commit()

    # Track processed IDs to avoid duplicates
    processed_ids = set()

    with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        for row in reader:
            try:
                logger.info(f"Processing row: {row}")

                # Skip empty rows
                if not any(row.values()):
                    continue

                # Validate and skip duplicate product IDs
                product_id = row['id'].strip()
                if not product_id or product_id in processed_ids:
                    logger.warning(f"Skipping duplicate or invalid product ID: {product_id}")
                    continue

                # Validate price
                try:
                    price = float(row['price'].strip())
                    if price < 0:
                        raise ValueError("Price cannot be negative")
                except (ValueError, TypeError):
                    logger.warning(f"Skipping row with invalid price: {row}")
                    continue

                # Add product to database
                logger.info(f"Adding product with ID: {product_id}")
                product = Product(
                    id=str(product_id),  
                    name=row['name'].strip(),
                    description=row.get('description', '').strip(),
                    category=row.get('category', '').strip(),
                    price=price,
                    image=row.get('image', '').strip(),
                    badge_text=row.get('badge_text', '').strip() or None,
                    badge_type=row.get('badge_type', '').strip() or None,
                    is_new=row.get('is_new', '').strip().upper() == 'TRUE'
                )

                db.session.add(product)
                processed_ids.add(product_id)

            except KeyError as e:
                # Handle missing required fields
                logger.error(f"Missing required field {str(e)}: {row}")
                continue
            except Exception as e:
                # Catch all other exceptions during row processing
                logger.error(f"Error processing row: {str(e)}")
                continue
        # Commit all valid products to the database
        db.session.commit()
        logger.info("Finished loading products into the database.")
