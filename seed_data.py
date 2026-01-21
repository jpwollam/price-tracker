"""
seed_data.py
------------
Populates the database with mock products and test sale events.

Run this once after initializing the database to have products to work with.
Includes 25 electronics products across multiple categories and retailers,
plus a few sale events for testing notifications.
"""

from datetime import datetime, timedelta
from database import db
from models import Product, SaleEvent


# Mock product catalog - 25 electronics items
MOCK_PRODUCTS = [
    # Headphones
    {"name": "Sony WH-1000XM5", "category": "headphones", "retailer": "Walmart", "base_price": 399.99},
    {"name": "Sony WH-1000XM5", "category": "headphones", "retailer": "Target", "base_price": 399.99},
    {"name": "Apple AirPods Pro 2", "category": "headphones", "retailer": "Walmart", "base_price": 249.99},
    {"name": "Apple AirPods Pro 2", "category": "headphones", "retailer": "Target", "base_price": 249.99},
    {"name": "Bose QuietComfort Ultra", "category": "headphones", "retailer": "Walmart", "base_price": 429.99},
    
    # Gaming
    {"name": "PlayStation 5 Console", "category": "gaming", "retailer": "Walmart", "base_price": 499.99},
    {"name": "PlayStation 5 Console", "category": "gaming", "retailer": "Target", "base_price": 499.99},
    {"name": "Xbox Series X", "category": "gaming", "retailer": "Walmart", "base_price": 499.99},
    {"name": "Nintendo Switch OLED", "category": "gaming", "retailer": "Target", "base_price": 349.99},
    {"name": "Steam Deck 512GB", "category": "gaming", "retailer": "Newegg", "base_price": 549.99},
    
    # TVs
    {"name": "LG C3 55\" OLED TV", "category": "tv", "retailer": "Walmart", "base_price": 1299.99},
    {"name": "Samsung 65\" QLED 4K", "category": "tv", "retailer": "Target", "base_price": 999.99},
    {"name": "TCL 55\" 4K Roku TV", "category": "tv", "retailer": "Walmart", "base_price": 299.99},
    {"name": "Sony 55\" Bravia XR", "category": "tv", "retailer": "eBay", "base_price": 1199.99},
    
    # Laptops & Tablets
    {"name": "MacBook Air M3", "category": "laptop", "retailer": "Walmart", "base_price": 1099.99},
    {"name": "MacBook Air M3", "category": "laptop", "retailer": "Target", "base_price": 1099.99},
    {"name": "iPad Pro 11\"", "category": "tablet", "retailer": "Walmart", "base_price": 799.99},
    {"name": "Samsung Galaxy Tab S9", "category": "tablet", "retailer": "Target", "base_price": 849.99},
    {"name": "Dell XPS 13", "category": "laptop", "retailer": "Newegg", "base_price": 1299.99},
    
    # Smart Home
    {"name": "Amazon Echo Show 10", "category": "smart_home", "retailer": "Walmart", "base_price": 249.99},
    {"name": "Google Nest Hub Max", "category": "smart_home", "retailer": "Target", "base_price": 229.99},
    {"name": "Ring Video Doorbell Pro 2", "category": "smart_home", "retailer": "Walmart", "base_price": 249.99},
    {"name": "Philips Hue Starter Kit", "category": "smart_home", "retailer": "Target", "base_price": 199.99},
    {"name": "Sonos One Speaker", "category": "smart_home", "retailer": "eBay", "base_price": 219.99},
    {"name": "Apple HomePod Mini", "category": "smart_home", "retailer": "Walmart", "base_price": 99.99},
]


def seed_products():
    """
    Add all mock products to the database.
    Sets current_price equal to base_price initially.
    
    Returns:
        int: Number of products added
    """
    count = 0
    
    for product_data in MOCK_PRODUCTS:
        # Check if product already exists (by name + retailer)
        existing = Product.query.filter_by(
            name=product_data['name'],
            retailer=product_data['retailer']
        ).first()
        
        if existing:
            print(f"  Skipping (exists): {product_data['name']} @ {product_data['retailer']}")
            continue
        
        product = Product(
            name=product_data['name'],
            category=product_data['category'],
            retailer=product_data['retailer'],
            base_price=product_data['base_price'],
            current_price=product_data['base_price'],  # Start at base price
            last_updated=datetime.utcnow()
        )
        
        db.session.add(product)
        count += 1
        print(f"  Added: {product_data['name']} @ {product_data['retailer']}")
    
    db.session.commit()
    return count


def seed_sale_events():
    """
    Create some test sale events for predictable testing.
    
    Creates:
    - A sale starting today (immediate test)
    - A sale starting in 2 days (future test)
    - A sale that already ended (should have no effect)
    
    Returns:
        int: Number of sale events created
    """
    now = datetime.utcnow()
    
    # Find some products to put on sale
    sony_headphones = Product.query.filter_by(name="Sony WH-1000XM5", retailer="Walmart").first()
    ps5 = Product.query.filter_by(name="PlayStation 5 Console", retailer="Walmart").first()
    airpods = Product.query.filter_by(name="Apple AirPods Pro 2", retailer="Target").first()
    
    sale_events = []
    
    if sony_headphones:
        # Active sale: Sony headphones 25% off for next 3 days
        sale_events.append(SaleEvent(
            product_id=sony_headphones.id,
            sale_price=299.99,  # 25% off from $399.99
            start_date=now - timedelta(hours=1),  # Started 1 hour ago
            end_date=now + timedelta(days=3)
        ))
        print(f"  Sale: {sony_headphones.name} @ $299.99 (active now)")
    
    if ps5:
        # Future sale: PS5 $50 off starting in 2 days
        sale_events.append(SaleEvent(
            product_id=ps5.id,
            sale_price=449.99,
            start_date=now + timedelta(days=2),
            end_date=now + timedelta(days=5)
        ))
        print(f"  Sale: {ps5.name} @ $449.99 (starts in 2 days)")
    
    if airpods:
        # Past sale: AirPods were on sale last week (should not affect anything)
        sale_events.append(SaleEvent(
            product_id=airpods.id,
            sale_price=199.99,
            start_date=now - timedelta(days=10),
            end_date=now - timedelta(days=7)
        ))
        print(f"  Sale: {airpods.name} @ $199.99 (ended, for testing)")
    
    for event in sale_events:
        db.session.add(event)
    
    db.session.commit()
    return len(sale_events)


def seed_test_watch(email="test@example.com"):
    """
    Create a test watch for the active sale event.
    This lets you immediately test the notification flow.
    
    Args:
        email: Email address for the test watch
        
    Returns:
        Watch or None
    """
    from models import Watch
    
    # Find Sony headphones at Walmart (has active sale)
    product = Product.query.filter_by(name="Sony WH-1000XM5", retailer="Walmart").first()
    
    if not product:
        print("  No product found for test watch")
        return None
    
    # Check if watch already exists
    existing = Watch.query.filter_by(email=email, product_id=product.id).first()
    if existing:
        print(f"  Test watch already exists for {email}")
        return existing
    
    # Create watch with 20% threshold (sale is 25% off, so it should trigger)
    watch = Watch(
        email=email,
        product_id=product.id,
        threshold_type='percent',
        threshold_value=20,  # Notify at 20% off
        created_at=datetime.utcnow()
    )
    
    db.session.add(watch)
    db.session.commit()
    
    print(f"  Test watch created: {email} watching {product.name} for 20% off")
    return watch


def seed_all(test_email=None):
    """
    Run all seed functions.
    
    Args:
        test_email: If provided, also creates a test watch with this email
        
    Returns:
        dict: Summary of what was seeded
    """
    print("\n=== Seeding Database ===\n")
    
    print("Adding products...")
    products_added = seed_products()
    
    print("\nAdding sale events...")
    sales_added = seed_sale_events()
    
    test_watch = None
    if test_email:
        print(f"\nCreating test watch for {test_email}...")
        test_watch = seed_test_watch(test_email)
    
    print("\n=== Seeding Complete ===")
    print(f"  Products: {products_added} added")
    print(f"  Sale events: {sales_added} added")
    if test_watch:
        print(f"  Test watch: created for {test_email}")
    
    return {
        'products_added': products_added,
        'sale_events_added': sales_added,
        'test_watch': test_watch is not None
    }


def clear_all_data():
    """
    Remove all data from the database.
    Use with caution - this is destructive!
    """
    from models import Watch, SaleEvent, Product
    
    Watch.query.delete()
    SaleEvent.query.delete()
    Product.query.delete()
    db.session.commit()
    
    print("All data cleared from database.")
