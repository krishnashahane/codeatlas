import os
import re
import shutil
import stat
import subprocess
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import urlparse

from fastapi import UploadFile

MAX_UPLOAD_BYTES = 50 * 1024 * 1024
MAX_EXTRACTED_BYTES = 250 * 1024 * 1024
MAX_EXTRACTED_FILES = 5000
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_GITHUB_CLONE_SECONDS = 120

GITHUB_RE = re.compile(r"^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?$")


def _safe_relative_path(root: Path, member_name: str) -> Path:
    candidate = (root / member_name).resolve()
    root_resolved = root.resolve()
    if candidate != root_resolved and root_resolved not in candidate.parents:
        raise ValueError("Archive contains an unsafe path.")
    return candidate


async def load_from_zip(upload_file: UploadFile) -> Path:
    tmp_dir = Path(tempfile.mkdtemp(prefix="codeatlas_"))
    zip_path = tmp_dir / "repo.zip"
    repo_dir = tmp_dir / "repo"
    (tmp_dir / ".codeatlas-root").touch()

    try:
        size = 0
        with zip_path.open("wb") as out:
            while chunk := await upload_file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise ValueError("ZIP exceeds the 50 MB upload limit.")
                out.write(chunk)

        with zipfile.ZipFile(zip_path, "r") as zf:
            infos = zf.infolist()
            if len(infos) > MAX_EXTRACTED_FILES:
                raise ValueError("ZIP contains too many files.")

            total_uncompressed = sum(max(0, info.file_size) for info in infos)
            if total_uncompressed > MAX_EXTRACTED_BYTES:
                raise ValueError("ZIP expands beyond the 250 MB extraction limit.")

            repo_dir.mkdir()
            extracted = 0
            for info in infos:
                target = _safe_relative_path(repo_dir, info.filename)
                mode = (info.external_attr >> 16) & 0o170000
                if mode == stat.S_IFLNK:
                    raise ValueError("ZIP contains an unsupported symbolic link.")
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue

                if info.file_size > MAX_FILE_BYTES:
                    raise ValueError("ZIP contains a file larger than the 2 MB analysis limit.")

                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info, "r") as source, target.open("wb") as dest:
                    while chunk := source.read(1024 * 1024):
                        extracted += len(chunk)
                        if extracted > MAX_EXTRACTED_BYTES:
                            raise ValueError("ZIP exceeds the extraction limit.")
                        dest.write(chunk)

        return _normalize_repo_root(repo_dir)
    except Exception:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise
    finally:
        await upload_file.close()


def load_from_github(url: str) -> Path:
    clean_url = url.strip().rstrip("/")
    match = GITHUB_RE.fullmatch(clean_url)
    if not match:
        raise ValueError("Only public https://github.com/OWNER/REPOSITORY URLs are supported.")

    owner, repo = match.groups()
    repo_dir_name = f"{owner}-{repo}"
    tmp_dir = Path(tempfile.mkdtemp(prefix="codeatlas_"))
    (tmp_dir / ".codeatlas-root").touch()
    repo_dir = tmp_dir / repo_dir_name
    clone_url = f"https://github.com/{owner}/{repo}.git"

    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env.pop("GIT_ASKPASS", None)

    try:
        result = subprocess.run(
            [
                "git", "clone",
                "--depth", "1",
                "--single-branch",
                "--no-tags",
                clone_url,
                str(repo_dir),
            ],
            capture_output=True,
            text=True,
            timeout=MAX_GITHUB_CLONE_SECONDS,
            env=env,
        )
        if result.returncode != 0:
            raise ValueError("GitHub repository could not be cloned.")
        return repo_dir
    except Exception:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise


def cleanup_repository(repo_path: Path) -> Path:
    path = repo_path.resolve()
    for candidate in (path, *path.parents):
        if (candidate / ".codeatlas-root").is_file():
            return candidate
    return path


def _normalize_repo_root(repo_dir: Path) -> Path:
    children = [p for p in repo_dir.iterdir() if not p.is_symlink()]
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return repo_dir
