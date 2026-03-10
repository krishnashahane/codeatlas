from fastapi import APIRouter, HTTPException
from app.models.schemas import AnalysisResult
from app import store

router = APIRouter()


@router.get("/analysis/{session_id}", response_model=AnalysisResult)
def get_analysis(session_id: str):
    if session_id not in store.sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return store.sessions[session_id]
