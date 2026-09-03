"""FastAPI router for the authenticated CommUnity Agent."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from google.adk.runners import Runner
from google.genai.types import Content, Part
from agent import community_agent, session_service, _APP_NAME
from auth_utils import decode_access_token
from database import get_user_by_email
from fastapi import Header


def get_current_user_for_agent(authorization: str = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication token is missing or malformed")
    token = authorization.split(" ", 1)[1].strip()
    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired or is invalid")
    user = get_user_by_email(payload["sub"])
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authenticated user no longer exists")
    profile = dict(user); profile.pop("hashed_password", None)
    return profile


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: str | None = Field(default=None, max_length=200)


class ChatResponse(BaseModel):
    response: str
    session_id: str


router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/chat", response_model=ChatResponse)
async def agent_chat(payload: ChatRequest, current_user: dict = Depends(get_current_user_for_agent)) -> ChatResponse:
    user_id = str(current_user["id"])
    session_id = payload.session_id
    if session_id:
        existing = await session_service.get_session(app_name=_APP_NAME, user_id=user_id, session_id=session_id)
        if not existing:
            session_id = None
    if not session_id:
        session = await session_service.create_session(
            app_name=_APP_NAME, user_id=user_id,
            state={"user_id": current_user["id"], "user_role": current_user["role"], "user_name": current_user["name"]}
        )
        session_id = session.id
    runner = Runner(agent=community_agent, app_name=_APP_NAME, session_service=session_service)
    msg = Content(role="user", parts=[Part(text=payload.message.strip())])
    parts = []
    try:
        async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=msg):
            if event.is_final_response() and event.content and event.content.parts:
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        parts.append(part.text)
    except Exception as exc:
        # Do not leak provider internals/secrets to the browser.
        raise HTTPException(status_code=502, detail="The CommUnity Agent is temporarily unavailable. Please try again.") from exc
    return ChatResponse(response="".join(parts) or "I could not generate a response. Please try again.", session_id=session_id)
