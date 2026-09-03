"""CommUnity Agent: one ADK agent for Residents and Admins."""

import datetime
import json

from google.adk.agents import Agent
from google.adk.sessions import InMemorySessionService
from google.adk.tools import ToolContext

from database import (
    get_all_contacts, get_contact_by_id, create_contact as db_create_contact, update_contact as db_update_contact,
    get_all_recommendations, get_recommendation_by_id,
    get_all_announcements, get_announcement_by_id, create_announcement as db_create_announcement, update_announcement as db_update_announcement,
    get_all_issues, get_issue_by_id,
    create_issue as db_create_issue, update_issue_status_and_assignee as db_update_issue,
    create_recommendation as db_create_recommendation, update_recommendation_details as db_update_recommendation,
)

_MODEL = "gemini-3.8-flash"
_APP_NAME = "community_agent"
session_service = InMemorySessionService()

ISSUE_CATEGORIES = ["Water", "Lift", "Parking", "Security", "Housekeeping", "Electrical", "Other"]
REC_CATEGORIES = ["Broadband", "Plumber", "Electrician", "AC Service", "Appliance Repair", "Cleaning", "Tutor", "Healthcare", "Laundry", "Other"]
CONTACT_CATEGORIES = ["Management", "Maintenance", "Security", "Emergency", "Other"]
ANNOUNCEMENT_CATEGORIES = ["General", "Maintenance", "Security", "Water", "Other"]
ISSUE_STATUSES = ["Open", "Assigned", "In Progress", "Resolved", "Closed"]
ISSUE_ASSIGNEES = ["Maintenance Manager", "Plumbing & Electrical Lead", "Housekeeping Supervisor", "Head of Security", "Other"]


def _ctx(context):
    return context.state if context else {}


def _require_user(context):
    state = _ctx(context)
    if not state.get("user_id"):
        return None, {"error": "User context not available - please re-authenticate."}
    return state, None


def _require_admin(context):
    state, error = _require_user(context)
    if error:
        return None, error
    if state.get("user_role") != "Admin":
        return None, {"error": "Admin permission is required for this action."}
    return state, None


def _pending(context, action, payload):
    state = _ctx(context)
    state["pending_write"] = {"action": action, "payload": payload}
    return {"status": "pending_confirmation", "preview": {"action": action, **payload},
            "instruction": "Ask the user for explicit confirmation. Only after confirmation call this tool with confirmed=True."}


def _confirm(context, action, payload):
    state = _ctx(context)
    pending = state.get("pending_write")
    if not pending or pending.get("action") != action or pending.get("payload") != payload:
        return {"error": "Confirmation is required. Please preview the action and ask the user to confirm before executing it."}
    state.pop("pending_write", None)
    return None


def search_contacts(query: str = "", category: str = "", tool_context: ToolContext = None) -> dict:
    results = get_all_contacts(category=category or None, search=query or None)
    return {"contacts": results, "count": len(results)}


def search_recommendations(query: str = "", category: str = "", tool_context: ToolContext = None) -> dict:
    results = get_all_recommendations(category=category or None, search=query or None)
    return {"recommendations": results, "count": len(results)}


def search_announcements(tool_context: ToolContext = None) -> dict:
    state = _ctx(tool_context)
    status_filter = None if state.get("user_role") == "Admin" else "published"
    results = get_all_announcements(status_filter=status_filter)
    return {"announcements": results, "count": len(results)}


def get_my_issues(tool_context: ToolContext = None) -> dict:
    state, error = _require_user(tool_context)
    if error: return error
    results = get_all_issues(user_id=state["user_id"])
    return {"issues": results, "count": len(results)}


def search_issues(query: str = "", category: str = "", status: str = "", tool_context: ToolContext = None) -> dict:
    """Search issues; Residents are restricted to their own issues, Admins can see all."""
    state, error = _require_user(tool_context)
    if error: return error
    if category and category not in ISSUE_CATEGORIES: return {"error": f"Invalid category. Choose from: {', '.join(ISSUE_CATEGORIES)}"}
    if status and status not in ISSUE_STATUSES: return {"error": f"Invalid status. Choose from: {', '.join(ISSUE_STATUSES)}"}
    user_id = None if state.get("user_role") == "Admin" else state["user_id"]
    results = get_all_issues(category=category or None, status=status or None, search=query or None, user_id=user_id)
    return {"issues": results, "count": len(results)}


def create_issue(title: str, description: str, category: str, location: str, confirmed: bool = False, tool_context: ToolContext = None) -> dict:
    if category not in ISSUE_CATEGORIES: return {"error": f"Invalid category. Choose from: {', '.join(ISSUE_CATEGORIES)}"}
    state, error = _require_user(tool_context)
    if error: return error
    payload = {"title": title.strip(), "description": description.strip(), "category": category, "location": location.strip()}
    if not all(payload.values()): return {"error": "Title, description, category, and location are required."}
    if not confirmed: return _pending(tool_context, "Report a new community issue", payload)
    error = _confirm(tool_context, "Report a new community issue", payload)
    if error: return error
    result = db_create_issue(**payload, user_id=state["user_id"], user_name=state.get("user_name", "Unknown"), created_date=datetime.date.today().isoformat())
    return {"status": "success", "issue": result} if result else {"error": "Failed to create issue. Please try again."}


def create_recommendation(service_name: str, category: str, description: str, contact_info: str = "", confirmed: bool = False, tool_context: ToolContext = None) -> dict:
    if category not in REC_CATEGORIES: return {"error": f"Invalid category. Choose from: {', '.join(REC_CATEGORIES)}"}
    state, error = _require_user(tool_context)
    if error: return error
    payload = {"service_name": service_name.strip(), "category": category, "description": description.strip(), "contact_info": contact_info.strip()}
    if not payload["service_name"] or not payload["description"]: return {"error": "Service name and description are required."}
    if not confirmed: return _pending(tool_context, "Add a new service recommendation", payload)
    error = _confirm(tool_context, "Add a new service recommendation", payload)
    if error: return error
    result = db_create_recommendation(**payload, user_id=state["user_id"], user_name=state.get("user_name", "Unknown"), created_date=datetime.date.today().isoformat())
    return {"status": "success", "recommendation": result} if result else {"error": "Failed to create recommendation. Please try again."}


def create_contact(name: str, designation: str, category: str, phone: str = "", email: str = "", availability: str = "", confirmed: bool = False, tool_context: ToolContext = None) -> dict:
    if category not in CONTACT_CATEGORIES: return {"error": f"Invalid category. Choose from: {', '.join(CONTACT_CATEGORIES)}"}
    _, error = _require_admin(tool_context)
    if error: return error
    payload = {"name": name.strip(), "designation": designation.strip(), "category": category, "phone": phone.strip(), "email": email.strip(), "availability": availability.strip()}
    if not payload["name"] or not payload["designation"]: return {"error": "Name and designation are required."}
    if not confirmed: return _pending(tool_context, "Create a community contact", payload)
    error = _confirm(tool_context, "Create a community contact", payload)
    if error: return error
    result = db_create_contact(**payload)
    return {"status": "success", "contact": result} if result else {"error": "Failed to create contact."}


def update_contact(contact_id: int, name: str, designation: str, category: str, phone: str = "", email: str = "", availability: str = "", confirmed: bool = False, tool_context: ToolContext = None) -> dict:
    if category not in CONTACT_CATEGORIES: return {"error": f"Invalid category. Choose from: {', '.join(CONTACT_CATEGORIES)}"}
    _, error = _require_admin(tool_context)
    if error: return error
    if not get_contact_by_id(contact_id): return {"error": "Contact not found."}
    payload = {"contact_id": contact_id, "name": name.strip(), "designation": designation.strip(), "category": category, "phone": phone.strip(), "email": email.strip(), "availability": availability.strip()}
    if not payload["name"] or not payload["designation"]: return {"error": "Name and designation are required."}
    if not confirmed: return _pending(tool_context, "Update a community contact", payload)
    error = _confirm(tool_context, "Update a community contact", payload)
    if error: return error
    data = dict(payload); data.pop("contact_id")
    result = db_update_contact(contact_id, **data)
    return {"status": "success", "contact": result} if result else {"error": "Failed to update contact."}


def update_recommendation(rec_id: int, service_name: str, category: str, description: str, contact_info: str = "", confirmed: bool = False, tool_context: ToolContext = None) -> dict:
    if category not in REC_CATEGORIES: return {"error": f"Invalid category. Choose from: {', '.join(REC_CATEGORIES)}"}
    state, error = _require_admin(tool_context)
    if error: return error
    if not get_recommendation_by_id(rec_id): return {"error": "Recommendation not found."}
    payload = {"rec_id": rec_id, "service_name": service_name.strip(), "category": category, "description": description.strip(), "contact_info": contact_info.strip()}
    if not payload["service_name"] or not payload["description"]: return {"error": "Service name and description are required."}
    if not confirmed: return _pending(tool_context, "Update a community recommendation", payload)
    error = _confirm(tool_context, "Update a community recommendation", payload)
    if error: return error
    data = dict(payload); data.pop("rec_id")
    result = db_update_recommendation(rec_id, **data)
    return {"status": "success", "recommendation": result} if result else {"error": "Failed to update recommendation."}


def create_announcement(title: str, content: str, category: str = "General", status: str = "published", confirmed: bool = False, tool_context: ToolContext = None) -> dict:
    if category not in ANNOUNCEMENT_CATEGORIES or status not in ("published", "archived"): return {"error": "Invalid announcement category or status."}
    state, error = _require_admin(tool_context)
    if error: return error
    payload = {"title": title.strip(), "content": content.strip(), "category": category, "status": status}
    if not payload["title"] or not payload["content"]: return {"error": "Title and content are required."}
    if not confirmed: return _pending(tool_context, "Create an announcement", payload)
    error = _confirm(tool_context, "Create an announcement", payload)
    if error: return error
    result = db_create_announcement(**payload, user_id=state["user_id"], user_name=state.get("user_name", "Unknown"), published_date=datetime.date.today().isoformat())
    return {"status": "success", "announcement": result} if result else {"error": "Failed to create announcement."}


def update_announcement(ann_id: int, title: str, content: str, category: str = "General", status: str = "published", confirmed: bool = False, tool_context: ToolContext = None) -> dict:
    if category not in ANNOUNCEMENT_CATEGORIES or status not in ("published", "archived"): return {"error": "Invalid announcement category or status."}
    _, error = _require_admin(tool_context)
    if error: return error
    if not get_announcement_by_id(ann_id): return {"error": "Announcement not found."}
    payload = {"ann_id": ann_id, "title": title.strip(), "content": content.strip(), "category": category, "status": status}
    if not payload["title"] or not payload["content"]: return {"error": "Title and content are required."}
    if not confirmed: return _pending(tool_context, "Update an announcement", payload)
    error = _confirm(tool_context, "Update an announcement", payload)
    if error: return error
    data = dict(payload); data.pop("ann_id")
    result = db_update_announcement(ann_id, **data)
    return {"status": "success", "announcement": result} if result else {"error": "Failed to update announcement."}


def update_issue(issue_id: int, status: str, assigned_to: str = "", admin_note: str = "", confirmed: bool = False, tool_context: ToolContext = None) -> dict:
    if status not in ISSUE_STATUSES: return {"error": f"Invalid status. Choose from: {', '.join(ISSUE_STATUSES)}"}
    _, error = _require_admin(tool_context)
    if error: return error
    if not get_issue_by_id(issue_id): return {"error": "Issue not found."}
    payload = {"issue_id": issue_id, "status": status, "assigned_to": assigned_to.strip(), "admin_note": admin_note.strip()}
    if not confirmed: return _pending(tool_context, "Update an issue", payload)
    error = _confirm(tool_context, "Update an issue", payload)
    if error: return error
    result = db_update_issue(issue_id, status, assigned_to, datetime.date.today().isoformat(), admin_note)
    return {"status": "success", "issue": result} if result else {"error": "Failed to update issue."}


_SYSTEM_PROMPT = """You are the CommUnity Agent, a helpful AI agent for a residential community.

You serve both Residents and Admins in one agent. The authenticated user's role is in your tool context. Never claim an action succeeded unless the tool reports success.

READ ACTIONS: search_contacts, search_recommendations, search_announcements, get_my_issues, search_issues.
RESIDENT WRITES: create_issue, create_recommendation.
ADMIN WRITES: create_contact, update_contact, update_recommendation, create_announcement, update_announcement, update_issue.

WRITE CONSENT IS MANDATORY:
1. Always call a write tool first with confirmed=False.
2. Show the returned preview clearly and ask for explicit confirmation.
3. Only after a clear affirmative reply call the same tool again with the exact same parameters and confirmed=True.
4. Never execute a write on the first attempt or when confirmation is absent.
5. If the user changes any value, make a new preview.

ROLE RULES:
- Residents can use resident reads and resident writes only.
- Admins can use all supported tools.
- Do not expose unpublished/archived announcements to Residents.
- Do not expose reporter identity to Residents through issue results unless the data already labels it as their own.

Be concise and action-oriented. If a request is outside the supported tools, explain what you can do instead."""

community_agent = Agent(
    name="community_agent",
    model=_MODEL,
    description="CommUnity Agent for community information and authorized operations.",
    instruction=_SYSTEM_PROMPT,
    tools=[
        search_contacts, search_recommendations, search_announcements, get_my_issues, search_issues,
        create_issue, create_recommendation,
        create_contact, update_contact, update_recommendation,
        create_announcement, update_announcement, update_issue,
    ],
)
