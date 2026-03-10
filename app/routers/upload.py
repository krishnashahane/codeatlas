import uuid
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

from app.models.schemas import UploadResponse, GithubUrlRequest
from app.services.repo_loader import load_from_zip, load_from_github
from app.services.analyzer import analyze
from app import store

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_repo(file: UploadFile | None = File(None), github_url: str | None = None):
    session_id = str(uuid.uuid4())

    try:
        if file and file.filename:
            repo_path = await load_from_zip(file)
        elif github_url:
            repo_path = load_from_github(github_url)
        else:
            raise HTTPException(status_code=400, detail="Provide a zip file or github_url")

        result = analyze(repo_path)
        store.sessions[session_id] = result

        # Clean up temp directory
        shutil.rmtree(repo_path, ignore_errors=True)

        return UploadResponse(session_id=session_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload/github", response_model=UploadResponse)
async def upload_github(request: GithubUrlRequest):
    session_id = str(uuid.uuid4())
    try:
        repo_path = load_from_github(request.github_url)
        result = analyze(repo_path)
        store.sessions[session_id] = result
        shutil.rmtree(repo_path, ignore_errors=True)
        return UploadResponse(session_id=session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
