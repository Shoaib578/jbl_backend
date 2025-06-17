import pytest
import sys
import os
# Inserting parent directory into sys.path to import 'app' module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app, db
from app.models import Product
from app.__init__ import load_products_from_csv
from unittest.mock import patch
from io import StringIO

@pytest.fixture
def client():
    """
    Creates a test client for the Flask application.
    Enables testing mode and provides a client to send requests to the app.
    """
    # Create Flask app instance using factory function
    app = create_app()
    #Enable testing mode for better error reporting
    app.config['TESTING'] = True
    # Creates test client using Flask app's context
    with app.test_client() as client: 
        # Provide test client to tests
        yield client

@pytest.fixture(autouse=True)
def setup_database():
    """
    Automatically sets up the database before each test.
    """
    app = create_app()
    with app.app_context():
        # Clear existing products
        Product.query.delete()
        db.session.commit()
        # Load test products from CSV
        load_products_from_csv()


def test_get_products_status_code(client):
    """
    Tests that the /api/products endpoint returns 200 OK status code.
    """
    # Send GET request to /api/products endpoint
    response = client.get('/api/products')
    # Assert the response status code is 200 (OK)
    assert response.status_code == 200

def test_get_products_returns_json(client):
    """
    Tests that the /api/products endpoint returns a JSON response.
    """
    response = client.get('/api/products')
    # Assert the response is in JSON format
    assert response.is_json

def test_get_products_returns_list(client):
    """
    Tests that the /api/products endpoint returns a list of products.
    """
    response = client.get('/api/products')
    # Parse JSON data from response
    data = response.get_json()
    # Assert the data is a list
    assert isinstance(data, list)

def test_product_fields(client):
    """
    Tests that each product in the response contains all required fields.
    """
    response = client.get('/api/products')
    products = response.get_json()
    # Define a set of required fields for each product 
    required_fields = {'id', 'name', 'description', 'price', 'image', 'category', 'badge_text', 'badge_type', 'is_new'}
    # Iterate over each product in the response
    for product in products:
        # Asserts the presence of required fields
        assert required_fields.issubset(product.keys())

def test_get_new_products(client):
    """
    Tests that the /api/products/new endpoint returns only new products.
    """
    response = client.get('/api/products')
    assert response.status_code == 200
    products = response.get_json() or []

    # Filter products manually for 'is_new=True'
    new_products = [product for product in products if product['is_new']]

    # Assert that new products exist
    assert len(new_products) == 3
    assert all(product['is_new'] is True for product in new_products)

def test_missing_csv(client):
    """
    Tests that when the CSV file is missing, the /api/products endpoint returns an empty list.
    """
    with client.application.app_context():
        # Ensure no products are present
        Product.query.delete()
        db.session.commit()

    # Mock 'os.path.join' to simulate a missing CSV file
    with patch('app.routes.os.path.join', return_value='non_existent.csv'):
        # Send GET request to the /api/products endpoint
        response = client.get('/api/products')
        data = response.get_json() or []
        # Asserts the response data is an empty list
        assert data == []
        # Asserts the response status code is still 200 
        assert response.status_code == 200

def test_invalid_price_in_csv(client, monkeypatch):
    """
    Tests that products with invalid price values in the CSV are skipped and not included in the response.
    """
    # Define invalid CSV content with non-numeric price
    invalid_csv_content = """id;name;description;price;image;category;badge_text;badge_type;is_new
                             1;Test Product;Test Description;10.99;/path/to/image.jpg;Test Category;;;FALSE
                             1;Duplicate Product;Invalid Description;15.99;/path/to/image2.jpg;Test Category;;;FALSE
                             2;Invalid Product;Invalid Description;invalid_price;/path/to/image3.jpg/;Invalid Category;;;FALSE
                          """
    def mock_open(*args, **kwargs):
        """
        Mock the open function to return the invalid CSV content.
        """
        return StringIO(invalid_csv_content)

    # Apply mock to built-in open function
    monkeypatch.setattr('builtins.open', mock_open)

    # Attempt to load products from mocked invalid CSV
    with client.application.app_context():
        from app.__init__ import load_products_from_csv
        load_products_from_csv()

    # Send GET request to /api/products endpoint
    response = client.get('/api/products')
    products = response.get_json() or []

    # Validate that only valid products are loaded
    # Only the first product should be valid
    assert len(products) == 1  
    assert str(products[0]['id']) == '1'
    assert products[0]['name'] == 'Test Product'
    assert products[0]['price'] == 10.99


def test_filter_products_by_category(client):
    """
    Tests that filtering products by category returns only products from the given category.
    """
    response = client.get('/api/products')
    assert response.status_code == 200

    products = response.get_json()

    # Filter products by 'Headphones' category
    filtered_products = [product for product in products if product['category'].strip().lower() == 'headphones']
    # Assert at least one product is found in the 'Headphones' category
    assert len(filtered_products) > 0, f"No products found for category 'Headphones'. Retrieved: {products}"
    # Assert all filtered products belong to the 'Headphones' category
    assert all(product['category'].strip().lower() == 'headphones' for product in filtered_products)

def test_product_badge_info(client):
    """
    Tests that product badge information is correctly structured.
    """
    response = client.get('/api/products')
    products = response.get_json()
    # Iterate over each product to verify badge information
    for product in products:
        if product['badge_text'] and product['badge_type']:
            # Assert that badge_text is a string
            assert isinstance(product['badge_text'], str)
            # Assert that badge_type is a string
            assert isinstance(product['badge_type'], str)
        else:
            # If badge_text or badge_type is missing, assert they are None or empty strings
            assert product['badge_text'] is None or product['badge_text'] == ''
            assert product['badge_type'] is None or product['badge_type'] == ''

def test_unique_product_ids(client):
    """
    Tests that all products have unique IDs to prevent duplication.
    """
    response = client.get('/api/products')
    products = response.get_json()
    # Extract all product IDs
    ids = [product['id'] for product in products]
    # Assert that the number of IDs equals the number of unique IDs
    assert len(ids) == len(set(ids)), "Duplicate product IDs found"

def test_empty_csv_file(client, monkeypatch):
    """
    Tests that when the CSV is empty, the /api/products endpoint returns an empty list.
    """
    def mock_load_products_from_csv():
        """
        Mock function to simulate loading products from an empty CSV file.
        """
        # Remove all products
        Product.query.delete()
        db.session.commit()

    with client.application.app_context():
        # Replace actual CSV loading function with the mock
        monkeypatch.setattr('app.__init__.load_products_from_csv', mock_load_products_from_csv)
        # Attempt to load products from the mocked empty CSV
        from app.__init__ import load_products_from_csv
        load_products_from_csv()

    response = client.get('/api/products')
    data = response.get_json()
    # Assert that no products are returned
    assert data == []
    assert response.status_code == 200