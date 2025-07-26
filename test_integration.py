"""
Integration tests for the Enterprise FastAPI Application with real PostgreSQL.
These tests require a running PostgreSQL database.
"""
import os
import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy import text

# Set environment variables for real database testing
os.environ["USE_MOCK_DB"] = "false"
os.environ["DB_HOST"] = "localhost"
os.environ["DB_PORT"] = "5433"  # Use test database port
os.environ["DB_NAME"] = "fastapi_test_db"
os.environ["DB_USER"] = "postgres"
os.environ["DB_PASSWORD"] = "password"

from main import app
from app.models.database import db_manager
from app.models.entities import Base
from app.config import config


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_test_database():
    """Set up test database before all tests and clean up after."""
    try:
        # Initialize database connection
        await db_manager.initialize()
        
        # Create all tables
        if db_manager.engine:
            async with db_manager.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        
        yield
        
        # Clean up after all tests
        if db_manager.engine:
            async with db_manager.engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
        
        await db_manager.close()
        
    except Exception as e:
        pytest.skip(f"PostgreSQL not available for integration tests: {e}")


@pytest.fixture(autouse=True)
async def clean_database():
    """Clean database before each test."""
    try:
        if db_manager.engine:
            async with db_manager.engine.begin() as conn:
                # Clean all data but keep tables
                await conn.execute(text("TRUNCATE TABLE items RESTART IDENTITY CASCADE"))
        yield
    except Exception as e:
        pytest.skip(f"Database cleanup failed: {e}")


client = TestClient(app)


class TestDatabaseIntegration:
    """Integration tests with real PostgreSQL database."""
    
    def test_database_health_check(self):
        """Test that the database health check works."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
        assert data["database"] is True
    
    def test_create_and_retrieve_item(self):
        """Test creating and retrieving an item from real database."""
        # Create an item
        item_data = {
            "name": "Integration Test Item",
            "price": 99.99,
            "is_offer": True
        }
        
        create_response = client.post("/api/v1/items", json=item_data)
        assert create_response.status_code == 201
        created_item = create_response.json()
        
        assert created_item["name"] == item_data["name"]
        assert created_item["price"] == item_data["price"]
        assert created_item["is_offer"] == item_data["is_offer"]
        assert "id" in created_item
        assert "created_at" in created_item
        assert "updated_at" in created_item
        
        # Retrieve the item
        item_id = created_item["id"]
        get_response = client.get(f"/api/v1/items/{item_id}")
        assert get_response.status_code == 200
        retrieved_item = get_response.json()
        
        assert retrieved_item["id"] == created_item["id"]
        assert retrieved_item["name"] == created_item["name"]
        assert retrieved_item["price"] == created_item["price"]
    
    def test_update_item_in_database(self):
        """Test updating an item in the real database."""
        # Create an item first
        item_data = {"name": "Original Item", "price": 50.0}
        create_response = client.post("/api/v1/items", json=item_data)
        assert create_response.status_code == 201
        created_item = create_response.json()
        
        # Update the item
        update_data = {"name": "Updated Item", "price": 75.0}
        item_id = created_item["id"]
        update_response = client.put(f"/api/v1/items/{item_id}", json=update_data)
        assert update_response.status_code == 200
        updated_item = update_response.json()
        
        assert updated_item["name"] == update_data["name"]
        assert updated_item["price"] == update_data["price"]
        assert updated_item["updated_at"] != created_item["updated_at"]
    
    def test_delete_item_from_database(self):
        """Test deleting an item from the real database."""
        # Create an item first
        item_data = {"name": "Item to Delete", "price": 30.0}
        create_response = client.post("/api/v1/items", json=item_data)
        assert create_response.status_code == 201
        created_item = create_response.json()
        
        # Delete the item
        item_id = created_item["id"]
        delete_response = client.delete(f"/api/v1/items/{item_id}")
        assert delete_response.status_code == 204
        
        # Verify it's gone
        get_response = client.get(f"/api/v1/items/{item_id}")
        assert get_response.status_code == 404
    
    def test_pagination_with_database(self):
        """Test pagination functionality with real database."""
        # Create multiple items
        items_data = [
            {"name": f"Item {i}", "price": float(i * 10)}
            for i in range(1, 16)  # 15 items
        ]
        
        for item_data in items_data:
            response = client.post("/api/v1/items", json=item_data)
            assert response.status_code == 201
        
        # Test pagination
        response = client.get("/api/v1/items?page=1&limit=5")
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["items"]) == 5
        assert data["total"] == 15
        assert data["page"] == 1
        assert data["pages"] == 3
        
        # Test second page
        response = client.get("/api/v1/items?page=2&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 5
        assert data["page"] == 2
    
    def test_search_with_database(self):
        """Test search functionality with real database."""
        # Create test items
        items_data = [
            {"name": "Apple iPhone", "price": 999.0},
            {"name": "Samsung Galaxy", "price": 899.0},
            {"name": "Apple MacBook", "price": 1299.0},
            {"name": "Dell Laptop", "price": 799.0},
        ]
        
        for item_data in items_data:
            response = client.post("/api/v1/items", json=item_data)
            assert response.status_code == 201
        
        # Search for Apple products
        response = client.get("/api/v1/items/search?q=Apple")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 2
        assert all("Apple" in item["name"] for item in data["items"])
        
        # Search for Laptop products
        response = client.get("/api/v1/items/search?q=Laptop")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["total"] == 1
        assert "Laptop" in data["items"][0]["name"]
    
    def test_database_constraints(self):
        """Test database constraints and validation."""
        # Test unique constraints and data integrity
        item_data = {"name": "Test Item", "price": 10.0}
        
        # Create first item
        response1 = client.post("/api/v1/items", json=item_data)
        assert response1.status_code == 201
        
        # Create second item with same data (should work as no unique constraint on name)
        response2 = client.post("/api/v1/items", json=item_data)
        assert response2.status_code == 201
        
        # Verify both items exist
        response = client.get("/api/v1/items")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
    
    def test_concurrent_operations(self):
        """Test concurrent database operations."""
        import threading
        import time
        
        results = []
        
        def create_item(index):
            item_data = {"name": f"Concurrent Item {index}", "price": float(index)}
            response = client.post("/api/v1/items", json=item_data)
            results.append(response.status_code)
        
        # Create multiple items concurrently
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_item, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all operations succeeded
        assert all(status == 201 for status in results)
        
        # Verify all items were created
        response = client.get("/api/v1/items")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5