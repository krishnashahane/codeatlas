import os
import re
import shutil
import stat
import subprocess
import tempfile
import zipfile
import zlib
from pathlib import Path, PurePosixPath, PureWindowsPath

from fastapi import UploadFile
from starlette.concurrency import run_in_threadpool


MAX_UPLOAD_BYTES = 50 * 1024 * 1024
MAX_EXTRACTED_BYTES = 250 * 1024 * 1024
MAX_EXTRACTED_FILES = 5000
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_GITHUB_CLONE_SECONDS = 120

GITHUB_RE = re.compile(
    r"^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?$"
)


def _safe_relative_path(root: Path, member_name: str) -> Path:
    """Resolve a ZIP path and reject POSIX and Windows traversal forms."""
    if (
        not member_name
        or "\x00" in member_name
        or "\\" in member_name
        or PurePosixPath(member_name).is_absolute()
        or PureWindowsPath(member_name).is_absolute()
        or PureWindowsPath(member_name).drive
        or ".." in PurePosixPath(member_name).parts
    ):
        raise ValueError("Archive contains an unsafe path.")

    root_resolved = root.resolve()
    candidate = (root_resolved / member_name).resolve()
    if candidate != root_resolved and root_resolved not in candidate.parents:
        raise ValueError("Archive contains an unsafe path.")
    return candidate


async def load_from_zip(upload_file: UploadFile) -> Path:
    """Stream an upload to disk, then extract it off the event loop."""
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

        return await run_in_threadpool(_extract_zip_archive, zip_path, repo_dir)
    except Exception:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise
    finally:
        await upload_file.close()


def _extract_zip_archive(zip_path: Path, repo_dir: Path) -> Path:
    tmp_dir = zip_path.parent
    try:
        with zipfile.ZipFile(zip_path, "r") as archive:
            infos = archive.infolist()
            if len(infos) > MAX_EXTRACTED_FILES:
                raise ValueError("ZIP contains too many entries.")

            total_uncompressed = sum(max(0, info.file_size) for info in infos)
            if total_uncompressed > MAX_EXTRACTED_BYTES:
                raise ValueError("ZIP expands beyond the 250 MB extraction limit.")

            repo_dir.mkdir()
            extracted = 0
            seen_paths: set[str] = set()

            for info in infos:
                target = _safe_relative_path(repo_dir, info.filename)
                relative_key = target.relative_to(repo_dir.resolve()).as_posix()
                if relative_key in seen_paths:
                    raise ValueError("ZIP contains duplicate paths.")
                seen_paths.add(relative_key)

                if info.flag_bits & 0x1:
                    raise ValueError("Encrypted ZIP entries are not supported.")

                mode = (info.external_attr >> 16) & 0o170000
                if mode not in {0, stat.S_IFREG, stat.S_IFDIR}:
                    raise ValueError("ZIP contains an unsupported special file.")

                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue

                if info.file_size > MAX_FILE_BYTES:
                    raise ValueError(
                        "ZIP contains a file larger than the 2 MB analysis limit."
                    )

                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info, "r") as source, target.open("xb") as dest:
                    while chunk := source.read(1024 * 1024):
                        extracted += len(chunk)
                        if extracted > MAX_EXTRACTED_BYTES:
                            raise ValueError("ZIP exceeds the extraction limit.")
                        dest.write(chunk)

        return _normalize_repo_root(repo_dir)
    except (zipfile.BadZipFile, EOFError, zlib.error, NotImplementedError) as exc:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise ValueError("Uploaded file is not a valid supported ZIP archive.") from exc
    except Exception:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise


def load_from_github(url: str) -> Path:
    """Clone a public GitHub repository with prompts and inherited Git config disabled."""
    clean_url = url.strip().rstrip("/")
    match = GITHUB_RE.fullmatch(clean_url)
    if not match:
        raise ValueError(
            "Only public https://github.com/OWNER/REPOSITORY URLs are supported."
        )

    owner, repo = match.groups()
    if owner in {".", ".."} or repo in {".", ".."}:
        raise ValueError("Invalid GitHub owner or repository name.")

    tmp_dir = Path(tempfile.mkdtemp(prefix="codeatlas_"))
    (tmp_dir / ".codeatlas-root").touch()
    repo_dir = tmp_dir / f"{owner}-{repo}"
    clone_url = f"https://github.com/{owner}/{repo}.git"

    env = os.environ.copy()
    env.update({
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_LFS_SKIP_SMUDGE": "1",
    })
    for key in (
        "GIT_ASKPASS", "SSH_ASKPASS", "GIT_DIR", "GIT_WORK_TREE",
        "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_CONFIG_PARAMETERS", "GIT_CONFIG_COUNT", "GIT_TRACE",
        "GIT_TRACE_PACKET", "GIT_TRACE_PERFORMANCE", "GIT_CURL_VERBOSE",
    ):
        env.pop(key, None)

    try:
        subprocess.run(
            [
                "git", "-c", "protocol.file.allow=never",
                "-c", "protocol.ext.allow=never",
                "clone", "--depth", "1", "--single-branch", "--no-tags",
                clone_url, str(repo_dir),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=MAX_GITHUB_CLONE_SECONDS,
            env=env,
        )
        return repo_dir
    except subprocess.TimeoutExpired as exc:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise TimeoutError("GitHub repository clone timed out.") from exc
    except (OSError, subprocess.CalledProcessError) as exc:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise ValueError("GitHub repository could not be cloned.") from exc
    except Exception:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise


def cleanup_repository(repo_path: Path) -> Path | None:
    """Return a temporary directory only when its ownership marker is present."""
    path = repo_path.resolve()
    for candidate in (path, *path.parents):
        if (candidate / ".codeatlas-root").is_file():
            return candidate
    return None


def _normalize_repo_root(repo_dir: Path) -> Path:
    children = [path for path in repo_dir.iterdir() if not path.is_symlink()]
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return repo_dir
