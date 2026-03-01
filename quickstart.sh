#!/bin/bash
# Membread Quick Start Script

set -e

echo "=================================================="
echo "Membread - Quick Start"
echo "=================================================="

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your OPENAI_API_KEY"
    echo "   Then run this script again."
    exit 1
fi

# Check if OPENAI_API_KEY is set
if ! grep -q "OPENAI_API_KEY=sk-" .env 2>/dev/null; then
    echo "⚠️  OPENAI_API_KEY not set in .env file"
    echo "   Please add your OpenAI API key to .env"
    exit 1
fi

echo "✅ Environment configured"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not found. Please install Docker Compose first."
    exit 1
fi

echo "✅ Docker and Docker Compose found"

# Start services
echo ""
echo "🚀 Starting Membread services..."
docker-compose up -d

echo ""
echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 10

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    echo "✅ Services are running!"
    echo ""
    echo "=================================================="
    echo "Membread is ready!"
    echo "=================================================="
    echo ""
    echo "📊 Service Status:"
    docker-compose ps
    echo ""
    echo "📝 Next Steps:"
    echo "  1. Generate a test JWT token:"
    echo "     python -c \"from src.auth.jwt_authenticator import JWTAuthenticator; print(JWTAuthenticator().generate_token('tenant-1', 'user-1'))\""
    echo ""
    echo "  2. Run the demo:"
    echo "     python demo.py"
    echo ""
    echo "  3. View logs:"
    echo "     docker-compose logs -f membread"
    echo ""
    echo "  4. Stop services:"
    echo "     docker-compose down"
    echo ""
else
    echo "❌ Services failed to start. Check logs:"
    echo "   docker-compose logs"
    exit 1
fi
