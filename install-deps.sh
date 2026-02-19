#!/bin/bash
# Install all dependencies for Lucid development

set -e

echo "=== Installing Lucid dependencies ==="

# Backend Python dependencies
echo "Installing backend Python dependencies..."
cd backend
pip install -r requirements.txt
cd ..

# Frontend Node.js dependencies
echo "Installing frontend Node.js dependencies..."
cd frontend
npm install
cd ..

echo "=== All dependencies installed successfully ==="
echo ""
echo "Next steps:"
echo "1. Set up Google API key (optional): cp .env.example .env"
echo "2. Initialize config: echo '{}' > config.json"
echo "3. Run the app: docker-compose up --build"
echo ""
echo "Or run manually:"
echo "- Backend: cd backend && uvicorn app.main:app --reload --port 8000"
echo "- Frontend: cd frontend && npm run dev"