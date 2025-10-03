#!/bin/bash

# Real-Time Stock Dashboard Setup Script
echo "================================"
echo "Stock Dashboard Setup"
echo "================================"
echo ""

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install finnhub-python websocket-client

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Creating from template..."
    cat > .env << EOF
# OpenAI/Azure Configuration
AZURE_OPENAI_API_KEY=your_azure_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT=your-deployment-name

# Alternative: Standard OpenAI
OPENAI_API_KEY=your_openai_key_here

# Finnhub Configuration (Dashboard)
FINNHUB_API_KEY=your_finnhub_key_here

# Database
DATABASE_URL=sqlite:///./app.db

# JWT Secret
JWT_SECRET=your-secret-key-change-this-in-production
EOF
    echo "✅ Created .env file. Please edit it with your API keys."
fi

# Check if Finnhub API key is set
if grep -q "your_finnhub_key_here" .env 2>/dev/null; then
    echo ""
    echo "⚠️  IMPORTANT: Set your Finnhub API key in .env file"
    echo ""
    echo "Get a free API key:"
    echo "1. Visit: https://finnhub.io/"
    echo "2. Click 'Get free API key'"
    echo "3. Sign up and copy your key"
    echo "4. Add to .env: FINNHUB_API_KEY=your_key_here"
    echo ""
fi

# Check frontend dependencies
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
else
    echo "✅ Frontend dependencies already installed"
fi

echo ""
echo "================================"
echo "✅ Setup Complete!"
echo "================================"
echo ""
echo "To start the application:"
echo ""
echo "1. Backend (Terminal 1):"
echo "   uvicorn main:app --reload"
echo ""
echo "2. Frontend (Terminal 2):"
echo "   cd frontend && npm run dev"
echo ""
echo "3. Access the dashboard:"
echo "   http://localhost:5173"
echo "   Login → Click 'Dashboard' tab"
echo ""
echo "📚 See DASHBOARD_GUIDE.md for full documentation"
echo ""
