from uuid import UUID

from fastapi import APIRouter, HTTPException

from app import store
from app.models.schemas import AnalysisResult


router = APIRouter()


@router.get("/analysis/{session_id}", response_model=AnalysisResult)
def get_analysis(session_id: UUID):
    result = store.get_session(str(session_id))
    if result is None:
        raise HTTPException(status_code=404, detail="Session not found or expired.")
    return result
