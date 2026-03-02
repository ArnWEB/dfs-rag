"""Sessions API router."""
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import Any, List

from api.services.sessions_db import sessions_db
from api.dependencies.auth import get_current_user, User

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

class CreateSessionRequest(BaseModel):
    name: str
    dfs_path: str = ""

class UpdateSessionRequest(BaseModel):
    status: str | None = None
    dfs_path: str | None = None
    name: str | None = None

@router.get("", response_model=List[dict[str, Any]])
async def list_sessions(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user)
):
    try:
        return sessions_db.list_sessions(user_id=current_user.id, limit=limit, offset=offset)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("")
async def create_session(request: CreateSessionRequest, current_user: User = Depends(get_current_user)):
    try:
        session = sessions_db.create_session(name=request.name, user_id=current_user.id, dfs_path=request.dfs_path)
        return session
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{session_id}")
async def get_session(session_id: str, current_user: User = Depends(get_current_user)):
    try:
        session = sessions_db.get_session(session_id, user_id=current_user.id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{session_id}")
async def update_session(session_id: str, request: UpdateSessionRequest, current_user: User = Depends(get_current_user)):
    try:
        # First verify the user owns this session or it's public
        session = sessions_db.get_session(session_id, user_id=current_user.id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found or forbidden")
            
        updates = {k: v for k, v in request.model_dump().items() if v is not None}
        session = sessions_db.update_session(session_id, updates)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
