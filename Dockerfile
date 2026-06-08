# Use a lightweight and stable python image
FROM python:3.11-slim

# Set work directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r backend/requirements.txt && \
    pip install --no-cache-dir bcrypt==4.0.1

# Copy backend and frontend folders
COPY backend ./backend
COPY frontend ./frontend

# Change workdir to backend so that relative path "../frontend" resolves correctly
WORKDIR /app/backend

# Expose the application port (must match docker-compose & nginx upstream)
EXPOSE 8080

# Run uvicorn with socket_app (FastAPI + Socket.IO) on port 8080
CMD ["uvicorn", "main:socket_app", "--host", "127.0.0.1", "--port", "8080"]
