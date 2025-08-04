"""
Simplified integration tests for PostgreSQL connectivity.
Tests database operations directly without FastAPI TestClient to avoid event loop conflicts.
"""
import os
import pytest
import asyncio
import httpx
from contextlib import asynccontextmanager
import sys

# Add parent directory to path to import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment variables for real database testing
os.environ["USE_MOCK_DB"] = "false"
os.environ["DB_HOST"] = "localhost"
os.environ["DB_PORT"] = "5433"
os.environ["DB_NAME"] = "fastapi_test_db"
os.environ["DB_USER"] = "postgres"
os.environ["DB_PASSWORD"] = "password"

from app.models.database import db_manager
from app.models.entities import Base, Item
from app.repositories.item_repository import ItemRepository
from app.models.schemas import ItemCreate, ItemUpdate, PaginationParams
from sqlalchemy import text, select


@asynccontextmanager
@pytest.mark.asyncio
async def test_database():
    """Context manager for test database setup and cleanup."""
    await db_manager.initialize()
    
    # Create tables
    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    try:
        yield
    finally:
        # Clean up
        async with db_manager.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await db_manager.close()


async def clean_tables():
    """Clean all data from tables."""
    async with db_manager.engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE items RESTART IDENTITY CASCADE"))


@pytest.mark.asyncio
async def test_database_connection():
    """Test basic database connectivity."""
    async with test_database():
        # Test database connection
        async with db_manager.get_session() as session:
            result = await session.execute(text("SELECT 1 as test"))
            assert result.scalar() == 1
        
        print("✓ Database connection test passed")


@pytest.mark.asyncio
async def test_table_creation():
    """Test that tables are created properly."""
    async with test_database():
        # Check if items table exists
        async with db_manager.engine.begin() as conn:
            result = await conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'items'
                )
            """))
            assert result.scalar() is True
        
        print("✓ Table creation test passed")


@pytest.mark.asyncio
async def test_item_repository_crud():
    """Test CRUD operations using the repository."""
    async with test_database():
        repo = ItemRepository()
        
        # Test CREATE
        item_data = ItemCreate(name="Test Item", price=99.99, is_offer=True)
        created_item = await repo.create(item_data)
        assert created_item.name == "Test Item"
        assert created_item.price == 99.99
        assert created_item.is_offer is True
        assert created_item.id is not None
        
        # Test READ
        retrieved_item = await repo.get_by_id(created_item.id)
        assert retrieved_item is not None
        assert retrieved_item.name == "Test Item"
        
        # Test UPDATE
        update_data = ItemUpdate(name="Updated Item", price=149.99)
        updated_item = await repo.update(created_item.id, update_data)
        assert updated_item.name == "Updated Item"
        assert updated_item.price == 149.99
        
        # Test LIST
        items, total = await repo.get_all()
        assert total == 1
        assert len(items) == 1
        
        # Test DELETE
        deleted = await repo.delete(created_item.id)
        assert deleted is True
        
        # Verify deletion
        deleted_item = await repo.get_by_id(created_item.id)
        assert deleted_item is None
        
        print("✓ Repository CRUD operations test passed")


@pytest.mark.asyncio
async def test_search_functionality():
    """Test search functionality."""
    async with test_database():
        repo = ItemRepository()
        
        # Create test items
        items_data = [
            ItemCreate(name="Apple iPhone", price=999.0, is_offer=False),
            ItemCreate(name="Samsung Galaxy", price=899.0, is_offer=True),
            ItemCreate(name="Apple MacBook", price=1299.0, is_offer=False),
        ]
        
        created_items = []
        for item_data in items_data:
            item = await repo.create(item_data)
            created_items.append(item)
        
        # Test search
        apple_items, total = await repo.search("Apple")
        assert total == 2
        assert len(apple_items) == 2
        assert all("Apple" in item.name for item in apple_items)
        
        samsung_items, total = await repo.search("Samsung")
        assert total == 1
        assert len(samsung_items) == 1
        assert "Samsung" in samsung_items[0].name
        
        print("✓ Search functionality test passed")


@pytest.mark.asyncio
async def test_pagination():
    """Test pagination functionality."""
    async with test_database():
        repo = ItemRepository()
        
        # Create multiple items
        for i in range(15):
            item_data = ItemCreate(name=f"Item {i+1}", price=float((i+1) * 10), is_offer=False)
            await repo.create(item_data)
        
        # Test pagination
        pagination = PaginationParams(page=1, limit=5)
        items, total = await repo.get_all(pagination)
        
        assert total == 15
        assert len(items) == 5
        
        # Test second page
        pagination = PaginationParams(page=2, limit=5)
        items, total = await repo.get_all(pagination)
        
        assert total == 15
        assert len(items) == 5
        
        print("✓ Pagination test passed")


@pytest.mark.asyncio
async def test_concurrent_operations():
    """Test concurrent database operations."""
    async with test_database():
        repo = ItemRepository()
        
        async def create_item(index):
            item_data = ItemCreate(name=f"Concurrent Item {index}", price=float(index * 10), is_offer=False)
            return await repo.create(item_data)
        
        # Create items concurrently
        tasks = [create_item(i) for i in range(5)]
        created_items = await asyncio.gather(*tasks)
        
        # Verify all items were created
        assert len(created_items) == 5
        
        # Check total count
        items, total = await repo.get_all()
        assert total == 5
        
        print("✓ Concurrent operations test passed")


async def run_all_tests():
    """Run all integration tests."""
    print("Starting PostgreSQL integration tests...")
    print(f"Database: postgresql://postgres:***@localhost:5433/fastapi_test_db")
    print()
    
    try:
        await test_database_connection()
        await test_table_creation()
        await test_item_repository_crud()
        await test_search_functionality()
        await test_pagination()
        await test_concurrent_operations()
        
        print()
        print("🎉 All PostgreSQL integration tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Run tests directly
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)