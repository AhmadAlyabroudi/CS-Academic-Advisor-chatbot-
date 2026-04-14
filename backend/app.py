from fastapi import FastAPI, Depends
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base, Session
import uvicorn

# FastAPI app
app = FastAPI(
    title="CS Academic Advisor Chatbot API",
    description="Backend for the CS Academic Advisor Chatbot, providing dummy endpoints and SQLAlchemy automigration.",
    version="0.1.0"
)

# Database setup
DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dummy class for automigration
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)

# Automigrate (create tables)
Base.metadata.create_all(bind=engine)

# Dependency to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Seed database with 5 students if they don't exist
def seed_db():
    db = SessionLocal()
    if db.query(User).count() == 0:
        students = [
            User(name="Alice Johnson"),
            User(name="Bob Smith"),
            User(name="Charlie Brown"),
            User(name="Diana Prince"),
            User(name="Edward Elric")
        ]
        db.add_all(students)
        db.commit()
    db.close()

seed_db()

@app.get("/", tags=["Root"])
def read_root():
    """
    Returns a simple hello world message.
    """
    return {"Hello": "Root"}

@app.get("/my_endpoint", tags=["Anas"])
def Anas_Func(db: Session = Depends(get_db)):
    """
    Returns all users from the database.
    """
    users = db.query(User).all()
    return {"users": users}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
