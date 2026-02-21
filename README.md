# Lucid 🌠
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/FloLey/Lucid)

**Transform rough drafts into polished, high-converting social media carousels.**
Lucid is a containerized web application that orchestrates a sophisticated pipeline to convert your messy, unstructured ideas into beautiful, ready-to-publish 4:5 carousel slides. Built with a FastAPI backend and a React/TypeScript frontend, it leverages Google Gemini for creative heavy lifting and a deterministic rendering engine for pixel-perfect typography.
---
## The Philosophy: The Progressive Pipeline Architecture
Why does Lucid exist? Because **Generative AI struggles with rendering text inside images.** Relying on a single zero-shot prompt to generate a complete, spelled-correctly, well-laid-out slide is a recipe for hallucinations and warped artifacts.
Lucid solves this by implementing a **Progressive Pipeline Architecture**. We treat AI as a chain of specialized workers rather than a magic black box:
1. **Separation of Concerns:** The AI is strictly relegated to structural writing and generating *text-free* background imagery. A deterministic engine (Pillow/PIL) handles all typography.
2. **Grounding & Context:** Each stage's output grounds the next. A raw draft is structured into JSON text arrays $\rightarrow$ Text informs global visual styles $\rightarrow$ Styles dictate slide-specific image prompts $\rightarrow$ Prompts generate clean backgrounds $\rightarrow$ Text is accurately layered on top.
3. **Human-in-the-Loop Intercession:** By breaking the process into 5 discrete stages, users can audit, edit, and safely course-correct at any step without having to start over.
---
## The Workflow
Lucid is designed around a strict, bi-directional 5-stage workflow. At any point, you can regenerate an individual slide, edit the output, or step backward without losing your downstream configurations.
### 📝 Stage 1: The Draft
Dump your unstructured notes, bullet points, or stream-of-consciousness text. The AI acts as a content strategist, splitting the draft into a cohesive, logically flowing sequence of slides with distinct Titles and Bodies.
*Customize language, slide count, and toggle title generation.*
### 🎨 Stage 2: Style Proposals
The AI analyzes your slide text and generates distinct "Style Proposals" (e.g., *Minimalist geometric, warm watercolor washes, dark moody photography*). This guarantees that every image generated later will share a consistent visual vocabulary.
### 🧠 Stage 3: Image Prompts
Instead of generating images directly, the AI first writes highly specific, text-free image prompts for *each individual slide*, prepending the global style you chose in Stage 2.
*Don't like a specific slide's concept? Edit the prompt manually or ask the AI to regenerate it.*
### 🖼️ Stage 4: Image Generation
Lucid triggers parallel execution of image generation requests, creating clean, consistent background images mapped to your 4:5 layout.
### 🔤 Stage 5: Typography & Layout
The deterministic rendering engine takes over. Drag, drop, and resize text boxes directly on the canvas. Adjust fonts, weights, colors, drop shadows, and strokes. The system automatically calculates perfect scaling to fit your text into the layout. Finally, hit **Export ZIP** to download your ready-to-post carousel.
---
## Feature Highlights
Lucid packs several advanced technical implementations to make the pipeline robust and seamless:
*   **Binary Search Text Fitting:** The `RenderingService` uses an $O(\log n)$ binary search algorithm (`_find_fitting_size`) to calculate the mathematically perfect font size for a given bounding box, replacing brittle linear decrements and ensuring text never overflows.
*   **Fuzzy Font Matching:** The `FontManager` builds an indexed registry of your TTF/OTF files on startup. If the UI requests "Inter 600" but only "Inter 700" is available, it gracefully degrades to the nearest available mathematical weight.
*   **Debounced Sync & Render Loop:** The frontend `useDebouncedRender` hook eliminates React state race conditions. It ensures rapid keystrokes trigger a single, synchronous database save followed by a PIL background render, using monotonic request IDs to silently drop stale in-flight responses.
*   **Hot-Swappable, Validated Prompts:** LLM system instructions live in version-controlled `.prompt` files (e.g., `slide_generation.prompt`), editable directly via the UI. The backend runs AST-style validation to ensure required `{variables}` aren't accidentally deleted by the user.
*   **Concurrency & Rate Limiting:** Outbound AI calls utilize `asyncio.Semaphore` implementations to strictly limit concurrent LLM text and image requests, preventing `429 Too Many Requests` API limits.
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
## API & CLI Reference
The FastAPI backend exposes a clean REST API. Here are the core architectural routes:
| Route | Method | Description |
| :--- | :--- | :--- |
| `/api/projects/` | `POST` | Create a new project state (optionally from a Template). |
| `/api/stage1/generate` | `POST` | Convert draft string $\rightarrow$ JSON slide array using Gemini 3 Flash. |
| `/api/stage-style/generate` | `POST` | Propose visual theme prompts. |
| `/api/stage2/generate` | `POST` | Generate individual image prompts in parallel. |
| `/api/stage3/generate` | `POST` | Render image prompts $\rightarrow$ Base64/Disk PNGs using Gemini 2.5 Image. |
| `/api/stage4/apply-all` | `POST` | Run PIL typography engine to composite text over backgrounds. |
| `/api/export/zip` | `POST` | Archive project metadata and final composited images. |
| `/api/prompts/validate` | `POST` | Dry-run validation of `.prompt` template edits. |
*Local Dev Note: If running without Docker, utilize the provided `install-deps.sh` script to install Node/Python requirements and trigger the `download_fonts.py` hook.*
