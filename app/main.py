import os
import time
from collections import OrderedDict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from app.routers import analysis, upload


MAX_REQUEST_BYTES = 55 * 1024 * 1024
RATE_WINDOW_SECONDS = 60.0


def _positive_int_env(name: str, default: int, *, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default
    return min(maximum, max(1, value))


MAX_UPLOADS_PER_MINUTE = _positive_int_env(
    "CODEATLAS_UPLOADS_PER_MINUTE", 10, maximum=1000
)
_request_buckets: OrderedDict[str, tuple[int, float]] = OrderedDict()


class RequestBodyTooLarge(Exception):
    """Raised when an upload exceeds the configured byte limit."""


class RequestBodyLimitMiddleware:
    """Enforce a request-body limit even when Content-Length is absent."""

    def __init__(self, app, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http" or scope.get("path") not in {
            "/api/upload",
            "/api/upload/github",
        }:
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        raw_length = headers.get(b"content-length")
        if raw_length is not None:
            try:
                content_length = int(raw_length)
            except (TypeError, ValueError):
                response = JSONResponse(
                    status_code=400,
                    content={"detail": "Invalid Content-Length header."},
                )
                await response(scope, receive, send)
                return
            if content_length < 0:
                response = JSONResponse(
                    status_code=400,
                    content={"detail": "Invalid Content-Length header."},
                )
                await response(scope, receive, send)
                return
            if content_length > self.max_bytes:
                response = JSONResponse(
                    status_code=413,
                    content={"detail": "Request body exceeds the 55 MB limit."},
                )
                await response(scope, receive, send)
                return

        received = 0

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise RequestBodyTooLarge()
            return message

        await self.app(scope, limited_receive, send)


app = FastAPI(
    title="CodeAtlas",
    description="Repository architecture, dependency, and knowledge graph analyzer",
)

app.add_middleware(RequestBodyLimitMiddleware, max_bytes=MAX_REQUEST_BYTES)


@app.exception_handler(RequestBodyTooLarge)
async def request_body_too_large(_request: Request, _exc: RequestBodyTooLarge):
    return JSONResponse(
        status_code=413,
        content={"detail": "Request body exceeds the 55 MB limit."},
    )


allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CODEATLAS_CORS_ORIGINS",
        "http://localhost:5173,http://localhost:3000",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def request_guards(request: Request, call_next):
    if request.url.path.startswith("/api/upload") and request.method == "POST":
        client_host = request.client.host if request.client else "unknown"
        now = time.monotonic()
        count, reset = _request_buckets.get(
            client_host, (0, now + RATE_WINDOW_SECONDS)
        )
        if now >= reset:
            count, reset = 0, now + RATE_WINDOW_SECONDS
        count += 1
        _request_buckets.pop(client_host, None)
        _request_buckets[client_host] = (count, reset)
        while len(_request_buckets) > 4096:
            _request_buckets.popitem(last=False)

        if count > MAX_UPLOADS_PER_MINUTE:
            return JSONResponse(
                status_code=429,
                content={"detail": "Upload rate limit exceeded. Try again shortly."},
                headers={"Retry-After": str(max(1, int(reset - now)))},
            )

    return await call_next(request)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Permissions-Policy",
        "camera=(), microphone=(), geolocation=()",
    )
    response.headers.setdefault("Cache-Control", "no-store")
    return response


app.include_router(upload.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}
