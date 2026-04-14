# CS Academic Advisor Chatbot - Backend

This backend application uses FastAPI to provide a dummy endpoint and SQLAlchemy for database management with automigration.

## Features
- **FastAPI Endpoint**: A "Hello World" endpoint is available at the root URL (`/`) and a `/my_endpoint` to retrieve all users.
- **API Documentation**: Interactive API documentation (Swagger UI) is available at `/docs`.
- **SQLAlchemy Automigration**: A dummy `User` class is defined, and tables are automatically created on startup using SQLite.
- **Seeding**: The application automatically seeds the database with 5 dummy students on startup if the database is empty.
- **Port**: The server listens on port 8000.

## Installation
To install the required dependencies:
```bash
pip install fastapi uvicorn sqlalchemy
```

## Running the Application
To start the server, run:
```bash
python app.py
```
The server will be available at `http://localhost:8000`.

## Database and Automigration
The application is configured to use SQLite (`test.db`). 

### Automigration
Automigration happens automatically whenever you run the application. The line `Base.metadata.create_all(bind=engine)` in `app.py` ensures that all defined SQLAlchemy models (like the `User` class) are created as tables in the database if they don't already exist.

### Viewing the Dummy Table Locally
To see the `users` table created by the dummy class, you can use the `sqlite3` command-line tool:

1. Open the database:
   ```bash
   sqlite3 test.db
   ```
2. List the tables to verify `users` exists:
   ```sql
   .tables
   ```
3. View the table schema:
   ```sql
   PRAGMA table_info(users);
   ```
4. Query the table:
   ```sql
   SELECT * FROM users;
   ```
5. Exit `sqlite3`:
   ```sql
   .exit
   ```
   

### Anas Notes
1- JSON
    3 simple data types for values (Number, String, Boolean) or array of any of these. other values will be discussed later
    {
        "KEY" : "Value",
        KEY : VALUE
    }
