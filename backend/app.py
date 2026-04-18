<<<<<<< Updated upstream
=======
<<<<<<< HEAD

from fastapi import FastAPI, Depends
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base, Session
=======
>>>>>>> 35e81689b13453df6a4cd370b8f67d53e6d21b07
>>>>>>> Stashed changes
import uvicorn
from main import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
