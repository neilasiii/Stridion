#!/usr/bin/env python3
"""
Unit tests for Google Drive health data sync functionality

Tests cover:
- Path validation and security
- Configuration validation
- File size validation
- Sync state management
- Error handling
"""

import unittest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Import the module to test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Try to import sync module; skip tests if Google dependencies not installed
try:
    from sync_health_data_from_drive import (
        GoogleDriveHealthSync,
        ConfigurationError,
        SecurityError,
        MAX_FILE_SIZE_MB
    )
    GOOGLE_DEPS_AVAILABLE = True
except SystemExit:
    # Module exits with sys.exit(1) if dependencies not installed
    GOOGLE_DEPS_AVAILABLE = False
    # Define dummy classes so tests can at least import
    class GoogleDriveHealthSync:
        pass
    class ConfigurationError(Exception):
        pass
    class SecurityError(Exception):
        pass
    MAX_FILE_SIZE_MB = 500


@unittest.skipIf(not GOOGLE_DEPS_AVAILABLE, "Google Drive dependencies not installed")
class TestPathValidation(unittest.TestCase):
    """Test path traversal and security validation"""

    def setUp(self):
        """Create a mock syncer instance for testing"""
        self.syncer = GoogleDriveHealthSync.__new__(GoogleDriveHealthSync)

    def test_valid_simple_path(self):
        """Test that simple valid paths are accepted"""
        valid_paths = [
            "file.csv",
            "Health Sync Activities",
            "folder/subfolder/file.csv",
            "Health Sync Sleep/sleep_2024.csv"
        ]
        for path in valid_paths:
            with self.subTest(path=path):
                result = self.syncer._validate_path(path)
                self.assertEqual(result, path)

    def test_path_traversal_attacks(self):
        """Test that path traversal attempts are blocked"""
        malicious_paths = [
            "../etc/passwd",
            "../../etc/shadow",
            "folder/../../etc/passwd",
            "..\\windows\\system32",
            ".../.../etc/passwd"
        ]
        for path in malicious_paths:
            with self.subTest(path=path):
                with self.assertRaises(SecurityError):
                    self.syncer._validate_path(path)

    def test_absolute_paths_rejected(self):
        """Test that absolute paths are rejected"""
        absolute_paths = [
            "/etc/passwd",
            "/home/user/file.txt",
            "/var/log/messages"
        ]
        for path in absolute_paths:
            with self.subTest(path=path):
                with self.assertRaises(SecurityError):
                    self.syncer._validate_path(path)

    def test_dangerous_characters_rejected(self):
        """Test that paths with dangerous characters are rejected"""
        dangerous_paths = [
            "file\x00.csv",  # Null byte
            "file\n.csv",    # Newline
            "file;rm -rf /.csv",  # Shell injection attempt
        ]
        for path in dangerous_paths:
            with self.subTest(path=path):
                with self.assertRaises(SecurityError):
                    self.syncer._validate_path(path)

    def test_path_length_limit(self):
        """Test that excessively long paths are rejected"""
        long_path = "a" * 256  # Exceeds MAX_PATH_LENGTH (255)
        with self.assertRaises(SecurityError):
            self.syncer._validate_path(long_path)

    def test_empty_path_rejected(self):
        """Test that empty paths are rejected"""
        with self.assertRaises(SecurityError):
            self.syncer._validate_path("")

    def test_windows_absolute_paths_rejected(self):
        """Test that Windows-style absolute paths are rejected"""
        windows_paths = [
            "C:\\Windows\\System32",
            "D:\\data\\file.txt"
        ]
        for path in windows_paths:
            with self.subTest(path=path):
                with self.assertRaises(SecurityError):
                    self.syncer._validate_path(path)


@unittest.skipIf(not GOOGLE_DEPS_AVAILABLE, "Google Drive dependencies not installed")
class TestConfigValidation(unittest.TestCase):
    """Test configuration file validation"""

    def setUp(self):
        """Create temporary config file"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "test_config.json"
        self.credentials_file = Path(self.temp_dir) / "credentials.json"
        self.token_file = Path(self.temp_dir) / ".drive_token.json"

        # Create a minimal valid config
        self.valid_config = {
            "google_drive_folder_id": "1234567890abcdefghij"
        }

    def tearDown(self):
        """Clean up temporary files"""
        import shutil
        shutil.rmtree(self.temp_dir)

    def write_config(self, config_dict):
        """Helper to write config to temp file"""
        with open(self.config_file, 'w') as f:
            json.dump(config_dict, f)

    def test_missing_config_file(self):
        """Test that missing config file raises error"""
        with self.assertRaises(ConfigurationError) as cm:
            syncer = GoogleDriveHealthSync(config_file=str(self.config_file))
        self.assertIn("Config file not found", str(cm.exception))

    def test_invalid_json(self):
        """Test that invalid JSON raises error"""
        with open(self.config_file, 'w') as f:
            f.write("{invalid json content")

        with self.assertRaises(ConfigurationError) as cm:
            syncer = GoogleDriveHealthSync(config_file=str(self.config_file))
        self.assertIn("Invalid JSON", str(cm.exception))

    def test_missing_required_field(self):
        """Test that missing required field raises error"""
        self.write_config({})

        with self.assertRaises(ConfigurationError) as cm:
            syncer = GoogleDriveHealthSync(config_file=str(self.config_file))
        self.assertIn("Missing required config fields", str(cm.exception))
        self.assertIn("google_drive_folder_id", str(cm.exception))

    def test_invalid_folder_id_type(self):
        """Test that non-string folder ID raises error"""
        self.write_config({"google_drive_folder_id": 12345})

        with self.assertRaises(ConfigurationError) as cm:
            syncer = GoogleDriveHealthSync(config_file=str(self.config_file))
        self.assertIn("Invalid google_drive_folder_id", str(cm.exception))

    def test_invalid_folder_id_length(self):
        """Test that too-short folder ID raises error"""
        self.write_config({"google_drive_folder_id": "short"})

        with self.assertRaises(ConfigurationError) as cm:
            syncer = GoogleDriveHealthSync(config_file=str(self.config_file))
        self.assertIn("Invalid google_drive_folder_id", str(cm.exception))

    def test_empty_folder_id(self):
        """Test that empty folder ID raises error"""
        self.write_config({"google_drive_folder_id": ""})

        with self.assertRaises(ConfigurationError) as cm:
            syncer = GoogleDriveHealthSync(config_file=str(self.config_file))
        self.assertIn("Invalid google_drive_folder_id", str(cm.exception))

    def test_valid_config_loads(self):
        """Test that valid config loads successfully"""
        self.write_config(self.valid_config)

        syncer = GoogleDriveHealthSync(config_file=str(self.config_file))
        self.assertEqual(
            syncer.config['google_drive_folder_id'],
            self.valid_config['google_drive_folder_id']
        )

    def test_default_max_file_size(self):
        """Test that default max_file_size_mb is set"""
        self.write_config(self.valid_config)

        syncer = GoogleDriveHealthSync(config_file=str(self.config_file))
        self.assertEqual(syncer.config['max_file_size_mb'], MAX_FILE_SIZE_MB)


@unittest.skipIf(not GOOGLE_DEPS_AVAILABLE, "Google Drive dependencies not installed")
class TestFileSizeValidation(unittest.TestCase):
    """Test file size validation"""

    def setUp(self):
        """Create temporary config and syncer"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "test_config.json"

        config = {
            "google_drive_folder_id": "1234567890abcdefghij"
        }
        with open(self.config_file, 'w') as f:
            json.dump(config, f)

    def tearDown(self):
        """Clean up temporary files"""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_max_file_size_must_be_numeric(self):
        """Test that max_file_size_mb must be a number"""
        config = {
            "google_drive_folder_id": "1234567890abcdefghij",
            "max_file_size_mb": "not_a_number"
        }
        with open(self.config_file, 'w') as f:
            json.dump(config, f)

        with self.assertRaises(ConfigurationError) as cm:
            syncer = GoogleDriveHealthSync(config_file=str(self.config_file))
        self.assertIn("must be a number", str(cm.exception))

    def test_max_file_size_must_be_positive(self):
        """Test that max_file_size_mb must be positive"""
        for invalid_size in [-1, -100, 0]:
            with self.subTest(size=invalid_size):
                config = {
                    "google_drive_folder_id": "1234567890abcdefghij",
                    "max_file_size_mb": invalid_size
                }
                with open(self.config_file, 'w') as f:
                    json.dump(config, f)

                with self.assertRaises(ConfigurationError) as cm:
                    syncer = GoogleDriveHealthSync(config_file=str(self.config_file))
                self.assertIn("must be positive", str(cm.exception))

    def test_max_file_size_upper_limit(self):
        """Test that max_file_size_mb cannot exceed 10GB"""
        config = {
            "google_drive_folder_id": "1234567890abcdefghij",
            "max_file_size_mb": 10241  # Just over 10GB
        }
        with open(self.config_file, 'w') as f:
            json.dump(config, f)

        with self.assertRaises(ConfigurationError) as cm:
            syncer = GoogleDriveHealthSync(config_file=str(self.config_file))
        self.assertIn("too large", str(cm.exception))
        self.assertIn("10240", str(cm.exception))

    def test_valid_file_sizes(self):
        """Test that valid file sizes are accepted"""
        valid_sizes = [1, 100, 500, 1024, 10240, 500.5, 1024.75]

        for size in valid_sizes:
            with self.subTest(size=size):
                config = {
                    "google_drive_folder_id": "1234567890abcdefghij",
                    "max_file_size_mb": size
                }
                with open(self.config_file, 'w') as f:
                    json.dump(config, f)

                # Should not raise
                syncer = GoogleDriveHealthSync(config_file=str(self.config_file))
                self.assertEqual(syncer.config['max_file_size_mb'], size)

    def test_integer_and_float_accepted(self):
        """Test that both int and float are accepted for file size"""
        for size in [100, 100.5]:
            with self.subTest(size=size, type=type(size).__name__):
                config = {
                    "google_drive_folder_id": "1234567890abcdefghij",
                    "max_file_size_mb": size
                }
                with open(self.config_file, 'w') as f:
                    json.dump(config, f)

                syncer = GoogleDriveHealthSync(config_file=str(self.config_file))
                self.assertEqual(syncer.config['max_file_size_mb'], size)


@unittest.skipIf(not GOOGLE_DEPS_AVAILABLE, "Google Drive dependencies not installed")
class TestSyncStateManagement(unittest.TestCase):
    """Test sync state tracking"""

    def setUp(self):
        """Create temporary directory and syncer"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "test_config.json"
        self.sync_state_file = Path(self.temp_dir) / ".drive_sync_state.json"

        config = {
            "google_drive_folder_id": "1234567890abcdefghij"
        }
        with open(self.config_file, 'w') as f:
            json.dump(config, f)

        self.syncer = GoogleDriveHealthSync(config_file=str(self.config_file))
        self.syncer.sync_state_file = self.sync_state_file

    def tearDown(self):
        """Clean up temporary files"""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_load_missing_sync_state(self):
        """Test loading sync state when file doesn't exist"""
        state = self.syncer._load_sync_state()
        self.assertEqual(state, {"synced_files": {}})

    def test_load_valid_sync_state(self):
        """Test loading valid sync state"""
        test_state = {
            "synced_files": {
                "file1.csv": {"modified_time": "2024-01-01", "size": 1024},
                "file2.csv": {"modified_time": "2024-01-02", "size": 2048}
            }
        }
        with open(self.sync_state_file, 'w') as f:
            json.dump(test_state, f)

        state = self.syncer._load_sync_state()
        self.assertEqual(state, test_state)

    def test_load_corrupted_sync_state(self):
        """Test that corrupted sync state returns fresh state"""
        with open(self.sync_state_file, 'w') as f:
            f.write("{invalid json")

        state = self.syncer._load_sync_state()
        self.assertEqual(state, {"synced_files": {}})

    def test_save_sync_state(self):
        """Test saving sync state"""
        test_state = {
            "synced_files": {
                "test.csv": {"modified_time": "2024-01-01", "size": 512}
            }
        }

        self.syncer._save_sync_state(test_state)

        # Verify file was created and contains correct data
        self.assertTrue(self.sync_state_file.exists())
        with open(self.sync_state_file, 'r') as f:
            loaded_state = json.load(f)
        self.assertEqual(loaded_state, test_state)


class TestErrorHandling(unittest.TestCase):
    """Test error handling and edge cases"""

    def test_security_error_is_exception(self):
        """Test that SecurityError is an Exception"""
        self.assertTrue(issubclass(SecurityError, Exception))

    def test_configuration_error_is_exception(self):
        """Test that ConfigurationError is an Exception"""
        self.assertTrue(issubclass(ConfigurationError, Exception))

    def test_security_error_message(self):
        """Test SecurityError carries message"""
        msg = "Test security violation"
        error = SecurityError(msg)
        self.assertEqual(str(error), msg)

    def test_configuration_error_message(self):
        """Test ConfigurationError carries message"""
        msg = "Test configuration issue"
        error = ConfigurationError(msg)
        self.assertEqual(str(error), msg)


if __name__ == '__main__':
    unittest.main()
