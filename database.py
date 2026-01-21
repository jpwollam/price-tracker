"""
database.py
-----------
Handles database connection and provides the SQLAlchemy instance.

This is kept separate from models.py to avoid circular imports
and to make it easy to configure the database location.
"""

from flask_sqlalchemy import SQLAlchemy

# Create the SQLAlchemy instance
# This will be initialized with the Flask app in app.py
db = SQLAlchemy()


def init_db(app):
    """
    Initialize the database with the Flask app.
    Creates all tables if they don't exist.
    
    Args:
        app: The Flask application instance
    """
    db.init_app(app)
    
    with app.app_context():
        # Import models here to ensure they're registered before creating tables
        import models  # noqa
        db.create_all()
        print("Database initialized successfully.")
