"""
Constants and configuration values for the running coach service.
"""

# File management constants
VALID_FILE_CATEGORIES = ['plans', 'frameworks', 'calendar']
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Rate limiting defaults
DEFAULT_RATE_LIMIT_GLOBAL = "200 per hour"
DEFAULT_RATE_LIMIT_PER_MINUTE = "50 per minute"
DEFAULT_RATE_LIMIT_CHAT = "20 per minute"

# API versioning
API_VERSION = "v1"

# Logging
DEFAULT_LOG_LEVEL = "INFO"
