# Docker Deployment Guide

This guide explains how to deploy the Running Coach Service as a Docker container on your home server.

## Overview

The Running Coach Service is now a standalone web application that can be accessed via HTTP. It's AI-provider agnostic and supports:

- **Claude** (Anthropic)
- **ChatGPT** (OpenAI)
- **Gemini** (Google)
- **Ollama** (Local LLMs)

## Prerequisites

- Docker and Docker Compose installed on your server
- API key for your chosen AI provider (or Ollama installed for local LLMs)
- (Optional) Garmin Connect credentials for health data sync

## Quick Start

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd running-coach
```

### 2. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your configuration
nano .env
```

**Required Configuration:**

```bash
# Choose your AI provider
AI_PROVIDER=claude  # or openai, gemini, ollama

# Add your API key (depending on provider)
ANTHROPIC_API_KEY=your_key_here
# OR
OPENAI_API_KEY=your_key_here
# OR
GOOGLE_API_KEY=your_key_here
```

**Optional Configuration:**

```bash
# Garmin Connect (for health data sync)
GARMIN_EMAIL=your@email.com
GARMIN_PASSWORD=your_password

# Server settings
PORT=5000
DEBUG=false
```

### 3. Start the Service

**Using Claude, OpenAI, or Gemini:**

```bash
docker-compose up -d
```

**Using Ollama (local LLM):**

```bash
# Start with Ollama included
docker-compose --profile ollama up -d

# Pull your desired model (first time only)
docker exec ollama ollama pull llama3.1:latest
```

### 4. Access the Service

Open your browser and navigate to:

```
http://your-server-ip:5000
```

You should see the Running Coach web interface.

## Configuration Options

### AI Provider Selection

Set the `AI_PROVIDER` environment variable to choose your AI backend:

```bash
# Claude (Anthropic) - Best for detailed, nuanced coaching
AI_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-...

# ChatGPT (OpenAI) - Fast and versatile
AI_PROVIDER=openai
OPENAI_API_KEY=sk-...

# Gemini (Google) - Good balance of speed and quality
AI_PROVIDER=gemini
GOOGLE_API_KEY=AIza...

# Ollama (Local) - Free, private, no API costs
AI_PROVIDER=ollama
OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL=llama3.1:latest
```

### Model Preferences

Each agent can specify a model preference (fast/default/powerful). The mapping varies by provider:

**Claude:**
- Fast: `claude-3-5-haiku-20241022`
- Default: `claude-3-5-sonnet-20241022`
- Powerful: `claude-3-opus-20240229`

**OpenAI:**
- Fast: `gpt-4o-mini`
- Default: `gpt-4o`
- Powerful: `gpt-4o`

**Gemini:**
- Fast: `gemini-1.5-flash`
- Default: `gemini-1.5-pro`
- Powerful: `gemini-1.5-pro`

**Ollama:**
- Fast: `llama3.2:latest`
- Default: `llama3.1:latest`
- Powerful: `llama3.1:70b`

## API Endpoints

The service exposes the following HTTP endpoints:

### `GET /`
Web interface for interacting with the coach

### `GET /api/health`
Health check endpoint
```json
{
  "status": "healthy",
  "provider": "Claude",
  "agents_loaded": 4
}
```

### `GET /api/agents`
List available coaching agents
```json
{
  "agents": {
    "running-coach": "Expert running coach...",
    "strength-coach": "Strength training specialist...",
    ...
  }
}
```

### `POST /api/chat`
Send a coaching query

**Request:**
```json
{
  "query": "What should I run today?",
  "agent": "running-coach",  // optional
  "history": []  // optional conversation history
}
```

**Response:**
```json
{
  "response": "Based on your current training...",
  "agent": "running-coach"
}
```

### `POST /api/chat/stream`
Stream a coaching response (for real-time output)

## Data Persistence

The following directories are mounted as volumes to persist data:

- `./data` - Athlete profile, health data, workout library
- `./.claude` - Agent configurations
- `./config` - Service configuration files

These directories will persist even if the container is recreated.

## Ollama Setup

### Using Ollama with Docker Compose

The `docker-compose.yml` includes an optional Ollama service:

```bash
# Start both services
docker-compose --profile ollama up -d

# Check Ollama is running
docker exec ollama ollama list

# Pull a model (first time)
docker exec ollama ollama pull llama3.1:latest

# Or pull a different model
docker exec ollama ollama pull mistral:latest
```

### Using External Ollama

If you have Ollama running elsewhere:

```bash
# In .env file
AI_PROVIDER=ollama
OLLAMA_HOST=http://your-ollama-host:11434
OLLAMA_MODEL=llama3.1:latest

# Then start without the ollama profile
docker-compose up -d
```

## Health Data Sync

To sync data from Garmin Connect:

```bash
# Enter the container
docker exec -it running-coach bash

# Run sync script
bash bin/sync_garmin_data.sh

# Or with Python directly
python3 src/garmin_sync.py --days 30 --summary
```

You can also set up a cron job on your host to run this periodically:

```bash
# Add to crontab (sync daily at 6 AM)
0 6 * * * docker exec running-coach bash bin/sync_garmin_data.sh --quiet
```

## Updating the Service

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose down
docker-compose build
docker-compose up -d
```

## Troubleshooting

### Container won't start

```bash
# Check logs
docker-compose logs running-coach

# Common issues:
# 1. Missing API key - check .env file
# 2. Port already in use - change PORT in .env
# 3. Invalid provider name - check AI_PROVIDER spelling
```

### Can't connect to Ollama

```bash
# Verify Ollama is running
docker ps | grep ollama

# Check Ollama logs
docker logs ollama

# Test Ollama connection
docker exec ollama ollama list
```

### Health data not syncing

```bash
# Verify Garmin credentials
docker exec running-coach bash -c 'echo $GARMIN_EMAIL'

# Test sync manually
docker exec -it running-coach bash
bash bin/sync_garmin_data.sh
```

### AI responses are slow

- **Claude/OpenAI/Gemini**: Check your network connection and API status
- **Ollama**: Use a smaller model (llama3.2) or ensure adequate CPU/RAM

## Security Considerations

1. **API Keys**: Keep your `.env` file secure and never commit it to version control
2. **Network**: Consider using a reverse proxy (nginx) with HTTPS
3. **Firewall**: Restrict access to port 5000 to trusted networks only
4. **Updates**: Regularly update the Docker images and dependencies

## Advanced Configuration

### Reverse Proxy with Nginx

```nginx
server {
    listen 80;
    server_name coach.yourdomain.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### Custom Port

```bash
# In .env
PORT=8080

# Update docker-compose.yml ports section
ports:
  - "8080:8080"
```

### Resource Limits

Add to `docker-compose.yml`:

```yaml
services:
  running-coach:
    # ... other config ...
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

## Support

For issues or questions:
- Check the logs: `docker-compose logs running-coach`
- Review the API documentation above
- Check the main README.md for project details
