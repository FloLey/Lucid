# Lucid v0.2

Transform rough drafts into polished social media carousels.

Lucid is a containerized web application that turns your ideas into beautiful 4:5 aspect ratio carousel slides (1080x1350px) ready for Instagram and other social platforms.

## Features

- **4-Stage Workflow**: Draft → Slide Texts → Image Prompts → Final Slides
- **AI-Powered Generation**: Uses Gemini 3 Flash Preview for text and Gemini 2.5 Flash for images
- **Typography Rendering**: PIL-based text rendering with binary search fitting algorithm
- **Fuzzy Font Matching**: Intelligent font loading with weight approximation
- **Session Persistence**: Sessions survive Docker hot-reloads during development
- **Stage-Scoped Chat**: Context-aware commands with autocomplete
- **Bi-Directional Navigation**: Navigate back and forth between stages
- **Style Presets**: Modern, Bold, Elegant, Minimal, and Impact styles
- **Export**: Download as ZIP with all slides and metadata

## Quick Start (Docker)

```bash
# Clone and start
git clone <repo-url>
cd Lucid
cp .env.example .env  # Add your GEMINI_API_KEY if you have one

# Build and run (fonts download automatically)
docker-compose up --build
```

The app will be available at `http://localhost:5173`.

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

# Set Gemini API key (optional - mock responses work without it)
export GEMINI_API_KEY="your-api-key"

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
