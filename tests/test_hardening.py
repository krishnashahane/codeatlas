import asyncio
import tempfile
import unittest
import zipfile
from pathlib import Path

from fastapi import UploadFile

from app import store
from app.main import RequestBodyLimitMiddleware, RequestBodyTooLarge
from app.models.schemas import MAX_GRAPH_EDGES, MAX_GRAPH_NODES
from app.services.graph_builder import _build_knowledge_graph
from app.services.python_parser import MAX_SYMBOL_REFERENCES, parse_file
from app.services.repo_loader import cleanup_repository, _safe_relative_path, load_from_zip


class HardeningTests(unittest.TestCase):
    def test_windows_and_posix_archive_traversal_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            for name in (
                "../../outside.txt",
                "..\\..\\outside.txt",
                "C:\\Windows\\system.ini",
                "/etc/passwd",
            ):
                with self.subTest(name=name):
                    with self.assertRaises(ValueError):
                        _safe_relative_path(root, name)

    def test_cleanup_does_not_return_unowned_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            unowned = Path(tmp)
            self.assertIsNone(cleanup_repository(unowned))

    def test_invalid_zip_returns_validation_error_and_closes_upload(self):
        async def run():
            with tempfile.TemporaryDirectory() as tmp:
                invalid = Path(tmp) / "invalid.zip"
                invalid.write_bytes(b"not a ZIP archive")
                with invalid.open("rb") as fp:
                    upload = UploadFile(filename="invalid.zip", file=fp)
                    with self.assertRaisesRegex(ValueError, "valid supported ZIP"):
                        await load_from_zip(upload)
                    self.assertTrue(upload.file.closed)

        asyncio.run(run())

    def test_zip_duplicate_paths_are_rejected_and_workspace_is_cleaned(self):
        async def run():
            with tempfile.TemporaryDirectory() as tmp:
                archive = Path(tmp) / "duplicate.zip"
                with zipfile.ZipFile(archive, "w") as zf:
                    zf.writestr("repo/main.py", "print('first')")
                    zf.writestr("repo/main.py", "print('second')")

                with archive.open("rb") as fp:
                    upload = UploadFile(filename="duplicate.zip", file=fp)
                    with self.assertRaises(ValueError):
                        await load_from_zip(upload)
                    self.assertTrue(upload.file.closed)

        asyncio.run(run())

    def test_body_limiter_rejects_chunked_body_over_configured_limit(self):
        async def run():
            body = b"abcdef"
            sent = []

            async def receive():
                nonlocal body
                if body:
                    chunk, body = body, b""
                    return {"type": "http.request", "body": chunk, "more_body": False}
                return {"type": "http.disconnect"}

            async def send(message):
                sent.append(message)

            async def downstream(scope, limited_receive, send):
                await limited_receive()

            middleware = RequestBodyLimitMiddleware(downstream, max_bytes=5)
            scope = {
                "type": "http",
                "path": "/api/upload",
                "method": "POST",
                "headers": [],
            }
            with self.assertRaises(RequestBodyTooLarge):
                await middleware(scope, receive, send)

        asyncio.run(run())

    def test_knowledge_graph_nodes_and_edges_are_bounded(self):
        file_info = {
            "file": "src/module.py",
            "module": "src.module",
            "classes": [
                {
                    "name": f"Class{index}",
                    "fqn": f"src.module.Class{index}",
                    "bases": [],
                    "methods": [],
                    "decorators": [],
                }
                for index in range(MAX_GRAPH_NODES + 100)
            ],
            "functions": [],
            "variables": [],
        }
        graph = _build_knowledge_graph([file_info])
        self.assertLessEqual(len(graph.nodes), MAX_GRAPH_NODES)
        self.assertLessEqual(len(graph.edges), MAX_GRAPH_EDGES)

    def test_python_parser_caps_extracted_symbols(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "module.py"
            source.write_text(
                "\n".join(f"def function_{index}():\n    return {index}" for index in range(MAX_SYMBOL_REFERENCES + 50)),
                encoding="utf-8",
            )
            parsed = parse_file(source, root)
            self.assertLessEqual(len(parsed["functions"]), MAX_SYMBOL_REFERENCES)

    def test_session_store_enforces_byte_budget_and_recency(self):
        old_max_sessions = store.MAX_SESSIONS
        old_max_bytes = store.MAX_SESSION_BYTES
        try:
            with store._lock:
                store.sessions.clear()
                store._total_bytes = 0
            store.MAX_SESSIONS = 2
            store.MAX_SESSION_BYTES = 256

            store.save_session("first", {"value": "1"})
            store.save_session("second", {"value": "2"})
            self.assertEqual(store.get_session("first"), {"value": "1"})
            store.save_session("third", {"value": "3"})
            self.assertIsNone(store.get_session("second"))
            self.assertEqual(store.get_session("first"), {"value": "1"})
            self.assertEqual(store.get_session("third"), {"value": "3"})

            with self.assertRaises(store.SessionCapacityError):
                store.save_session("oversized", {"value": "x" * 512})
        finally:
            with store._lock:
                store.sessions.clear()
                store._total_bytes = 0
            store.MAX_SESSIONS = old_max_sessions
            store.MAX_SESSION_BYTES = old_max_bytes


if __name__ == "__main__":
    unittest.main()
