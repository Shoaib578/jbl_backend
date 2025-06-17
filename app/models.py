from .extensions import db, login_manager
from datetime import datetime
from sqlalchemy.sql import func

from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class Product(db.Model):
    """
    Represents a product in the JBL ecommerce platform.
    """
    __tablename__ = 'products'

    # Unique identifier for each product
    id = db.Column(db.Integer, primary_key=True)
    # Product name
    name = db.Column(db.String(255), nullable=False)
    # Product description
    description = db.Column(db.Text, nullable=True)
    # Product category
    category = db.Column(db.String(100), nullable=False)
    # Product price
    price = db.Column(db.Float, nullable = False)
    # Optional badge text for product
    badge_text = db.Column(db.String(50), nullable=True)
    # Badge type 
    badge_type = db.Column(db.String(50), nullable=True)
    # Whether the product is new
    is_new = db.Column(db.Boolean, default=False)
    # Path to the product image
    image = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        """
        Returns a string representation of the product.
        """
        return f"<Product {self.name}>"

class User(db.Model, UserMixin):
    """
    Represents a user in the JBL ecommerce platform.
    """
    __tablename__ = 'users'

    # Unique identifier for each user
    id = db.Column(db.Integer, primary_key=True)
    # User's username
    username = db.Column(db.String(50), nullable=False)
    # User's email
    email = db.Column(db.String(100), nullable=False, unique=True)
    # User's hashed password
    password_hash = db.Column(db.String(255), nullable=False)
    # User's shipping address
    shipping_address = db.Column(db.String(255), nullable=True)
    # Flag to determine if the user is an admin
    is_admin = db.Column(db.Boolean, default=False)
   

    @property
    def password(self):
        """
        Prevents direct access to the password attribute.
        """
        raise AttributeError("Password is not a readable attribute.")

    @password.setter
    def password(self, password):
        """
        Hashes the password and stores it securely.
        """
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        """
        Checks if a plaintext password matches the stored hash.
        """
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        """
        Returns a string representation of the user.
        """
        return f"<User {self.username}>"
    
# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    """
    Callback to load a user from the database by their ID.
    """
    return db.session.get(User, int(user_id))

class Order(db.Model):
    """
    Represents an order placed by a user.
    """
    __tablename__ = 'orders'
    
    # Unique identifier for each order
    order_id = db.Column(db.Integer, primary_key=True)
    # User who placed the order
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    # Ordered product
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='SET NULL'), nullable=True)
    # Quantity of the ordered product
    amount = db.Column(db.Integer, nullable=False)
    # Total price of order
    total_price = db.Column(db.Float, nullable=False)
    # Order status
    status = db.Column(db.String(50), default='Pending')
    # Shipping address for the order
    shipping_address = db.Column(db.String(255), nullable=False)
    # Contact number for the order
    phone_number = db.Column(db.String(15), nullable=False)
    # Email from user who placed the order
    email = db.Column(db.String(100), nullable=False)
    # Optional product image for the order
    image = db.Column(db.String(255), nullable=True)  

    # Relationships to other models
    # Relationship with Product
    product = db.relationship('Product', backref='orders', lazy=True)
    # Relationship with User
    user = db.relationship('User', backref='orders', lazy=True)

    def __repr__(self):
        """
        Returns a string representation of the order.
        """
        return f"<Order {self.order_id} - {self.product.name} - {self.status}>"


class Wishlist(db.Model):
    __tablename__ = 'wishlist'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.ForeignKey('users.id'), nullable=False)  # Assuming you have a User model with an ID
    product_id = db.Column(db.ForeignKey('products.id'), nullable=False)  # Foreign key to Product table
    
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())
    
    product = db.relationship('Product', backref='wishlist')

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "product_id": self.product_id,
            "created_at": self.created_at.isoformat()
        }

class Review(db.Model):
    __tablename__ = 'reviews'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Keys for Product and User
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)  # The product the review is for
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
   
    # Review content
    rating = db.Column(db.Integer, nullable=False)  # Rating out of 5
    review_text = db.Column(db.Text, nullable=True)  # Optional text for the review
    
    # Review metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Time the review was created
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)  # Time the review was last updated
    
    # Relationship with Product
    product = db.relationship('Product', backref='reviews', lazy=True)
    # Relationship with User
    user = db.relationship('User', backref='reviews', lazy=True)
    
    def __init__(self, product_id, user_id, rating, review_text=None):
        self.product_id = product_id
        self.user_id = user_id
        self.rating = rating
        self.review_text = review_text

    def __repr__(self):
        return f"<Review {self.id} - Product {self.product_id} by User {self.user_id}>"


class PromoCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    discount_percentage = db.Column(db.Float, nullable=False)
    expiration_date = db.Column(db.DateTime, nullable=False)

    def is_valid(self):
        return datetime.utcnow() <= self.expiration_date

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "discount_percentage": self.discount_percentage,
            "expiration_date": self.expiration_date.strftime("%Y-%m-%d %H:%M:%S"),
        }