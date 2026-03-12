# Lucid 🌠
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/FloLey/Lucid)

**AI-powered creative content studio — turn ideas into polished slides and concept matrices.**

Lucid is a containerized web application with two first-class creation modes: a **6-stage carousel pipeline** that converts rough drafts into pixel-perfect social media slides, and a **Concept Matrix Generator** that maps any theme or cross-axis relationship into a streamed n×n visual grid. Built with a FastAPI backend and a React/TypeScript frontend, it uses Google Gemini for creative heavy lifting and a deterministic rendering engine for reliable typography.

---

## Slide Generation

### The Pipeline Architecture

Why a pipeline instead of a single prompt? Because **Generative AI struggles with rendering text inside images.** Asking one model to generate a complete, correctly-spelled, well-laid-out slide in a single shot reliably produces hallucinations and warped artifacts.

Lucid solves this with a **Progressive Pipeline Architecture** — AI as a chain of specialized workers, not a magic black box:

1. **Separation of Concerns:** The AI handles structural writing and generates *text-free* background imagery. A deterministic engine (Pillow/PIL) handles all typography.
2. **Grounding & Context:** Each stage's output grounds the next. Search-grounded research feeds a structured draft → Draft is split into slide text → Text informs global visual styles → Styles dictate slide-specific image prompts → Prompts generate clean backgrounds → Text is accurately layered on top.
3. **Human-in-the-Loop:** Six discrete stages let you audit, edit, and course-correct at any step without starting over.

### The 6-Stage Workflow

Lucid uses a strict, bi-directional 6-stage workflow. You can regenerate individual slides, edit any output, or step backward without losing downstream configuration.

#### 🔍 Stage 1: Research
Chat with an AI research assistant grounded in real-time Google Search to brainstorm ideas, gather facts, and explore angles. When ready, click **Create Draft** to synthesise the conversation into a structured draft — or skip if you already have content.

#### 📝 Stage 2: Draft
Paste or refine your draft text. The AI acts as a content strategist, splitting it into a logically flowing sequence of slides with distinct Titles and Bodies.

*Customise language, slide count, and toggle title generation.*

#### 🎨 Stage 3: Style Proposals
The AI analyses your slide text and generates distinct style proposals (e.g. *Minimalist geometric, warm watercolour washes, dark moody photography*). Picking one here guarantees that all images generated later share a consistent visual vocabulary.

#### 🧠 Stage 4: Image Prompts
Instead of generating images directly, the AI first writes highly specific, text-free image prompts for *each individual slide*, prepending the global style chosen in Stage 3.

*Edit or regenerate individual prompts before spending API calls on images.*

#### 🖼️ Stage 5: Image Generation
Lucid sends all image prompts in parallel to Gemini and renders clean, consistent 4:5 background images (1080×1350 px).

#### 🔤 Stage 6: Typography & Layout
The deterministic rendering engine takes over. Drag, drop, and resize text boxes on the canvas. Adjust fonts, weights, colours, drop shadows, and strokes. The system binary-searches for the mathematically perfect font size to fit your text. Hit **Export ZIP** to download your ready-to-post carousel.

---

## Matrix Generation

### Overview

The Concept Matrix Generator creates an n×n grid of AI-generated cells. Each cell represents the intersection of two descriptive axes and carries its own title, body text, and optional background image. Cells stream to the UI as they complete — you see the grid fill in live.

Matrices are fully independent of the carousel pipeline. They have their own home screen, project list, settings, and views.

### Input Modes

When creating a matrix you choose one of two modes:

| Mode | What you provide | What the AI does |
| :--- | :--- | :--- |
| **Theme** | A theme string (e.g. *"The philosophy of time and consciousness"*) | Picks n distinct diagonal concepts from the theme; invents a unique pair of descriptive axes for each concept; then populates all n×n cells at the intersection of those axes. Grid is square (n×n). |
| **Description** | A cross-axis relationship (e.g. *"feels like a certain generation but is actually from a different one"*) | A single LLM call derives both axis labels and n shared labels for rows and columns, producing a rectangular grid (rows×cols). |

### Grid Size

- **Theme mode:** choose n ∈ {2, 3, 4, 5, 6} → produces an n×n grid (4–36 cells).
- **Description mode:** choose rows and columns independently from {2, 3, 4, 5, 6}.

### Style Mode

Each matrix is generated with one of four style modes that shape the tone of every cell:

| Style | Character |
| :--- | :--- |
| **Neutral** | Balanced, informative |
| **Fun** | Playful, informal |
| **Absurd** | Unexpected, surreal juxtapositions |
| **Academic** | Analytical, precise |

### Generation & Streaming

Clicking **Generate Matrix** starts an async generation job on the backend. Cells are generated in parallel (bounded by `max_concurrency`) and streamed to the UI via SSE. You can watch the grid populate cell by cell without waiting for the full job to finish.

A generation job has four statuses: **Pending → Generating → Complete / Failed**.

### Image Generation

Images are optional and can be added at any time:

- **At creation time:** check **Generate images for each cell** in the New Matrix modal.
- **After generation:** click **Generate Images** from the matrix view to bulk-generate backgrounds for all cells.
- **Per cell:** click **Regen** on any individual cell to regenerate its image without touching others.

Images are produced by Gemini from an AI-written prompt that combines the cell's content with the matrix's global style.

### Revalidation

If some cells fail during generation (or produce low-quality content), click **Revalidate** from the matrix view. This runs a validation pass that identifies failed or weak cells and regenerates only those. You can optionally supply a **user comment** (e.g. *"cells should be more specific"*) which is injected into the validator prompt as extra instructions.

Progress streams via the same SSE endpoint as initial generation.

### Views

Once a matrix is generated, three views are available:

| View | Description |
| :--- | :--- |
| **Grid** | Default interactive view. Shows all cells in the n×n grid with axis labels. Click any cell to expand it. |
| **Poster** | Full-page visual layout designed for screenshots or sharing — renders all cells in a clean grid with large axis headers. |
| **Reveal** | Presentation mode: cycles through cells one at a time for storytelling or slide-by-slide review. |

### Settings

Click **Settings** in the Matrix workspace to configure:

| Setting | Description |
| :--- | :--- |
| **Text Model** | Gemini model ID used for cell text generation |
| **Image Model** | Gemini model ID used for cell image generation |
| **Diagonal Temperature** | LLM temperature for seed concept generation (higher = more surprising) |
| **Axes Temperature** | Temperature for descriptor/axis generation |
| **Cell Temperature** | Temperature for off-diagonal cell content |
| **Validation Temperature** | Temperature for the revalidation pass |
| **Max Concurrency** | Number of parallel LLM calls during generation (1–20) |
| **Max Retries** | Automatic retry attempts for failed cells (0–5) |

Settings are persisted in `matrix_settings.json` and can be reset to factory defaults.

---

## Feature Highlights

- **Binary Search Text Fitting:** The `RenderingService` uses an O(log n) binary search algorithm to find the mathematically perfect font size for a given bounding box — text never overflows or runs short.
- **Fuzzy Font Matching:** The `FontManager` indexes all TTF/OTF files on startup. If the UI requests "Inter 600" but only "Inter 700" is available, it gracefully uses the nearest weight.
- **Debounced Sync & Render Loop:** `useDebouncedRender` eliminates React state race conditions. Rapid keystrokes trigger a single synchronous database save followed by a deterministic PIL render, using monotonic request IDs to drop stale in-flight responses.
- **SSE Streaming:** Both slide text regeneration and matrix cell generation use Server-Sent Events. The `useStreamingText` and `useMatrixStream` hooks share a common `parseSSELine` utility.
- **Hot-Swappable, Validated Prompts:** LLM instructions live in version-controlled `.prompt` files editable via the UI. The backend runs AST-style validation to ensure required `{variables}` aren't accidentally deleted.
- **Concurrency Control:** `bounded_gather()` — a thin `asyncio.Semaphore` wrapper — limits concurrent LLM calls for both the carousel pipeline and matrix generator, preventing 429 errors.
- **Per-Template Prompt Overrides:** Root `.prompt` files are shared defaults. Files in `prompts/carousel/` or `prompts/painting/` override only the templates that need different behaviour.

---

## Configuration & Customisation

### Carousel — `config.json`

| Key | Description |
| :--- | :--- |
| `global_defaults` | Default language, slide count, title inclusion |
| `image` | Output resolution (default: 1080×1350, aspect ratio 4:5) |
| `style` | Base typography: font family, colours, stroke properties |
| `stage_instructions` | Pre-seeded instructions for specific pipeline stages |

### Carousel — Templates

Any project configuration can be saved as a reusable **Template**. Future projects launched from a template inherit its slide count, configuration defaults, and prompt logic. Templates are managed via the **Templates** button on the carousel home screen.

### Matrix — Settings

Matrix generation parameters (models, temperatures, concurrency, retries) are configured through the **Settings** button in the Matrix workspace and persisted in `matrix_settings.json`.

---

## Quick Start — GitHub Codespaces

The fastest way to run Lucid with zero local setup:

1. **Set your API key** as a Codespaces secret — go to [github.com/settings/codespaces](https://github.com/settings/codespaces), add a secret named `GOOGLE_API_KEY` with your key from [aistudio.google.com/apikey](https://aistudio.google.com/apikey), and grant it access to this repository.
2. **Open the Codespace** — click the badge above or go to [codespaces.new/FloLey/Lucid](https://codespaces.new/FloLey/Lucid).
3. The app builds and launches automatically. The browser tab for port **5173** opens when ready.

> The `GOOGLE_API_KEY` secret is injected into the Docker Compose environment automatically — no `.env` file needed.

---

## Installation & Requirements

Lucid is built for containerized, Docker-first development.

**Prerequisites:**
- Docker & Docker Compose
- A Google Generative AI API Key (https://aistudio.google.com/apikey)

### 1. Environment Setup

```bash
git clone https://github.com/FloLey/Lucid.git
cd Lucid
cp .env.example .env
```

Add your `GOOGLE_API_KEY` to the `.env` file. *(Without an API key the app falls back to gradient placeholder images and text generation is unavailable.)*

### 2. Initialize Configuration

```bash
echo '{}' > config.json
```

### 3. Build and Run

```bash
docker-compose up --build
```

*Docker downloads required open-source fonts during the build.*

- App: **`http://localhost:5173`**
- API docs: **`http://localhost:8000/docs`**

---

## Deploy on VPS (private access via Tailscale)

Run Lucid on a VPS with the frontend and API reachable **only from devices on your Tailscale network**.

Instead of binding ports to `0.0.0.0`, we bind exclusively to the Tailscale IP (`100.x.y.z`). Docker's iptables rules only forward traffic that arrives on that interface — no public exposure, no UFW rules needed for app ports.

### Prerequisites

- Docker & Docker Compose on the VPS
- [Tailscale](https://tailscale.com/download) installed and connected (`tailscale up`)
- Tailscale on any client device you want to access from

### 1. Clone and configure

```bash
git clone https://github.com/FloLey/Lucid.git
cd Lucid
cp .env.example .env
# Edit .env and set GOOGLE_API_KEY
echo '{}' > config.json
```

### 2. Start in production mode

```bash
./scripts/prod_up.sh
```

The script detects your Tailscale IPv4 address, binds the frontend (port 5173) and backend (port 8000) to it, builds, and starts in detached mode.

```
Tailscale IP detected: 100.64.0.12
Starting Lucid (production mode) on 100.64.0.12 ...
Lucid is running (Tailscale-private access only):
  Frontend : http://100.64.0.12:5173
  API docs : http://100.64.0.12:8000/docs
```

### 3. Stop

```bash
./scripts/prod_down.sh
```

The `lucid-data` volume (database + generated images) is preserved. To also remove the data volume: `docker compose down -v`.

### Firewall notes (optional defence-in-depth)

```bash
sudo ufw default deny incoming
sudo ufw allow ssh
sudo ufw allow in on tailscale0
sudo ufw enable
```

### Manual usage

```bash
export LUCID_BIND_IP="$(tailscale ip -4 | head -n1)"
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

---

## API Reference

All routes are under the `/api` prefix. The full interactive docs are at `http://localhost:8000/docs`.

### Carousel Pipeline

| Route | Method | Description |
| :--- | :--- | :--- |
| `/api/projects/` | `POST` | Create a new project (optionally from a template) |
| `/api/projects/{id}/reorder` | `POST` | Reorder slides within a project |
| `/api/stage-research/chat` | `POST` | Send a message to the search-grounded research assistant |
| `/api/stage-research/extract-draft` | `POST` | Synthesise the research conversation into a draft |
| `/api/stage-draft/generate` | `POST` | Convert draft text → slide array |
| `/api/stage-draft/regenerate-stream` | `POST` | Regenerate a single slide's text via SSE |
| `/api/stage-style/generate` | `POST` | Generate visual style proposals |
| `/api/stage-prompts/generate` | `POST` | Generate per-slide image prompts |
| `/api/stage-images/generate` | `POST` | Generate background images from prompts |
| `/api/stage-typography/apply-all` | `POST` | Composite text over backgrounds via PIL |
| `/api/export/zip` | `POST` | Download project as a ZIP archive |
| `/api/prompts/validate` | `POST` | Validate `.prompt` template edits without saving |

### Matrix Generator

| Route | Method | Description |
| :--- | :--- | :--- |
| `/api/matrix/` | `POST` | Start a new matrix generation job (theme or description mode) |
| `/api/matrix/` | `GET` | List all matrices |
| `/api/matrix/{id}` | `GET` | Get a matrix with all cells |
| `/api/matrix/{id}/events` | `GET` | SSE stream of generation progress |
| `/api/matrix/{id}/generate-images` | `POST` | Bulk-generate background images for an existing matrix |
| `/api/matrix/{id}/revalidate` | `POST` | Run a validation pass; accepts `{"user_comment": "..."}` for extra instructions |

*Local dev note: if running without Docker, use `install-deps.sh` to install Node/Python requirements and run `download_fonts.py` to fetch fonts.*
