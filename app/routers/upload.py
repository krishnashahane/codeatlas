import shutil
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from app import store
from app.models.schemas import GithubUrlRequest, UploadResponse
from app.services.analyzer import analyze
from app.services.repo_loader import cleanup_repository, load_from_github, load_from_zip

router = APIRouter()


async def _analyze_repository(repo_path):
    result = await run_in_threadpool(analyze, repo_path)
    session_id = str(uuid.uuid4())
    try:
        await run_in_threadpool(store.save_session, session_id, result)
    except store.SessionCapacityError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    return UploadResponse(session_id=session_id)


@router.post("/upload", response_model=UploadResponse)
async def upload_repo(
    file: UploadFile | None = File(None),
    github_url: str | None = None,
):
    if file is None and not github_url:
        raise HTTPException(status_code=400, detail="Provide a ZIP file or github_url")
    if file is not None and github_url:
        raise HTTPException(status_code=400, detail="Provide only one repository source")

    repo_path = None
    try:
        if file is not None:
            repo_path = await load_from_zip(file)
        else:
            repo_path = await run_in_threadpool(load_from_github, github_url)
        return await _analyze_repository(repo_path)
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
            owned_root = cleanup_repository(repo_path)
            if owned_root is not None:
                shutil.rmtree(owned_root, ignore_errors=True)
        if file is not None:
            await file.close()


@router.post("/upload/github", response_model=UploadResponse)
async def upload_github(request: GithubUrlRequest):
    repo_path = None
    try:
        repo_path = await run_in_threadpool(
            load_from_github, str(request.github_url)
        )
        return await _analyze_repository(repo_path)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except TimeoutError as exc:
        raise HTTPException(status_code=408, detail=str(exc)) from exc
    except Exception:
        raise HTTPException(status_code=500, detail="GitHub repository analysis failed.")
    finally:
        if repo_path is not None:
            shutil.rmtree(cleanup_repository(repo_path), ignore_errors=True)
