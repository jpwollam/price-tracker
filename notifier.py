"""
notifier.py
-----------
Handles sending email notifications via SendGrid.

Email content includes:
- Product name and retailer
- Current price and discount percentage
- Timestamp of price check
- "Prices may change quickly" urgency language
- Direct link to retailer (placeholder for now, will be affiliate link later)
"""

import os
from datetime import datetime
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content


# Get SendGrid API key from environment
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
FROM_EMAIL = os.environ.get('FROM_EMAIL', 'alerts@pricetracker.com')


def format_price(price):
    """Format a price as $X.XX"""
    return f"${price:,.2f}"


def format_timestamp():
    """Get current timestamp in readable format."""
    return datetime.utcnow().strftime("%I:%M %p UTC on %B %d, %Y")


def build_multi_retailer_email(product_name, deals, threshold_type, threshold_value):
    """
    Build email content for multiple retailer deals on the same product.
    
    Args:
        product_name: The product name (e.g., "PlayStation 5 Console")
        deals: List of dicts with retailer info [{retailer, current_price, base_price, savings, discount_percent}, ...]
        threshold_type: 'percent' or 'absolute'
        threshold_value: The user's threshold value
        
    Returns:
        tuple: (subject, html_body, plain_body)
    """
    # Sort deals by price (best deal first)
    deals_sorted = sorted(deals, key=lambda x: x['current_price'])
    best_price = deals_sorted[0]['current_price']
    
    subject = f"🔔 Price Drop: {product_name} is now {format_price(best_price)}"
    
    # Build retailer rows for HTML
    retailer_rows = ""
    for deal in deals_sorted:
        retailer_rows += f"""
            <tr style="border-bottom: 1px solid #e2e8f0;">
                <td style="padding: 12px; font-weight: 500;">{deal['retailer']}</td>
                <td style="padding: 12px; color: #38a169; font-weight: bold;">{format_price(deal['current_price'])}</td>
                <td style="padding: 12px; color: #718096; text-decoration: line-through;">{format_price(deal['base_price'])}</td>
                <td style="padding: 12px; color: #38a169;">{deal['discount_percent']}% off</td>
                <td style="padding: 12px;">
                    <a href="#" style="color: #4299e1; text-decoration: none;">View Deal →</a>
                </td>
            </tr>
        """
    
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2d3748;">Price Alert: Your target has been reached!</h2>
        
        <div style="background-color: #f7fafc; border-radius: 8px; padding: 20px; margin: 20px 0;">
            <h3 style="margin-top: 0; color: #1a202c;">{product_name}</h3>
            <p style="color: #718096;">Found at {len(deals)} retailer{'s' if len(deals) > 1 else ''} below your target</p>
        </div>
        
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <thead>
                <tr style="background-color: #edf2f7;">
                    <th style="padding: 12px; text-align: left;">Retailer</th>
                    <th style="padding: 12px; text-align: left;">Price</th>
                    <th style="padding: 12px; text-align: left;">Was</th>
                    <th style="padding: 12px; text-align: left;">Savings</th>
                    <th style="padding: 12px; text-align: left;"></th>
                </tr>
            </thead>
            <tbody>
                {retailer_rows}
            </tbody>
        </table>
        
        <p style="color: #718096; font-size: 12px; margin-top: 30px;">
            Price checked at {format_timestamp()}.<br>
            <strong>Prices may change quickly</strong> — we recommend checking availability now.
        </p>
        
        <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;">
        
        <p style="color: #a0aec0; font-size: 11px;">
            You're receiving this because you set a price alert for {product_name}.
            Your target was: {threshold_type} threshold of {threshold_value}{'%' if threshold_type == 'percent' else ''}.
        </p>
    </body>
    </html>
    """
    
    # Plain text fallback
    plain_lines = [f"Price Alert: Your target has been reached!", "", f"{product_name}", ""]
    for deal in deals_sorted:
        plain_lines.append(f"  {deal['retailer']}: {format_price(deal['current_price'])} (was {format_price(deal['base_price'])}, {deal['discount_percent']}% off)")
    plain_lines.extend([
        "",
        f"Price checked at {format_timestamp()}.",
        "Prices may change quickly — we recommend checking availability now.",
        "",
        f"Your target: {threshold_type} threshold of {threshold_value}{'%' if threshold_type == 'percent' else ''}"
    ])
    plain_body = "\n".join(plain_lines)
    
    return subject, html_body, plain_body


def send_multi_retailer_notification(email, product_name, deals, threshold_type, threshold_value):
    """
    Send a combined price alert email for multiple retailers.
    
    Args:
        email: Recipient email address
        product_name: The product name
        deals: List of deal dicts
        threshold_type: 'percent' or 'absolute'
        threshold_value: The user's threshold
        
    Returns:
        bool: True if sent successfully
    """
    if not SENDGRID_API_KEY:
        retailers = ", ".join([d['retailer'] for d in deals])
        prices = ", ".join([format_price(d['current_price']) for d in deals])
        print(f"[MOCK EMAIL] Would send to {email} about {product_name} at {len(deals)} retailers: {retailers} ({prices})")
        return True
    
    subject, html_body, plain_body = build_multi_retailer_email(
        product_name, deals, threshold_type, threshold_value
    )
    
    try:
        message = Mail(
            from_email=Email(FROM_EMAIL, "Price Tracker Alerts"),
            to_emails=To(email),
            subject=subject,
            plain_text_content=Content("text/plain", plain_body),
            html_content=Content("text/html", html_body)
        )
        
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        
        print(f"[EMAIL SENT] To {email} about {product_name} at {len(deals)} retailers - Status: {response.status_code}")
        return response.status_code in [200, 201, 202]
        
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send to {email}: {str(e)}")
        return False


def build_email_content(product, watch):
    """
    Build the email subject and body for a price alert.
    
    Args:
        product: The Product that triggered the alert
        watch: The Watch (user's alert settings)
        
    Returns:
        tuple: (subject, html_body, plain_body)
    """
    # Calculate savings
    savings = product.base_price - product.current_price
    
    subject = f"🔔 Price Drop: {product.name} is now {format_price(product.current_price)}"
    
    # Build HTML email body
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2d3748;">Price Alert: Your target has been reached!</h2>
        
        <div style="background-color: #f7fafc; border-radius: 8px; padding: 20px; margin: 20px 0;">
            <h3 style="margin-top: 0; color: #1a202c;">{product.name}</h3>
            <p style="color: #718096; margin: 5px 0;">Retailer: {product.retailer}</p>
            
            <div style="margin: 20px 0;">
                <span style="font-size: 28px; font-weight: bold; color: #38a169;">
                    {format_price(product.current_price)}
                </span>
                <span style="text-decoration: line-through; color: #a0aec0; margin-left: 10px;">
                    {format_price(product.base_price)}
                </span>
            </div>
            
            <p style="color: #38a169; font-weight: bold; margin: 10px 0;">
                You save {format_price(savings)} ({product.discount_percent}% off)
            </p>
        </div>
        
        <div style="margin: 20px 0;">
            <a href="#" style="display: inline-block; background-color: #4299e1; color: white; 
                              padding: 12px 24px; text-decoration: none; border-radius: 6px;
                              font-weight: bold;">
                View Deal at {product.retailer} →
            </a>
        </div>
        
        <p style="color: #718096; font-size: 12px; margin-top: 30px;">
            Price checked at {format_timestamp()}.<br>
            <strong>Prices may change quickly</strong> — we recommend checking availability now.
        </p>
        
        <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;">
        
        <p style="color: #a0aec0; font-size: 11px;">
            You're receiving this because you set a price alert for {product.name}.
            Your target was: {watch.threshold_type} threshold of {watch.threshold_value}{'%' if watch.threshold_type == 'percent' else ''}.
        </p>
    </body>
    </html>
    """
    
    # Plain text fallback
    plain_body = f"""
Price Alert: Your target has been reached!

{product.name}
Retailer: {product.retailer}

Current Price: {format_price(product.current_price)}
Original Price: {format_price(product.base_price)}
You Save: {format_price(savings)} ({product.discount_percent}% off)

View this deal at {product.retailer}: [Link]

---
Price checked at {format_timestamp()}.
Prices may change quickly — we recommend checking availability now.

You set a {watch.threshold_type} threshold of {watch.threshold_value}{'%' if watch.threshold_type == 'percent' else ''} for this product.
    """
    
    return subject, html_body, plain_body


def send_notification(product, watch):
    """
    Send a price alert email to a user.
    
    Args:
        product: The Product that triggered the alert
        watch: The Watch containing user email and threshold info
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    if not SENDGRID_API_KEY:
        print(f"[MOCK EMAIL] Would send to {watch.email} about {product.name} at {format_price(product.current_price)}")
        return True  # Return True in mock mode so the flow continues
    
    subject, html_body, plain_body = build_email_content(product, watch)
    
    try:
        message = Mail(
            from_email=Email(FROM_EMAIL, "Price Tracker Alerts"),
            to_emails=To(watch.email),
            subject=subject,
            plain_text_content=Content("text/plain", plain_body),
            html_content=Content("text/html", html_body)
        )
        
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        
        print(f"[EMAIL SENT] To {watch.email} about {product.name} - Status: {response.status_code}")
        return response.status_code in [200, 201, 202]
        
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send to {watch.email}: {str(e)}")
        return False


def send_test_email(to_email):
    """
    Send a test email to verify SendGrid configuration.
    
    Args:
        to_email: Email address to send test to
        
    Returns:
        bool: True if sent successfully
    """
    if not SENDGRID_API_KEY:
        print(f"[MOCK TEST EMAIL] Would send test to {to_email}")
        return True
    
    try:
        message = Mail(
            from_email=Email(FROM_EMAIL, "Price Tracker Alerts"),
            to_emails=To(to_email),
            subject="Price Tracker - Test Email",
            plain_text_content=Content("text/plain", "If you received this, your email configuration is working!"),
            html_content=Content("text/html", "<h2>Test Successful!</h2><p>Your Price Tracker email configuration is working correctly.</p>")
        )
        
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        
        return response.status_code in [200, 201, 202]
        
    except Exception as e:
        print(f"[TEST EMAIL ERROR] {str(e)}")
        return False
