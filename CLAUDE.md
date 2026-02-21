# CLAUDE.md — Lucid v0.2

## Project Overview

Lucid transforms rough drafts into polished social media carousels (4:5 aspect ratio, 1080x1350px) for Instagram and similar platforms. It is a containerized monorepo with a Python/FastAPI backend and a React/TypeScript frontend, orchestrated via Docker Compose.

The app follows a 6-stage pipeline: **Research → Draft → Style → Image Prompts → Images → Typography/Design**.

## Repository Structure

```
Lucid/
├── CLAUDE.md                    # This file
├── docker-compose.yml           # Container orchestration (backend + frontend)
├── .env.example                 # Environment template (GOOGLE_API_KEY, VITE_API_TARGET)
├── config.example.json          # App config template (defaults, image size, style)
├── backend/                     # Python FastAPI server
│   ├── Dockerfile               # Python 3.13-slim, installs Pillow deps + fonts
│   ├── requirements.txt         # Python dependencies
│   ├── download_fonts.py        # Downloads TTF fonts at Docker build time
│   ├── pytest.ini               # Test configuration
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, router registration
│   │   ├── config.py            # App-level config
│   │   ├── models/              # Pydantic data models (session, slide, style, config)
│   │   ├── routes/              # 12 API routers under /api prefix
│   │   └── services/            # 18 service modules (business logic)
│   ├── prompts/                 # LLM prompt templates (.prompt files)
│   ├── fonts/                   # Downloaded TTF font files (gitignored)
│   └── tests/                   # pytest test suite (12 test files)
└── frontend/                    # React + TypeScript + Vite
    ├── Dockerfile               # Node 22 Alpine
    ├── package.json             # Scripts: dev, build, lint, preview
    ├── tsconfig.json            # Strict TypeScript config
    ├── vite.config.ts           # Dev server on :5173, proxies /api → backend:8000
    ├── tailwind.config.js       # Custom "lucid" color palette
    └── src/
        ├── App.tsx              # Root component
        ├── main.tsx             # React entry point
        ├── components/          # Stage components + shared UI
        ├── hooks/               # useSession custom hook
        ├── services/            # Axios API client (api.ts)
        ├── types/               # TypeScript interfaces (index.ts)
        └── utils/               # Error handling utilities
```

## Quick Reference — Commands

### Running the App

```bash
# Docker (primary method)
docker-compose up --build

# Manual — backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python download_fonts.py
uvicorn app.main:app --reload --port 8000

# Manual — frontend
cd frontend
npm install
npm run dev
```

### Backend Tests

```bash
cd backend
pytest -v              # Run all tests
pytest tests/test_stage_draft.py -v   # Run a specific test file
```

Tests use FastAPI's `TestClient` (via `conftest.py` fixture). There are no frontend tests.

### Frontend Lint & Build

```bash
cd frontend
npm run lint           # ESLint with --max-warnings 0 (zero tolerance)
npm run build          # tsc type-check + vite production build
```

## Architecture

### Backend (FastAPI)

**Entry point:** `backend/app/main.py` — registers 12 routers under `/api`, configures CORS, handles `GeminiError` globally.

**Layers:**
- **Routes** (`app/routes/`): HTTP endpoints, request validation, delegate to services
- **Services** (`app/services/`): Business logic, LLM calls, image processing
- **Models** (`app/models/`): Pydantic v2 schemas for all data structures

**Key services:**
| Service | Role |
|---|---|
| `project_manager.py` | Async SQLite persistence for project state |
| `gemini_service.py` | Google Gemini API wrapper (text: Gemini Flash, images: Gemini 2.5 Flash) |
| `stage_research_service.py` | Search-grounded chat and draft extraction (Stage 1) |
| `stage_draft_service.py` | Draft text → slide text generation (Stage 2) |
| `stage_style_service.py` | Style proposal generation (Stage 3) |
| `stage_prompts_service.py` | Slide text → image prompt generation (Stage 4) |
| `stage_images_service.py` | Image prompt → background image generation (Stage 5) |
| `stage_typography_service.py` | Typography rendering onto images (Stage 6) |
| `rendering_service.py` | PIL-based text rendering with binary search font-size fitting |
| `font_manager.py` | Font loading with fuzzy weight matching |
| `export_service.py` | ZIP archive generation |
| `config_manager.py` | Configuration CRUD |
| `template_manager.py` | Template CRUD and default seeding |

**API prefix:** All routes are under `/api` (e.g., `/api/projects`, `/api/stage-research`, `/api/stage-draft`).

**Prompt templates:** Stored as `.prompt` files in `backend/prompts/`. These are the system/user prompts sent to Gemini. Edit these to change LLM behavior.

### Frontend (React + TypeScript + Vite)

**Entry point:** `frontend/src/main.tsx` → `App.tsx`

**State management:** Custom `useSession` hook manages session lifecycle with localStorage persistence for the session ID and API calls for session data.

**API client:** `frontend/src/services/api.ts` — Axios-based, 30+ endpoint wrappers. The Vite dev server proxies `/api` requests to the backend.

**Styling:** Tailwind CSS with a custom `lucid` color palette (blue-based, shades 50–900).

**Components map to stages:**
- `StageResearch.tsx` — Search-grounded chat and draft extraction (Stage 1)
- `StageDraft.tsx` — Draft input and slide generation (Stage 2)
- `StageStyle.tsx` — Style proposal viewing and selection (Stage 3)
- `StagePrompts.tsx` — Image prompt viewing and regeneration (Stage 4)
- `StageImages.tsx` — Image generation and review (Stage 5)
- `StageTypography.tsx` — Typography preview, style editing, and export (Stage 6)
- `ConfigSettings.tsx` — Configuration UI
- `Header.tsx` — Project and navigation management
- `StageIndicator.tsx` — Visual stage progress

## Code Conventions

### Python (Backend)
- **Type hints** on all function signatures (use `Optional`, `list`, `dict`, etc.)
- **Pydantic v2** for all request/response models with strict field validation
- **Async/await** for service methods (uses `asyncio` and `aiofiles`)
- **Logging** via `logging.getLogger(__name__)` per module
- **Error handling**: Custom `GeminiError` exception, caught globally in `main.py` → HTTP 503
- **No explicit linter config** — follow PEP 8 conventions
- **Services are singletons** instantiated at module level

### TypeScript (Frontend)
- **Strict mode** enabled in `tsconfig.json` (`strict: true`, `noUnusedLocals`, `noUnusedParameters`, `noFallthroughCasesInSwitch`)
- **Zero ESLint warnings** enforced (`--max-warnings 0`)
- **React functional components** with hooks (no class components)
- **Axios** for all HTTP calls (never raw `fetch`)
- **Tailwind CSS** for styling (no CSS modules or styled-components)

### General
- **No CI/CD pipelines** configured — tests and lint run manually
- **Docker-first development** — `docker-compose up --build` is the standard workflow
- **Config over code**: App behavior is configurable via `config.json` and `.prompt` files without code changes
- **Session persistence**: `sessions_db.json` stores sessions to survive Docker hot-reloads (file is gitignored)

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GOOGLE_API_KEY` | For AI features | (none) | Google Gemini API key. Without it, images are gradient placeholders and text generation is unavailable. |
| `VITE_API_TARGET` | No | `http://backend:8000` (Docker) / `http://localhost:8000` (local) | Backend URL for the Vite proxy |
| `CORS_ALLOWED_ORIGINS` | No | `http://localhost:3000,http://localhost:5173` | Comma-separated allowed origins |

## Testing Patterns

- Test files are in `backend/tests/`, named `test_*.py`
- `conftest.py` provides a `client` fixture using FastAPI's `TestClient`
- Tests cover all stages, models, sessions, chat, fonts, export, and health endpoints
- No frontend tests exist
- Run `pytest -v` from the `backend/` directory

## Key Gotchas

- `config.json` must exist in the project root before running `docker-compose up` (otherwise Docker creates a directory). Initialize with `echo '{}' > config.json`.
- Fonts are downloaded during Docker build via `download_fonts.py`. For manual setup, run `python download_fonts.py` in the backend directory first.
- The frontend proxies `/api` to the backend — API calls in the browser go to the same origin, not directly to port 8000.
- Project state flows through `ProjectManager` — always update projects via its methods, not by modifying state directly.
