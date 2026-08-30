from fastapi import FastAPI, HTTPException, Header, Depends, status, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import re
import datetime
from dotenv import load_dotenv

# Load env variables from .env file if it exists
load_dotenv()

# Import database and authentication helper functions
from database import (
    get_user_by_email, create_user,
    get_all_contacts, get_contact_by_id,
    get_all_recommendations, get_recommendation_by_id, create_recommendation,
    upvote_recommendation, toggle_vote_recommendation, get_user_votes, has_user_voted,
    update_recommendation_details, delete_recommendation_by_id,
    get_all_issues, get_issue_by_id, create_issue, update_issue_status_and_assignee,
    get_all_announcements, get_announcement_by_id, create_announcement, update_announcement
)
from auth_utils import hash_password, verify_password, create_access_token, decode_access_token
from agent_routes import router as agent_router

app = FastAPI(title="CommUnity API")

# Configure CORS (useful for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount agent router
app.include_router(agent_router)

# Email verification regex (simple, standard format validation)
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

# ─── Pydantic Schemas ──────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    name: str
    email: str
    flat_number: str
    password: str
    confirm_password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class CreateRecommendationRequest(BaseModel):
    service_name: str
    category: str
    description: str
    contact_info: str = ""

class CreateIssueRequest(BaseModel):
    title: str
    description: str
    category: str
    location: str
    attachment_ref: str = ""

class UpdateIssueRequest(BaseModel):
    status: str
    assigned_to: str = ""
    admin_note: str = ""

class UpdateRecommendationRequest(BaseModel):
    service_name: str
    category: str
    description: str
    contact_info: str = ""

class CreateAnnouncementRequest(BaseModel):
    title: str
    content: str
    category: str = "General"
    status: str = "published"

class UpdateAnnouncementRequest(BaseModel):
    title: str
    content: str
    category: str = "General"
    status: str = "published"

# ─── Status ───────────────────────────────────────────────────────────────────

@app.get("/api/status")
def get_status():
    return {
        "status": "connected",
        "message": "Hello from the CommUnity FastAPI Backend!",
        "version": "0.3.0",
        "database": "Cloud SQL PostgreSQL (pg8000)"
    }

# ─── Auth Endpoints ───────────────────────────────────────────────────────────

@app.post("/api/auth/signup")
def signup(payload: SignupRequest):
    name = payload.name.strip()
    email = payload.email.strip().lower()
    flat_number = payload.flat_number.strip()
    password = payload.password
    confirm_password = payload.confirm_password

    if not name or not email or not flat_number or not password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="All fields are required")

    if not EMAIL_REGEX.match(email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email format")

    if password != confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match")

    if len(password) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be at least 6 characters long")

    if get_user_by_email(email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email address is already registered")

    hashed_pwd = hash_password(password)
    new_user = create_user(name=name, email=email, flat_number=flat_number, hashed_password=hashed_pwd, role="Resident")

    if not new_user:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to register user. Please try again.")

    return {
        "id": new_user["id"],
        "name": new_user["name"],
        "email": new_user["email"],
        "flat_number": new_user["flat_number"],
        "role": new_user["role"]
    }

@app.post("/api/auth/login")
def login(payload: LoginRequest):
    email = payload.email.strip().lower()
    password = payload.password

    if not email or not password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email and password are required")

    user = get_user_by_email(email)
    if not user or not verify_password(password, user["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token_data = {"sub": user["email"], "name": user["name"], "role": user["role"], "id": user["id"]}
    access_token = create_access_token(data=token_data)

    return {"access_token": access_token, "token_type": "bearer"}

# ─── Auth Dependency ──────────────────────────────────────────────────────────

def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication token is missing or malformed")

    token = authorization.split(" ")[1]
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired or is invalid")

    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    user = get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authenticated user no longer exists")

    user_profile = dict(user)
    user_profile.pop("hashed_password", None)
    return user_profile

@app.get("/api/auth/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return current_user

# ─── Contacts Endpoints ───────────────────────────────────────────────────────

@app.get("/api/contacts")
def list_contacts(
    category: str = Query(default=None),
    search: str = Query(default=None),
    current_user: dict = Depends(get_current_user)
):
    """Returns community contacts, optionally filtered by category and/or search text."""
    return get_all_contacts(category=category, search=search)

@app.get("/api/contacts/{contact_id}")
def get_contact(contact_id: int, current_user: dict = Depends(get_current_user)):
    """Returns a single community contact by ID."""
    contact = get_contact_by_id(contact_id)
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return contact

# ─── Recommendations Endpoints ────────────────────────────────────────────────

@app.get("/api/recommendations")
def list_recommendations(
    category: str = Query(default=None),
    search: str = Query(default=None),
    current_user: dict = Depends(get_current_user)
):
    """Returns all recommendations, optionally filtered, sorted by votes descending."""
    recs = get_all_recommendations(category=category, search=search)
    user_id = current_user["id"]
    user_voted_ids = get_user_votes(user_id)
    for r in recs:
        r["user_has_voted"] = r["id"] in user_voted_ids
    return recs

@app.get("/api/recommendations/{rec_id}")
def get_recommendation(rec_id: int, current_user: dict = Depends(get_current_user)):
    """Returns a single recommendation by ID."""
    rec = get_recommendation_by_id(rec_id)
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")
    rec["user_has_voted"] = has_user_voted(rec_id, current_user["id"])
    return rec

@app.post("/api/recommendations")
def add_recommendation(
    payload: CreateRecommendationRequest,
    current_user: dict = Depends(get_current_user)
):
    """Creates a new recommendation associated with the authenticated resident."""
    service_name = payload.service_name.strip()
    category = payload.category.strip()
    description = payload.description.strip()
    contact_info = payload.contact_info.strip() if payload.contact_info else ""

    if not service_name or not category or not description:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Service name, category, and description are required")

    valid_categories = ["Broadband", "Plumber", "Electrician", "AC Service", "Appliance Repair",
                        "Cleaning", "Tutor", "Healthcare", "Laundry", "Other"]
    if category not in valid_categories:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid category. Choose from: {', '.join(valid_categories)}")

    created_date = datetime.date.today().isoformat()
    rec = create_recommendation(
        service_name=service_name,
        category=category,
        description=description,
        contact_info=contact_info,
        user_id=current_user["id"],
        user_name=current_user["name"],
        created_date=created_date
    )

    if not rec:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save recommendation")

    rec["user_has_voted"] = False
    return rec

@app.post("/api/recommendations/{rec_id}/vote")
def vote_recommendation(rec_id: int, current_user: dict = Depends(get_current_user)):
    """Toggles an upvote from the authenticated resident for a recommendation.
    Adds the vote if the user has not voted yet; removes it if they have already voted.
    Each resident can have at most one active vote per recommendation."""
    rec = get_recommendation_by_id(rec_id)
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")

    voted_date = datetime.date.today().isoformat()
    updated = toggle_vote_recommendation(rec_id=rec_id, user_id=current_user["id"], voted_date=voted_date)

    if updated is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update vote")

    updated["user_has_voted"] = has_user_voted(rec_id, current_user["id"])
    return updated


@app.put("/api/recommendations/{rec_id}")
def edit_recommendation(
    rec_id: int,
    payload: UpdateRecommendationRequest,
    current_user: dict = Depends(get_current_user)
):
    """Updates a recommendation. Only the creator or an Admin may edit."""
    rec = get_recommendation_by_id(rec_id)
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")

    if rec["created_by_user_id"] != current_user["id"] and current_user.get("role") != "Admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to edit this recommendation")

    service_name = payload.service_name.strip()
    category = payload.category.strip()
    description = payload.description.strip()
    contact_info = payload.contact_info.strip() if payload.contact_info else ""

    if not service_name or not category or not description:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Service name, category, and description are required")

    valid_categories = ["Broadband", "Plumber", "Electrician", "AC Service", "Appliance Repair",
                        "Cleaning", "Tutor", "Healthcare", "Laundry", "Other"]
    if category not in valid_categories:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid category")

    updated = update_recommendation_details(rec_id, service_name, category, description, contact_info)
    if not updated:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update recommendation")

    updated["user_has_voted"] = has_user_voted(rec_id, current_user["id"])
    return updated


@app.delete("/api/recommendations/{rec_id}")
def remove_recommendation(
    rec_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Deletes a recommendation. Only the creator or an Admin may delete."""
    rec = get_recommendation_by_id(rec_id)
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")

    if rec["created_by_user_id"] != current_user["id"] and current_user.get("role") != "Admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to delete this recommendation")

    success = delete_recommendation_by_id(rec_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete recommendation")

    return {"message": "Recommendation deleted successfully"}


# ─── Issues Endpoints ─────────────────────────────────────────────────────────

@app.get("/api/issues")
def list_issues(
    category: str = Query(default=None),
    status: str = Query(default=None),
    search: str = Query(default=None),
    only_mine: bool = Query(default=False),
    current_user: dict = Depends(get_current_user)
):
    """Returns community issues with filters. Residents can filter to their own reported issues."""
    user_id = current_user["id"]
    filter_user_id = user_id if only_mine else None
    return get_all_issues(category=category, status=status, search=search, user_id=filter_user_id)


@app.get("/api/issues/{issue_id}")
def get_issue(issue_id: int, current_user: dict = Depends(get_current_user)):
    """Returns a single issue by ID."""
    issue = get_issue_by_id(issue_id)
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")
    return issue


@app.post("/api/issues")
def add_issue(
    payload: CreateIssueRequest,
    current_user: dict = Depends(get_current_user)
):
    """Creates a new community issue reported by the current user."""
    title = payload.title.strip()
    description = payload.description.strip()
    category = payload.category.strip()
    location = payload.location.strip()
    attachment_ref = payload.attachment_ref.strip() if payload.attachment_ref else ""

    if not title or not description or not category or not location:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Title, description, category, and location are required")

    valid_categories = ["Water", "Lift", "Parking", "Security", "Housekeeping", "Electrical", "Other"]
    if category not in valid_categories:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid category. Choose from: {', '.join(valid_categories)}")

    created_date = datetime.date.today().isoformat()
    issue = create_issue(
        title=title,
        description=description,
        category=category,
        location=location,
        user_id=current_user["id"],
        user_name=current_user["name"],
        created_date=created_date,
        attachment_ref=attachment_ref
    )

    if not issue:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save issue")

    return issue


@app.put("/api/issues/{issue_id}")
def update_issue(
    issue_id: int,
    payload: UpdateIssueRequest,
    current_user: dict = Depends(get_current_user)
):
    """Updates issue status, assignment, and admin note. Restricted to Admins."""
    if current_user.get("role") != "Admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can update issue status or assignment")

    issue = get_issue_by_id(issue_id)
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    new_status = payload.status.strip()
    assigned_to = payload.assigned_to.strip() if payload.assigned_to else ""
    admin_note = payload.admin_note.strip() if payload.admin_note else ""

    valid_statuses = ["Open", "Assigned", "In Progress", "Resolved", "Closed"]
    if new_status not in valid_statuses:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid status. Choose from: {', '.join(valid_statuses)}")

    updated_date = datetime.date.today().isoformat()
    updated = update_issue_status_and_assignee(
        issue_id=issue_id,
        status_val=new_status,
        assigned_to=assigned_to,
        updated_date=updated_date,
        admin_note=admin_note
    )

    if not updated:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update issue")

    return updated


# ─── Announcements Endpoints ───────────────────────────────────────────────────

@app.get("/api/announcements")
def list_announcements(current_user: dict = Depends(get_current_user)):
    """Returns all announcements. Admins see all statuses; residents see published only."""
    if current_user.get("role") == "Admin":
        return get_all_announcements()
    return get_all_announcements(status_filter="published")


@app.get("/api/announcements/{ann_id}")
def get_one_announcement(ann_id: int, current_user: dict = Depends(get_current_user)):
    """Returns a single announcement by ID. Non-admins may only view published ones."""
    ann = get_announcement_by_id(ann_id)
    if not ann:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")
    if current_user.get("role") != "Admin" and ann["status"] != "published":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")
    return ann


@app.post("/api/announcements")
def add_announcement(
    payload: CreateAnnouncementRequest,
    current_user: dict = Depends(get_current_user)
):
    """Creates a new announcement. Restricted to Admins."""
    if current_user.get("role") != "Admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can create announcements")

    title = payload.title.strip()
    content = payload.content.strip()
    category = payload.category.strip() if payload.category else "General"
    ann_status = payload.status if payload.status in ("published", "archived") else "published"

    if not title or not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Title and content are required")

    valid_categories = ["General", "Maintenance", "Security", "Water", "Other"]
    if category not in valid_categories:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid category")

    published_date = datetime.date.today().isoformat()
    ann = create_announcement(
        title=title, content=content, category=category,
        user_id=current_user["id"], user_name=current_user["name"],
        published_date=published_date, status=ann_status
    )
    if not ann:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create announcement")
    return ann


@app.put("/api/announcements/{ann_id}")
def edit_announcement(
    ann_id: int,
    payload: UpdateAnnouncementRequest,
    current_user: dict = Depends(get_current_user)
):
    """Updates an announcement. Restricted to Admins."""
    if current_user.get("role") != "Admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can edit announcements")

    ann = get_announcement_by_id(ann_id)
    if not ann:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")

    title = payload.title.strip()
    content = payload.content.strip()
    category = payload.category.strip() if payload.category else "General"
    ann_status = payload.status if payload.status in ("published", "archived") else "published"

    if not title or not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Title and content are required")

    updated = update_announcement(ann_id, title, content, category, ann_status)
    if not updated:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update announcement")
    return updated


# ─── Serve Frontend ───────────────────────────────────────────────────────────

current_dir = os.path.dirname(os.path.realpath(__file__))
frontend_dir = os.path.abspath(os.path.join(current_dir, "..", "frontend"))
os.makedirs(frontend_dir, exist_ok=True)
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
