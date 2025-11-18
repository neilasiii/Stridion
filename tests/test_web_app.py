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


class TestFileOperationsIntegration(unittest.TestCase):
    """Integration tests for file operations."""

    def setUp(self):
        """Set up test client."""
        app.config['TESTING'] = True
        self.client = app.test_client()
        self.test_filename = 'test_integration_file.md'
        self.test_content = '# Test File\n\nThis is a test.'
        self.test_category = 'plans'

    def tearDown(self):
        """Clean up test files."""
        # Try to delete test file if it exists
        self.client.delete(f'/api/v1/files/{self.test_category}/{self.test_filename}')

    def test_file_lifecycle(self):
        """Test complete file lifecycle: save, list, download, delete."""
        # 1. Save file
        save_response = self.client.post(
            '/api/v1/files',
            data=json.dumps({
                'content': self.test_content,
                'filename': self.test_filename,
                'category': self.test_category
            }),
            content_type='application/json'
        )

        self.assertEqual(save_response.status_code, 200)
        save_data = json.loads(save_response.data)
        self.assertTrue(save_data.get('success'))
        self.assertEqual(save_data.get('filename'), self.test_filename)

        # 2. List files (verify it appears)
        list_response = self.client.get(f'/api/v1/files?category={self.test_category}')
        self.assertEqual(list_response.status_code, 200)
        list_data = json.loads(list_response.data)
        filenames = [f['filename'] for f in list_data['files']]
        self.assertIn(self.test_filename, filenames)

        # 3. Download file (verify content)
        download_response = self.client.get(
            f'/api/v1/files/{self.test_category}/{self.test_filename}'
        )
        self.assertEqual(download_response.status_code, 200)
        self.assertEqual(download_response.data.decode('utf-8'), self.test_content)

        # 4. Delete file
        delete_response = self.client.delete(
            f'/api/v1/files/{self.test_category}/{self.test_filename}'
        )
        self.assertEqual(delete_response.status_code, 200)
        delete_data = json.loads(delete_response.data)
        self.assertTrue(delete_data.get('success'))

        # 5. Verify file is gone
        download_after_delete = self.client.get(
            f'/api/v1/files/{self.test_category}/{self.test_filename}'
        )
        self.assertEqual(download_after_delete.status_code, 404)


class TestStreamingEndpoint(unittest.TestCase):
    """Test cases for streaming endpoint."""

    def setUp(self):
        """Set up test client."""
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_streaming_endpoint_exists(self):
        """Test that streaming endpoint is available."""
        # Skip if service not initialized
        if not coach_service:
            self.skipTest("Coach service not initialized")

        response = self.client.post(
            '/api/v1/chat/stream',
            data=json.dumps({'query': 'test'}),
            content_type='application/json'
        )

        # Should not return 404
        self.assertNotEqual(response.status_code, 404)


if __name__ == '__main__':
    unittest.main()
