#!/bin/bash
# Docker setup script for quick deployment

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/.."

echo "================================"
echo "Legal Tabular Review - Docker Setup"
echo "================================"
echo

# Check Docker installation
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    echo "Please install Docker from https://www.docker.com/products/docker-desktop"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed"
    exit 1
fi

echo "✓ Docker version: $(docker --version)"
echo "✓ Docker Compose version: $(docker-compose --version)"
echo

# Check if .env exists
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo "Creating .env file..."
    
    read -p "Which environment? (dev/staging/prod) [dev]: " ENV
    ENV=${ENV:-dev}
    
    if [ "$ENV" = "prod" ]; then
        cp "$PROJECT_ROOT/.env.production" "$PROJECT_ROOT/.env"
        echo "⚠️  IMPORTANT: Edit .env and set strong passwords!"
        echo "   - POSTGRES_PASSWORD"
        echo "   - SECRET_KEY"
    else
        cp "$PROJECT_ROOT/.env.development" "$PROJECT_ROOT/.env"
        echo "✓ Using development environment"
    fi
fi

echo

# Build images
read -p "Build Docker images? (y/N): " BUILD
if [ "$BUILD" = "y" ]; then
    echo "Building images..."
    
    if [ "$ENV" = "dev" ]; then
        docker-compose -f "$PROJECT_ROOT/docker/docker-compose.dev.yml" build
    else
        docker-compose -f "$PROJECT_ROOT/docker/docker-compose.yml" build
    fi
    
    echo "✓ Images built successfully"
fi

echo

# Start services
read -p "Start services? (Y/n): " START
if [ "$START" != "n" ]; then
    echo "Starting services..."
    
    if [ "$ENV" = "dev" ]; then
        docker-compose -f "$PROJECT_ROOT/docker/docker-compose.dev.yml" up -d
        
        echo "✓ Services started"
        echo
        echo "Access services at:"
        echo "  Frontend: http://localhost:5173"
        echo "  Backend: http://localhost:8000"
        echo "  API Docs: http://localhost:8000/docs"
        echo "  pgAdmin: http://localhost:5050"
    else
        docker-compose -f "$PROJECT_ROOT/docker/docker-compose.yml" up -d
        
        echo "✓ Services started"
        echo
        echo "Access services at:"
        echo "  Nginx: http://localhost"
        echo "  API: http://localhost/api"
        echo "  API Docs: http://localhost/api/docs"
    fi
    
    echo
    echo "Monitor services:"
    echo "  docker-compose ps"
    echo "  docker-compose logs -f backend"
fi

echo
echo "✓ Setup complete!"
