# Lucid 🌠
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/FloLey/Lucid)

**Transform rough drafts into polished, high-converting social media carousels.**
Lucid is a containerized web application that orchestrates a sophisticated pipeline to convert your messy, unstructured ideas into beautiful, ready-to-publish 4:5 carousel slides. Built with a FastAPI backend and a React/TypeScript frontend, it leverages Google Gemini for creative heavy lifting and a deterministic rendering engine for pixel-perfect typography.
---
## The Philosophy: The Progressive Pipeline Architecture
Why does Lucid exist? Because **Generative AI struggles with rendering text inside images.** Relying on a single zero-shot prompt to generate a complete, spelled-correctly, well-laid-out slide is a recipe for hallucinations and warped artifacts.
Lucid solves this by implementing a **Progressive Pipeline Architecture**. We treat AI as a chain of specialized workers rather than a magic black box:
1. **Separation of Concerns:** The AI is strictly relegated to structural writing and generating *text-free* background imagery. A deterministic engine (Pillow/PIL) handles all typography.
2. **Grounding & Context:** Each stage's output grounds the next. Search-grounded research feeds a structured draft $\rightarrow$ Draft is split into slide text $\rightarrow$ Text informs global visual styles $\rightarrow$ Styles dictate slide-specific image prompts $\rightarrow$ Prompts generate clean backgrounds $\rightarrow$ Text is accurately layered on top.
3. **Human-in-the-Loop Intercession:** By breaking the process into 6 discrete stages, users can audit, edit, and safely course-correct at any step without having to start over.
---
## The Workflow
Lucid is designed around a strict, bi-directional 6-stage workflow. At any point, you can regenerate an individual slide, edit the output, or step backward without losing your downstream configurations.
### 🔍 Stage 1: Research
Chat with an AI research assistant grounded in real-time Google Search to brainstorm ideas, gather facts, and explore angles for your carousel. When you're ready, hit **Create Draft** to synthesise the conversation into a structured draft — or skip this stage if you already have content.
*Add research instructions to guide how the conversation is summarised into a draft.*
### 📝 Stage 2: Draft
Paste or refine your draft text. The AI acts as a content strategist, splitting it into a cohesive, logically flowing sequence of slides with distinct Titles and Bodies.
*Customize language, slide count, and toggle title generation.*
### 🎨 Stage 3: Style Proposals
The AI analyzes your slide text and generates distinct "Style Proposals" (e.g., *Minimalist geometric, warm watercolor washes, dark moody photography*). This guarantees that every image generated later will share a consistent visual vocabulary.
### 🧠 Stage 4: Image Prompts
Instead of generating images directly, the AI first writes highly specific, text-free image prompts for *each individual slide*, prepending the global style you chose in Stage 3.
*Don't like a specific slide's concept? Edit the prompt manually or ask the AI to regenerate it.*
### 🖼️ Stage 5: Image Generation
Lucid triggers parallel execution of image generation requests, creating clean, consistent background images mapped to your 4:5 layout.
### 🔤 Stage 6: Typography & Layout
The deterministic rendering engine takes over. Drag, drop, and resize text boxes directly on the canvas. Adjust fonts, weights, colors, drop shadows, and strokes. The system automatically calculates perfect scaling to fit your text into the layout. Finally, hit **Export ZIP** to download your ready-to-post carousel.
---
## Feature Highlights
Lucid packs several advanced technical implementations to make the pipeline robust and seamless:
*   **Binary Search Text Fitting:** The `RenderingService` uses an $O(\log n)$ binary search algorithm (`_find_fitting_size`) to calculate the mathematically perfect font size for a given bounding box, replacing brittle linear decrements and ensuring text never overflows.
*   **Fuzzy Font Matching:** The `FontManager` builds an indexed registry of your TTF/OTF files on startup. If the UI requests "Inter 600" but only "Inter 700" is available, it gracefully degrades to the nearest available mathematical weight.
*   **Debounced Sync & Render Loop:** The frontend `useDebouncedRender` hook eliminates React state race conditions. It ensures rapid keystrokes trigger a single, synchronous database save followed by a PIL background render, using monotonic request IDs to silently drop stale in-flight responses.
*   **Hot-Swappable, Validated Prompts:** LLM system instructions live in version-controlled `.prompt` files (e.g., `slide_generation.prompt`), editable directly via the UI. The backend runs AST-style validation to ensure required `{variables}` aren't accidentally deleted by the user.
*   **Concurrency & Rate Limiting:** Outbound AI calls use `bounded_gather()` — a thin wrapper around `asyncio.Semaphore` — to strictly limit concurrent LLM text and image requests, preventing `429 Too Many Requests` API limits.
*   **Concept Matrix Generator:** A standalone side-feature that produces n×n visual concept grids. Accepts a **theme** (AI picks diagonal concepts and per-concept axes) or a **description** of a cross-axis relationship (a single LLM call derives both axis labels). Results stream via SSE as each cell is generated in parallel.
---
## Configuration & Customization
Lucid behavior is highly customizable via the **Templates** editor (Templates button on the home screen) or the `config.json` file.
### App Config Schema (`config.json`)
*   **`global_defaults`**: Set default languages (e.g., "English"), slide counts, and toggle title inclusion.
*   **`image`**: Controls backend rendering resolutions (defaults to `1080x1350`, aspect ratio `4:5`).
*   **`style`**: Base typography configurations (`default_font_family`, colors, stroke properties).
*   **`stage_instructions`**: Pre-seed standard instructions into specific pipeline stages (e.g., "Always use an energetic tone" for Stage 1).
### Templates
You can save any project configuration as a reusable **Template**. Future projects launched from a template will inherit the slide counts, configuration defaults, and even the exact prompt logic of the template base.
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
Clone the repository and set up your `.env` file:
```bash
git clone https://github.com/FloLey/Lucid.git
cd Lucid
cp .env.example .env
```
Add your `GOOGLE_API_KEY` to the `.env` file. *(Note: Without an API key, the app gracefully falls back to generating placeholder gradient images).*
### 2. Initialize Configuration
Ensure the base config file exists before Docker boots:
```bash
echo '{}' > config.json
```
### 3. Build and Run
```bash
docker-compose up --build
```
*Docker will automatically download the required open-source fonts during the build process.*
Access the application at **`http://localhost:5173`**.
Access the Swagger API documentation at **`http://localhost:8000/docs`**.
---
## Deploy on VPS (private access via Tailscale)

This section describes how to run Lucid on a VPS so that the frontend and API
are reachable **only from devices on your Tailscale network** — not from the
public internet.

The key idea: instead of binding ports to `0.0.0.0` (all interfaces), we bind
them exclusively to the Tailscale IP (`100.x.y.z`).  Docker's port-publishing
mechanism goes through iptables, which bypasses UFW — binding to the Tailscale
interface sidesteps this entirely.

### Prerequisites

- Docker & Docker Compose installed on the VPS
- [Tailscale](https://tailscale.com/download) installed and connected on the VPS (`tailscale up`)
- Tailscale also installed on any client device you want to access the app from

### 1. Clone and configure

```bash
git clone https://github.com/FloLey/Lucid.git
cd Lucid
cp .env.example .env
# Edit .env and set your GOOGLE_API_KEY
```

Ensure the base config file exists:

```bash
echo '{}' > config.json
```

### 2. Start in production mode

```bash
./scripts/prod_up.sh
```

The script will:
1. Detect your Tailscale IPv4 address via `tailscale ip -4`.
2. Bind the frontend (port 5173) and backend (port 8000) **only** to that IP.
3. Build and start the containers in detached mode.
4. Print the private URLs.

Example output:

```
Tailscale IP detected: 100.64.0.12
Starting Lucid (production mode) on 100.64.0.12 ...
...
Lucid is running (Tailscale-private access only):
  Frontend : http://100.64.0.12:5173
  API docs : http://100.64.0.12:8000/docs

These URLs are reachable only from devices on your Tailscale network.
```

### 3. Verify access

From any device on your Tailscale network, open:

- `http://<TAILSCALE_IP>:5173` — Lucid UI
- `http://<TAILSCALE_IP>:8000/docs` — Swagger API docs

The same URLs will return "connection refused" from the public internet.

### 4. Stop

```bash
./scripts/prod_down.sh
```

This stops the containers. The `lucid-data` volume (database + generated images)
is **preserved**. To also delete the data volume, run
`docker compose down -v` manually.

### Firewall notes

Binding ports to the Tailscale IP is sufficient to prevent public access —
Docker's iptables rules will only forward traffic that arrives on the Tailscale
interface.  You do **not** need UFW rules for the app ports.

If you want defence-in-depth, a minimal UFW policy:

```bash
sudo ufw default deny incoming
sudo ufw allow ssh          # or: ufw allow in on tailscale0
sudo ufw allow in on tailscale0
sudo ufw enable
```

### Manual usage (without the script)

If you prefer to run the compose command directly, export `LUCID_BIND_IP` first:

```bash
export LUCID_BIND_IP="$(tailscale ip -4 | head -n1)"
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

The `docker-compose.prod.yml` overlay has **no fallback** for `LUCID_BIND_IP`.
If the variable is unset, Docker Compose will error out rather than silently
bind on `0.0.0.0`.

### Future auto-deploy

When automating deployments (e.g. via GitHub Actions or a deploy hook), always
invoke `./scripts/prod_up.sh` rather than a plain `docker compose up`.  This
guarantees that the Tailscale IP is detected at deploy time and the ports are
never accidentally exposed publicly.

---
## API & CLI Reference
The FastAPI backend exposes a clean REST API. Here are the core architectural routes:
| Route | Method | Description |
| :--- | :--- | :--- |
| `/api/projects/` | `POST` | Create a new project state (optionally from a Template). |
| `/api/stage-research/chat` | `POST` | Send a user message and receive a search-grounded AI reply. |
| `/api/stage-research/extract-draft` | `POST` | Summarise the research conversation into a draft text. |
| `/api/stage-draft/generate` | `POST` | Convert draft string $\rightarrow$ JSON slide array using Gemini Flash. |
| `/api/stage-style/generate` | `POST` | Propose visual theme prompts. |
| `/api/stage-prompts/generate` | `POST` | Generate individual image prompts in parallel. |
| `/api/stage-images/generate` | `POST` | Render image prompts $\rightarrow$ Base64/Disk PNGs using Gemini 2.5 Image. |
| `/api/stage-typography/apply-all` | `POST` | Run PIL typography engine to composite text over backgrounds. |
| `/api/projects/{id}/reorder` | `POST` | Reorder slides within a project. |
| `/api/stage-draft/regenerate-stream` | `POST` | Regenerate a single slide's text via SSE streaming. |
| `/api/export/zip` | `POST` | Archive project metadata and final composited images. |
| `/api/prompts/validate` | `POST` | Dry-run validation of `.prompt` template edits. |
| `/api/matrix/` | `POST` | Start a new Concept Matrix generation job (theme or description mode). |
| `/api/matrix/{id}/generate-images` | `POST` | Bulk-generate background images for an existing matrix. |
*Local Dev Note: If running without Docker, utilize the provided `install-deps.sh` script to install Node/Python requirements and trigger the `download_fonts.py` hook.*
