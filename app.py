"""
app.py
------
The main Flask application.

Handles:
- Serving the web form for creating price alerts
- Processing form submissions (upsert into watches table)
- Admin routes for testing and manual operations

Run with: python app.py
Or for production: gunicorn app:app
"""

import os
from flask import Flask, render_template, request, redirect, url_for, jsonify
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Create Flask app
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///price_tracker.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
from database import init_db, db
init_db(app)

# Import models after db is initialized
from models import Product, Watch, SaleEvent


# ============================================
# PUBLIC ROUTES
# ============================================

@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Main page - display form and handle submissions.
    """
    message = None
    message_type = None
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        product_name = request.form.get('product_name', '').strip()
        threshold_type = request.form.get('threshold_type')
        threshold_value = request.form.get('threshold_value')
        
        # Validate inputs
        if not all([email, product_name, threshold_type, threshold_value]):
            message = "Please fill in all fields."
            message_type = "error"
        else:
            try:
                threshold_value = float(threshold_value)
                
                # Find all products with this name (across all retailers)
                products_to_watch = Product.query.filter_by(name=product_name).all()
                
                if not products_to_watch:
                    message = "Invalid product selected."
                    message_type = "error"
                else:
                    # Create/update a watch for each retailer
                    retailers_added = []
                    for product in products_to_watch:
                        watch = Watch.query.filter_by(
                            email=email,
                            product_id=product.id
                        ).first()
                        
                        if watch:
                            # Update existing watch
                            watch.threshold_type = threshold_type
                            watch.threshold_value = threshold_value
                        else:
                            # Create new watch
                            watch = Watch(
                                email=email,
                                product_id=product.id,
                                threshold_type=threshold_type,
                                threshold_value=threshold_value
                            )
                            db.session.add(watch)
                        
                        retailers_added.append(product.retailer)
                    
                    db.session.commit()
                    retailer_list = ", ".join(retailers_added)
                    message = f"Alert created for {product_name}! Tracking at: {retailer_list}"
                    message_type = "success"
                    
            except ValueError:
                message = "Invalid threshold value."
                message_type = "error"
    
    # Get unique products (grouped by name) for the dropdown
    all_products = Product.query.order_by(Product.category, Product.name).all()
    
    # Group by product name to show unique entries
    unique_products = {}
    for p in all_products:
        if p.name not in unique_products:
            unique_products[p.name] = {
                'name': p.name,
                'base_price': p.base_price,
                'retailers': [p.retailer]
            }
        else:
            unique_products[p.name]['retailers'].append(p.retailer)
    
    # Convert to list and format retailers as string
    products_for_template = []
    for name, data in unique_products.items():
        products_for_template.append({
            'name': data['name'],
            'base_price': data['base_price'],
            'retailers': ", ".join(data['retailers'])
        })
    
    return render_template('index.html', 
                         products=products_for_template, 
                         message=message, 
                         message_type=message_type)


# ============================================
# ADMIN / TESTING ROUTES
# ============================================

@app.route('/admin/products')
def list_products():
    """List all products with current prices."""
    products = Product.query.all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'category': p.category,
        'retailer': p.retailer,
        'base_price': p.base_price,
        'current_price': p.current_price,
        'discount_percent': p.discount_percent,
        'last_updated': p.last_updated.isoformat()
    } for p in products])


@app.route('/admin/watches')
def list_watches():
    """List all active watches."""
    watches = Watch.query.all()
    return jsonify([{
        'id': w.id,
        'email': w.email,
        'product_id': w.product_id,
        'product_name': w.product.name,
        'threshold_type': w.threshold_type,
        'threshold_value': w.threshold_value,
        'last_notified_at': w.last_notified_at.isoformat() if w.last_notified_at else None
    } for w in watches])


@app.route('/admin/sales')
def list_sales():
    """List all sale events."""
    sales = SaleEvent.query.all()
    return jsonify([{
        'id': s.id,
        'product_id': s.product_id,
        'product_name': s.product.name,
        'sale_price': s.sale_price,
        'start_date': s.start_date.isoformat(),
        'end_date': s.end_date.isoformat(),
        'is_active': s.is_active
    } for s in sales])


@app.route('/admin/run-check', methods=['POST'])
def trigger_check():
    """Manually trigger a price check cycle."""
    from checker import run_price_check
    result = run_price_check()
    return jsonify(result)


@app.route('/admin/update-prices', methods=['POST'])
def update_prices():
    """Manually update all prices without checking thresholds."""
    from price_engine import update_all_prices
    result = update_all_prices()
    return jsonify(result)


@app.route('/admin/set-price/<int:product_id>/<float:price>', methods=['POST'])
def set_price(product_id, price):
    """Manually set a product's price (for testing)."""
    from price_engine import simulate_price_drop
    product = simulate_price_drop(product_id, price)
    if product:
        return jsonify({
            'success': True,
            'product': product.name,
            'new_price': product.current_price
        })
    return jsonify({'success': False, 'error': 'Product not found'}), 404


@app.route('/admin/seed', methods=['POST'])
def seed_database():
    """Seed the database with mock data."""
    from seed_data import seed_all
    test_email = request.args.get('email')
    result = seed_all(test_email)
    return jsonify(result)


@app.route('/admin/test-email', methods=['POST'])
def test_email():
    """Send a test email to verify SendGrid configuration."""
    from notifier import send_test_email
    email = request.args.get('email')
    if not email:
        return jsonify({'error': 'Email parameter required'}), 400
    
    success = send_test_email(email)
    return jsonify({'success': success})


# ============================================
# CLI COMMANDS
# ============================================

@app.cli.command('seed')
def seed_command():
    """Seed the database with mock products."""
    from seed_data import seed_all
    seed_all()


@app.cli.command('check')
def check_command():
    """Run a price check cycle."""
    from checker import run_price_check
    run_price_check()


# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    # Check if we should start the scheduler
    enable_scheduler = os.environ.get('ENABLE_SCHEDULER', 'false').lower() == 'true'
    check_interval = os.environ.get('CHECK_INTERVAL_MINUTES')
    
    if enable_scheduler:
        from scheduler import init_scheduler
        if check_interval:
            init_scheduler(app, int(check_interval))
        else:
            init_scheduler(app)
    
    # Run the Flask development server
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    
    print(f"\n🚀 Price Tracker starting on http://localhost:{port}")
    print(f"   Scheduler: {'enabled' if enable_scheduler else 'disabled'}")
    print(f"   Debug mode: {debug}\n")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
