"""
models.py
---------
Defines the database tables (models) for the price tracker.

Tables:
- Product: The mock product catalog (electronics items)
- Watch: User price alerts (email + product + threshold)
- SaleEvent: Scripted sales for predictable testing
"""

from datetime import datetime
from database import db


class Product(db.Model):
    """
    Represents a product in our mock catalog.
    
    base_price: The "normal" MSRP that doesn't change
    current_price: The price right now (fluctuates via simulation or sales)
    """
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # e.g., "headphones", "gaming", "tv"
    retailer = db.Column(db.String(50), nullable=False)  # e.g., "Walmart", "Target"
    base_price = db.Column(db.Float, nullable=False)     # Original MSRP
    current_price = db.Column(db.Float, nullable=False)  # Current selling price
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to watches (for easy querying)
    watches = db.relationship('Watch', backref='product', lazy=True)
    
    def __repr__(self):
        return f'<Product {self.name} @ {self.retailer}: ${self.current_price}>'
    
    @property
    def discount_percent(self):
        """Calculate current discount percentage from base price."""
        if self.base_price <= 0:
            return 0
        return round((1 - self.current_price / self.base_price) * 100, 1)


class Watch(db.Model):
    """
    Represents a user's price alert.
    
    threshold_type: Either 'percent' or 'absolute'
    - 'percent': Notify when discount reaches X% off base price
    - 'absolute': Notify when price drops to $X or below
    
    last_notified_at: Tracks when we last emailed this user about this product.
    Used to enforce the 3-day cooldown between notifications.
    """
    __tablename__ = 'watches'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    threshold_type = db.Column(db.String(10), nullable=False)  # 'percent' or 'absolute'
    threshold_value = db.Column(db.Float, nullable=False)      # e.g., 20 (%) or 299.99 ($)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_notified_at = db.Column(db.DateTime, nullable=True)   # None if never notified
    
    # Unique constraint: one watch per email/product combination
    # If same user submits same product again, we update instead of creating duplicate
    __table_args__ = (
        db.UniqueConstraint('email', 'product_id', name='unique_email_product'),
    )
    
    def __repr__(self):
        return f'<Watch {self.email} watching product {self.product_id}>'
    
    def threshold_met(self, product):
        """
        Check if the product's current price meets this watch's threshold.
        
        Args:
            product: The Product instance to check against
            
        Returns:
            bool: True if the threshold is met (user should be notified)
        """
        if self.threshold_type == 'percent':
            # Check if discount percentage meets or exceeds target
            return product.discount_percent >= self.threshold_value
        else:  # absolute
            # Check if current price is at or below target
            return product.current_price <= self.threshold_value


class SaleEvent(db.Model):
    """
    Represents a scripted sale for testing purposes.
    
    When a sale event is active (between start_date and end_date),
    it overrides random price fluctuation for that product.
    This lets you create predictable scenarios to test notifications.
    """
    __tablename__ = 'sale_events'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    sale_price = db.Column(db.Float, nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    
    # Relationship to product
    product = db.relationship('Product', backref='sale_events')
    
    def __repr__(self):
        return f'<SaleEvent product {self.product_id}: ${self.sale_price}>'
    
    @property
    def is_active(self):
        """Check if this sale is currently running."""
        now = datetime.utcnow()
        return self.start_date <= now <= self.end_date
