import os
import logging
from flask import Blueprint, jsonify, request,current_app as app
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from sqlalchemy.exc import SQLAlchemyError
import datetime
from app.models import User, Product, Order,Review,Wishlist,PromoCode
from app.extensions import db

# Set up logging for the module
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Blueprint for main routes
main = Blueprint('main', __name__)

# Define the upload folder
UPLOAD_FOLDER = 'static/uploads'
# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@main.route('/api/products', methods=['GET'])
@jwt_required(optional=True)  # Allows both authenticated and unauthenticated requests
def get_products():
    try:
        # Get current user ID if authenticated
        user_id = get_jwt_identity()

        # Fetch all products from the database
        products = Product.query.all()

        # Prepare product data with full image paths
        base_url = request.host_url.rstrip('/')
        products_list = [
            {
                "id": product.id,
                "name": product.name,
                "description": product.description,
                "category": product.category,
                "price": product.price,
                "image": f"{base_url}{product.image}" if product.image else None,
                "badge_text": product.badge_text,
                "badge_type": product.badge_type,
                "is_new": product.is_new,
                "is_wishlisted": (
                    Wishlist.query.filter_by(user_id=user_id, product_id=product.id).first() is not None
                    if user_id
                    else False
                ),  # Wishlist status
            }
            for product in products
        ]

        # Return products list with 200 status code
        return jsonify(products_list), 200

    except Exception as e:
        # Log error and return 500 status code
        return jsonify({"error": str(e)}), 500

@main.route('/api/signup', methods=['POST'])
def signup():
    # Extract user details from request payload
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    # Check if email already exists in the database
    if User.query.filter_by(email=email).first():
        return jsonify({'message': 'Email already exists'}), 400

    # Hash the password and create a new user record
    hashed_password = generate_password_hash(password)
    new_user = User(username=username, email=email, password_hash=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    # Return success message with 201 status code
    return jsonify({'message': 'User created successfully'}), 201

@main.route('/api/signin', methods=['POST'])
def signin():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email, is_admin=False).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'message': 'Invalid credentials'}), 401

    expires = datetime.timedelta(days=365)
    # Generate JWT token
    token = create_access_token(identity=user.id, expires_delta=False)
    return jsonify({'message': 'Login successful', 'token': token}), 200
    
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

@main.route('/api/products/<int:id>', methods=['GET'])
@jwt_required(optional=True)  # Allows accessing without authentication
def get_product(id):
    """
    Fetch a specific product by its ID, including related products, reviews, and wishlist status.
    """
    try:
        # Query the requested product from the database
        product = Product.query.get(id)
        if not product:
            return jsonify({"error": "Product not found"}), 404

        # Get current user ID if authenticated
        user_id = get_jwt_identity()

        # Check if the product is in the user's wishlist
        is_wishlisted = False
        if user_id:
            is_wishlisted = (
                Wishlist.query.filter_by(user_id=user_id, product_id=id).first() is not None
            )

        # Prepare product data for the response
        base_url = request.host_url.rstrip('/')
        product_data = {
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "price": product.price,
            "image": f"{base_url}{product.image}" if product.image else None,
            "category": product.category,
            "badge_text": product.badge_text,
            "badge_type": product.badge_type,
            "is_new": product.is_new,
            "is_wishlisted": is_wishlisted,  # Add wishlist status here
        }

        # Query related products (excluding the current product)
        related_products_query = (
            Product.query.filter(Product.category == product.category, Product.id != id)
            .limit(5)  # Limit related products to 5
            .all()
        )

        related_products = [
            {
                "id": related.id,
                "name": related.name,
                "description": related.description,
                "price": related.price,
                "image": f"{base_url}{related.image}" if related.image else None,
                "badge_text": related.badge_text,
                "badge_type": related.badge_type,
            }
            for related in related_products_query
        ]

        # Prepare reviews data for the product
        reviews_query = Review.query.filter(Review.product_id == id).all()
        reviews = [
            {
                "id": review.id,
                "reviewText": review.review_text,
                "rating": review.rating,
                "user": review.user.username,
            }
            for review in reviews_query
        ]

        # Add related products and reviews to the response
        product_data["related_products"] = related_products
        product_data["reviews"] = reviews

        return jsonify(product_data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main.route('/api/wishlist', methods=['GET'])
@jwt_required()
def get_wishlist():
    
    try:
        # Get the current user ID from the token
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({"error": "User not found"}), 404

        # Fetch all wishlist items for the user
        wishlist_items = (
            Wishlist.query.filter_by(user_id=user.id)
            .join(Product, Product.id == Wishlist.product_id)
            .all()
        )

        # Prepare the wishlist products for the response
        base_url = request.host_url.rstrip('/')
        wishlist_products = [
            {
                "id": item.product.id,
                "name": item.product.name,
                "description": item.product.description,
                "price": item.product.price,
                "image": f"{base_url}{item.product.image}" if item.product.image else None,
                "category": item.product.category,
                "badge_text": item.product.badge_text,
                "badge_type": item.product.badge_type,
                "is_new": item.product.is_new,
            }
            for item in wishlist_items
        ]

        return jsonify(wishlist_products), 200

    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500


@main.route('/api/wishlist/toggle', methods=['POST'])
@jwt_required()
def toggle_wishlist():
    try:
        user_id = get_jwt_identity()
        product_id = request.json.get('product_id')

        if not product_id:
            return jsonify({"error": "Product ID is required"}), 400

        # Check if the product is already in the wishlist
        existing_item = Wishlist.query.filter_by(user_id=user_id, product_id=product_id).first()

        if existing_item:
            # Remove the product from the wishlist
            db.session.delete(existing_item)
            db.session.commit()
            return jsonify({"message": "Product removed from wishlist"}), 200
        else:
            # Add the product to the wishlist
            new_wishlist_item = Wishlist(user_id=user_id, product_id=product_id)
            db.session.add(new_wishlist_item)
            db.session.commit()
            return jsonify({"message": "Product added to wishlist"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main.route('/api/reviews', methods=['POST'])
@jwt_required()  # Ensure the user is logged in to submit a review
def submit_review():
    try:
        user_id = get_jwt_identity()  # Get user ID from JWT token
        user = User.query.get(user_id)
        if not user:
            return jsonify({"message": "User not found"}), 404

        data = request.get_json()  # Get review data from the request

        review_text = data.get('reviewText')
        rating = data.get('rating')
        product_id = data.get('productId')

        # Validate the input fields
        if not review_text or not rating or not product_id:
            return jsonify({"message": "Missing required fields"}), 400

        # Fetch the product and validate it exists
        product = Product.query.get(product_id)
        if not product:
            return jsonify({"message": "Product not found"}), 404

        # Create a new review and save to the database
        new_review = Review(
            review_text=review_text,
            rating=rating,
            product_id=product_id,
            user_id=user_id,
        )
        db.session.add(new_review)
        db.session.commit()

        return jsonify({"success": True, "review": {
            "id": new_review.id,
            "reviewText": new_review.review_text,
            "rating": new_review.rating,
            "user": user.username,
        }}), 201

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

    
@main.route('/api/account', methods=['GET'])
@jwt_required()
def get_account():
    try:
        user_id = get_jwt_identity()
      
        user = User.query.get(user_id)
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        return jsonify({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'shipping_address': user.shipping_address,
        }), 200
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@main.route('/api/account', methods=['PUT'])
@jwt_required()
def update_account():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    data = request.json
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    try:
        user.username = data.get('username', user.username)
        user.email = data.get('email', user.email)
        user.shipping_address = data.get('shipping_address', user.shipping_address)
        db.session.commit()
        return jsonify({'message': 'Account updated successfully'}), 200
    except Exception as e:
        return jsonify({"message": "An error occurred while updating the account"}), 500


@main.route('/api/account', methods=['DELETE'])
@jwt_required()
def delete_account():
    """
    API endpoint to delete a user's account.
    """
    try:
        user_id = get_jwt_identity()
        # Retrieve the user from the database
        user = db.session.get(User, user_id)
        if user is None:
            return jsonify({"message": "User not found"}), 404
        # Delete the user from the database
        db.session.delete(user)
        db.session.commit()

        return jsonify({"message": "Account deleted successfully"}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"message": "An error occurred while deleting the account"}), 500

@main.route('/api/account/password', methods=['PUT'])
@jwt_required()
def change_password():
    user_id = get_jwt_identity()
    data = request.json
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'message': 'User not found'}), 404

    try:
        current_password = data.get('current_password')
        new_password = data.get('new_password')

        if not user.verify_password(current_password):
            return jsonify({'message': 'Current password is incorrect'}), 400

        user.password = new_password
        db.session.commit()
        return jsonify({'message': 'Password changed successfully'}), 200 
    except Exception as e:
        return jsonify({"message": "An error occurred while changing the password"}), 500

@main.route('/api/checkout', methods=['POST'])
@jwt_required()
def checkout():
    data = request.get_json()
    user_id = get_jwt_identity()
    
    user = User.query.get(user_id)

    if not user:
        return jsonify({"message": "User not authenticated!"}), 401

    if not data.get('shipping_address'):
        return jsonify({"message": "Please provide your shipping address"}), 400

    discount = data.get('discount',0)
    orders = []
    for item in data.get('items', []):
        product_id = item.get('id')
        amount = item.get('amount')
        
        product = Product.query.get(product_id)
        total_price = product.price * amount
        discounted_price = total_price * (float(discount)/100)
        order = Order(
            product_id=product_id,
            amount=amount,
            total_price=total_price-discounted_price,
            image=product.image,
            user_id=user_id,
            email=data.get('email'),
            phone_number=data.get('phone_number'),
            shipping_address=data.get('shipping_address'),
            status="Pending"
        )
        orders.append(order)

    db.session.add_all(orders)
    db.session.commit()

    return jsonify({"message": "Order placed successfully!"}), 201

@main.route("/api/cart/details", methods=["POST"])
def get_cart_details():
    cart_items = request.json.get("cartItems", [])

    updated_cart = []
    for item in cart_items:
        product = Product.query.get(item["productId"])  # Fetch latest price from DB
        if product:
            updated_cart.append({
                "id": product.id,
                "name": product.name,
                "image": product.image,
                "price": product.price,  # Always use DB price
                "amount": item["amount"]
            })

    return jsonify({"updatedCart": updated_cart}), 200

@main.route('/api/orders', methods=['GET'])
@jwt_required()
def get_order_history():
    user_id = get_jwt_identity()
    # Fetch orders for the user
    orders = Order.query.filter_by(user_id=user_id).all()
    if not orders:
        return jsonify({"message": "No orders found."}), 404

    # Format the orders
    orders_data = []
    for order in orders:
        orders_data.append({
            "order_id": order.order_id,
            "product_id": order.product_id,
            "product_name":order.product.name if order.product else "Product Deleted",
            "amount": order.amount,
            "total_price": order.total_price,
            "status": order.status,
            "email": order.email,
            "phone_number": order.phone_number,
            "shipping_address": order.shipping_address,
            "username": order.user.username if order.user else "Unknown User"
        })

    return jsonify({"orders": orders_data})

@main.route('/api/orders/cancel/<int:order_id>', methods=['POST'])
@jwt_required()
def cancel_order(order_id):
    user_id = get_jwt_identity()

    order = Order.query.filter_by(order_id=order_id,user_id=user_id).first()

    if not order:
        return jsonify({"message": "Order not found or unauthorized"}), 404

    if order.status == "Cancelled":
        return jsonify({"message": "Order is already cancelled"}), 400

    if order.status != "Pending":
        return jsonify({"message": "Only pending orders can be cancelled"}), 400

    order.status = "Cancelled"
    db.session.commit()

    return jsonify({"message": "Order cancelled successfully"}), 200


@main.route('/api/promo/apply', methods=['POST'])
@jwt_required()
def apply_promo():
    try:
        data = request.json
        promo_code = data.get("code")
        if not promo_code:
            return jsonify({"error": "Promo code is required"}), 400

        promo = PromoCode.query.filter_by(code=promo_code).first()

        if not promo or not promo.is_valid():
            return jsonify({"error": "Invalid or expired promo code"}), 400

        return jsonify({
            "success": True,
            "discount_percentage": promo.discount_percentage
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main.route('/debug-config')
def debug_config():
    """
    Temporary route to check if environment variables are loaded correctly.
    """
    return {
        "SECRET_KEY": app.config['SECRET_KEY'],
        "DATABASE_URL": app.config['SQLALCHEMY_DATABASE_URI']
    }
