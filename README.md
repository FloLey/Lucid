# Lucid

Transform rough drafts into polished social media carousels.

Lucid is a single-page web application that turns your ideas into beautiful 4:5 aspect ratio carousel slides (1080x1350px) ready for Instagram and other social platforms.

## Features

- **4-Stage Workflow**: Draft → Slide Texts → Image Prompts → Final Slides
- **AI-Powered Generation**: Uses Gemini Flash for text and image generation
- **Typography Rendering**: PIL-based text rendering with custom fonts
- **Style Presets**: Modern, Bold, Elegant, Minimal, and Impact styles
- **Chat Interface**: Natural language commands and slash commands
- **Export**: Download as ZIP with all slides and metadata

## Tech Stack

**Backend:**
- Python 3.11+
- FastAPI
- Google Generative AI (Gemini)
- Pillow (PIL)
- Pydantic

**Frontend:**
- React 18
- TypeScript
- Vite
- Tailwind CSS
- Axios

## Setup

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

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

The frontend will be available at `http://localhost:5173` and proxies API requests to the backend at `http://localhost:8000`.

## API Endpoints

### Sessions
- `POST /sessions` - Create a new session
- `GET /sessions/{id}` - Get session state
- `DELETE /sessions/{id}` - Delete session

### Stage 1 - Draft to Slides
- `POST /stage1/generate` - Generate slide texts from draft
- `PUT /stage1/slides/{index}` - Update slide text
- `POST /stage1/regenerate/{index}` - Regenerate specific slide
- `DELETE /stage1/slides/{index}` - Delete slide
- `POST /stage1/slides` - Add new slide

### Stage 2 - Image Prompts
- `POST /stage2/generate` - Generate image prompts
- `PUT /stage2/prompts/{index}` - Update prompt
- `POST /stage2/regenerate/{index}` - Regenerate prompt

### Stage 3 - Image Generation
- `POST /stage3/generate` - Generate background images
- `POST /stage3/regenerate/{index}` - Regenerate image

### Stage 4 - Typography & Rendering
- `POST /stage4/render` - Render slides with typography
- `PUT /stage4/styles/{index}` - Update slide style
- `POST /stage4/apply-preset` - Apply style preset
- `GET /stage4/preview/{index}` - Get rendered slide preview

### Chat
- `POST /chat` - Send chat message for processing

### Export
- `GET /export/{session_id}` - Download carousel as ZIP

### Fonts
- `GET /fonts` - List available fonts
- `GET /fonts/{family}` - Get font variants

## Style Presets

| Preset | Font | Size | Color | Position |
|--------|------|------|-------|----------|
| Modern | Inter | 48 | White | Bottom |
| Bold | Montserrat | 56 | White | Center |
| Elegant | Playfair | 44 | Cream | Bottom |
| Minimal | Roboto | 40 | White | Top |
| Impact | Oswald | 64 | Yellow | Center |

## Chat Commands

**Slash Commands:**
- `/next` - Move to next stage
- `/back` - Go to previous stage
- `/regen slide 2` - Regenerate slide 2
- `/style bold` - Apply bold preset

**Natural Language:**
- "Make the text bigger"
- "Change font to Montserrat"
- "Generate 5 slides about productivity"
- "Export my carousel"

## Project Structure

```
Lucid/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app
│   │   ├── config.py         # Configuration
│   │   ├── models/           # Pydantic models
│   │   ├── routes/           # API routes
│   │   └── services/         # Business logic
│   ├── tests/                # Backend tests
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── components/       # React components
    │   ├── hooks/            # Custom hooks
    │   ├── services/         # API client
    │   └── types/            # TypeScript types
    ├── package.json
    └── vite.config.ts
```

## Testing

```bash
cd backend
pytest -v
```

155 tests covering all services and API endpoints.

## License

MIT
