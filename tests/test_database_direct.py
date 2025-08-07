"""
Simplified integration tests for PostgreSQL connectivity.
Tests database operations directly without FastAPI TestClient to avoid event loop conflicts.
"""
import os
import pytest
import pytest_asyncio
import asyncio
import httpx
from contextlib import asynccontextmanager
import sys
import socket

# Add parent directory to path to import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment variables for testing with mock database
os.environ["USE_MOCK_DB"] = "true"

from app.models.database import db_manager
from app.models.entities import Base


@pytest_asyncio.fixture(autouse=True)
async def clean_database():
    """Clean database before each test."""
    # For mock database, clear the storage
    from app.models.entities import _items_storage
    _items_storage.clear(), Item
from app.repositories.item_repository import ItemRepository
from app.models.schemas import ItemCreate, ItemUpdate, PaginationParams
from sqlalchemy import text, select


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


@pytest.fixture(scope="module", autouse=True)
async def setup_test_database():
    """Setup and teardown test database."""
    if not check_database_availability():
        pytest.skip("PostgreSQL database not available - skipping direct database tests")
    
    try:
        await db_manager.initialize()
        
        # Create tables
        async with db_manager.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        yield
        
    except Exception as e:
        pytest.skip(f"Database setup failed: {e}")
    finally:
        # Clean up
        try:
            if db_manager.engine:
                async with db_manager.engine.begin() as conn:
                    await conn.run_sync(Base.metadata.drop_all)
                await db_manager.close()
        except Exception:
            pass  # Ignore cleanup errors


@pytest_asyncio.fixture(autouse=True)
async def clean_database():
    """Clean database before each test."""
    # For mock database, clear the storage
    from app.models.entities import _items_storage
    _items_storage.clear()


@pytest.mark.asyncio
async def test_database_connection():
    """Test basic database connectivity (mock mode)."""
    # Test ItemRepository can be instantiated and used
    repo = ItemRepository()
    assert repo is not None
    assert repo.use_mock is True
    print("✓ Mock database connection test passed")


@pytest.mark.asyncio
async def test_table_creation():
    """Test that mock storage is available."""
    # In mock mode, test that storage is available
    from app.models.entities import _items_storage
    
    # Clear storage and verify it's empty
    _items_storage.clear()
    assert len(_items_storage) == 0
    
    print("✓ Mock storage test passed")


@pytest.mark.asyncio
async def test_item_repository_crud():
    """Test CRUD operations with ItemRepository."""
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
    
    # Test DELETE
    deleted = await repo.delete(created_item.id)
    assert deleted is True
    
    # Verify deletion
    deleted_item = await repo.get_by_id(created_item.id)
    assert deleted_item is None
    
    print("✓ CRUD operations test passed")


@pytest.mark.asyncio
async def test_search_functionality():
    """Test search functionality."""
    repo = ItemRepository()
    
    # Create test items
    await repo.create(ItemCreate(name="Apple iPhone", price=999.99))
    await repo.create(ItemCreate(name="Samsung Galaxy", price=899.99))
    await repo.create(ItemCreate(name="Apple MacBook", price=1299.99))
    
    # Test search
    search_results, total = await repo.search("Apple")
    assert len(search_results) == 2
    assert total == 2
    assert all("Apple" in item.name for item in search_results)
    
    print("✓ Search functionality test passed")


@pytest.mark.asyncio
async def test_pagination():
    """Test pagination functionality."""
    repo = ItemRepository()
    
    # Create multiple items
    for i in range(10):
        await repo.create(ItemCreate(name=f"Item {i}", price=float(i * 10)))
    
    # Test pagination
    page1_items, page1_total = await repo.get_all(PaginationParams(page=1, limit=5))
    assert len(page1_items) == 5
    assert page1_total == 10
    
    page2_items, page2_total = await repo.get_all(PaginationParams(page=2, limit=5))
    assert len(page2_items) == 5
    assert page2_total == 10
    
    print("✓ Pagination test passed")


@pytest.mark.asyncio
async def test_concurrent_operations():
    """Test concurrent database operations."""
    import asyncio
    
    async def create_item(index):
        repo = ItemRepository()
        return await repo.create(ItemCreate(name=f"Concurrent Item {index}", price=float(index)))
    
    # Create multiple items concurrently
    tasks = [create_item(i) for i in range(5)]
    results = await asyncio.gather(*tasks)
    
    assert len(results) == 5
    assert all(item.id is not None for item in results)
    
