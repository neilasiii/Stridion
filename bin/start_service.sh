#!/bin/bash
#
# Start the Running Coach Service
#
# This script starts the running coach web service either in Docker
# or directly on the host system.
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

usage() {
    echo "Usage: $0 [docker|local] [options]"
    echo ""
    echo "Modes:"
    echo "  docker    - Start service in Docker container (recommended)"
    echo "  local     - Start service on local system (development)"
    echo ""
    echo "Options:"
    echo "  --ollama  - Include Ollama container (Docker mode only)"
    echo "  --build   - Force rebuild of Docker image"
    echo ""
    echo "Examples:"
    echo "  $0 docker                 # Start in Docker"
    echo "  $0 docker --ollama        # Start with Ollama"
    echo "  $0 local                  # Start locally"
    exit 1
}

start_docker() {
    local compose_args=""
    local build=false

    # Parse options
    for arg in "$@"; do
        case $arg in
            --ollama)
                compose_args="--profile ollama"
                ;;
            --build)
                build=true
                ;;
        esac
    done

    echo "Starting Running Coach Service in Docker..."
    cd "$PROJECT_ROOT"

    # Check for .env file
    if [ ! -f .env ]; then
        echo "⚠️  No .env file found. Creating from .env.example..."
        cp .env.example .env
        echo "⚠️  Please edit .env with your API keys before continuing."
        echo "Run: nano .env"
        exit 1
    fi

    # Build if requested
    if [ "$build" = true ]; then
        echo "Building Docker image..."
        docker-compose build
    fi

    # Start services
    echo "Starting services..."
    docker-compose $compose_args up -d

    # Wait for service to be healthy
    echo "Waiting for service to start..."
    sleep 5

    # Check health
    if curl -s http://localhost:5000/api/health > /dev/null 2>&1; then
        echo "✓ Service is running!"
        echo ""
        echo "Web interface: http://localhost:5000"
        echo "API endpoint: http://localhost:5000/api/chat"
        echo ""
        echo "View logs: docker-compose logs -f running-coach"
        echo "Stop service: docker-compose down"
    else
        echo "⚠️  Service may not be ready yet. Check logs:"
        echo "docker-compose logs running-coach"
    fi
}

start_local() {
    echo "Starting Running Coach Service locally..."
    cd "$PROJECT_ROOT"

    # Check for .env file
    if [ -f .env ]; then
        echo "Loading environment from .env..."
        set -a
        source .env
        set +a
    else
        echo "⚠️  No .env file found. Using environment variables."
    fi

    # Check Python version
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python 3 is required but not found."
        exit 1
    fi

    # Check if virtualenv exists
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi

    # Activate virtualenv
    source venv/bin/activate

    # Install dependencies
    echo "Installing dependencies..."
    pip install -q -r requirements.txt

    # Start service
    echo "Starting web service..."
    export PYTHONPATH="$PROJECT_ROOT"
    python3 -m src.web.app
}

# Main
if [ $# -lt 1 ]; then
    usage
fi

MODE=$1
shift

case $MODE in
    docker)
        start_docker "$@"
        ;;
    local)
        start_local "$@"
        ;;
    *)
        usage
        ;;
esac
