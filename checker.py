"""
checker.py
----------
The core price checking logic.

This module is called by the scheduler to:
1. Update all product prices (via price_engine)
2. Check each watch against the new prices
3. Group triggered watches by email + product name
4. Send ONE combined email per product (listing all retailers)
5. Update last_notified_at timestamps

The 3-day cooldown prevents spamming users when a price stays below
their threshold across multiple check cycles.
"""

from datetime import datetime, timedelta
from collections import defaultdict
from database import db
from models import Product, Watch
from price_engine import update_all_prices
from notifier import send_multi_retailer_notification


# Cooldown period: don't notify same user about same product more than once per 3 days
NOTIFICATION_COOLDOWN_DAYS = 3


def is_cooldown_expired(watch):
    """
    Check if enough time has passed since the last notification.
    
    Args:
        watch: The Watch to check
        
    Returns:
        bool: True if we can send a notification (cooldown expired or never notified)
    """
    if watch.last_notified_at is None:
        return True  # Never notified, so no cooldown
    
    cooldown_end = watch.last_notified_at + timedelta(days=NOTIFICATION_COOLDOWN_DAYS)
    return datetime.utcnow() >= cooldown_end


def check_watch(watch):
    """
    Check a single watch and determine if it should trigger.
    Does NOT send notification - just returns the check result.
    
    Args:
        watch: The Watch to check
        
    Returns:
        dict: Result of the check
    """
    product = watch.product
    
    result = {
        'watch_id': watch.id,
        'email': watch.email,
        'product_name': product.name,
        'product_price': product.current_price,
        'product_base_price': product.base_price,
        'retailer': product.retailer,
        'discount_percent': product.discount_percent,
        'threshold_type': watch.threshold_type,
        'threshold_value': watch.threshold_value,
        'threshold_met': False,
        'cooldown_expired': False,
        'should_notify': False,
        'reason': ''
    }
    
    # Store watch reference separately (not in result dict, to keep it JSON-serializable)
    watch_ref = watch
    
    # Check if threshold is met
    if not watch.threshold_met(product):
        result['reason'] = 'Threshold not met'
        return result
    
    result['threshold_met'] = True
    
    # Check cooldown
    if not is_cooldown_expired(watch):
        result['reason'] = f'Cooldown active (notified on {watch.last_notified_at})'
        return result
    
    result['cooldown_expired'] = True
    result['should_notify'] = True
    result['reason'] = 'Ready to notify'
    result['_watch_ref'] = watch_ref  # Internal use only, removed before JSON response
    
    return result


def run_price_check():
    """
    Run a complete price check cycle.
    
    This is the main function called by the scheduler. It:
    1. Updates all product prices
    2. Checks all watches against new prices
    3. Groups triggered watches by email + product name
    4. Sends ONE combined email per email+product (listing all retailers)
    5. Returns a summary of what happened
    
    Returns:
        dict: Summary of the check cycle
    """
    print(f"\n{'='*50}")
    print(f"PRICE CHECK CYCLE - {datetime.utcnow().isoformat()}")
    print(f"{'='*50}\n")
    
    # Step 1: Update all prices
    print("Step 1: Updating prices...")
    price_summary = update_all_prices()
    print(f"  Updated {price_summary['total']} products")
    print(f"  - Sale events active: {price_summary['sale_events']}")
    print(f"  - Random fluctuations: {price_summary['random_fluctuations']}")
    
    # Step 2: Check all watches
    print("\nStep 2: Checking watches...")
    watches = Watch.query.all()
    
    results = []
    
    # Group watches that should notify by (email, product_name)
    # Key: (email, product_name) -> list of check results
    notifications_to_send = defaultdict(list)
    
    for watch in watches:
        result = check_watch(watch)
        results.append(result)
        
        if result['should_notify']:
            key = (result['email'], result['product_name'])
            notifications_to_send[key].append(result)
        
        # Log each check
        status = "✓ TRIGGERED" if result['should_notify'] else f"○ {result['reason']}"
        print(f"  [{watch.email}] {watch.product.name} ({watch.product.retailer}): {status}")
    
    # Step 3: Send grouped notifications
    print("\nStep 3: Sending notifications...")
    notifications_sent = 0
    
    for (email, product_name), triggered_results in notifications_to_send.items():
        # Build deals list for email
        deals = []
        for r in triggered_results:
            deals.append({
                'retailer': r['retailer'],
                'current_price': r['product_price'],
                'base_price': r['product_base_price'],
                'savings': r['product_base_price'] - r['product_price'],
                'discount_percent': r['discount_percent']
            })
        
        # Get threshold info (same for all watches of same product for same user)
        threshold_type = triggered_results[0]['threshold_type']
        threshold_value = triggered_results[0]['threshold_value']
        
        # Send combined email
        success = send_multi_retailer_notification(
            email, product_name, deals, threshold_type, threshold_value
        )
        
        if success:
            notifications_sent += 1
            # Update last_notified_at for all watches that were included
            for r in triggered_results:
                r['_watch_ref'].last_notified_at = datetime.utcnow()
            db.session.commit()
            
            retailers = ", ".join([d['retailer'] for d in deals])
            print(f"  ✓ Sent to {email} about {product_name} ({len(deals)} retailers: {retailers})")
        else:
            print(f"  ✗ Failed to send to {email} about {product_name}")
    
    # Clean up internal references before returning (for JSON serialization)
    for r in results:
        r.pop('_watch_ref', None)
    
    # Summary
    thresholds_met = sum(1 for r in results if r['threshold_met'])
    
    summary = {
        'timestamp': datetime.utcnow().isoformat(),
        'price_updates': price_summary,
        'watches_checked': len(watches),
        'thresholds_met': thresholds_met,
        'notifications_sent': notifications_sent,
        'details': results
    }
    
    print(f"\n{'='*50}")
    print(f"CYCLE COMPLETE")
    print(f"  Watches checked: {len(watches)}")
    print(f"  Thresholds met: {thresholds_met}")
    print(f"  Emails sent: {notifications_sent}")
    print(f"{'='*50}\n")
    
    return summary


def check_single_product(product_id):
    """
    Run checks for all watches on a specific product.
    Useful for testing after manually changing a price.
    
    Args:
        product_id: The ID of the product to check
        
    Returns:
        list: Results for each watch on this product
    """
    watches = Watch.query.filter_by(product_id=product_id).all()
    
    results = []
    for watch in watches:
        result = check_watch(watch)
        results.append(result)
    
    return results