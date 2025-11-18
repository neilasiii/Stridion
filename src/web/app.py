"""
Flask web application for the running coach service.
"""

import os
from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS

from ..coach_service import CoachService, FileManager
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

# Initialize file manager
file_manager = FileManager()

# Constants
VALID_CATEGORIES = ['plans', 'frameworks', 'calendar']
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


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


@app.route('/api/files', methods=['GET'])
def list_files():
    """
    List available files.

    Query params:
        category: Filter by category (plans, frameworks, calendar)
    """
    category = request.args.get('category')

    try:
        files = file_manager.list_files(category=category)
        return jsonify({'files': files})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/files/<category>/<filename>', methods=['GET'])
def download_file(category, filename):
    """
    Download a specific file.

    Args:
        category: File category (plans, frameworks, calendar)
        filename: Filename
    """
    # Validate category
    if category not in VALID_CATEGORIES:
        return jsonify({'error': 'Invalid category'}), 400

    try:
        content = file_manager.get_file(filename, category)

        if content is None:
            return jsonify({'error': 'File not found'}), 404

        # Determine MIME type based on extension
        if filename.endswith('.md'):
            mimetype = 'text/markdown'
        elif filename.endswith('.ics'):
            mimetype = 'text/calendar'
        elif filename.endswith('.json'):
            mimetype = 'application/json'
        else:
            mimetype = 'text/plain'

        return Response(
            content,
            mimetype=mimetype,
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"'
            }
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/files', methods=['POST'])
def save_file():
    """
    Save a new file.

    Expected JSON:
    {
        "content": "File content...",
        "filename": "my_plan.md",
        "category": "plans",
        "metadata": {...}  // optional
    }
    """
    data = request.get_json()

    if not data or 'content' not in data or 'filename' not in data:
        return jsonify({'error': 'Missing required parameters'}), 400

    content = data['content']
    filename = data['filename']
    category = data.get('category', 'plans')
    metadata = data.get('metadata', {})

    # Validate category
    if category not in VALID_CATEGORIES:
        return jsonify({'error': 'Invalid category'}), 400

    # Validate file size
    if len(content) > MAX_FILE_SIZE:
        return jsonify({'error': f'File too large. Maximum size is {MAX_FILE_SIZE / (1024*1024):.0f}MB'}), 413

    try:
        file_path = file_manager.save_file(
            content=content,
            filename=filename,
            category=category,
            metadata=metadata
        )

        return jsonify({
            'success': True,
            'filename': filename,
            'category': category,
            'path': file_path
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/files/<category>/<filename>', methods=['DELETE'])
def delete_file(category, filename):
    """
    Delete a file.

    Args:
        category: File category
        filename: Filename
    """
    # Validate category
    if category not in VALID_CATEGORIES:
        return jsonify({'error': 'Invalid category'}), 400

    try:
        success = file_manager.delete_file(filename, category)

        if not success:
            return jsonify({'error': 'File not found'}), 404

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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
