"""
Enterprise FastAPI Application Entry Point.
This file serves as the entry point for the application, importing from the new structure.
"""
from app.main import app

# Re-export the app for compatibility with existing deployment scripts
__all__ = ["app"]