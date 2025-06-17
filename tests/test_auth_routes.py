import pytest
import uuid
import sys 
import os
# Modify system path to ensure the app module is discoverable for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app
from app.extensions import db
from app.models import User, Product, Order

@pytest.fixture
def app():
    """
    Creates and configures the Flask app for testing.
    """
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.app_context():
        # Create all tables based on models
        db.create_all()
        # Provide app to tests
        yield app
    with app.app_context():
        # Remove session after tests
        db.session.remove()
        # Drop all tables to cleanup
        db.drop_all()

@pytest.fixture
def client(app):
    """
    Provides a test client for the Flask app.
    """
    return app.test_client()

def test_user_signup_success(client):
    """
    Tests successful user signup with unique email.
    """
    unique_email = f"testuser_{uuid.uuid4().hex}@example.com"
    response = client.post('/api/signup', json={
        'username': 'testuser',
        'email': unique_email,
        'password': 'testpassword'
    })
    assert response.status_code == 201
    data = response.get_json()
    assert data['message'] == 'User created successfully'

    with client.application.app_context():
        user = User.query.filter_by(email=unique_email).first()
        assert user is not None
        assert user.username == 'testuser'

def test_user_signin_success(client, app):
    """
    Tests successful user signin with correct credentials.
    """
    unique_email = f"testuser_{uuid.uuid4().hex}@example.com"
    with app.app_context():
        user = User(username='testuser', email=unique_email)
        user.password = 'testpassword'
        db.session.add(user)
        db.session.commit()
        print("User created and committed to the database.")

    response = client.post('/api/signin', json={
        'email': unique_email,
        'password': 'testpassword'
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['message'] == 'Login successful'
    assert 'user' in data
    assert isinstance(data['user'], int)

def test_get_products(client, app):
    """
    Tests retrieving all products from the API.
    """
    with app.app_context():
        # Clear existing products
        Product.query.delete()
        db.session.commit()

        # Add test product
        product = Product(
            name='Test product',
            description='Test description',
            category='Test category',
            price=19.99,
            badge_text='New',
            badge_type='new',
            is_new=True,
            image=''
        )
        db.session.add(product)
        db.session.commit()

    # Make API call to get products
    response = client.get('/api/products')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) > 0

    # Assert the first product is the test product
    assert data[0]['name'] == 'Test product'
    assert data[0]['description'] == 'Test description'

def test_get_single_product(client, app):
    """
    Tests retrieving a single product by its ID.
    """
    with app.app_context():
        # Add test product
        product = Product(
            name='Test product',
            description='Test description',
            category='Test category',
            price=19.99,
            badge_text='',
            badge_type='',
            is_new=False,
            image=''
        )
        db.session.add(product)
        db.session.commit()
        product_id = product.id
    
    # Make API call to get the single product
    response = client.get(f'/api/products/{product_id}')
    assert response.status_code == 200
    data = response.get_json()
    # Assert the fetched product matches the single product
    assert data['name'] == 'Test product'
    assert data['id'] == product_id

def test_checkout(client, app):
    """
    Tests the checkout process for placing an order.
    """
    unique_email = f"testuser_{uuid.uuid4().hex}@example.com"
    with app.app_context():
        # Create user
        user = User(username='testuser', email=unique_email)
        user.password = 'testpassword'
        db.session.add(user)
        db.session.commit()
        user_id = user.id

        # Create products
        product1 = Product(
            name='Product 1',
            description='Description 1',
            category='Category 1',
            price=10.00,
            badge_text='New',
            badge_type='new',
            is_new=True,
            image=''
        )

        product2 = Product(
            name='Product 2',
            description='Description 2',
            category='Category 2',
            price=20.00,
            badge_text='',
            badge_type='',
            is_new=False,
            image=''
        )
        db.session.add_all([product1, product2])
        db.session.commit()

        # Prepare order data
        order_data = {
            'user_id': user_id,
            'items': [
                {'productId': product1.id, 'amount': 2},
                {'productId': product2.id, 'amount': 2}
            ],
            'shipping_address': '123 Test Rd',
            'phone_number': '01234567890',
            'email': unique_email
        }
        # Send checkout request
        response = client.post('/api/checkout', json=order_data)
        assert response.status_code == 201
        data = response.get_json()
        assert data['message'] == 'Order placed successfully!'

def test_get_order_history(client, app):
    """
    Tests fetching a user's order history.
    """
    unique_email = f"testuser_{uuid.uuid4().hex}@example.com"
    with app.app_context():
        user = User(username='testuser', email=unique_email)
        user.password = 'securepassword'
        db.session.add(user)
        db.session.commit()
        user_id = user.id

        product = Product(
            name='Test product',
            description='Test description',
            category='Test category',
            price=19.99,
            badge_text='New',
            badge_type='new',
            is_new=True,
            image=''
        )
        db.session.add(product)
        db.session.commit()

        order = Order(
            user_id=user_id,
            product_id=product.id,
            amount=2,
            total_price=39.98,
            status='Completed',
            shipping_address='123 Test Rd',
            phone_number='01234567890',
            email=unique_email
        )
        db.session.add(order)
        db.session.commit()

    # Send request to get order history
    response = client.get(f'/api/orders/{user_id}')
    assert response.status_code == 200
    data = response.get_json()
    assert 'orders' in data
    assert len(data['orders']) > 0
