"""
Flask web application for the running coach service.
"""

import os
import logging
from flask import Flask, request, jsonify, render_template, Response, Blueprint
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from ..coach_service import CoachService, FileManager
from ..ai_providers import get_provider
from ..config.logging_config import setup_logging, get_logger
from ..config.constants import (
    VALID_FILE_CATEGORIES,
    MAX_FILE_SIZE,
    DEFAULT_RATE_LIMIT_GLOBAL,
    DEFAULT_RATE_LIMIT_PER_MINUTE,
    DEFAULT_RATE_LIMIT_CHAT,
    DEFAULT_LOG_LEVEL
)

# Setup logging with error handling
log_level = os.getenv('LOG_LEVEL', DEFAULT_LOG_LEVEL)
log_file = os.getenv('LOG_FILE')
try:
    setup_logging(log_level=log_level, log_file=log_file)
except Exception as e:
    print(f"Warning: Logging setup failed ({e}), using defaults")
    setup_logging(log_level=DEFAULT_LOG_LEVEL)

logger = get_logger(__name__)

# Create Flask app
app = Flask(__name__, template_folder='templates', static_folder='static')

# Setup CORS with configurable origins
cors_origins = os.getenv('CORS_ORIGINS', '*')
if cors_origins != '*':
    # Split comma-separated origins
    cors_origins = [origin.strip() for origin in cors_origins.split(',')]
CORS(app, origins=cors_origins)
logger.info(f"CORS enabled for origins: {cors_origins}")

# Setup rate limiting with configurable storage
rate_limit_storage = os.getenv('RATE_LIMIT_STORAGE_URI', 'memory://')
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[DEFAULT_RATE_LIMIT_GLOBAL, DEFAULT_RATE_LIMIT_PER_MINUTE],
    storage_uri=rate_limit_storage
)
logger.info(f"Rate limiting enabled (storage: {rate_limit_storage})")

# Initialize coach service
try:
    provider = get_provider()
    coach_service = CoachService(ai_provider=provider)
    logger.info(f"Initialized with {provider.get_provider_name()} provider")
except Exception as e:
    logger.warning(f"Failed to initialize AI provider: {e}")
    logger.warning("Service will start but may not be functional")
    coach_service = None

# Initialize file manager
file_manager = FileManager()
logger.info("File manager initialized")

# Create API v1 blueprint
api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')


# =============================================================================
# Main Routes (Web Interface)
# =============================================================================

@app.route('/')
def index():
    """Serve the main HTML interface."""
    agents = coach_service.list_agents() if coach_service else {}
    provider_name = coach_service.provider.get_provider_name() if coach_service else "Unknown"
    return render_template('index.html', agents=agents, provider=provider_name)


# =============================================================================
# API v1 Routes
# =============================================================================

@api_v1.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'version': 'v1',
        'provider': coach_service.provider.get_provider_name() if coach_service else None,
        'agents_loaded': len(coach_service.agent_loader.agents) if coach_service else 0
    })


@api_v1.route('/agents')
def list_agents():
    """List available coaching agents."""
    if not coach_service:
        return jsonify({'error': 'Service not initialized'}), 503

    return jsonify({
        'agents': coach_service.list_agents()
    })


@api_v1.route('/chat', methods=['POST'])
@limiter.limit(DEFAULT_RATE_LIMIT_CHAT)
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
        logger.error("Chat request received but service not initialized")
        return jsonify({'error': 'Service not initialized'}), 503

    data = request.get_json()

    if not data or 'query' not in data:
        logger.warning("Chat request missing query parameter")
        return jsonify({'error': 'Missing query parameter'}), 400

    query = data['query']
    agent_name = data.get('agent')
    history = data.get('history', [])

    # Log query length instead of content to avoid PII in logs
    logger.info(f"Chat request: query_length={len(query)}, agent={agent_name}")

    try:
        response = coach_service.chat(
            query=query,
            agent_name=agent_name,
            conversation_history=history
        )

        selected_agent = coach_service._select_agent(query, agent_name)
        logger.info(f"Chat response generated using {selected_agent}")

        return jsonify({
            'response': response,
            'agent': selected_agent
        })

    except Exception as e:
        logger.error(f"Chat request failed: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@api_v1.route('/chat/stream', methods=['POST'])
@limiter.limit(DEFAULT_RATE_LIMIT_CHAT)
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
        logger.error("Stream chat request received but service not initialized")
        return jsonify({'error': 'Service not initialized'}), 503

    data = request.get_json()

    if not data or 'query' not in data:
        logger.warning("Stream chat request missing query parameter")
        return jsonify({'error': 'Missing query parameter'}), 400

    query = data['query']
    agent_name = data.get('agent')
    history = data.get('history', [])

    # Log query length instead of content to avoid PII in logs
    logger.info(f"Stream chat request: query_length={len(query)}, agent={agent_name}")

    def generate():
        """Generator for streaming response."""
        try:
            for chunk in coach_service.stream_chat(
                query=query,
                agent_name=agent_name,
                conversation_history=history
            ):
                yield chunk
            logger.info("Stream chat completed successfully")
        except Exception as e:
            logger.error(f"Stream chat failed: {e}", exc_info=True)
            yield f"\n\nError: {str(e)}"

    return Response(generate(), mimetype='text/plain')


@api_v1.route('/files', methods=['GET'])
def list_files():
    """
    List available files.

    Query params:
        category: Filter by category (plans, frameworks, calendar)
    """
    category = request.args.get('category')
    logger.info(f"List files request: category={category}")

    try:
        files = file_manager.list_files(category=category)
        logger.info(f"Listed {len(files)} files")
        return jsonify({'files': files})
    except Exception as e:
        logger.error(f"List files failed: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@api_v1.route('/files/<category>/<filename>', methods=['GET'])
def download_file(category, filename):
    """
    Download a specific file.

    Args:
        category: File category (plans, frameworks, calendar)
        filename: Filename
    """
    logger.info(f"Download file request: category={category}, filename={filename}")

    # Validate category
    if category not in VALID_CATEGORIES:
        logger.warning(f"Invalid category requested: {category}")
        return jsonify({'error': 'Invalid category'}), 400

    try:
        content = file_manager.get_file(filename, category)

        if content is None:
            logger.warning(f"File not found: {category}/{filename}")
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

        logger.info(f"File downloaded successfully: {category}/{filename}")
        return Response(
            content,
            mimetype=mimetype,
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"'
            }
        )
    except Exception as e:
        logger.error(f"Download file failed: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@api_v1.route('/files', methods=['POST'])
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
        logger.warning("Save file request missing required parameters")
        return jsonify({'error': 'Missing required parameters'}), 400

    content = data['content']
    filename = data['filename']
    category = data.get('category', 'plans')
    metadata = data.get('metadata', {})

    logger.info(f"Save file request: filename={filename}, category={category}, size={len(content)} bytes")

    # Validate category
    if category not in VALID_CATEGORIES:
        logger.warning(f"Invalid category in save request: {category}")
        return jsonify({'error': 'Invalid category'}), 400

    # Validate file size
    if len(content) > MAX_FILE_SIZE:
        logger.warning(f"File too large: {len(content)} bytes (max {MAX_FILE_SIZE})")
        return jsonify({'error': f'File too large. Maximum size is {MAX_FILE_SIZE / (1024*1024):.0f}MB'}), 413

    try:
        file_path = file_manager.save_file(
            content=content,
            filename=filename,
            category=category,
            metadata=metadata
        )

        logger.info(f"File saved successfully: {category}/{filename}")
        return jsonify({
            'success': True,
            'filename': filename,
            'category': category,
            'path': file_path
        })
    except Exception as e:
        logger.error(f"Save file failed: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@api_v1.route('/files/<category>/<filename>', methods=['DELETE'])
def delete_file(category, filename):
    """
    Delete a file.

    Args:
        category: File category
        filename: Filename
    """
    logger.info(f"Delete file request: category={category}, filename={filename}")

    # Validate category
    if category not in VALID_CATEGORIES:
        logger.warning(f"Invalid category in delete request: {category}")
        return jsonify({'error': 'Invalid category'}), 400

    try:
        success = file_manager.delete_file(filename, category)

        if not success:
            logger.warning(f"File not found for deletion: {category}/{filename}")
            return jsonify({'error': 'File not found'}), 404

        logger.info(f"File deleted successfully: {category}/{filename}")
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Delete file failed: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# =============================================================================
# Register API v1 Blueprint
# =============================================================================

app.register_blueprint(api_v1)


# =============================================================================
# Backward Compatibility Routes (redirect /api/* to /api/v1/*)
# =============================================================================

@app.route('/api/health')
def api_health_compat():
    """Backward compatibility for /api/health -> /api/v1/health"""
    return health()


@app.route('/api/agents')
def api_agents_compat():
    """Backward compatibility for /api/agents -> /api/v1/agents"""
    return list_agents()


@app.route('/api/chat', methods=['POST'])
@limiter.limit(DEFAULT_RATE_LIMIT_CHAT)
def api_chat_compat():
    """Backward compatibility for /api/chat -> /api/v1/chat"""
    return chat()


@app.route('/api/chat/stream', methods=['POST'])
@limiter.limit(DEFAULT_RATE_LIMIT_CHAT)
def api_chat_stream_compat():
    """Backward compatibility for /api/chat/stream -> /api/v1/chat/stream"""
    return chat_stream()


@app.route('/api/files', methods=['GET'])
def api_files_list_compat():
    """Backward compatibility for /api/files -> /api/v1/files"""
    return list_files()


@app.route('/api/files/<category>/<filename>', methods=['GET'])
def api_files_download_compat(category, filename):
    """Backward compatibility for /api/files/<category>/<filename>"""
    return download_file(category, filename)


@app.route('/api/files', methods=['POST'])
def api_files_save_compat():
    """Backward compatibility for POST /api/files"""
    return save_file()


@app.route('/api/files/<category>/<filename>', methods=['DELETE'])
def api_files_delete_compat(category, filename):
    """Backward compatibility for DELETE /api/files/<category>/<filename>"""
    return delete_file(category, filename)


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')
    debug = os.getenv('DEBUG', 'false').lower() == 'true'

    logger.info("="*60)
    logger.info("Running Coach Service")
    logger.info("="*60)
    logger.info(f"Provider: {coach_service.provider.get_provider_name() if coach_service else 'Not initialized'}")
    logger.info(f"Agents loaded: {len(coach_service.agent_loader.agents) if coach_service else 0}")
    if coach_service:
        for agent_name in coach_service.agent_loader.list_agents():
            logger.info(f"  - {agent_name}")
    logger.info(f"Host: {host}")
    logger.info(f"Port: {port}")
    logger.info(f"Debug: {debug}")
    logger.info(f"Log level: {log_level}")
    logger.info("="*60)

    app.run(host=host, port=port, debug=debug)
