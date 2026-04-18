# CS Academic Advisor Chatbot - Backend

This backend application uses FastAPI to provide a simplified student management system with a layered architecture.

## Features
- **FastAPI Endpoints**: 
  - Root URL (`/`): Returns a "Hello World" message.
  - `/students`: Retrieves all students from the database.
  - `/login`: Simple authentication endpoint for student login.
- **API Documentation**: Interactive API documentation (Swagger UI) is available at `/docs`.
- **SQLAlchemy Automigration**: Tables are automatically created on startup using SQLite.
- **Seeding**: The application automatically seeds the database with initial student records (including a test account `anas@cs-gp.com`) if the database is empty.
- **Simplified Architecture**: Logic is organized into Controllers, Models, Schemas, and Core database configuration.

## Installation
To install the required dependencies:
```bash
pip install fastapi uvicorn sqlalchemy pydantic[email]
```

## Running the Application
To start the server, run:
```bash
python app.py
```
The server will be available at `http://localhost:8000`.

## Database
The application is configured to use SQLite (`test.db`).

### Viewing the Students Table Locally
To see the `students` table, you can use the `sqlite3` command-line tool:

1. Open the database:
   ```bash
   sqlite3 test.db
   ```
2. List the tables:
   ```sql
   .tables
   ```
3. Query the table:
   ```sql
   SELECT * FROM students;
   ```

## Test Account
- **Email**: anas@cs-gp.com
- **Password**: HelloWorld

### Free time topics
- SOAP
- RPC


### Anas Notes
We use JSON for REST
1- JSON
    3 simple data types for values (Number, String, Boolean) or array of any of these or Array of Objects.
    {
        "KEY" : "Value",
        KEY : VALUE
    }



# GET , POST, PUT, PATCH, DELETE -- API HTTP Methods
######
# GET -> Retrieve Data
# POST -> Write Data
# PUT -> Update an attribute
# PATCH -> Update One or Multi attributes
# DELETE -> Delete

