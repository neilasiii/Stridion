# API Client Examples

This document provides examples of how to interact with the Running Coach Service API from various clients.

## Python Client

```python
import requests

# Service URL
BASE_URL = "http://localhost:5000"

def get_health():
    """Check if service is healthy."""
    response = requests.get(f"{BASE_URL}/api/health")
    return response.json()

def list_agents():
    """Get available coaching agents."""
    response = requests.get(f"{BASE_URL}/api/agents")
    return response.json()

def chat(query, agent=None, history=None):
    """Send a coaching query."""
    payload = {
        "query": query,
    }
    if agent:
        payload["agent"] = agent
    if history:
        payload["history"] = history

    response = requests.post(
        f"{BASE_URL}/api/chat",
        json=payload
    )
    return response.json()

def stream_chat(query, agent=None, history=None):
    """Stream a coaching response."""
    payload = {
        "query": query,
    }
    if agent:
        payload["agent"] = agent
    if history:
        payload["history"] = history

    response = requests.post(
        f"{BASE_URL}/api/chat/stream",
        json=payload,
        stream=True
    )

    for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
        if chunk:
            print(chunk, end='', flush=True)

# Example usage
if __name__ == "__main__":
    # Check health
    print("Service health:", get_health())
    print()

    # List agents
    print("Available agents:", list_agents())
    print()

    # Simple chat
    response = chat("What should I run today?")
    print(f"Agent: {response['agent']}")
    print(f"Response: {response['response']}")
    print()

    # Chat with specific agent
    response = chat(
        "Design a strength workout for me",
        agent="strength-coach"
    )
    print(f"Response: {response['response']}")
    print()

    # Streaming chat
    print("Streaming response:")
    stream_chat("Explain the Jack Daniels VDOT system")
```

## JavaScript/Node.js Client

```javascript
const axios = require('axios');

const BASE_URL = 'http://localhost:5000';

async function getHealth() {
    const response = await axios.get(`${BASE_URL}/api/health`);
    return response.data;
}

async function listAgents() {
    const response = await axios.get(`${BASE_URL}/api/agents`);
    return response.data;
}

async function chat(query, agent = null, history = null) {
    const payload = { query };
    if (agent) payload.agent = agent;
    if (history) payload.history = history;

    const response = await axios.post(`${BASE_URL}/api/chat`, payload);
    return response.data;
}

async function streamChat(query, agent = null, history = null) {
    const payload = { query };
    if (agent) payload.agent = agent;
    if (history) payload.history = history;

    const response = await axios.post(`${BASE_URL}/api/chat/stream`, payload, {
        responseType: 'stream'
    });

    return new Promise((resolve, reject) => {
        let fullResponse = '';

        response.data.on('data', (chunk) => {
            const text = chunk.toString();
            process.stdout.write(text);
            fullResponse += text;
        });

        response.data.on('end', () => {
            resolve(fullResponse);
        });

        response.data.on('error', reject);
    });
}

// Example usage
(async () => {
    // Check health
    console.log('Service health:', await getHealth());

    // List agents
    console.log('Available agents:', await listAgents());

    // Simple chat
    const response = await chat('What should I run today?');
    console.log(`Agent: ${response.agent}`);
    console.log(`Response: ${response.response}`);

    // Streaming chat
    console.log('Streaming response:');
    await streamChat('Explain threshold training');
})();
```

## cURL Examples

### Check Health
```bash
curl http://localhost:5000/api/health
```

### List Agents
```bash
curl http://localhost:5000/api/agents
```

### Simple Chat
```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What should I run today?"
  }'
```

### Chat with Specific Agent
```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Design a strength workout",
    "agent": "strength-coach"
  }'
```

### Chat with History
```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What about tomorrow?",
    "history": [
      {"role": "user", "content": "What should I run today?"},
      {"role": "assistant", "content": "Today you should do..."}
    ]
  }'
```

### Streaming Chat
```bash
curl -X POST http://localhost:5000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Explain VDOT training"
  }' \
  --no-buffer
```

## Home Assistant Integration

You can integrate the Running Coach with Home Assistant using REST commands:

```yaml
# configuration.yaml
rest_command:
  running_coach:
    url: http://your-server:5000/api/chat
    method: POST
    headers:
      Content-Type: application/json
    payload: >
      {
        "query": "{{ query }}",
        "agent": "{{ agent }}"
      }

# Example automation
automation:
  - alias: "Morning Running Advice"
    trigger:
      - platform: time
        at: "06:00:00"
    action:
      - service: rest_command.running_coach
        data:
          query: "What should I run today?"
      - service: notify.mobile_app
        data:
          message: "Check your running coach for today's workout"
```

## iOS Shortcuts

Create an iOS Shortcut to query your running coach:

1. Add a "Text" action with your query
2. Add a "Get Contents of URL" action:
   - URL: `http://your-server:5000/api/chat`
   - Method: POST
   - Headers: `Content-Type: application/json`
   - Request Body: JSON
     ```json
     {
       "query": "[Text from step 1]"
     }
     ```
3. Add a "Get Dictionary Value" action for "response"
4. Add a "Show Result" action

## Response Format

### Successful Response

```json
{
  "response": "Based on your current training phase...",
  "agent": "running-coach"
}
```

### Error Response

```json
{
  "error": "Service not initialized"
}
```

HTTP status codes:
- `200` - Success
- `400` - Bad request (missing parameters)
- `500` - Server error
- `503` - Service unavailable

## Rate Limiting

The service does not currently implement rate limiting, but consider:
- Implementing a reverse proxy with rate limiting (nginx)
- Using API gateway services
- Implementing authentication for production use

## Authentication (Future)

For production deployments, consider adding authentication:

```python
# Example with API key
headers = {
    "Authorization": "Bearer your-api-key",
    "Content-Type": "application/json"
}

response = requests.post(
    f"{BASE_URL}/api/chat",
    headers=headers,
    json={"query": "What should I run?"}
)
```
