import os
import time
from collections import OrderedDict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from app.routers import upload, analysis

MAX_REQUEST_BYTES = 55 * 1024 * 1024
RATE_WINDOW_SECONDS = 60.0
_request_buckets: OrderedDict[str, tuple[int, float]] = OrderedDict()

app = FastAPI(
    title="CodeAtlas",
    description="Repository architecture, dependency, and knowledge graph analyzer",
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
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_REQUEST_BYTES:
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Request body exceeds the 55 MB limit."},
                )
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid Content-Length header."},
            )

    if request.url.path.startswith("/api/upload") and request.method == "POST":
        client_host = request.client.host if request.client else "unknown"
        now = time.monotonic()
        count, reset = _request_buckets.get(client_host, (0, now + RATE_WINDOW_SECONDS))
        if now >= reset:
            count, reset = 0, now + RATE_WINDOW_SECONDS
        count += 1
        _request_buckets.pop(client_host, None)
        _request_buckets[client_host] = (count, reset)
        while len(_request_buckets) > 4096:
            _request_buckets.popitem(last=False)
        try:
            max_uploads = max(1, int(os.getenv("CODEATLAS_UPLOADS_PER_MINUTE", "10")))
        except ValueError:
            max_uploads = 10
        if count > max_uploads:
            return JSONResponse(
                status_code=429,
                content={"detail": "Upload rate limit exceeded. Try again shortly."},
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
    return response


app.include_router(upload.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}
