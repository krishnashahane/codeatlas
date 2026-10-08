from fastapi import APIRouter, HTTPException
from app.models.schemas import AnalysisResult
from app import store

router = APIRouter()


@router.get("/analysis/{session_id}", response_model=AnalysisResult)
def get_analysis(session_id: str):
    result = store.get_session(session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return result
