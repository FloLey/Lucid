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
│   │   ├── dependencies.py      # ServiceContainer (dependency injection wiring)
│   │   ├── models/              # Pydantic data models (session, slide, style, config)
│   │   ├── routes/              # 14 routers under /api prefix (13 route files; matrix.py registers 2)
│   │   └── services/            # 24 service modules (business logic)
│   ├── prompts/                 # LLM prompt templates (.prompt files); carousel/ and painting/ subdirs override per template
│   ├── fonts/                   # Downloaded TTF font files (gitignored)
│   └── tests/                   # pytest test suite (19 test files)
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
        ├── hooks/               # Custom hooks: useStyleManager, useApiAction, useDebouncedRender, useDragResize, useDarkMode, useMatrixStream, useStreamingText, usePerSlideLoading, useRegenInstruction, useTemplateManager
        ├── services/            # Axios API client (api.ts)
        ├── types/               # TypeScript interfaces (index.ts) — exports Alignment, CellStatus, Corner named types
        └── utils/               # Shared utilities: error handling (error.ts), date formatting (date.ts), SSE parsing (sse.ts), matrix utilities (matrix.ts)
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

Tests use FastAPI's `TestClient` (via `conftest.py` fixture).

### Frontend Tests

```bash
cd frontend
npm run test           # Run vitest test suite (once)
npm run test:watch     # Run in watch mode
```

### Frontend Lint & Build

```bash
cd frontend
npm run lint           # ESLint with --max-warnings 0 (zero tolerance)
npm run build          # tsc type-check + vite production build
```

## Architecture

### Backend (FastAPI)

**Entry point:** `backend/app/main.py` — registers 14 routers under `/api`, configures CORS (restricted methods/headers), registers an in-memory sliding-window rate limiter (120 req/min/IP), handles `GeminiError` globally.

**Layers:**
- **Routes** (`app/routes/`): HTTP endpoints, request validation, delegate to services
- **Services** (`app/services/`): Business logic, LLM calls, image processing
- **Models** (`app/models/`): Pydantic v2 schemas for all data structures
- **Dependencies** (`app/dependencies.py`): `ServiceContainer` wires all singleton services for dependency injection

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
| `storage_service.py` | Disk-based image read/write/delete |
| `image_service.py` | Gemini image generation wrapper (produces PNG from a prompt) |
| `matrix_db.py` | SQLite CRUD layer for Concept Matrix projects and cells |
| `matrix_generator.py` | Stateless LLM pipeline for matrix generation; accepts an `emit` callback for SSE events |
| `matrix_service.py` | Matrix orchestrator: starts/cancels per-project asyncio tasks, manages SSE fan-out queues |
| `matrix_settings_manager.py` | JSON-file persistence for matrix configuration (`matrix_settings.json`) |
| `async_utils.py` | `bounded_gather()` — concurrent async operations with a concurrency limit |
| `base_stage_service.py` | Base class for stage services: `_require()` validation, `_project_ctx()` async context manager (fetch + auto-save, used by all stage methods except `regenerate_slide_text_stream` which is an async generator), `_batch()` concurrency helper, `_style_from_config()` |
| `llm_logger.py` | Structured JSONL logging of all LLM calls; `log_llm_method` decorator auto-logs async/sync methods |
| `prompt_loader.py` | Loads `.prompt` files with per-template fallback (carousel/, painting/ override shared defaults) |
| `prompt_validator.py` | Validates prompt variable substitution at startup |

**API prefix:** All routes are under `/api` (e.g., `/api/projects`, `/api/stage-research`, `/api/stage-draft`). Notable endpoints added in recent sessions: `POST /api/projects/{id}/reorder` (slide reordering), `POST /api/stage-draft/regenerate-stream` (SSE streaming text regeneration), and `POST /api/matrix/{id}/generate-images` (bulk image generation for an existing matrix that was created without images).

**Matrix generator input modes:** `POST /api/matrix/` accepts two modes via `input_mode` field:
- `"theme"` (default): user provides a theme string; LLM picks n diagonal concepts and invents per-concept axes
- `"description"`: user describes a cross-axis relationship (e.g. "feels like a generation but is actually from one"); a single LLM call to `matrix_description_axes.prompt` derives both axis labels and n shared labels for both axes

**Prompt templates:** Stored as `.prompt` files in `backend/prompts/`. Subdirectories `prompts/carousel/` and `prompts/painting/` contain template-specific overrides; missing overrides fall back to the root prompt file. Edit `.prompt` files to change LLM behaviour without code changes.

### Frontend (React + TypeScript + Vite)

**Entry point:** `frontend/src/main.tsx` → `App.tsx`

**State management:** `ProjectContext` (in `src/contexts/ProjectContext.tsx`) manages project lifecycle — exposes `useProject()` hook consumed by all stage components. Persists the active project ID in `localStorage`.

**API client:** `frontend/src/services/api.ts` — Axios-based, 30+ endpoint wrappers. The Vite dev server proxies `/api` requests to the backend.

**Styling:** Tailwind CSS with a custom `lucid` color palette (blue-based, shades 50–900).

**Components map to stages:**
- `StageResearch.tsx` — Search-grounded chat and draft extraction (Stage 1)
- `StageDraft.tsx` — Draft input and slide generation (Stage 2)
- `StageStyle.tsx` — Style proposal viewing and selection (Stage 3)
- `StagePrompts.tsx` — Image prompt viewing and regeneration (Stage 4)
- `StageImages.tsx` — Image generation and review (Stage 5)
- `StageTypography.tsx` — Typography preview, style editing, and export (Stage 6)
- `ModeSelector.tsx` — Landing screen with two equal-prominence mode cards (Slide Generation / Matrix Generation); shown on every fresh page load before any section is chosen
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
- **Axios** for all HTTP calls; exception: SSE streaming uses native `fetch` + `ReadableStream`. `useStreamingText` and `useMatrixStream` hooks share the `parseSSELine` utility from `utils/sse.ts`
- **Tailwind CSS** for styling (no CSS modules or styled-components)

### General
- **No CI/CD pipelines** configured — tests and lint run manually
- **Docker-first development** — `docker-compose up --build` is the standard workflow
- **Docker health check** — the backend service has a health check at `/health`; `docker ps` shows `(healthy)` when ready
- **Config over code**: App behavior is configurable via `config.json` and `.prompt` files without code changes
- **Session persistence**: `sessions_db.json` stores sessions to survive Docker hot-reloads (file is gitignored)

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GOOGLE_API_KEY` | For AI features | (none) | Google Gemini API key. Without it, images are gradient placeholders and text generation is unavailable. |
| `VITE_API_TARGET` | No | `http://backend:8000` (Docker) / `http://localhost:8000` (local) | Backend URL for the Vite proxy |
| `CORS_ALLOWED_ORIGINS` | No | `http://localhost:3000,http://localhost:5173` | Comma-separated allowed origins |
| `RATE_LIMIT_MAX_CALLS` | No | `120` | Max `/api/*` requests per IP per rate-limit window |
| `RATE_LIMIT_WINDOW_SECONDS` | No | `60` | Sliding-window size for the rate limiter (seconds) |

## Testing Patterns

- Test files are in `backend/tests/`, named `test_*.py`
- `conftest.py` provides a `client` fixture using FastAPI's `TestClient`
- Tests cover all stages, models, sessions, chat, fonts, export, health endpoints, rendering service, and async utilities
- Frontend tests use Vitest + React Testing Library; test files are in `frontend/src/components/__tests__/`
- Run `pytest -v` from the `backend/` directory; run `npm run test` from the `frontend/` directory

### Testing Policy — **mandatory**

**Every code change must be accompanied by tests.** This is not optional:

1. **New features**: add tests covering the happy path, edge cases, and error paths
2. **Bug fixes**: add a regression test that would have caught the bug
3. **Prompt files**: add a parametrised case to `TestMatrixPromptFormatting` (or equivalent) verifying the prompt formats without error and that JSON example keys are properly escaped
4. **DB schema changes**: add tests verifying the new fields round-trip through create → get
5. **Model changes**: add validation tests for both valid and invalid inputs
6. Tests must pass (`pytest -v`) before any commit is made

### Documentation Policy — **mandatory**

**CLAUDE.md and any relevant README sections must be kept up to date** when you:

- Add a new feature, API endpoint, or service — document it in the relevant section of CLAUDE.md
- Add or rename prompt files — update the prompts table or service description
- Change environment variables — update the Environment Variables table
- Change the repository structure — update the Repository Structure section
- Change a command or workflow — update Quick Reference

## Key Gotchas

- `config.json` must exist in the project root before running `docker-compose up` (otherwise Docker creates a directory). Initialize with `echo '{}' > config.json`.
- Fonts are downloaded during Docker build via `download_fonts.py`. For manual setup, run `python download_fonts.py` in the backend directory first.
- The frontend proxies `/api` to the backend — API calls in the browser go to the same origin, not directly to port 8000.
- Project state flows through `ProjectManager` — always update projects via its methods, not by modifying state directly.
- The database is SQLite (`aiosqlite`) stored in the `lucid-data` Docker volume. SQLite is single-writer — horizontal scaling beyond one backend process requires migrating to PostgreSQL.
- Generated images are stored on disk in the `lucid-data` volume. They are not backed up automatically; use `docker volume` tools or mount a host path for persistence.
