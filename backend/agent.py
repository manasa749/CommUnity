"""
CommUnity ADK Agent
===================
Single agent serving both Resident and Admin users.

Architecture
------------
- Tools call existing database.py functions directly (same Python process).
- FastAPI JWT validation happens BEFORE the agent is invoked; the agent
  never sees credentials or raw DB connections.
- User context (id, role, name) is stored in ADK session state at creation
  time and injected into tools automatically via ToolContext.
- Write tools use a confirmed=False guard:
    1. First call (confirmed=False) -> returns a human-readable preview.
    2. Agent presents preview and asks user for explicit confirmation.
    3. Second call (confirmed=True) -> executes the write action.
- Admin-only operations are enforced by the existing database/FastAPI layer.

Environment variables required
-------------------------------
  GOOGLE_API_KEY                  Gemini API key (AI Studio / local dev)
  -- OR --
  GOOGLE_GENAI_USE_VERTEXAI=true  Use Vertex AI (relies on ADC)
  GOOGLE_CLOUD_PROJECT            GCP project id (Vertex AI mode only)
"""

import datetime

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import ToolContext

from database import (
    get_all_contacts,
    get_all_recommendations,
    get_all_announcements,
    get_all_issues,
    create_issue          as db_create_issue,
    create_recommendation as db_create_recommendation,
)

# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

_MODEL = "gemini-2.0-flash"

# ---------------------------------------------------------------------------
# READ tools  (no confirmation required)
# ---------------------------------------------------------------------------

def search_contacts(
    query: str = "",
    category: str = "",
    tool_context: ToolContext = None,
) -> dict:
    """
    Search community contacts (security, maintenance, management, emergency).

    Args:
        query: Optional name or designation keyword to filter by.
        category: Optional category - one of Management, Maintenance,
                  Security, Emergency, Other. Leave empty for all.

    Returns a list of matching contacts.
    """
    results = get_all_contacts(
        category=category if category else None,
        search=query    if query    else None,
    )
    return {"contacts": results, "count": len(results)}


def search_recommendations(
    query: str = "",
    category: str = "",
    tool_context: ToolContext = None,
) -> dict:
    """
    Search resident service recommendations.

    Args:
        query: Optional keyword to search in service name or description.
        category: Optional category - one of Broadband, Plumber, Electrician,
                  AC Service, Appliance Repair, Cleaning, Tutor, Healthcare,
                  Laundry, Other. Leave empty for all.

    Returns a list of matching recommendations sorted by vote count.
    """
    results = get_all_recommendations(
        category=category if category else None,
        search=query    if query    else None,
    )
    return {"recommendations": results, "count": len(results)}


def search_announcements(tool_context: ToolContext = None) -> dict:
    """
    Get community announcements.
    Admins see all statuses; Residents see published announcements only.

    Returns a list of announcements ordered by date descending.
    """
    user_role = "Resident"
    if tool_context:
        user_role = tool_context.state.get("user_role", "Resident")

    status_filter = None if user_role == "Admin" else "published"
    results = get_all_announcements(status_filter=status_filter)
    return {"announcements": results, "count": len(results)}


def get_my_issues(tool_context: ToolContext = None) -> dict:
    """
    Get community issues reported by the currently authenticated user.

    Returns a list of the user own issues ordered by date descending.
    """
    user_id = None
    if tool_context:
        user_id = tool_context.state.get("user_id")

    if not user_id:
        return {"error": "User context not available - please re-authenticate."}

    results = get_all_issues(user_id=user_id)
    return {"issues": results, "count": len(results)}


# ---------------------------------------------------------------------------
# WRITE tools  (confirmed=False returns preview; confirmed=True executes)
# ---------------------------------------------------------------------------

def create_issue(
    title: str,
    description: str,
    category: str,
    location: str,
    confirmed: bool = False,
    tool_context: ToolContext = None,
) -> dict:
    """
    Report a new community issue.

    Args:
        title: Short title for the issue.
        description: Detailed description of the problem.
        category: Must be one of: Water, Lift, Parking, Security,
                  Housekeeping, Electrical, Other.
        location: Where in the community the issue is located.
        confirmed: Set to True ONLY after the user has explicitly confirmed.
                   Always call with False first to return a preview.

    Returns a preview dict (confirmed=False) or the created issue (confirmed=True).
    """
    _VALID = ["Water", "Lift", "Parking", "Security", "Housekeeping", "Electrical", "Other"]
    if category not in _VALID:
        return {"error": f"Invalid category '{category}'. Choose from: {', '.join(_VALID)}"}

    if not confirmed:
        # Preview -- agent MUST show this to the user and ask before re-calling with confirmed=True
        return {
            "status": "pending_confirmation",
            "preview": {
                "action": "Report a new community issue",
                "title": title,
                "category": category,
                "location": location,
                "description": description,
            },
            "instruction": (
                "Present this preview to the user and ask for explicit confirmation "
                "before calling this tool again with confirmed=True."
            ),
        }

    # confirmed=True - execute the write
    user_id   = tool_context.state.get("user_id")             if tool_context else None
    user_name = tool_context.state.get("user_name", "Unknown") if tool_context else "Unknown"

    if not user_id:
        return {"error": "User context not available - please re-authenticate."}

    result = db_create_issue(
        title=title,
        description=description,
        category=category,
        location=location,
        user_id=user_id,
        user_name=user_name,
        created_date=datetime.date.today().isoformat(),
    )
    if result:
        return {"status": "success", "issue": result}
    return {"error": "Failed to create issue. Please try again."}


def create_recommendation(
    service_name: str,
    category: str,
    description: str,
    contact_info: str = "",
    confirmed: bool = False,
    tool_context: ToolContext = None,
) -> dict:
    """
    Add a new service recommendation for the community.

    Args:
        service_name: Name of the service or provider.
        category: Must be one of: Broadband, Plumber, Electrician, AC Service,
                  Appliance Repair, Cleaning, Tutor, Healthcare, Laundry, Other.
        description: Why you recommend this service.
        contact_info: Optional phone number or contact details.
        confirmed: Set to True ONLY after the user has explicitly confirmed.
                   Always call with False first to return a preview.

    Returns a preview dict (confirmed=False) or the created record (confirmed=True).
    """
    _VALID = [
        "Broadband", "Plumber", "Electrician", "AC Service",
        "Appliance Repair", "Cleaning", "Tutor", "Healthcare", "Laundry", "Other",
    ]
    if category not in _VALID:
        return {"error": f"Invalid category '{category}'. Choose from: {', '.join(_VALID)}"}

    if not confirmed:
        return {
            "status": "pending_confirmation",
            "preview": {
                "action": "Add a new service recommendation",
                "service_name": service_name,
                "category": category,
                "description": description,
                "contact_info": contact_info or "(not provided)",
            },
            "instruction": (
                "Present this preview to the user and ask for explicit confirmation "
                "before calling this tool again with confirmed=True."
            ),
        }

    user_id   = tool_context.state.get("user_id")             if tool_context else None
    user_name = tool_context.state.get("user_name", "Unknown") if tool_context else "Unknown"

    if not user_id:
        return {"error": "User context not available - please re-authenticate."}

    result = db_create_recommendation(
        service_name=service_name,
        category=category,
        description=description,
        contact_info=contact_info,
        user_id=user_id,
        user_name=user_name,
        created_date=datetime.date.today().isoformat(),
    )
    if result:
        return {"status": "success", "recommendation": result}
    return {"error": "Failed to create recommendation. Please try again."}


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "You are the CommUnity Assistant - a helpful AI for residents and administrators "
    "of a residential community.\n\n"
    "You can help with:\n"
    "  * Finding community contacts (security, maintenance, management, emergency)\n"
    "  * Searching service recommendations from fellow residents\n"
    "  * Viewing community announcements\n"
    "  * Listing issues the user has previously reported\n"
    "  * Reporting a new community issue\n"
    "  * Adding a new service recommendation\n\n"
    "RULES - follow these strictly:\n\n"
    "1. WRITE CONFIRMATION (mandatory for every write action):\n"
    "   a. When you intend to create an issue or recommendation, FIRST call\n"
    "      the tool with confirmed=False. This returns a structured preview.\n"
    "   b. Present the preview clearly to the user (title, category, location,\n"
    "      description, etc.).\n"
    "   c. Ask the user explicitly: 'Shall I go ahead? (yes / no)'\n"
    "   d. ONLY if the user confirms (yes, sure, go ahead, confirm, ok, etc.)\n"
    "      call the tool again with the same parameters plus confirmed=True.\n"
    "   e. If the user declines, do NOT call the tool with confirmed=True.\n"
    "   f. NEVER call a write tool with confirmed=True on the very first attempt.\n\n"
    "2. READ operations (search_contacts, search_recommendations,\n"
    "   search_announcements, get_my_issues) do NOT require confirmation.\n\n"
    "3. The same agent serves both Residents and Admins. The backend controls\n"
    "   what each role can actually do - you do not need to enforce roles.\n\n"
    "4. Be concise, friendly, and community-focused.\n"
    "5. Format lists neatly; highlight name, phone, vote count, or status.\n"
    "6. If asked about something outside your tools, politely explain what\n"
    "   you can help with.\n"
)

# ---------------------------------------------------------------------------
# Agent definition
# ---------------------------------------------------------------------------

community_agent = Agent(
    name="community_agent",
    model=_MODEL,
    description=(
        "CommUnity Assistant - helps residents and admins with community "
        "information, issue reporting, and service recommendations."
    ),
    instruction=_SYSTEM_PROMPT,
    tools=[
        search_contacts,
        search_recommendations,
        search_announcements,
        get_my_issues,
        create_issue,
        create_recommendation,
    ],
)

# ---------------------------------------------------------------------------
# Session service  (in-memory; one per process lifetime)
# ---------------------------------------------------------------------------

session_service = InMemorySessionService()

_APP_NAME = "community_agent"
