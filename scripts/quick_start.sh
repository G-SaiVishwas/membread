#!/bin/bash
# Quick start script for Membread

set -e

echo "=========================================="
echo "Membread Quick Start"
echo "=========================================="

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your OPENAI_API_KEY"
    exit 1
fi

# Check if OPENAI_API_KEY is set
if ! grep -q "OPENAI_API_KEY=sk-" .env; then
    echo "⚠️  Please set OPENAI_API_KEY in .env file"
    exit 1
fi

echo "✅ Environment configured"

# Start services
echo ""
echo "Starting PostgreSQL and Membread..."
docker-compose up -d

echo ""
echo "Waiting for services to be ready..."
sleep 10

echo ""
echo "✅ Membread is running!"
echo ""
echo "Next steps:"
echo "1. Generate a test token: python scripts/generate_token.py"
echo "2. Run the demo: python demo.py"
echo "3. Check logs: docker-compose logs -f membread"
echo ""
echo "To stop: docker-compose down"
echo "=========================================="
