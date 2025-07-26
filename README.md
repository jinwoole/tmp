# FastAPI Application

A simple FastAPI application with basic endpoints demonstrating modern Python API development.

## Features

- RESTful API endpoints
- Automatic interactive API documentation
- Data validation with Pydantic
- Type hints throughout
- Health check endpoint
- CRUD operations example

## Setup

### Prerequisites

- Python 3.8+
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

### Running the Application

#### Development Mode

Run the development server with hot reloading:

```bash
fastapi dev main.py
```

The application will be available at:
- **API**: http://127.0.0.1:8000
- **Interactive docs (Swagger UI)**: http://127.0.0.1:8000/docs
- **Alternative docs (ReDoc)**: http://127.0.0.1:8000/redoc

#### Production Mode

For production deployment:

```bash
fastapi run main.py
```

## API Endpoints

### GET /
- **Description**: Root endpoint
- **Response**: Welcome message

### GET /health
- **Description**: Health check endpoint
- **Response**: Service status

### GET /items/{item_id}
- **Description**: Get item by ID
- **Parameters**: 
  - `item_id` (int): Item identifier
  - `q` (str, optional): Query parameter
- **Response**: Item details

### POST /items/
- **Description**: Create new item
- **Body**: Item object with name, price, and optional is_offer flag
- **Response**: Confirmation message with created item

### PUT /items/{item_id}
- **Description**: Update existing item
- **Parameters**: `item_id` (int): Item identifier
- **Body**: Item object with updated data
- **Response**: Updated item details

## Data Models

### Item
```python
{
    "name": "string",
    "price": 0.0,
    "is_offer": true  # optional
}
```

## Development

The application uses:
- **FastAPI**: Modern, fast web framework for building APIs
- **Pydantic**: Data validation using Python type annotations
- **Uvicorn**: ASGI web server implementation

### Testing

Run the test suite:

```bash
python -m pytest test_main.py -v
```

The tests cover all API endpoints and validate:
- Response status codes
- Response data structure
- API functionality

## Documentation

FastAPI automatically generates interactive API documentation:
- Visit http://127.0.0.1:8000/docs for Swagger UI
- Visit http://127.0.0.1:8000/redoc for ReDoc interface
- OpenAPI schema available at http://127.0.0.1:8000/openapi.json