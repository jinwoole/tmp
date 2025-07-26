"""
Repository pattern implementation for data access.
Provides abstraction layer between business logic and data storage.
"""
import logging
import os
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy import select, func, text
from sqlalchemy.exc import SQLAlchemyError

from app.models.entities import Item, MockItem, _items_storage, get_next_id
from app.models.schemas import ItemCreate, ItemUpdate, PaginationParams
from app.models.database import db_manager

logger = logging.getLogger(__name__)


class BaseRepository(ABC):
    """Abstract base repository class."""
    
    @abstractmethod
    async def get_by_id(self, id: int):
        """Get entity by ID."""
        pass
    
    @abstractmethod
    async def get_all(self, pagination: Optional[PaginationParams] = None):
        """Get all entities with optional pagination."""
        pass
    
    @abstractmethod
    async def create(self, data: Dict[str, Any]):
        """Create new entity."""
        pass
    
    @abstractmethod
    async def update(self, id: int, data: Dict[str, Any]):
        """Update existing entity."""
        pass
    
    @abstractmethod
    async def delete(self, id: int):
        """Delete entity by ID."""
        pass


class ItemRepository(BaseRepository):
    """Repository for Item entities with enterprise-grade error handling."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.use_mock = os.getenv("USE_MOCK_DB", "false").lower() == "true"
    
    async def get_by_id(self, item_id: int) -> Optional[Item]:
        """Get item by ID with error handling."""
        try:
            self.logger.debug(f"Fetching item with id: {item_id}")
            
            if self.use_mock:
                # Mock implementation
                item = _items_storage.get(item_id)
                if item:
                    self.logger.debug(f"Found item: {item}")
                else:
                    self.logger.debug(f"Item with id {item_id} not found")
                return item
            
            # Real PostgreSQL implementation
            async with db_manager.get_session() as session:
                result = await session.execute(
                    select(Item).where(Item.id == item_id)
                )
                item = result.scalar_one_or_none()
                if item:
                    self.logger.debug(f"Found item: {item}")
                else:
                    self.logger.debug(f"Item with id {item_id} not found")
                return item
                
        except SQLAlchemyError as e:
            self.logger.error(f"Database error fetching item {item_id}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error fetching item {item_id}: {e}")
            raise
    
    async def get_all(self, pagination: Optional[PaginationParams] = None) -> tuple[List[Item], int]:
        """Get all items with pagination."""
        try:
            self.logger.debug("Fetching all items")
            
            if self.use_mock:
                # Mock implementation
                all_items = list(_items_storage.values())
                total = len(all_items)
                
                # Sort by creation time (newest first)
                all_items.sort(key=lambda x: x.created_at, reverse=True)
                
                if pagination:
                    start = pagination.offset
                    end = start + pagination.limit
                    items = all_items[start:end]
                else:
                    items = all_items
                
                self.logger.debug(f"Found {len(items)} items (total: {total})")
                return items, total
            
            # Real PostgreSQL implementation
            async with db_manager.get_session() as session:
                # Get total count
                count_result = await session.execute(select(func.count(Item.id)))
                total = count_result.scalar()
                
                # Get paginated results
                query = select(Item).order_by(Item.created_at.desc())
                if pagination:
                    query = query.offset(pagination.offset).limit(pagination.limit)
                
                result = await session.execute(query)
                items = result.scalars().all()
                
                self.logger.debug(f"Found {len(items)} items (total: {total})")
                return list(items), total
            
        except SQLAlchemyError as e:
            self.logger.error(f"Database error fetching items: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error fetching items: {e}")
            raise
    
    async def create(self, item_data: ItemCreate) -> Item:
        """Create new item with validation."""
        try:
            self.logger.debug(f"Creating new item: {item_data.model_dump()}")
            
            if self.use_mock:
                # Mock implementation
                item_id = get_next_id()
                item = MockItem(
                    id=item_id,
                    name=item_data.name,
                    price=item_data.price,
                    is_offer=item_data.is_offer
                )
                _items_storage[item_id] = item
                
                self.logger.info(f"Created item with id: {item_id}")
                return item
            
            # Real PostgreSQL implementation
            async with db_manager.get_session() as session:
                db_item = Item(**item_data.model_dump())
                session.add(db_item)
                await session.commit()
                await session.refresh(db_item)
                
                self.logger.info(f"Created item with id: {db_item.id}")
                return db_item
            
        except SQLAlchemyError as e:
            self.logger.error(f"Database error creating item: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error creating item: {e}")
            raise
    
    async def update(self, item_id: int, item_data: ItemUpdate) -> Optional[Item]:
        """Update existing item."""
        try:
            self.logger.debug(f"Updating item {item_id}: {item_data.model_dump(exclude_unset=True)}")
            
            if self.use_mock:
                # Mock implementation
                item = _items_storage.get(item_id)
                if not item:
                    self.logger.debug(f"Item {item_id} not found for update")
                    return None
                
                update_data = item_data.model_dump(exclude_unset=True)
                for field, value in update_data.items():
                    setattr(item, field, value)
                
                item.updated_at = datetime.now()
                
                self.logger.info(f"Updated item {item_id}")
                return item
            
            # Real PostgreSQL implementation
            async with db_manager.get_session() as session:
                result = await session.execute(
                    select(Item).where(Item.id == item_id)
                )
                db_item = result.scalar_one_or_none()
                
                if not db_item:
                    self.logger.debug(f"Item {item_id} not found for update")
                    return None
                
                update_data = item_data.model_dump(exclude_unset=True)
                for field, value in update_data.items():
                    setattr(db_item, field, value)
                
                db_item.updated_at = func.now()
                await session.commit()
                await session.refresh(db_item)
                
                self.logger.info(f"Updated item {item_id}")
                return db_item
            
        except SQLAlchemyError as e:
            self.logger.error(f"Database error updating item {item_id}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error updating item {item_id}: {e}")
            raise
    
    async def delete(self, item_id: int) -> bool:
        """Delete item by ID."""
        try:
            self.logger.debug(f"Deleting item: {item_id}")
            
            if self.use_mock:
                # Mock implementation
                if item_id in _items_storage:
                    del _items_storage[item_id]
                    self.logger.info(f"Deleted item {item_id}")
                    return True
                else:
                    self.logger.debug(f"Item {item_id} not found for deletion")
                    return False
            
            # Real PostgreSQL implementation
            async with db_manager.get_session() as session:
                result = await session.execute(
                    select(Item).where(Item.id == item_id)
                )
                db_item = result.scalar_one_or_none()
                
                if not db_item:
                    self.logger.debug(f"Item {item_id} not found for deletion")
                    return False
                
                await session.delete(db_item)
                await session.commit()
                
                self.logger.info(f"Deleted item {item_id}")
                return True
                
        except SQLAlchemyError as e:
            self.logger.error(f"Database error deleting item {item_id}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error deleting item {item_id}: {e}")
            raise
    
    async def search(self, query: str, pagination: Optional[PaginationParams] = None) -> tuple[List[Item], int]:
        """Search items by name."""
        try:
            self.logger.debug(f"Searching items with query: {query}")
            
            if self.use_mock:
                # Mock implementation
                all_items = list(_items_storage.values())
                filtered_items = [
                    item for item in all_items 
                    if query.lower() in item.name.lower()
                ]
                
                total = len(filtered_items)
                
                # Sort by relevance and creation time
                filtered_items.sort(key=lambda x: x.created_at, reverse=True)
                
                if pagination:
                    start = pagination.offset
                    end = start + pagination.limit
                    items = filtered_items[start:end]
                else:
                    items = filtered_items
                
                self.logger.debug(f"Found {len(items)} items matching query (total: {total})")
                return items, total
            
            # Real PostgreSQL implementation using full-text search
            async with db_manager.get_session() as session:
                # Use PostgreSQL's full-text search for better performance
                search_query = f"%{query.lower()}%"
                
                # Get total count
                count_result = await session.execute(
                    select(func.count(Item.id)).where(
                        func.lower(Item.name).like(search_query)
                    )
                )
                total = count_result.scalar()
                
                # Get paginated results
                query_stmt = select(Item).where(
                    func.lower(Item.name).like(search_query)
                ).order_by(Item.created_at.desc())
                
                if pagination:
                    query_stmt = query_stmt.offset(pagination.offset).limit(pagination.limit)
                
                result = await session.execute(query_stmt)
                items = result.scalars().all()
                
                self.logger.debug(f"Found {len(items)} items matching query (total: {total})")
                return list(items), total
            
        except SQLAlchemyError as e:
            self.logger.error(f"Database error searching items: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error searching items: {e}")
            raise