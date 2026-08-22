from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(title="CommUnity API")

# Configure CORS (useful for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API verification endpoint
@app.get("/api/status")
def get_status():
    return {
        "status": "connected",
        "message": "Hello from the CommUnity FastAPI Backend!",
        "version": "0.1.0",
        "database": "SQLite (In-Memory/Local Development)"
    }

# Find frontend directory path relative to this file
current_dir = os.path.dirname(os.path.realpath(__file__))
frontend_dir = os.path.abspath(os.path.join(current_dir, "..", "frontend"))

# Ensure the frontend directory exists
os.makedirs(frontend_dir, exist_ok=True)

# Mount the static files at the root level.
# API routes must be declared before mounting StaticFiles to avoid path conflicts.
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
