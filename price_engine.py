"""
price_engine.py
---------------
Handles price simulation for the mock product catalog.

Two modes of price changes:
1. Random fluctuation: Prices drift randomly within a range (simulates real market)
2. Sale events: Scripted sales override random fluctuation (for predictable testing)

Sale events take priority - if a product has an active sale, that price is used
regardless of what random fluctuation would have done.
"""

import random
from datetime import datetime
from database import db
from models import Product, SaleEvent


# Configuration for random price fluctuation
FLUCTUATION_CONFIG = {
    'min_percent': -5,   # Prices can drop up to 5% randomly
    'max_percent': 3,    # Prices can rise up to 3% randomly
    'sale_chance': 0.1,  # 10% chance of a random "flash sale" (bigger discount)
    'flash_sale_min': -15,  # Flash sales: 10-25% off
    'flash_sale_max': -10,
}


def apply_random_fluctuation(product):
    """
    Apply random price fluctuation to a product.
    
    Most of the time, prices drift slightly up or down.
    Occasionally (10% chance), a "flash sale" creates a bigger discount.
    
    Prices never go above the base_price (no inflation beyond MSRP).
    
    Args:
        product: The Product instance to update
        
    Returns:
        float: The new current_price
    """
    # Determine if this is a flash sale
    if random.random() < FLUCTUATION_CONFIG['sale_chance']:
        # Flash sale: bigger discount
        percent_change = random.uniform(
            FLUCTUATION_CONFIG['flash_sale_min'],
            FLUCTUATION_CONFIG['flash_sale_max']
        )
    else:
        # Normal fluctuation
        percent_change = random.uniform(
            FLUCTUATION_CONFIG['min_percent'],
            FLUCTUATION_CONFIG['max_percent']
        )
    
    # Calculate new price
    new_price = product.current_price * (1 + percent_change / 100)
    
    # Enforce bounds: never above base_price, never below 50% of base
    new_price = min(new_price, product.base_price)
    new_price = max(new_price, product.base_price * 0.5)
    
    # Round to 2 decimal places
    return round(new_price, 2)


def get_active_sale(product_id):
    """
    Check if a product has an active sale event.
    
    Args:
        product_id: The ID of the product to check
        
    Returns:
        SaleEvent or None: The active sale if one exists
    """
    now = datetime.utcnow()
    
    return SaleEvent.query.filter(
        SaleEvent.product_id == product_id,
        SaleEvent.start_date <= now,
        SaleEvent.end_date >= now
    ).first()


def update_product_price(product):
    """
    Update a single product's price.
    
    Checks for active sale events first. If one exists, use the sale price.
    Otherwise, apply random fluctuation.
    
    Args:
        product: The Product instance to update
        
    Returns:
        tuple: (new_price, is_sale_event) - the new price and whether it came from a sale
    """
    # Check for active sale event
    active_sale = get_active_sale(product.id)
    
    if active_sale:
        # Sale event takes priority
        new_price = active_sale.sale_price
        is_sale_event = True
    else:
        # Apply random fluctuation
        new_price = apply_random_fluctuation(product)
        is_sale_event = False
    
    # Update the product
    product.current_price = new_price
    product.last_updated = datetime.utcnow()
    
    return new_price, is_sale_event


def update_all_prices():
    """
    Update prices for all products in the catalog.
    
    This is called by the scheduler during each price check cycle.
    
    Returns:
        dict: Summary of updates {
            'total': int,
            'sale_events': int,
            'random_fluctuations': int,
            'details': list of update info
        }
    """
    products = Product.query.all()
    
    summary = {
        'total': len(products),
        'sale_events': 0,
        'random_fluctuations': 0,
        'details': []
    }
    
    for product in products:
        old_price = product.current_price
        new_price, is_sale = update_product_price(product)
        
        if is_sale:
            summary['sale_events'] += 1
        else:
            summary['random_fluctuations'] += 1
        
        summary['details'].append({
            'product_id': product.id,
            'name': product.name,
            'old_price': old_price,
            'new_price': new_price,
            'is_sale_event': is_sale,
            'discount_percent': product.discount_percent
        })
    
    # Commit all changes
    db.session.commit()
    
    return summary


def simulate_price_drop(product_id, target_price):
    """
    Manually force a product to a specific price (for testing).
    
    This is useful for triggering notifications during development
    without waiting for random fluctuation or setting up sale events.
    
    Args:
        product_id: The ID of the product
        target_price: The price to set
        
    Returns:
        Product: The updated product, or None if not found
    """
    product = Product.query.get(product_id)
    
    if product:
        product.current_price = target_price
        product.last_updated = datetime.utcnow()
        db.session.commit()
    
    return product
