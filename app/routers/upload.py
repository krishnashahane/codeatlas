import shutil
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile

from app import store
from app.models.schemas import GithubUrlRequest, UploadResponse
from app.services.analyzer import analyze
from app.services.repo_loader import cleanup_repository, load_from_github, load_from_zip

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_repo(
    file: UploadFile | None = File(None),
    github_url: str | None = None,
):
    if file is None and not github_url:
        raise HTTPException(status_code=400, detail="Provide a zip file or github_url")

    session_id = str(uuid.uuid4())
    repo_path = None
    try:
        if file and file.filename:
            repo_path = await load_from_zip(file)
        elif github_url:
            repo_path = load_from_github(github_url)

        result = analyze(repo_path)
        store.save_session(session_id, result)
        return UploadResponse(session_id=session_id)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except TimeoutError as exc:
        raise HTTPException(status_code=408, detail=str(exc)) from exc
    except Exception:
        raise HTTPException(status_code=500, detail="Repository analysis failed.")
    finally:
        if repo_path is not None:
            shutil.rmtree(cleanup_repository(repo_path), ignore_errors=True)


@router.post("/upload/github", response_model=UploadResponse)
async def upload_github(request: GithubUrlRequest):
    session_id = str(uuid.uuid4())
    repo_path = None
    try:
        repo_path = load_from_github(str(request.github_url))
        result = analyze(repo_path)
        store.save_session(session_id, result)
        return UploadResponse(session_id=session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except TimeoutError as exc:
        raise HTTPException(status_code=408, detail=str(exc)) from exc
    except Exception:
        raise HTTPException(status_code=500, detail="GitHub repository analysis failed.")
    finally:
        if repo_path is not None:
            shutil.rmtree(cleanup_repository(repo_path), ignore_errors=True)
