# CodeAtlas

CodeAtlas is a repository-structure analyzer with a React/Vite frontend and FastAPI backend.

You can upload a ZIP repository or analyze a public GitHub repository URL. CodeAtlas parses Python and JavaScript/TypeScript source and produces three deterministic graph views:

- **Architecture map** — directory/module relationships and heuristic layers.
- **Dependency graph** — file-to-file and external-package imports.
- **Knowledge graph** — classes, functions, variables, inheritance, definitions, and call references that can be resolved from the parsed source.

This repository does **not** currently run an LLM, embeddings service, or semantic code-understanding model. The analysis is static and deterministic.

## Requirements

- Python 3.10+
- Node.js 20.19+
- npm
- Git, when analyzing a GitHub URL

The backend pins FastAPI `0.143.0`, Uvicorn `0.54.0`, and python-multipart `0.0.27`. The multipart package is pinned to `0.0.27` because versions below that release have a published multipart-header denial-of-service vulnerability. citeturn616743search12

The frontend uses React `19.3.0`, Vite `8.1.0`, `@vitejs/plugin-react` `6.1.2`, and D3 `7.9.0`. Vite has had multiple development-server file-disclosure/security advisories across older branches, so the project uses the current Vite 8 line. citeturn616743search0turn809934search0turn984890search2

## Project structure

```text
codeatlas/
├── app/
│   ├── models/         # Pydantic request/response models
│   ├── routers/        # FastAPI HTTP routes
│   ├── services/       # Repository loading, parsing, graph generation
│   └── store.py        # Bounded in-memory analysis sessions
├── src/
│   ├── components/     # React dashboard and graph views
│   ├── api.js          # Backend API client
│   └── App.jsx
├── package.json
├── requirements.txt
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
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health check:

`http://127.0.0.1:8000/api/health`

### Frontend

```bash
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.

Vite is explicitly bound to loopback and proxies `/api` requests to FastAPI.

### Production frontend

```bash
npm run build
npm run preview
```

Run FastAPI separately behind your reverse proxy.

## How analysis works

1. A ZIP or public GitHub URL is accepted.
2. The backend creates a temporary workspace.
3. ZIP entries are checked for path traversal, symlinks, file-count limits, extracted-size limits, and per-file limits.
4. Public GitHub URLs are restricted to `https://github.com/OWNER/REPOSITORY` and cloned with shallow history.
5. Python files are parsed with the Python AST.
6. JavaScript/TypeScript files are analyzed with deterministic regex-based extraction.
7. Parsed file information is converted into architecture, dependency, and knowledge graphs.
8. The result is stored temporarily in a bounded in-memory session and returned through the analysis endpoint.

## Resource limits

| Limit | Value |
| --- | ---: |
| Uploaded ZIP | 50 MB |
| ZIP entries | 5,000 |
| Expanded ZIP size | 250 MB |
| Individual analyzed source file | 2 MB |
| Total analyzed source | 50 MB |
| GitHub clone timeout | 120 seconds |
| Stored analysis sessions | 256 |
| Session lifetime | 1 hour |

Large or unusual repositories may be reported as truncated rather than being analyzed without bounds.

## Security controls

- ZIP path traversal is rejected before extraction.
- Archive symlinks are rejected.
- Repository analysis ignores symlinked paths.
- GitHub cloning accepts only HTTPS GitHub repository URLs.
- Git prompts are disabled during automated cloning.
- Temporary repositories are cleaned up after successful or failed analysis.
- API errors no longer expose raw exception strings.
- CORS is restricted to explicit local development origins.
- Security response headers are applied by FastAPI.
- Analysis sessions expire and are bounded to prevent unbounded memory growth.
- Vite dev/preview servers bind to `127.0.0.1` rather than all interfaces.
- Generated Python bytecode and frontend build artifacts are excluded from Git.

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
curl -X POST -H "Content-Type: application/json" -d '{"github_url":"https://github.com/OWNER/REPOSITORY"}' http://127.0.0.1:8000/api/upload/github
```

Both endpoints return a `session_id`.

```bash
curl http://127.0.0.1:8000/api/analysis/SESSION_ID
```

## Limitations

- JavaScript/TypeScript parsing is heuristic and regex-based; it is not a full ECMAScript/TypeScript AST parser.
- Import resolution is intentionally conservative.
- Knowledge-graph call edges are only resolved when symbol names can be matched.
- The in-memory session store is process-local and intended for single-instance use. Multi-worker or multi-instance deployments should use shared persistence and distributed rate limiting.
- Public GitHub repositories only. Private repositories and authenticated GitHub access are intentionally unsupported.

## License

MIT
