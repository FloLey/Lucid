# Lucid v0.2

Transform rough drafts into polished social media carousels.

Lucid is a containerized web application that turns your ideas into beautiful 4:5 aspect ratio carousel slides (1080x1350px) ready for Instagram and other social platforms.

## Features

- **5-Stage Workflow**: Draft → Style → Image Prompts → Images → Design
- **AI-Powered Generation**: Uses Gemini 3 Flash Preview for text and Gemini 2.5 Flash for images
- **Typography Rendering**: PIL-based text rendering with binary search fitting algorithm
- **Fuzzy Font Matching**: Intelligent font loading with weight approximation
- **Session Persistence**: Sessions survive Docker hot-reloads during development
- **Stage-Scoped Chat**: Context-aware commands with autocomplete
- **Bi-Directional Navigation**: Navigate back and forth between stages
- **Style Presets**: Modern, Bold, Elegant, Minimal, and Impact styles
- **Export**: Download as ZIP with all slides and metadata

## Quick Start

### Option 1: GitHub Codespaces (Recommended)

Click the button below to open a fully configured development environment in the cloud:

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/FloLey/Lucid)

Before creating the Codespace, add your Google API key as a **Codespaces secret** so AI features work out of the box:

1. Go to [github.com/settings/codespaces](https://github.com/settings/codespaces)
2. Under **Secrets**, click **New secret**
3. **Name:** `GOOGLE_API_KEY`, **Value:** your key ([get one here](https://aistudio.google.com/apikey))
4. Under **Repository access**, select the Lucid repository

Then create the Codespace. It will automatically:
- Build both backend and frontend containers
- Download fonts during build
- Inject your API key into the backend
- Forward ports 5173 (frontend) and 8000 (API)
- Open the app in your browser

### Option 2: Local Docker

```bash
# Clone and start
git clone <repo-url>
cd Lucid
cp .env.example .env  # Add your GOOGLE_API_KEY

# Initialize config file (prevents Docker from creating a directory)
echo '{}' > config.json

# Build and run (fonts download automatically)
docker-compose up --build
```

The app will be available at `http://localhost:5173`.

## Setting Up Your Google API Key

Lucid uses the Google Gemini API for text generation and image generation. You need a `GOOGLE_API_KEY` to enable AI features.

**Get a key:** Go to [Google AI Studio](https://aistudio.google.com/apikey) and create an API key.

### GitHub Codespaces

Set the key as a Codespaces secret so it's automatically available in every Codespace:

1. Go to [github.com/settings/codespaces](https://github.com/settings/codespaces)
2. Under **Secrets**, click **New secret**
3. **Name:** `GOOGLE_API_KEY`, **Value:** your API key
4. Under **Repository access**, select the Lucid repository
5. Click **Add secret**
6. Create (or rebuild) your Codespace — the key is injected automatically

### Local Docker

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Then edit `.env` and fill in your key:

```
GOOGLE_API_KEY=your-api-key-here
```

Restart containers with `docker compose up` to pick up the change.

### Without an API Key

The app runs without an API key — image generation returns gradient placeholders and text generation is unavailable. This is useful for frontend/UI development.

## Tech Stack

**Backend:**
- Python 3.13
- FastAPI
- Google Generative AI (Gemini 3 Flash Preview, Gemini 2.5 Flash Image)
- Pillow (PIL)
- Pydantic

**Frontend:**
- Node 25
- React 18
- TypeScript
- Vite
- Tailwind CSS
- Axios

## Manual Setup

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download fonts (required for typography)
python download_fonts.py

# Set Google API key (optional - placeholder images work without it)
export GOOGLE_API_KEY="your-api-key"

# Run the server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

## v0.2 Improvements

### Docker Infrastructure
- Zero-config startup with `docker-compose up --build`
- Fonts download during build (no manual steps required)
- Hot-reload volumes for development

### Rendering Engine
- **Binary Search Fitting**: O(log n) text sizing instead of O(n) linear decrement
- **Fuzzy Font Matching**: Requests "Montserrat 600" but only 700 exists → returns 700

### Session Persistence
- Sessions persist to `sessions_db.json` during development
- Survives Docker hot-reloads without losing progress

### Stage-Scoped Chat
- Commands are validated against current stage
- Helpful error messages when using wrong-stage commands
- Frontend autocomplete shows only available commands

### Bi-Directional Navigation
- Back buttons on Stage 2, 3, and 4
- `/back` command in chat
- Fix upstream content without starting over

## Chat Commands

**Stage 1 (Draft → Slides):**
- `/next` - Advance to Stage 2
- `/generate` - Generate slides from draft
- `/regen slide 2` - Regenerate slide 2

**Stage 2 (Slides → Prompts):**
- `/back` - Return to Stage 1
- `/next` - Advance to Stage 3
- `/generate` - Generate image prompts
- `/regen prompt 2` - Regenerate prompt 2

**Stage 3 (Prompts → Images):**
- `/back` - Return to Stage 2
- `/next` - Advance to Stage 4
- `/generate` - Generate background images
- `/regen image 2` - Regenerate image 2

**Stage 4 (Typography):**
- `/back` - Return to Stage 3
- `/style modern|bold|elegant|minimal|impact` - Apply preset
- `/export` - Export carousel as ZIP

## API Endpoints

### Sessions
- `POST /sessions/create` - Create a new session
- `GET /sessions/{id}` - Get session state
- `POST /sessions/next-stage` - Advance to next stage
- `POST /sessions/previous-stage` - Go back to previous stage

### Stage 1-4
Full CRUD operations for each stage. See `/api/docs` when running.

### Chat
- `POST /chat/message` - Send chat message with stage-aware routing

## Project Structure

```
Lucid/
├── .devcontainer/          # GitHub Codespaces configuration
│   └── devcontainer.json
├── docker-compose.yml      # Container orchestration
├── .env.example            # Environment template
├── backend/
│   ├── Dockerfile
│   ├── download_fonts.py   # Font downloader (runs at build)
│   ├── sessions_db.json    # Session persistence
│   ├── app/
│   │   ├── main.py
│   │   ├── models/
│   │   ├── routes/
│   │   └── services/
│   │       ├── font_manager.py      # Fuzzy font matching
│   │       ├── rendering_service.py # Binary search fitting
│   │       ├── session_manager.py   # JSON persistence
│   │       └── chat_service.py      # Stage-scoped tools
│   └── tests/
└── frontend/
    ├── Dockerfile
    └── src/
        ├── components/
        │   ├── ChatBar.tsx     # Autocomplete commands
        │   ├── Stage2.tsx      # Back button
        │   ├── Stage3.tsx      # Back button
        │   └── Stage4.tsx      # Back button
        └── hooks/
            └── useSession.ts   # previousStage support
```

## Testing

```bash
cd backend
pytest -v
```

158 tests covering all services and API endpoints.

## License

MIT
