from fastapi import FastAPI, HTTPException, Header, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import os
import re
from dotenv import load_dotenv

# Load env variables from .env file if it exists
load_dotenv()

# Import database and authentication helper functions
from database import get_user_by_email, create_user, DB_PATH
from auth_utils import hash_password, verify_password, create_access_token, decode_access_token

app = FastAPI(title="CommUnity API")

# Configure CORS (useful for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Email verification regex (simple, standard format validation)
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

# Pydantic Schemas for validation
class SignupRequest(BaseModel):
    name: str
    email: str
    flat_number: str
    password: str
    confirm_password: str

class LoginRequest(BaseModel):
    email: str
    password: str

# API verification endpoint
@app.get("/api/status")
def get_status():
    return {
        "status": "connected",
        "message": "Hello from the CommUnity FastAPI Backend!",
        "version": "0.2.0",
        "database_file": DB_PATH
    }

# Signup endpoint
@app.post("/api/auth/signup")
def signup(payload: SignupRequest):
    name = payload.name.strip()
    email = payload.email.strip().lower()
    flat_number = payload.flat_number.strip()
    password = payload.password
    confirm_password = payload.confirm_password

    # Validation: Check empty inputs
    if not name or not email or not flat_number or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All fields are required"
        )

    # Validation: Email format validation
    if not EMAIL_REGEX.match(email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format"
        )

    # Validation: Passwords matching
    if password != confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )

    # Validation: Password strength (basic check)
    if len(password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters long"
        )

    # Prevent duplicate registration
    existing_user = get_user_by_email(email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is already registered"
        )

    # Securely hash password
    hashed_pwd = hash_password(password)

    # Save to SQLite with default "Resident" role
    new_user = create_user(
        name=name,
        email=email,
        flat_number=flat_number,
        hashed_password=hashed_pwd,
        role="Resident"
    )

    if not new_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register user. Please try again."
        )

    # Return registered user profile, omitting sensitive hashed password
    return {
        "id": new_user["id"],
        "name": new_user["name"],
        "email": new_user["email"],
        "flat_number": new_user["flat_number"],
        "role": new_user["role"]
    }

# Login endpoint
@app.post("/api/auth/login")
def login(payload: LoginRequest):
    email = payload.email.strip().lower()
    password = payload.password

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required"
        )

    # Lookup user
    user = get_user_by_email(email)
    
    # Generic, secure validation response (prevents account enumeration)
    if not user or not verify_password(password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Create JWT access token
    token_data = {
        "sub": user["email"],
        "name": user["name"],
        "role": user["role"]
    }
    access_token = create_access_token(data=token_data)

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

# Dependency helper to extract current authenticated user from header
def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing or malformed"
        )
    
    token = authorization.split(" ")[1]
    payload = decode_access_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired or is invalid"
        )
    
    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
        
    user = get_user_by_email(email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user no longer exists"
        )
        
    # Return user details excluding hashed password
    user_profile = dict(user)
    user_profile.pop("hashed_password", None)
    return user_profile

# Protected profile/me endpoint
@app.get("/api/auth/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return current_user


# Find frontend directory path relative to this file
current_dir = os.path.dirname(os.path.realpath(__file__))
frontend_dir = os.path.abspath(os.path.join(current_dir, "..", "frontend"))

# Ensure the frontend directory exists
os.makedirs(frontend_dir, exist_ok=True)

# Mount the static files at the root level.
# API routes must be declared before mounting StaticFiles to avoid path conflicts.
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
