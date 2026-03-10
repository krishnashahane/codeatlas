import tempfile
import zipfile
import subprocess
from pathlib import Path
from fastapi import UploadFile


async def load_from_zip(upload_file: UploadFile) -> Path:
    tmp_dir = Path(tempfile.mkdtemp(prefix="codeatlas_"))
    zip_path = tmp_dir / "repo.zip"

    content = await upload_file.read()
    zip_path.write_bytes(content)

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(tmp_dir / "repo")

    zip_path.unlink()

    # If the zip contained a single top-level directory, use that as root
    repo_dir = tmp_dir / "repo"
    children = list(repo_dir.iterdir())
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return repo_dir


def load_from_github(url: str) -> Path:
    tmp_dir = Path(tempfile.mkdtemp(prefix="codeatlas_"))
    repo_dir = tmp_dir / "repo"

    # Normalize URL
    clean_url = url.strip().rstrip("/")
    if not clean_url.endswith(".git"):
        clean_url += ".git"

    result = subprocess.run(
        ["git", "clone", "--depth", "1", clean_url, str(repo_dir)],
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Git clone failed: {result.stderr}")

    return repo_dir
