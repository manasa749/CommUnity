"""
CommUnity Agent FastAPI Router
==============================
Exposes a single /api/agent/chat endpoint that:
  1. Validates the JWT (via the existing get_current_user dependency).
  2. Creates or resumes an ADK session with the user context in state.
  3. Sends the user message to the community_agent runner.
  4. Returns the agent response text and a session_id for multi-turn use.

Security
--------
- Authentication is enforced by get_current_user before the agent runs.
- User context (id, role, name) is passed to session state; tools read it
  via ToolContext. The model never receives raw credentials.
- Write operations require confirmed=True in the tool call, which the agent
  sets only after the user explicitly confirms in the conversation.
"""

import asyncio

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from google.adk.runners import Runner
from google.genai.types import Content, Part

from agent import community_agent, session_service, _APP_NAME

# Import the auth dependency from main WITHOUT importing main (circular import
# risk); we re-use the same auth helper module instead.
from auth_utils import decode_access_token
from database import get_user_by_email
from fastapi import Header


# ---------------------------------------------------------------------------
# Auth dependency (mirrors main.py get_current_user, kept local to avoid
# circular imports when main.py includes this router)
# ---------------------------------------------------------------------------

def _get_current_user(authorization: str = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing or malformed",
        )
    token = authorization.split(" ", 1)[1]
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired or is invalid",
        )
    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    user = get_user_by_email(email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user no longer exists",
        )
    user_profile = dict(user)
    user_profile.pop("hashed_password", None)
    return user_profile


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    session_id: str = None  # Optional: pass to continue a previous conversation


class ChatResponse(BaseModel):
    response: str
    session_id: str


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/chat", response_model=ChatResponse)
async def agent_chat(
    payload: ChatRequest,
    current_user: dict = Depends(_get_current_user),
) -> ChatResponse:
    """
    Send a message to the CommUnity AI assistant.

    - Authenticated users only (JWT required).
    - Pass session_id from a previous response to continue the conversation.
    - Omit session_id to start a new conversation.
    """
    user_context = {
        "user_id":   current_user["id"],
        "user_role": current_user["role"],
        "user_name": current_user["name"],
    }
    user_id_str = str(current_user["id"])

    # --- Resolve session ---
    session_id = payload.session_id
    if session_id:
        # Try to reuse an existing session
        existing = await session_service.get_session(
            app_name=_APP_NAME,
            user_id=user_id_str,
            session_id=session_id,
        )
        if not existing:
            # Session expired or not found - start fresh
            session_id = None

    if not session_id:
        session = await session_service.create_session(
            app_name=_APP_NAME,
            user_id=user_id_str,
            state={
                "user_id":   user_context["user_id"],
                "user_role": user_context["user_role"],
                "user_name": user_context["user_name"],
            },
        )
        session_id = session.id

    # --- Run agent ---
    runner = Runner(
        agent=community_agent,
        app_name=_APP_NAME,
        session_service=session_service,
    )

    new_message = Content(role="user", parts=[Part(text=payload.message)])

    response_parts: list[str] = []
    async for event in runner.run_async(
        user_id=user_id_str,
        session_id=session_id,
        new_message=new_message,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    response_parts.append(part.text)

    response_text = "".join(response_parts) or "I am unable to respond right now. Please try again."

    return ChatResponse(response=response_text, session_id=session_id)
