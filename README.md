# Enterprise FastAPI Application with PostgreSQL

A production-ready FastAPI application demonstrating enterprise-grade architecture and PostgreSQL integration.

## Features

### Core Features
- 🏗️ **Clean Architecture**: Separation of concerns with layered architecture
- 🗄️ **PostgreSQL Integration**: Async database connections with connection pooling
- 🔍 **Enterprise Logging**: Structured JSON logging with request tracking
- ⚡ **High Performance**: Async/await throughout the application
- 🛡️ **Error Handling**: Comprehensive error handling with custom exceptions
- 📝 **API Documentation**: Auto-generated OpenAPI/Swagger documentation
- ✅ **Data Validation**: Pydantic models with business rule validation
- 🔄 **Health Checks**: Database and application health monitoring

### Enterprise Features
- 📊 **Request Tracking**: Unique request IDs for tracing
- 🏭 **Configuration Management**: Environment-based configuration
- 🔒 **Security**: CORS configuration and input validation
- 📈 **Production Ready**: Connection pooling, graceful shutdown
- 🧪 **Testing**: Comprehensive test coverage
- 📋 **API Standards**: RESTful design with proper HTTP status codes

## Architecture

```
app/
├── config/           # Configuration management
├── models/          # Data models and database setup
│   ├── database.py  # Database connection management
│   ├── entities.py  # Database entity models (SQLAlchemy)
│   └── schemas.py   # API request/response models (Pydantic)
├── repositories/    # Data access layer
├── services/        # Business logic layer
├── api/            # API endpoints and routes
└── utils/          # Utilities (logging, error handling)
```

## Setup

### Prerequisites

- Python 3.8+
- PostgreSQL 12+ (when using real database)
- pip

### Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd tmp
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

### Database Setup

For PostgreSQL integration, install additional dependencies:
```bash
pip install asyncpg sqlalchemy[asyncio] python-dotenv structlog pydantic-settings
```

Configure your database connection in `.env`:
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=fastapi_db
DB_USER=postgres
DB_PASSWORD=your_password
```

### Running the Application

#### Development Mode
```bash
fastapi dev main.py
```

#### Production Mode
```bash
fastapi run main.py
```

The application will be available at:
- **API**: http://127.0.0.1:8000
- **Interactive docs (Swagger UI)**: http://127.0.0.1:8000/docs
- **Alternative docs (ReDoc)**: http://127.0.0.1:8000/redoc

## API Endpoints

### Core Endpoints

#### Health Check
- **GET** `/api/v1/health` - Application and database health status

#### Items Management
- **GET** `/api/v1/items` - List all items with pagination
- **POST** `/api/v1/items` - Create a new item
- **GET** `/api/v1/items/{item_id}` - Get item by ID
- **PUT** `/api/v1/items/{item_id}` - Update item by ID
- **DELETE** `/api/v1/items/{item_id}` - Delete item by ID
- **GET** `/api/v1/items/search?q={query}` - Search items by name

### Request/Response Examples

#### Create Item
```bash
curl -X POST "http://localhost:8000/api/v1/items" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Sample Item",
       "price": 29.99,
       "is_offer": true
     }'
```

#### Response
```json
{
  "id": 1,
  "name": "Sample Item",
  "price": 29.99,
  "is_offer": true,
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T10:00:00Z"
}
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | Environment (development/staging/production) | `development` |
| `DEBUG` | Enable debug mode | `false` |
| `DB_HOST` | Database host | `localhost` |
| `DB_PORT` | Database port | `5432` |
| `DB_NAME` | Database name | `fastapi_db` |
| `DB_USER` | Database user | `postgres` |
| `DB_PASSWORD` | Database password | `password` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `LOG_FORMAT` | Log format (json/text) | `json` |

### Database Configuration

The application supports PostgreSQL with async connections and includes:
- Connection pooling for production workloads
- Automatic health checks
- Graceful connection management
- Database migration support (ready)

## Testing

Run the comprehensive test suite:

```bash
# Run all tests
python -m pytest test_main.py -v

# Run with coverage
python -m pytest test_main.py --cov=app --cov-report=html

# Run specific test
python -m pytest test_main.py::test_create_item -v
```

Tests cover:
- API endpoint functionality
- Business logic validation
- Error handling scenarios
- Database integration
- Request/response formats

## Production Deployment

### Docker Deployment

Create a `Dockerfile`:
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["fastapi", "run", "main.py", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Configuration

For production deployment:
```env
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
DB_HOST=your-postgres-host
DB_PASSWORD=secure-password
DB_POOL_SIZE=50
```

### Health Check Integration

The `/api/v1/health` endpoint provides comprehensive health information for load balancers and monitoring systems.

## Development

### Project Structure

The application follows clean architecture principles:

- **API Layer** (`app/api/`): HTTP request handling and routing
- **Service Layer** (`app/services/`): Business logic and validation
- **Repository Layer** (`app/repositories/`): Data access abstraction
- **Model Layer** (`app/models/`): Data models and database schema
- **Infrastructure** (`app/utils/`, `app/config/`): Cross-cutting concerns

### Adding New Features

1. Define data models in `app/models/schemas.py`
2. Create database entities in `app/models/entities.py`
3. Implement repository methods in `app/repositories/`
4. Add business logic in `app/services/`
5. Create API endpoints in `app/api/`
6. Write tests in `test_*.py`

### Code Quality

The application includes:
- Type hints throughout
- Comprehensive error handling
- Input validation and sanitization
- Business rule enforcement
- Structured logging
- Request tracing

## Monitoring and Observability

### Logging

The application provides structured JSON logging with:
- Request ID tracking
- Performance metrics
- Error categorization
- Database query logging

### Health Checks

Monitor application health:
```bash
curl http://localhost:8000/api/v1/health
```

Response includes:
- Application status
- Database connectivity
- Version information
- Timestamp

## Security Features

- Input validation with Pydantic
- SQL injection prevention through ORM
- CORS configuration
- Error message sanitization
- Environment-based configuration

## License

This project is licensed under the MIT License.