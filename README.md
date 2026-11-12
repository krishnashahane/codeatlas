# CodeAtlas

CodeAtlas analyzes the structure of a source repository and produces three deterministic graph views:

- **Architecture map** — directory/module relationships and heuristic layers.
- **Dependency graph** — file-to-file and external-package imports.
- **Knowledge graph** — classes, functions, variables, inheritance, definitions, and resolvable call references.

The application has a React/Vite frontend and a FastAPI backend. It accepts ZIP archives and public GitHub repository URLs. It does **not** run an LLM, embeddings service, or semantic code-understanding model; it does not execute uploaded source code.

## Requirements

- Python 3.10+
- Node.js 22.12+
- npm
- Git, when analyzing a public GitHub URL

Runtime backend dependencies are pinned in `requirements.txt`. Frontend dependencies are declared in `package.json`.

## Project structure

```text
codeatlas/
├── app/
│   ├── models/         # Pydantic request/response models and graph limits
│   ├── routers/        # FastAPI upload and analysis routes
│   ├── services/       # Repository loading, parsers, and graph generation
│   └── store.py        # Bounded, expiring in-memory analysis sessions
├── src/
│   ├── components/     # React dashboard and graph views
│   ├── utils/          # D3 helpers and safe tooltip rendering
│   ├── api.js          # Backend API client
│   └── App.jsx
├── tests/
├── requirements.txt
├── requirements-dev.txt
├── package.json
├── vite.config.js
└── README.md
```

## Run locally

### Backend

```bash
python -m venv .venv

# macOS/Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Health check: `http://127.0.0.1:8000/api/health`.

For development and tests, install the optional development tools:

```bash
python -m pip install -r requirements-dev.txt
pytest -q
ruff check app tests
```

### Frontend

```bash
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. Vite binds to loopback and proxies `/api` requests to FastAPI.

Build and test the production frontend:

```bash
npm test
npm run build
npm run preview
```

Run FastAPI separately behind a production reverse proxy. Configure the browser origin using `CODEATLAS_CORS_ORIGINS`.

## How analysis works

1. The backend accepts a ZIP archive or a public GitHub URL.
2. ZIP contents are streamed to a temporary workspace and extracted in a worker thread.
3. Archive paths, duplicate entries, symbolic links, special files, entry counts, expanded size, and individual file size are validated.
4. GitHub URLs are restricted to HTTPS repository URLs on `github.com`; Git prompts and inherited Git configuration are disabled during shallow cloning.
5. Python files are parsed with the Python AST. JavaScript/TypeScript extraction is heuristic and regex-based.
6. Parsed information is converted into architecture, dependency, and knowledge graphs.
7. Results are stored temporarily in a bounded process-local session store.

CPU- and blocking-I/O-heavy work is dispatched to the worker thread pool so upload requests do not synchronously block the ASGI event loop.

## Resource limits

| Limit | Value |
| --- | ---: |
| HTTP upload request body | 55 MB |
| ZIP archive | 50 MB |
| ZIP entries | 5,000 |
| Expanded ZIP size | 250 MB |
| Individual extracted file | 2 MB |
| Total analyzed source | 50 MB |
| Individual analyzed source file | 2 MB |
| Analyzed files | 5,000 |
| Analyzed path depth | 30 |
| Repository entries walked | 25,000 |
| Python AST nodes per file | 100,000 |
| Extracted symbols/references per file | 500 |
| Nodes per graph | 5,000 |
| Edges per graph | 10,000 |
| GitHub clone timeout | 120 seconds |
| Sessions retained per process | 32 |
| Maximum size per session | 16 MB |
| Aggregate session cache | 64 MB |
| Session lifetime | 1 hour |
| Upload requests per IP per minute | 10 by default |

Analysis reports indicate when source or graph processing was truncated by a configured limit.

## Security and privacy

- ZIP paths are validated before extraction; traversal, duplicate paths, symlinks, encrypted entries, and special files are rejected.
- Repository walking is iterative and never follows symlinks.
- GitHub input accepts only public HTTPS GitHub repository URLs. Private repository credentials and authenticated cloning are intentionally unsupported.
- Git prompts and inherited user/system Git configuration are disabled for automated clones.
- Request bodies are bounded even when the client omits `Content-Length`.
- Upload routes are rate-limited per client IP within each application process.
- Parser, graph, response, and session-store sizes are bounded.
- Session identifiers are UUIDs; sessions expire and are evicted under memory pressure.
- Repository-controlled tooltip content is HTML-escaped before rendering.
- DOM labels are rendered as text, not HTML.
- API responses use defensive security headers and errors avoid exposing raw exception details.
- CORS is restricted to explicit origins. Do not configure wildcard origins in production.
- Temporary repositories are cleaned up only when a CodeAtlas ownership marker is present, preventing cleanup from deleting arbitrary paths.
- Invalid ZIP archives are rejected with a client error; GitHub URL fields have a bounded input length.

The in-memory session store and per-process rate limiter are intended for a single-instance deployment. Multi-worker or multi-instance deployments should use shared persistence and distributed rate limiting.

## API

```text
GET  /api/health
POST /api/upload
POST /api/upload/github
GET  /api/analysis/{session_id}
```

### ZIP upload

```bash
curl -X POST -F "file=@repository.zip" http://127.0.0.1:8000/api/upload
```

### GitHub repository

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"github_url":"https://github.com/OWNER/REPOSITORY"}' \
  http://127.0.0.1:8000/api/upload/github
```

Both endpoints return a `session_id`:

```bash
curl http://127.0.0.1:8000/api/analysis/SESSION_ID
```

## Limitations

- JavaScript/TypeScript parsing is heuristic and regex-based; it is not a full ECMAScript or TypeScript AST parser.
- Import resolution is intentionally conservative.
- Knowledge-graph call edges are only resolved when symbol names can be matched.
- The session store and upload rate limiter are process-local. Horizontal scaling requires shared state and distributed limits.
- Only public GitHub repositories are supported.

## License

MIT. See [LICENSE](LICENSE).
