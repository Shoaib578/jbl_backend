import pytest
import sys
import os 
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from werkzeug.datastructures import FileStorage
from flask import Flask
from io import BytesIO
from app import create_app
from app.extensions import db
from app.models import User, Product

@pytest.fixture
def app():
    """
    Pytest fixture to create and configure a Flask app instance for testing.

    Yields:
        app (Flask): Configured Flask app instance.
    """
    # Create and configure Flask app for testing
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    # Initialise database with app
    with app.app_context():
        # Clear existing data
        db.drop_all()
        # Create all tables in the database
        db.create_all()
        # Check if admin user already exists
        existing_user = User.query.filter_by(email='admin@gmail.com').first()
        if not existing_user:
            # Create and add test admin user to database
            admin = User(username='admin', email='admin@gmail.com', is_admin=True)
            admin.password = 'admin123'
            db.session.add(admin)
            db.session.commit()
    yield app

@pytest.fixture
def client(app):
    """
    Pytest fixture to create a test client for the Flask app.

    Args:
        app (Flask): The Flask app instance provided by 'app'

    Returns:
        FlaskClient: Test client for Flask app.
    """
    # Create and return test client for making HTTP requests
    return app.test_client()

def test_admin_login_success(client):
    """
    Tests successful admin login with valid credentials
    """
    # Simulate POST request to admin login route with valid credentials
    response = client.post('/admin/login', data={
        'username': 'admin',
        'password': 'admin123'
    }, follow_redirects=True) # Follow redirects to reach final response

    # Assert the response code is 200
    assert response.status_code == 200
    # Assert the success message is present in response data
    assert b'Logged in successfully!' in response.data

def test_admin_login_failure(client):
    """
    Tests failed admin login with invalid credentials
    """
    # Simulate POST request to admin login route with invalid credentials
    response = client.post('/admin/login', data={
        'username': 'admin',
        'password': 'admin1234wrong' # Incorrect password
    }, follow_redirects=True)

    # Assert the response code is 200
    assert response.status_code == 200
    # Assert the error message is present in response data
    assert b'Invalid username or password.' in response.data

def test_admin_dashboard_requires_login(client):
    """
    Tests accessing the admin dashboard without being logged in.
    """
    # Simulate GET request to admin dashboard without logging in
    response = client.get('/admin/dashboard', follow_redirects=True)

    # Assert the response code is 200
    assert response.status_code == 200
    # Assert the redirection message is present
    assert b'Please log in to access this page.' in response.data

def test_admin_logout(client):
    """
    Tests admin logout functionality.
    """
    # Simulate logging in as admin user
    client.post('/admin/login', data={
        'username': 'admin',
        'password': 'admin123'
    }, follow_redirects=True)

    # Simulate GET request to logout route
    response = client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b'Logged out successfully.' in response.data

def test_admin_add_product(client, app):
    """
    Tests the admin adding a new product successfully.
    """
    # Simulate logging in as admin user
    client.post('/admin/login', data={
        'username': 'admin',
        'password': 'admin123'
    }, follow_redirects=True)

    # Prepare mock product data
    data = {
        'name': 'Test product',
        'description': 'Test description',
        'category': 'Test category', 
        'price': '19.99',
        'badge_text': 'New',
        'badge_type': 'new',
        'is_new': 'on', # Indicate product is new
    }

    # Mock FileStorage object for image upload
    image = FileStorage(
        stream=BytesIO(b"test image content"),
        filename='test_image.jpg',
        content_type='image/jpeg'
    )
    data['image'] = image

    # Simulate POST request to create new product
    response = client.post('/admin/create_product', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert response.status_code == 200
    assert b'Product created successfully!' in response.data

    # Confirm the product is stored in the database correctly
    with app.app_context():
        # Query database for newly added product by name
        product = Product.query.filter_by(name='Test product').first()
        # Assert the product exists in the database
        assert product is not None
        # Assert product details match input data
        assert product.description == 'Test description'
        assert product.price == 19.99

def test_admin_edit_product(client, app):
    """
    Tests admin editing an existing product successfully.
    """
    client.post('/admin/login', data={
        'username': 'admin',
        'password': 'admin123'
    }, follow_redirects=True)

    with app.app_context():
        # Create test product to be edited
        product = Product(
            name='Original product',
            description='Original description',
            category='Original category',
            price=29.99,
            badge_text='Original badge',
            badge_type='original',
            is_new=False,
        )
        db.session.add(product)
        # Commit new product to database
        db.session.commit()
        # Store product ID for editing
        product_id = product.id

        # Prepare updated product data
        data = {
            'name': 'Updated product',
            'description': 'Updated description',
            'category': 'Updated category',
            'price': '39.99',
            'badge_text': 'Updated badge',
            'badge_type': 'updated',
            'is_new': 'on',
        }

        # Simulate POST request to edit existing product
        response = client.post(f'/admin/edit_product/{product_id}', data=data, follow_redirects=True)
        assert response.status_code == 200
        assert b'Product updated successfully!' in response.data

        with app.app_context():
            # Query database for updated product by ID
            updated_product = db.session.get(Product, product_id)
            # Assert product's name has been updated
            assert updated_product.name == 'Updated product'
            # Assert product's description has been updated
            assert updated_product.description == 'Updated description'
            # Assert product's price has been updated
            assert updated_product.price == 39.99

def test_admin_delete_product(client, app):
    """
    Tests admin deleting an existing product successfully.
    """
    client.post('/admin/login', data={
        'username': 'admin',
        'password': 'admin123'
    }, follow_redirects=True)
    
    with app.app_context():
        # Create test product to be deleted
        product = Product(
            name='Product 1',
            description='Description',
            category='Category',
            price=49.99,
            badge_text='Badge',
            badge_type='type',
            is_new=False,
        )
        db.session.add(product)
        db.session.commit()
        # Store product ID for deletion
        product_id = product.id

    # Simulate POST request to delete existing product
    response = client.post(f'/admin/delete_product/{product_id}', follow_redirects=True)
    assert response.status_code == 200
    assert b"successfully deleted" in response.data

    # Attempt to delete same product again to test error handling
    response = client.post(f'/admin/delete_product/{product_id}', follow_redirects=True)
    assert b"Product not found." in response.data

    with app.app_context():
        # Query database for deleted product by ID
        deleted_product = db.session.get(Product, product_id)
        # Assert the product no longer exists in the databsae
        assert deleted_product is None