import asyncio
import tempfile
import unittest
import zipfile
from pathlib import Path

from fastapi import UploadFile

from app.services.repo_loader import (
    MAX_EXTRACTED_BYTES,
    MAX_EXTRACTED_FILES,
    _safe_relative_path,
    load_from_github,
    load_from_zip,
)
from app import store


class SecurityTests(unittest.TestCase):
    def test_archive_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            with self.assertRaises(ValueError):
                _safe_relative_path(root, "../../outside.txt")

    def test_github_url_must_be_public_github_https(self):
        for url in (
            "http://github.com/octocat/Hello-World",
            "https://example.com/repo",
            "https://github.com/user/repo/issues/1",
            "https://github.com/user/repo?x=1",
        ):
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
                        store_path = repo_path
                        while store_path.parent != store_path and not (store_path / ".codeatlas-root").exists():
                            store_path = store_path.parent
                        import shutil
                        shutil.rmtree(store_path, ignore_errors=True)

        asyncio.run(run())

    def test_session_store_is_bounded_and_expiring(self):
        original = dict(store.sessions)
        try:
            store.sessions.clear()
            store.save_session("a", {"ok": True})
            self.assertEqual(store.get_session("a"), {"ok": True})
            store.sessions["expired"] = {"created_at": 0, "result": {"old": True}}
            self.assertIsNone(store.get_session("expired"))
        finally:
            store.sessions.clear()
            store.sessions.update(original)


if __name__ == "__main__":
    unittest.main()
