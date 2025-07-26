#!/usr/bin/env python3
"""
Demo script showing the Enterprise FastAPI Application features.
"""
import asyncio
import json
from datetime import datetime

def print_banner(title):
    """Print a banner for the demo section."""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

async def demo_database():
    """Demonstrate database functionality."""
    print_banner("Database Connection Demo")
    
    from app.models.database import db_manager
    
    # Initialize database
    await db_manager.initialize()
    print(f"✓ Database initialized: {db_manager.is_connected}")
    
    # Health check
    healthy = await db_manager.health_check()
    print(f"✓ Database health check: {healthy}")
    
    # Close connection
    await db_manager.close()
    print("✓ Database connection closed")

async def demo_services():
    """Demonstrate service layer functionality."""
    print_banner("Service Layer Demo")
    
    from app.services.item_service import ItemService
    from app.repositories.item_repository import ItemRepository
    from app.models.schemas import ItemCreate, ItemUpdate, PaginationParams
    
    # Initialize service
    repository = ItemRepository()
    service = ItemService(repository)
    print("✓ Service initialized")
    
    # Create items
    items_to_create = [
        ItemCreate(name="Enterprise Laptop", price=1299.99, is_offer=False),
        ItemCreate(name="Wireless Mouse", price=49.99, is_offer=True),
        ItemCreate(name="Mechanical Keyboard", price=149.99, is_offer=False),
    ]
    
    created_items = []
    for item_data in items_to_create:
        item = await service.create_item(item_data)
        created_items.append(item)
        print(f"✓ Created: {item.name} (ID: {item.id})")
    
    # List all items
    pagination = PaginationParams(page=1, limit=10)
    result = await service.get_items(pagination)
    print(f"✓ Retrieved {len(result.items)} items (total: {result.total})")
    
    # Search items
    search_result = await service.search_items("laptop", pagination)
    print(f"✓ Search for 'laptop': {len(search_result.items)} results")
    
    # Update item
    if created_items:
        item_id = created_items[0].id
        update_data = ItemUpdate(price=999.99, is_offer=True)
        updated_item = await service.update_item(item_id, update_data)
        print(f"✓ Updated item {item_id}: price={updated_item.price}, is_offer={updated_item.is_offer}")
    
    # Demonstrate business logic validation
    try:
        invalid_item = ItemCreate(name="spam product", price=10.0)
        await service.create_item(invalid_item)
    except Exception as e:
        print(f"✓ Business rule validation working: {type(e).__name__}")

def demo_configuration():
    """Demonstrate configuration management."""
    print_banner("Configuration Management Demo")
    
    from app.config import config
    
    print(f"✓ Application: {config.title} v{config.version}")
    print(f"✓ Environment: {config.environment}")
    print(f"✓ Database URL: {config.database.url}")
    print(f"✓ Logging Level: {config.logging.level}")
    print(f"✓ Pool Size: {config.database.pool_size}")

def demo_error_handling():
    """Demonstrate error handling."""
    print_banner("Error Handling Demo")
    
    from app.utils.errors import BusinessLogicError, ValidationError, DatabaseError
    from app.models.schemas import ErrorResponse
    
    # Create error instances
    errors = [
        BusinessLogicError("Invalid business operation", {"code": "BL001"}),
        ValidationError("Invalid input data", "name", {"pattern": "required"}),
        DatabaseError("Connection failed", "create_item", {"timeout": 30}),
    ]
    
    for error in errors:
        print(f"✓ {error.__class__.__name__}: {error.message}")

def demo_logging():
    """Demonstrate logging capabilities."""
    print_banner("Logging System Demo")
    
    from app.utils.logging import setup_logging, get_logger
    
    # Setup logging
    setup_logging()
    print("✓ Logging system initialized")
    
    # Get logger and demonstrate different levels
    logger = get_logger("demo")
    
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.debug("This is a debug message")
    
    print("✓ Log messages sent (check console output)")

async def main():
    """Run the complete demo."""
    print_banner("Enterprise FastAPI Application Demo")
    print("This demo showcases the enterprise-grade features and architecture.")
    
    # Configuration demo
    demo_configuration()
    
    # Logging demo
    demo_logging()
    
    # Error handling demo
    demo_error_handling()
    
    # Database demo
    await demo_database()
    
    # Service layer demo
    await demo_services()
    
    print_banner("Demo Complete")
    print("✓ All enterprise features demonstrated successfully!")
    print("\nTo explore the API:")
    print("1. Run: fastapi dev main.py")
    print("2. Visit: http://127.0.0.1:8000/docs")
    print("3. Try the health check: http://127.0.0.1:8000/api/v1/health")

if __name__ == "__main__":
    asyncio.run(main())