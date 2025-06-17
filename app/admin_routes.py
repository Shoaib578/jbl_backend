import os 
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash,jsonify, current_app as app
from werkzeug.security import generate_password_hash
from sqlalchemy.exc import SQLAlchemyError
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename

from app.models import User, Product, Order, Review
from .extensions import db

# Define blueprint for admin-related routes
admin_routes = Blueprint('admin_routes', __name__)

@admin_routes.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        # Redirect already authenticated users to the dashboard
        return redirect(url_for('admin_routes.dashboard'))

    if request.method == 'POST':
        # Extract user credentials from login form
        username = request.form.get('username')
        password = request.form.get('password')

        # Query for admin user by username
        user = User.query.filter_by(username=username, is_admin=True).first()

        if user and user.verify_password(password):
            # Log in user and redirect to admin dashboard
            login_user(user)
            flash("Logged in successfully!", "success")
            return redirect(url_for('admin_routes.dashboard'))
        else:
            # Invalid credentials
            flash("Invalid username or password.", "danger")
    # Render admin login template
    return render_template('admin/login.html')

@admin_routes.route('/admin/dashboard')
@login_required
def dashboard():
    if not current_user.is_admin:
        # Restrict access for non-admin users
        flash('Access unauthorized!', 'danger')
        return redirect(url_for('admin_routes.admin_login'))
    
    # Fetch all orders for the dashboard
    orders = Order.query.order_by(Order.order_id.desc()).all()
    return render_template('admin/index.html',orders=orders)

@admin_routes.route('/admin/users')
@login_required
def users():
    if not current_user.is_admin:
        flash('Access unauthorized!', 'danger')
        return redirect(url_for('admin_routes.admin_login'))

    users = User.query.all()  # Fetch all users
    return render_template('admin/users.html', users=users)


@admin_routes.route('/admin/reviews')
@login_required
def reviews():
    if not current_user.is_admin:
        flash('Access unauthorized!', 'danger')
        return redirect(url_for('admin_routes.admin_login'))

    reviews = Review.query.order_by(Review.created_at.desc()).all()  # Fetch reviews in descending order
    return render_template('admin/reviews.html', reviews=reviews)



@admin_routes.route('/admin/reviews/delete/<int:review_id>', methods=['POST'])
@login_required
def delete_review(review_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    review = Review.query.get(review_id)
    if not review:
        return jsonify({'error': 'Review not found'}), 404

    db.session.delete(review)
    db.session.commit()
    return jsonify({'message': 'Review deleted successfully'})


@admin_routes.route('/admin/update_order_status', methods=['POST'])
@login_required
def update_order_status():
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    data = request.get_json()
    order_id = data.get('order_id')
    new_status = data.get('status')

    order = Order.query.get(order_id)
    if not order:
        return jsonify({'success': False, 'message': 'Order not found'}), 404

    order.status = new_status
    db.session.commit()

    return jsonify({'success': True, 'message': 'Order status updated successfully'})


@admin_routes.route('/admin/users/update/<int:user_id>', methods=['POST'])
@login_required
def update_user(user_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.json
    user.username = data.get('username', user.username)
    user.email = data.get('email', user.email)
    user.is_admin = data.get('is_admin', user.is_admin)

    # Check if a new password is provided
    new_password = data.get('password')
    if new_password:
        user.password_hash = generate_password_hash(new_password)

    db.session.commit()
    return jsonify({'message': 'User updated successfully'})

@admin_routes.route('/admin/products')
@login_required
def products():
    if not current_user.is_admin:
        flash('Access unauthorized!', 'danger')
        return redirect(url_for('admin_routes.admin_login'))
    
    # Fetch all products from the database
    products_data = Product.query.all()
    return render_template('admin/products.html', products=products_data)

@admin_routes.route('/admin/create_product', methods=['POST'])
@login_required
def create_product():
    if not current_user.is_admin:
        flash('Access unauthorized!', 'danger')
        return redirect(url_for('admin_routes.admin_login'))

    # Extract product data from the form
    name = request.form.get('name')
    description = request.form.get('description')
    category = request.form.get('category')
    price = request.form.get('price')
    badge_text = request.form.get('badge_text')
    badge_type = request.form.get('badge_type')
    is_new = 'is_new' in request.form

    # Handle image file upload
    image = request.files.get('image')
    image_url = None
    if image and image.filename:
        # Generate a random filename with the original file extension
        _, file_extension = os.path.splitext(secure_filename(image.filename))
        random_filename = f"{uuid.uuid4().hex}{file_extension}"
        
        # Save the file in the app's static/uploads directory
        upload_folder = os.path.join(app.root_path, 'static', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        image_path = os.path.join(upload_folder, random_filename)

        # Save the file
        image.save(image_path)
        image_url = f"/static/uploads/{random_filename}"

    # Create and save the product
    new_product = Product(
        name=name,
        description=description,
        category=category,
        price=float(price),
        badge_text=badge_text,
        badge_type=badge_type,
        is_new=is_new,
        image=image_url,
    )
    db.session.add(new_product)
    db.session.commit()

    flash("Product created successfully!", "success")
    return redirect(url_for('admin_routes.products'))

@admin_routes.route('/admin/edit_product/<int:product_id>', methods=['GET'])
@login_required
def edit_product(product_id):
    if not current_user.is_admin:
        # Restrict access for non-admin users
        flash('Access unauthorized!', 'danger')
        return redirect(url_for('admin_routes.admin_login'))
    
    # Fetch product from the database
    product = db.session.get(Product, product_id)
    
    # Render product edit form with fetched product details
    return render_template('admin/edit_product.html', product=product)

@admin_routes.route('/admin/edit_product/<int:product_id>', methods=['POST'])
@login_required
def update_product(product_id):
    
    if not current_user.is_admin:
        flash('Access unauthorized!', 'danger')
        return redirect(url_for('admin_routes.admin_login'))

    # Fetch product from the database
    product = db.session.get(Product, product_id)
    
    # Get updated details from the form
    name = request.form.get('name')
    description = request.form.get('description')
    category = request.form.get('category')
    price = request.form.get('price')
    badge_text = request.form.get('badge_text')
    badge_type = request.form.get('badge_type')
    is_new = 'is_new' in request.form

    # Handle image file upload
    image = request.files.get('image')
    if image and image.filename:
        # Delete the old image if it exists
        if product.image:
            old_image_path = os.path.join(app.root_path, product.image.lstrip('/'))
            if os.path.exists(old_image_path):
                os.remove(old_image_path)


        # Save the new image
        _, file_extension = os.path.splitext(secure_filename(image.filename))
        random_filename = f"{uuid.uuid4().hex}{file_extension}"
        upload_folder = os.path.join(app.root_path, 'static', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        image_path = os.path.join(upload_folder, random_filename)
        image.save(image_path)
        product.image = f"/static/uploads/{random_filename}"

    # Update other product fields
    product.name = name
    product.description = description
    product.category = category
    product.price = float(price)
    product.badge_text = badge_text
    product.badge_type = badge_type
    product.is_new = is_new

    try:
        # Commit changes to databse
        db.session.commit()
        flash("Product updated successfully!", "success")
    except Exception as e:
        # Rollback in case of any database errors
        db.session.rollback()
        flash(f"An error occurred: {str(e)}", "danger")

    # Redirect back to the product management page
    return redirect(url_for('admin_routes.products'))

@admin_routes.route('/admin/delete_product/<int:product_id>', methods=['POST', 'GET'])
@login_required
def delete_product(product_id):
    if not current_user.is_admin:
        flash('Access unauthorized!', 'danger')
        return redirect(url_for('admin_routes.admin_login'))

    # Query the product from the database by its ID
    product = db.session.get(Product, product_id)

    if product:
        try:
            if product.image:
                full_image_path = os.path.join(app.root_path, product.image.lstrip('/'))
                if os.path.exists(full_image_path):
                    os.remove(full_image_path)
            # Delete the product
            db.session.delete(product)
            db.session.commit()
            flash(f"Product '{product.name}' has been successfully deleted.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred: {e}", "danger")
    else:
        flash("Product not found.", "warning")

    # Redirect to the products page
    return redirect(url_for('admin_routes.products'))


@admin_routes.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('admin_routes.admin_login'))