#!/bin/bash
# iGosa — Development Setup Script
# Run: bash scripts/dev_setup.sh

set -e

echo "🏠 iGosa — Development Setup"
echo "============================"

# Check Python version
python3 --version

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Copy .env if not exists
if [ ! -f ".env" ]; then
    echo "📝 Creating .env from template..."
    cp .env.example .env
    echo "⚠️  Edit .env with your API keys!"
fi

# Initialize database
echo "🗄️  Initializing database..."
python scripts/init_db.py

echo ""
echo "✅ Setup complete!"
echo ""
echo "▶️  Start the server:"
echo "   source venv/bin/activate"
echo "   uvicorn app.main:app --reload --port 8000"
echo ""
echo "📖 API docs: http://localhost:8000/docs"
echo "🩺 Health:   http://localhost:8000/webhook/health"
