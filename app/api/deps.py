from app.db.sqlite import get_db

# Re-export so routes import from one place
# Add auth dependencies here later (e.g. verify JWT token)
__all__ = ["get_db"]
