"""
Flask web application for the running coach service.
"""

import os
from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS

from ..coach_service import CoachService
from ..ai_providers import get_provider


# Create Flask app
app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# Initialize coach service
try:
    provider = get_provider()
    coach_service = CoachService(ai_provider=provider)
    print(f"✓ Initialized with {provider.get_provider_name()} provider")
except Exception as e:
    print(f"Warning: Failed to initialize AI provider: {e}")
    print("Service will start but may not be functional.")
    coach_service = None


@app.route('/')
def index():
    """Serve the main HTML interface."""
    agents = coach_service.list_agents() if coach_service else {}
    provider_name = coach_service.provider.get_provider_name() if coach_service else "Unknown"
    return render_template('index.html', agents=agents, provider=provider_name)


@app.route('/api/health')
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'provider': coach_service.provider.get_provider_name() if coach_service else None,
        'agents_loaded': len(coach_service.agent_loader.agents) if coach_service else 0
    })


@app.route('/api/agents')
def list_agents():
    """List available coaching agents."""
    if not coach_service:
        return jsonify({'error': 'Service not initialized'}), 503

    return jsonify({
        'agents': coach_service.list_agents()
    })


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Handle coaching chat requests.

    Expected JSON:
    {
        "query": "What should I run today?",
        "agent": "running-coach",  // optional
        "history": [...]  // optional conversation history
    }
    """
    if not coach_service:
        return jsonify({'error': 'Service not initialized'}), 503

    data = request.get_json()

    if not data or 'query' not in data:
        return jsonify({'error': 'Missing query parameter'}), 400

    query = data['query']
    agent_name = data.get('agent')
    history = data.get('history', [])

    try:
        response = coach_service.chat(
            query=query,
            agent_name=agent_name,
            conversation_history=history
        )

        return jsonify({
            'response': response,
            'agent': coach_service._select_agent(query, agent_name)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat/stream', methods=['POST'])
def chat_stream():
    """
    Stream coaching chat responses.

    Expected JSON:
    {
        "query": "What should I run today?",
        "agent": "running-coach",  // optional
        "history": [...]  // optional conversation history
    }
    """
    if not coach_service:
        return jsonify({'error': 'Service not initialized'}), 503

    data = request.get_json()

    if not data or 'query' not in data:
        return jsonify({'error': 'Missing query parameter'}), 400

    query = data['query']
    agent_name = data.get('agent')
    history = data.get('history', [])

    def generate():
        """Generator for streaming response."""
        try:
            for chunk in coach_service.stream_chat(
                query=query,
                agent_name=agent_name,
                conversation_history=history
            ):
                yield chunk
        except Exception as e:
            yield f"\n\nError: {str(e)}"

    return Response(generate(), mimetype='text/plain')


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')
    debug = os.getenv('DEBUG', 'false').lower() == 'true'

    print(f"\n{'='*60}")
    print(f"Running Coach Service")
    print(f"{'='*60}")
    print(f"Provider: {coach_service.provider.get_provider_name() if coach_service else 'Not initialized'}")
    print(f"Agents loaded: {len(coach_service.agent_loader.agents) if coach_service else 0}")
    if coach_service:
        for agent_name in coach_service.agent_loader.list_agents():
            print(f"  - {agent_name}")
    print(f"{'='*60}\n")

    app.run(host=host, port=port, debug=debug)
