"""
Database entity models using SQLAlchemy.
Defines the database schema and ORM mappings.
"""
from datetime import datetime
from typing import Optional

# Note: These imports would be available once sqlalchemy is installed
# from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, func
# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import relationship

# Base = declarative_base()


class MockBase:
    """Mock base class for when SQLAlchemy is not available."""
    pass


# This would be the actual Item model with SQLAlchemy:
# class Item(Base):
#     """Item database model."""
#     __tablename__ = "items"
#     
#     id = Column(Integer, primary_key=True, index=True)
#     name = Column(String(100), nullable=False, index=True)
#     price = Column(Float, nullable=False, index=True)
#     is_offer = Column(Boolean, default=False, nullable=True)
#     created_at = Column(DateTime, default=func.now(), nullable=False)
#     updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
#     
#     def __repr__(self):
#         return f"<Item(id={self.id}, name='{self.name}', price={self.price})>"


class Item(MockBase):
    """Mock Item model for when SQLAlchemy is not available."""
    
    def __init__(self, id: int, name: str, price: float, is_offer: Optional[bool] = None):
        self.id = id
        self.name = name
        self.price = price
        self.is_offer = is_offer
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def __repr__(self):
        return f"<Item(id={self.id}, name='{self.name}', price={self.price})>"


# Mock in-memory storage for demonstration
_items_storage = {}
_next_id = 1


def get_next_id() -> int:
    """Get next available ID for mock storage."""
    global _next_id
    current_id = _next_id
    _next_id += 1
    return current_id


def reset_storage():
    """Reset mock storage (useful for testing)."""
    global _items_storage, _next_id
    _items_storage = {}
    _next_id = 1