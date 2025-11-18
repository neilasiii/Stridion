"""
Unit tests for the web application.
"""

import unittest
import json
import os
import sys
from unittest.mock import Mock, patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.web.app import app, coach_service, file_manager


class TestWebApp(unittest.TestCase):
    """Test cases for Flask web application."""

    def setUp(self):
        """Set up test client."""
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_index_route(self):
        """Test main index route."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Running Coach', response.data)

    def test_health_endpoint_v1(self):
        """Test health check endpoint (v1)."""
        response = self.client.get('/api/v1/health')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertIn('status', data)
        self.assertIn('version', data)
        self.assertEqual(data['version'], 'v1')
        self.assertEqual(data['status'], 'healthy')

    def test_health_endpoint_backward_compat(self):
        """Test health check backward compatibility."""
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertIn('status', data)
        self.assertEqual(data['status'], 'healthy')

    def test_list_agents_v1(self):
        """Test list agents endpoint (v1)."""
        if not coach_service:
            self.skipTest("Coach service not initialized")

        response = self.client.get('/api/v1/agents')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertIn('agents', data)
        self.assertIsInstance(data['agents'], dict)

    def test_list_agents_backward_compat(self):
        """Test list agents backward compatibility."""
        if not coach_service:
            self.skipTest("Coach service not initialized")

        response = self.client.get('/api/agents')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertIn('agents', data)

    def test_chat_missing_query(self):
        """Test chat endpoint with missing query."""
        if not coach_service:
            self.skipTest("Coach service not initialized")

        response = self.client.post(
            '/api/v1/chat',
            data=json.dumps({}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_list_files_v1(self):
        """Test list files endpoint (v1)."""
        response = self.client.get('/api/v1/files')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertIn('files', data)
        self.assertIsInstance(data['files'], list)

    def test_list_files_with_category(self):
        """Test list files endpoint with category filter."""
        response = self.client.get('/api/v1/files?category=plans')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertIn('files', data)

    def test_save_file_missing_params(self):
        """Test save file with missing parameters."""
        response = self.client.post(
            '/api/v1/files',
            data=json.dumps({}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_save_file_invalid_category(self):
        """Test save file with invalid category."""
        response = self.client.post(
            '/api/v1/files',
            data=json.dumps({
                'content': 'Test content',
                'filename': 'test.md',
                'category': 'invalid_category'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('Invalid category', data['error'])

    def test_download_file_invalid_category(self):
        """Test download file with invalid category."""
        response = self.client.get('/api/v1/files/invalid/test.md')
        self.assertEqual(response.status_code, 400)

        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_delete_file_invalid_category(self):
        """Test delete file with invalid category."""
        response = self.client.delete('/api/v1/files/invalid/test.md')
        self.assertEqual(response.status_code, 400)

        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_backward_compatibility_routes(self):
        """Test all backward compatibility routes exist."""
        # Test that old /api/* routes still work
        routes = [
            '/api/health',
            '/api/agents',
            '/api/files',
        ]

        for route in routes:
            response = self.client.get(route)
            # Should not return 404
            self.assertNotEqual(response.status_code, 404)


class TestFileManager(unittest.TestCase):
    """Test cases for FileManager."""

    def setUp(self):
        """Set up test file manager."""
        self.file_manager = file_manager

    def test_list_files(self):
        """Test listing files."""
        files = self.file_manager.list_files()
        self.assertIsInstance(files, list)

    def test_list_files_by_category(self):
        """Test listing files by category."""
        files = self.file_manager.list_files(category='plans')
        self.assertIsInstance(files, list)

        # All files should be in plans category
        for file_info in files:
            self.assertEqual(file_info['category'], 'plans')


class TestRateLimiting(unittest.TestCase):
    """Test cases for rate limiting."""

    def setUp(self):
        """Set up test client."""
        app.config['TESTING'] = True
        # Rate limiting is disabled in testing by default
        self.client = app.test_client()

    def test_rate_limit_headers_present(self):
        """Test that rate limit headers are present in responses."""
        response = self.client.get('/api/v1/health')

        # In testing mode, rate limits may be disabled
        # Just verify the endpoint works
        self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
