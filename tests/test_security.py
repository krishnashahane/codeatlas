import asyncio
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

from fastapi import UploadFile

from app import store
from app.services.repo_loader import (
    MAX_EXTRACTED_BYTES,
    MAX_EXTRACTED_FILES,
    _safe_relative_path,
    load_from_github,
    load_from_zip,
)


class SecurityTests(unittest.TestCase):
    def test_archive_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            for name in (
                "../../outside.txt",
                "..\\..\\outside.txt",
                "C:\\tmp\\outside.txt",
            ):
                with self.subTest(name=name):
                    with self.assertRaises(ValueError):
                        _safe_relative_path(root, name)

    def test_github_url_must_be_public_github_https(self):
        for url in (
            "http://github.com/octocat/Hello-World",
            "https://example.com/repo",
            "https://github.com/user/repo/issues/1",
            "https://github.com/user/repo?x=1",
            "https://github.com/../repo",
            "https://github.com/user/..",
        ):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    load_from_github(url)

    def test_zip_limits_are_defined(self):
        self.assertLessEqual(MAX_EXTRACTED_FILES, 5000)
        self.assertLessEqual(MAX_EXTRACTED_BYTES, 250 * 1024 * 1024)

    def test_zip_upload_extracts_and_closes(self):
        async def run():
            with tempfile.TemporaryDirectory() as tmp:
                archive = Path(tmp) / "repo.zip"
                with zipfile.ZipFile(archive, "w") as zf:
                    zf.writestr("project/main.py", "print('ok')")

                with archive.open("rb") as fp:
                    upload = UploadFile(filename="repo.zip", file=fp)
                    repo_path = await load_from_zip(upload)
                    try:
                        self.assertTrue((repo_path / "main.py").is_file())
                    finally:
                        shutil.rmtree(store_path(repo_path), ignore_errors=True)

        asyncio.run(run())

    def test_session_store_is_bounded_and_expiring(self):
        with store._lock:
            original = dict(store.sessions)
            original_total = store._total_bytes
            store.sessions.clear()
            store._total_bytes = 0
        try:
            store.save_session("a", {"ok": True})
            self.assertEqual(store.get_session("a"), {"ok": True})
            with store._lock:
                store.sessions["expired"] = {
                    "created_at": 0,
                    "result": {"old": True},
                    "size": 0,
                }
            self.assertIsNone(store.get_session("expired"))
        finally:
            with store._lock:
                store.sessions.clear()
                store.sessions.update(original)
                store._total_bytes = original_total


def store_path(repo_path: Path) -> Path:
    path = repo_path.resolve()
    for candidate in (path, *path.parents):
        if (candidate / ".codeatlas-root").is_file():
            return candidate
    return path


if __name__ == "__main__":
    unittest.main()
