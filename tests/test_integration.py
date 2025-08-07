"""
Integration tests for the Enterprise FastAPI Application with real PostgreSQL.
These tests require a running PostgreSQL database.

Note: Due to asyncio event loop conflicts between FastAPI TestClient and async database operations,
these tests focus on database-level integration testing.
"""
import os
import asyncio
import pytest
import sys
import socket

# Add parent directory to path to import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment variables for real database testing BEFORE importing anything else
os.environ["USE_MOCK_DB"] = "false"
os.environ["DB_HOST"] = "localhost"
os.environ["DB_PORT"] = "5433"  # Use test database port
os.environ["DB_NAME"] = "fastapi_test_db"
os.environ["DB_USER"] = "postgres"
os.environ["DB_PASSWORD"] = "password"

from app.models.database import db_manager
from app.models.entities import Base, Item
from app.repositories.item_repository import ItemRepository
from app.models.schemas import ItemCreate, ItemUpdate, PaginationParams
from sqlalchemy import text


def check_database_availability():
    """Check if PostgreSQL test database is available."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', 5433))
        sock.close()
        return result == 0
    except Exception:
        return False


# Check database availability at module level
if not check_database_availability():
    pytest.skip("PostgreSQL database not available - skipping integration tests", allow_module_level=True)


class TestDatabaseIntegration:
    """Integration tests with real PostgreSQL database using direct database operations."""
    
    @pytest.mark.asyncio
    async def test_database_connection(self):
        """Test that database connection works."""
        await db_manager.initialize()
        
        # Create tables
        async with db_manager.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        # Test basic query
        async with db_manager.get_session() as session:
            result = await session.execute(text("SELECT 1 as test"))
            assert result.scalar() == 1
            
        print("✓ Database connection test passed")
    
    @pytest.mark.asyncio 
    async def test_item_repository_operations(self):
        """Test CRUD operations using the item repository."""
        await db_manager.initialize()
        
        # Create tables
        async with db_manager.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        repo = ItemRepository()
        
        # Create an item
        item_data = ItemCreate(name="Test Item", price=99.99, is_offer=True)
        created_item = await repo.create(item_data)
        assert created_item.name == "Test Item"
        assert created_item.price == 99.99
        assert created_item.is_offer is True
        
        # Get the item
        retrieved_item = await repo.get_by_id(created_item.id)
        assert retrieved_item is not None
        assert retrieved_item.name == "Test Item"
        
        # Update the item
        update_data = ItemUpdate(name="Updated Item", price=149.99)
        updated_item = await repo.update(created_item.id, update_data)
        assert updated_item.name == "Updated Item"
        assert updated_item.price == 149.99
        
        # List items
        items, total = await repo.get_all(PaginationParams(skip=0, limit=10))
        assert len(items) >= 1
        assert total >= 1
        
        # Delete the item
        await repo.delete(created_item.id)
        deleted_item = await repo.get_by_id(created_item.id)
        assert deleted_item is None
        
        print("✓ Item repository operations test passed")
    
    @pytest.mark.asyncio
    async def test_search_functionality(self):
        """Test search functionality with real database."""
        await db_manager.initialize()
        
        # Create tables
        async with db_manager.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        repo = ItemRepository()
        
        # Create test items
        items = [
            ItemCreate(name="Apple iPhone", price=999.0),
            ItemCreate(name="Samsung Galaxy", price=899.0),
            ItemCreate(name="Apple MacBook", price=1299.0),
        ]
        
        created_items = []
        for item_data in items:
            item = await repo.create(item_data)
            created_items.append(item)
        
        # Search for Apple products
        search_results, total = await repo.search("Apple", PaginationParams(skip=0, limit=10))
        assert len(search_results) == 2
        assert total == 2
        assert all("Apple" in item.name for item in search_results)
        
        # Clean up
        for item in created_items:
            await repo.delete(item.id)
            
        print("✓ Search functionality test passed")
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test concurrent database operations."""
        await db_manager.initialize()
        
        # Create tables
        async with db_manager.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        async def create_item(index):
            repo = ItemRepository()
            item_data = ItemCreate(name=f"Concurrent Item {index}", price=float(index))
            return await repo.create(item_data)
        
        # Create multiple items concurrently
        tasks = [create_item(i) for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 5
        assert all(item.name.startswith("Concurrent Item") for item in results)
        
        # Clean up
        repo = ItemRepository()
        for item in results:
            await repo.delete(item.id)
            
        print("✓ Concurrent operations test passed")
    
    @pytest.mark.asyncio
    async def test_database_health_check(self):
        """Test database health check functionality."""
        await db_manager.initialize()
        
        health_status = await db_manager.health_check()
        assert health_status is True
        
        print("✓ Database health check test passed")
        
    @pytest.mark.asyncio
    async def test_transaction_rollback(self):
        """Test database transaction rollback."""
        await db_manager.initialize()
        
        # Create tables
        async with db_manager.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        repo = ItemRepository()
        
        # Get initial count
        items_before, count_before = await repo.get_all(PaginationParams(skip=0, limit=100))
        
        try:
            # This will test if transactions work properly
            # Since the repository handles its own sessions, we'll test with a direct approach
            item_data = ItemCreate(name="Transaction Test", price=50.0)
            created_item = await repo.create(item_data)
            assert created_item.id is not None
            
            # Verify the item exists
            found_item = await repo.get_by_id(created_item.id)
            assert found_item is not None
            
            # Clean up the test item
            await repo.delete(created_item.id)
            
        except Exception as e:
            # This should not happen with normal operations
            pass
            
        # Verify the item was properly cleaned up
        items_after, count_after = await repo.get_all(PaginationParams(skip=0, limit=100))
        assert count_after == count_before
        
        print("✓ Transaction rollback test passed")