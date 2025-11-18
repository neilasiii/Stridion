# Running Coach Service Architecture

## Overview

The Running Coach Service is a dockerized web application that provides personalized running, strength, mobility, and nutrition coaching through a simple HTTP interface. The system is AI-provider agnostic, supporting multiple LLM backends.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         Client Layer                         │
│  (Web Browser, Mobile App, API Client, Home Assistant)      │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/HTTPS
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      Flask Web Service                       │
│                     (src/web/app.py)                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Routes:                                              │   │
│  │  - GET  /              → Web UI                      │   │
│  │  - GET  /api/health    → Health check                │   │
│  │  - GET  /api/agents    → List agents                 │   │
│  │  - POST /api/chat      → Coaching query              │   │
│  │  - POST /api/chat/stream → Streaming response        │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Coach Service Layer                       │
│                 (src/coach_service/)                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  CoachService                                         │   │
│  │  - Query routing to appropriate agent                │   │
│  │  - Context loading (athlete profile, health data)    │   │
│  │  - Conversation history management                   │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  AgentLoader                                          │   │
│  │  - Loads agent configs from .claude/agents/*.md      │   │
│  │  - Parses YAML frontmatter + system prompts          │   │
│  │  - Provides agent selection and metadata             │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   AI Provider Layer                          │
│                 (src/ai_providers/)                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  AIProvider (Abstract Base Class)                     │   │
│  │  - chat() - Synchronous chat                         │   │
│  │  - stream_chat() - Streaming responses               │   │
│  │  - get_model_name() - Model selection                │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌────────────┬─────────────┬─────────────┬─────────────┐   │
│  │  Claude    │  OpenAI     │  Gemini     │  Ollama     │   │
│  │  Provider  │  Provider   │  Provider   │  Provider   │   │
│  └────────────┴─────────────┴─────────────┴─────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                     External Services                        │
│  ┌────────────┬─────────────┬─────────────┬─────────────┐   │
│  │ Anthropic  │   OpenAI    │   Google    │   Ollama    │   │
│  │    API     │     API     │     API     │  (Local)    │   │
│  └────────────┴─────────────┴─────────────┴─────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Coaching Query Flow

```
User Query
    ↓
Web Interface (POST /api/chat)
    ↓
CoachService.chat()
    ├─ Select appropriate agent (auto-detect or explicit)
    ├─ Load athlete context (data/athlete/*.md)
    ├─ Load health data summary (data/health/health_data_cache.json)
    ├─ Build enhanced query with context
    └─ Call AI Provider
         ↓
    AIProvider.chat()
         ├─ Format messages for specific provider
         ├─ Apply agent's system prompt
         └─ Call external API
              ↓
         Response
              ↓
    Return to user
```

### 2. Agent Selection Logic

The `CoachService._select_agent()` method uses keyword matching:

- **running-coach**: run, pace, threshold, interval, marathon, vdot
- **strength-coach**: strength, lift, squat, deadlift, gym
- **mobility-coach-runner**: mobility, stretch, flexibility, foam roll
- **endurance-nutrition-coach**: nutrition, diet, fuel, eat, meal

Default: `running-coach`

## Component Details

### AI Provider Abstraction

**Base Interface** (`src/ai_providers/base.py`):
- Defines `AIProvider` abstract class
- Common `Message` and `AgentConfig` data structures
- Enforces consistent interface across providers

**Implementations**:
1. **ClaudeProvider** - Anthropic API
   - Models: haiku (fast), sonnet (default), opus (powerful)
   - System prompts via separate parameter

2. **OpenAIProvider** - OpenAI API
   - Models: gpt-4o-mini (fast), gpt-4o (default/powerful)
   - System prompts as first message

3. **GeminiProvider** - Google Generative AI
   - Models: gemini-1.5-flash (fast), gemini-1.5-pro (default/powerful)
   - System prompts via system_instruction parameter

4. **OllamaProvider** - Local LLMs
   - Models: configurable (llama3.2, llama3.1, llama3.1:70b)
   - HTTP API to local Ollama instance

**Factory Pattern** (`src/ai_providers/factory.py`):
```python
provider = get_provider('claude')  # or 'openai', 'gemini', 'ollama'
```

### Agent System

**Agent Configuration** (`.claude/agents/*.md`):
```markdown
---
name: running-coach
description: Expert running coach
model: sonnet
---

<System prompt content>
```

**AgentLoader**:
- Scans `.claude/agents/` directory
- Parses YAML frontmatter
- Loads system prompts
- Provides agent metadata and selection

### Context Management

**Athlete Context Files** (`data/athlete/`):
- `goals.md` - Training objectives
- `training_history.md` - Past training, injuries
- `training_preferences.md` - Schedule, equipment, diet
- `upcoming_races.md` - Race calendar
- `current_training_status.md` - Current VDOT, paces
- `communication_preferences.md` - Detail level
- `health_profile.md` - Health summary

**Health Data** (`data/health/health_data_cache.json`):
- Recent activities (runs with pace, HR, distance)
- Sleep data
- Resting heart rate trends
- VO2 max estimates
- Weight tracking

The `CoachService` automatically loads and includes this context with each query.

## Deployment Architecture

### Docker Deployment

```
┌─────────────────────────────────────────────────────────┐
│                     Docker Host                          │
│  ┌────────────────────────────────────────────────┐     │
│  │  running-coach container                       │     │
│  │  - Flask web service                           │     │
│  │  - Port 5000 exposed                           │     │
│  │  - Volumes:                                    │     │
│  │    - ./data → /app/data                        │     │
│  │    - ./.claude → /app/.claude                  │     │
│  │    - ./config → /app/config                    │     │
│  └────────────────────────────────────────────────┘     │
│  ┌────────────────────────────────────────────────┐     │
│  │  ollama container (optional)                   │     │
│  │  - Local LLM inference                         │     │
│  │  - Port 11434 exposed                          │     │
│  │  - Volume: ollama_data                         │     │
│  └────────────────────────────────────────────────┘     │
│                                                          │
│  Network: running-coach-network (bridge)                │
└─────────────────────────────────────────────────────────┘
```

### Environment Configuration

Via `.env` file:
```bash
AI_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-...
GARMIN_EMAIL=user@example.com
GARMIN_PASSWORD=password
PORT=5000
DEBUG=false
```

## Data Persistence

**Docker Volumes**:
- `./data` - All athlete and health data
- `./.claude` - Agent configurations
- `./config` - Service settings
- `ollama_data` - Ollama models (if using)

These ensure data survives container restarts/recreations.

## API Design

**RESTful Endpoints**:
- `GET /api/health` - Service status
- `GET /api/agents` - Available coaches
- `POST /api/chat` - Synchronous coaching
- `POST /api/chat/stream` - Streaming responses

**Request Format**:
```json
{
  "query": "User question",
  "agent": "running-coach",  // optional
  "history": [...]           // optional
}
```

**Response Format**:
```json
{
  "response": "AI response",
  "agent": "agent-name"
}
```

## Security Considerations

1. **API Keys**: Stored in environment variables, never in code
2. **Network**: Service binds to 0.0.0.0 in container (internal network)
3. **Reverse Proxy**: Recommended for production (nginx + HTTPS)
4. **Authentication**: Not implemented (should add for production)
5. **Rate Limiting**: Not implemented (add via reverse proxy)

## Extensibility

### Adding New AI Provider

1. Create `src/ai_providers/newprovider.py`:
```python
class NewProvider(AIProvider):
    def validate_config(self): ...
    def chat(self, ...): ...
    def stream_chat(self, ...): ...
    def get_model_name(self, ...): ...
```

2. Register in `factory.py`:
```python
PROVIDERS = {
    ...
    'newprovider': NewProvider
}
```

3. Add to `.env.example` and documentation

### Adding New Agent

1. Create `.claude/agents/new-agent.md`:
```markdown
---
name: new-agent
description: Agent description
model: default
---

System prompt here...
```

2. Add keyword detection in `CoachService._select_agent()`

3. Update documentation

## Performance Considerations

**Response Times**:
- **Claude Sonnet**: 2-5 seconds typical
- **OpenAI GPT-4o**: 1-3 seconds typical
- **Gemini Pro**: 1-4 seconds typical
- **Ollama (local)**: 5-30 seconds depending on hardware

**Optimizations**:
- Use streaming responses for better UX
- Cache athlete context (loaded once per request)
- Use faster models for simple queries (haiku, gpt-4o-mini, flash)
- Consider response caching for common queries

## Monitoring

**Health Checks**:
```bash
# Docker
docker-compose ps
docker-compose logs running-coach

# API
curl http://localhost:5000/api/health
```

**Metrics to Monitor**:
- Container resource usage (CPU, RAM)
- API response times
- Error rates
- Provider API costs (Claude, OpenAI, Gemini)

## Future Enhancements

1. **Authentication & Authorization**
   - API key management
   - Multi-user support

2. **Advanced Features**
   - Conversation persistence (database)
   - Training plan generation and storage
   - Calendar integrations
   - Mobile apps

3. **Performance**
   - Response caching (Redis)
   - Async processing (Celery)
   - Load balancing for multiple instances

4. **Analytics**
   - Usage tracking
   - Cost monitoring
   - Query analytics

5. **Integration**
   - Strava sync
   - TrainingPeaks integration
   - Webhook support
