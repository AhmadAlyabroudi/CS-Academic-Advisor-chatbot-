import uvicorn
from fastapi import FastAPI
from app.core.database import engine, Base, SessionLocal
from app.models.student import Student
from app.api.student_controller import router as student_router

# FastAPI app
app = FastAPI(
    title="CS Academic Advisor Chatbot API",
    description="Backend for the CS Academic Advisor Chatbot (Simplified).",
    version="0.1.0"
)


# Automigrate (create tables)
Base.metadata.create_all(bind=engine)

# Seed database
def seed():
    db = SessionLocal()
    try:
        if db.query(Student).count() == 0:
            students = [
                Student(first_name="Alice", last_name="Johnson", email="alice@example.com", password="password123"),
                Student(first_name="Bob", last_name="Smith", email="bob@example.com", password="password123"),
                Student(first_name="Charlie", last_name="Brown", email="charlie@example.com", password="password123"),
                Student(first_name="Anas", last_name="Mallahi", email="anas@cs-gp.com", password="HelloWorld")
            ]
            db.add_all(students)
            db.commit()
    finally:
        db.close()

seed()

# Register routes
app.include_router(student_router)

@app.get("/", tags=["Root"])
def read_root():
    """
    Returns a simple hello world message.
    """
    return {"Hello": "Root"}
