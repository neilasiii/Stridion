"""
Security tests for the web application.
"""

import unittest
import json
import os
import sys
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.web.app import app
from src.config.logging_config import SensitiveDataFilter
import logging


class TestPathTraversal(unittest.TestCase):
    """Test cases for path traversal protection."""

    def setUp(self):
        """Set up test client."""
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_path_traversal_in_download(self):
        """Test that path traversal attempts are blocked in file download."""
        # Try various path traversal patterns
        traversal_attempts = [
            '/api/v1/files/plans/../../../etc/passwd',
            '/api/v1/files/plans/..%2F..%2F..%2Fetc%2Fpasswd',
            '/api/v1/files/plans/....//....//....//etc/passwd',
            '/api/v1/files/plans/..\\..\\..\\/etc/passwd',
        ]

        for attempt in traversal_attempts:
            response = self.client.get(attempt)
            # Should not return 200 (success)
            self.assertNotEqual(response.status_code, 200,
                              f"Path traversal not blocked: {attempt}")
            # Should return 400 (invalid) or 404 (not found)
            self.assertIn(response.status_code, [400, 404],
                         f"Unexpected status for: {attempt}")

    def test_path_traversal_in_delete(self):
        """Test that path traversal attempts are blocked in file deletion."""
        traversal_attempts = [
            '/api/v1/files/plans/../../../etc/passwd',
            '/api/v1/files/plans/..%2F..%2Fetc%2Fpasswd',
        ]

        for attempt in traversal_attempts:
            response = self.client.delete(attempt)
            self.assertNotEqual(response.status_code, 200,
                              f"Path traversal not blocked in delete: {attempt}")

    def test_absolute_path_rejection(self):
        """Test that absolute paths are rejected."""
        response = self.client.get('/api/v1/files/plans//etc/passwd')
        self.assertNotEqual(response.status_code, 200)


class TestFileSizeLimits(unittest.TestCase):
    """Test cases for file size limit enforcement."""

    def setUp(self):
        """Set up test client."""
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_file_size_limit_enforcement(self):
        """Test that files exceeding size limit are rejected."""
        # Create content larger than 10MB
        large_content = "x" * (11 * 1024 * 1024)  # 11MB

        response = self.client.post(
            '/api/v1/files',
            data=json.dumps({
                'content': large_content,
                'filename': 'large_file.md',
                'category': 'plans'
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 413)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('too large', data['error'].lower())

    def test_file_size_within_limit(self):
        """Test that files within size limit are accepted."""
        # Create content just under 10MB
        acceptable_content = "x" * (5 * 1024 * 1024)  # 5MB

        response = self.client.post(
            '/api/v1/files',
            data=json.dumps({
                'content': acceptable_content,
                'filename': 'acceptable_file.md',
                'category': 'plans'
            }),
            content_type='application/json'
        )

        # Should not fail due to size (may fail for other reasons in test)
        self.assertNotEqual(response.status_code, 413)


class TestCategoryValidation(unittest.TestCase):
    """Test cases for category validation."""

    def setUp(self):
        """Set up test client."""
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_invalid_category_download(self):
        """Test that invalid categories are rejected in download."""
        invalid_categories = [
            'invalid',
            '../etc',
            'plans/../frameworks',
            'system',
            '',
        ]

        for category in invalid_categories:
            response = self.client.get(f'/api/v1/files/{category}/test.md')
            self.assertEqual(response.status_code, 400,
                           f"Invalid category not rejected: {category}")
            data = json.loads(response.data)
            self.assertIn('error', data)
            self.assertIn('Invalid category', data['error'])

    def test_invalid_category_save(self):
        """Test that invalid categories are rejected in save."""
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

    def test_valid_categories(self):
        """Test that valid categories are accepted."""
        valid_categories = ['plans', 'frameworks', 'calendar']

        for category in valid_categories:
            response = self.client.get(f'/api/v1/files/{category}/nonexistent.md')
            # Should not be 400 (validation error)
            # Will be 404 (not found) since file doesn't exist
            self.assertNotEqual(response.status_code, 400,
                              f"Valid category rejected: {category}")


class TestSensitiveDataFilter(unittest.TestCase):
    """Test cases for sensitive data filtering in logs."""

    def setUp(self):
        """Set up filter."""
        self.filter = SensitiveDataFilter()

    def test_api_key_redaction(self):
        """Test that API keys are redacted from logs."""
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg='Connecting with api_key: sk-1234567890abcdef',
            args=(),
            exc_info=None
        )

        self.filter.filter(record)
        self.assertIn('[REDACTED]', record.msg)
        self.assertNotIn('sk-1234567890abcdef', record.msg)

    def test_bearer_token_redaction(self):
        """Test that Bearer tokens are redacted."""
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg='Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9',
            args=(),
            exc_info=None
        )

        self.filter.filter(record)
        self.assertIn('[REDACTED]', record.msg)
        self.assertNotIn('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9', record.msg)

    def test_email_partial_redaction(self):
        """Test that email addresses are partially redacted."""
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg='User logged in: user@example.com',
            args=(),
            exc_info=None
        )

        self.filter.filter(record)
        self.assertNotIn('user@example.com', record.msg)
        self.assertIn('***@example.com', record.msg)

    def test_password_redaction(self):
        """Test that passwords are redacted."""
        test_cases = [
            'password: secret123',
            'password=secret123',
            'PASSWORD: secret123',
            'token: abc123xyz',
            'secret: mySecret',
        ]

        for msg in test_cases:
            record = logging.LogRecord(
                name='test',
                level=logging.INFO,
                pathname='',
                lineno=0,
                msg=msg,
                args=(),
                exc_info=None
            )

            self.filter.filter(record)
            self.assertIn('[REDACTED]', record.msg,
                         f"Sensitive data not redacted in: {msg}")

    def test_normal_messages_unchanged(self):
        """Test that normal log messages are not modified."""
        normal_messages = [
            'Application started successfully',
            'Processing request from 192.168.1.1',
            'File saved to disk',
            'Chat request received',
        ]

        for msg in normal_messages:
            record = logging.LogRecord(
                name='test',
                level=logging.INFO,
                pathname='',
                lineno=0,
                msg=msg,
                args=(),
                exc_info=None
            )

            original_msg = msg
            self.filter.filter(record)
            self.assertEqual(record.msg, original_msg,
                           f"Normal message was modified: {msg}")


class TestInputValidation(unittest.TestCase):
    """Test cases for general input validation."""

    def setUp(self):
        """Set up test client."""
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_missing_required_fields_chat(self):
        """Test that missing required fields are caught in chat."""
        response = self.client.post(
            '/api/v1/chat',
            data=json.dumps({}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_missing_required_fields_save_file(self):
        """Test that missing required fields are caught in file save."""
        # Missing content
        response = self.client.post(
            '/api/v1/files',
            data=json.dumps({'filename': 'test.md'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

        # Missing filename
        response = self.client.post(
            '/api/v1/files',
            data=json.dumps({'content': 'test'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_malformed_json(self):
        """Test that malformed JSON is handled gracefully."""
        response = self.client.post(
            '/api/v1/chat',
            data='{"query": invalid json}',
            content_type='application/json'
        )

        # Should return 400 or 500, not crash
        self.assertIn(response.status_code, [400, 500])


if __name__ == '__main__':
    unittest.main()
