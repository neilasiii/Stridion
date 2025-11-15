#!/usr/bin/env python3
"""
Google Drive Health Data Sync Script

This script syncs Health Connect data from Google Drive to the local
health_connect_export directory. It uses the Google Drive API to download
files from a specified Drive folder.

Usage:
    python3 sync_health_data_from_drive.py              # Sync all files
    python3 sync_health_data_from_drive.py --check-only # Check what would sync
    python3 sync_health_data_from_drive.py --setup      # Run OAuth setup

Security features:
    - JSON token storage (no pickle)
    - Path traversal validation
    - File size limits
    - Atomic file downloads
"""

import os
import sys
import json
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import argparse

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
    from googleapiclient.errors import HttpError
except ImportError:
    print("ERROR: Google Drive dependencies not installed.")
    print("Please run: pip install -r requirements.txt")
    sys.exit(1)

# If modifying these scopes, delete the token file
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# Security limits
MAX_FILE_SIZE_MB = 500  # Maximum file size to download
MAX_PATH_LENGTH = 255   # Maximum path component length


class ConfigurationError(Exception):
    """Raised when configuration is invalid"""
    pass


class SecurityError(Exception):
    """Raised when security validation fails"""
    pass


class GoogleDriveHealthSync:
    """Manages syncing health data from Google Drive"""

    def __init__(self, config_file: str = "config/.drive_sync_config.json"):
        self.config_file = Path(config_file)
        self.token_file = Path("config/.drive_token.json")  # Changed from .pickle to .json
        self.credentials_file = Path("config/credentials.json")
        self.local_data_dir = Path("health_connect_export")
        self.sync_state_file = Path("config/.drive_sync_state.json")

        self.config = self._load_and_validate_config()
        self.service = None

    def _load_and_validate_config(self) -> Dict:
        """Load and validate configuration file"""
        if not self.config_file.exists():
            raise ConfigurationError(
                f"Config file not found: {self.config_file}\n"
                "Please create config/.drive_sync_config.json from the template in config/"
            )

        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in config file: {e}")

        # Validate required fields
        required_fields = ['google_drive_folder_id']
        missing_fields = [field for field in required_fields if field not in config]

        if missing_fields:
            raise ConfigurationError(
                f"Missing required config fields: {', '.join(missing_fields)}"
            )

        # Validate folder ID format (basic check)
        folder_id = config['google_drive_folder_id']
        if not folder_id or not isinstance(folder_id, str):
            raise ConfigurationError(
                f"Invalid google_drive_folder_id: must be a valid Drive folder ID"
            )
        # Allow "root" as special case for Drive root, otherwise require 10+ chars
        if folder_id != "root" and len(folder_id) < 10:
            raise ConfigurationError(
                f"Invalid google_drive_folder_id: must be 'root' or a valid Drive folder ID (10+ characters)"
            )

        # Set default values for optional fields
        config.setdefault('max_file_size_mb', MAX_FILE_SIZE_MB)
        config.setdefault('sync_options', {})

        # Validate max_file_size_mb if provided
        max_size = config['max_file_size_mb']
        if not isinstance(max_size, (int, float)):
            raise ConfigurationError(
                f"max_file_size_mb must be a number, got {type(max_size).__name__}"
            )
        if max_size <= 0:
            raise ConfigurationError(
                f"max_file_size_mb must be positive, got {max_size}"
            )
        if max_size > 10240:  # 10GB limit
            raise ConfigurationError(
                f"max_file_size_mb too large (max 10240 MB / 10 GB), got {max_size}"
            )

        return config

    def _load_sync_state(self) -> Dict:
        """Load sync state to track downloaded files"""
        if not self.sync_state_file.exists():
            return {"synced_files": {}}

        try:
            with open(self.sync_state_file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("Warning: Corrupted sync state file, starting fresh")
            return {"synced_files": {}}

    def _save_sync_state(self, state: Dict):
        """Save sync state atomically"""
        # Atomic write: write to temp file, then rename
        temp_fd, temp_path = tempfile.mkstemp(
            dir=self.sync_state_file.parent,
            prefix='.drive_sync_state_',
            suffix='.tmp'
        )

        try:
            with os.fdopen(temp_fd, 'w') as f:
                json.dump(state, f, indent=2)

            # Atomic rename
            os.replace(temp_path, self.sync_state_file)
        except Exception:
            # Clean up temp file on error
            try:
                os.unlink(temp_path)
            except:
                pass
            raise

    def _validate_path(self, path: str) -> str:
        """
        Validate path to prevent directory traversal attacks

        Raises SecurityError if path is unsafe
        """
        # Normalize the path
        normalized = os.path.normpath(path)

        # Check for path traversal attempts
        if normalized.startswith('..') or normalized.startswith('/'):
            raise SecurityError(f"Path traversal detected: {path}")

        # Check for absolute paths
        if os.path.isabs(normalized):
            raise SecurityError(f"Absolute path not allowed: {path}")

        # Check each component
        parts = Path(normalized).parts
        for part in parts:
            # Check for hidden files/directories at root level
            if part.startswith('.') and len(parts) == 1:
                raise SecurityError(f"Hidden root directory not allowed: {path}")

            # Check for dangerous characters
            if any(char in part for char in ['\0', '\n', '\r']):
                raise SecurityError(f"Invalid characters in path: {path}")

            # Check component length
            if len(part) > MAX_PATH_LENGTH:
                raise SecurityError(f"Path component too long: {part}")

        return normalized

    def authenticate(self) -> bool:
        """Authenticate with Google Drive using OAuth2"""
        creds = None

        # Load existing token from JSON (secure, not pickle)
        if self.token_file.exists():
            try:
                with open(self.token_file, 'r') as token:
                    token_data = json.load(token)
                    creds = Credentials.from_authorized_user_info(token_data, SCOPES)
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Warning: Could not load token file: {e}")
                print("Re-authenticating...")

        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    print("Refreshing access token...")
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Token refresh failed: {e}")
                    print("Re-authenticating...")
                    creds = None

            if not creds:
                if not self.credentials_file.exists():
                    print(f"ERROR: OAuth credentials file not found: {self.credentials_file}")
                    print("Please follow the setup instructions in docs/GOOGLE_DRIVE_SETUP.md")
                    return False

                try:
                    print("Starting OAuth authentication flow...")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self.credentials_file), SCOPES)
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    print(f"Authentication failed: {e}")
                    return False

            # Save credentials as JSON (secure, not pickle)
            try:
                token_data = {
                    'token': creds.token,
                    'refresh_token': creds.refresh_token,
                    'token_uri': creds.token_uri,
                    'client_id': creds.client_id,
                    'client_secret': creds.client_secret,
                    'scopes': creds.scopes
                }

                # Atomic write
                temp_fd, temp_path = tempfile.mkstemp(
                    dir=self.token_file.parent,
                    prefix='.drive_token_',
                    suffix='.tmp'
                )

                with os.fdopen(temp_fd, 'w') as token:
                    json.dump(token_data, token, indent=2)

                os.replace(temp_path, self.token_file)

                # Set restrictive permissions on token file
                os.chmod(self.token_file, 0o600)

                print("✓ Authentication successful!")
            except Exception as e:
                print(f"Warning: Could not save token: {e}")
                # Continue anyway - auth still succeeded

        # Build Drive service
        try:
            self.service = build('drive', 'v3', credentials=creds)
        except Exception as e:
            print(f"ERROR: Could not build Drive service: {e}")
            return False

        return True

    def _list_drive_files(self, folder_id: str) -> List[Dict]:
        """List all files in a Google Drive folder recursively"""
        all_files = []

        def list_folder(parent_id: str, path_prefix: str = ""):
            page_token = None
            while True:
                try:
                    query = f"'{parent_id}' in parents and trashed=false"
                    response = self.service.files().list(
                        q=query,
                        spaces='drive',
                        fields='nextPageToken, files(id, name, mimeType, modifiedTime, size)',
                        pageToken=page_token
                    ).execute()

                    for item in response.get('files', []):
                        # Build path and validate it
                        try:
                            if path_prefix:
                                item_path = f"{path_prefix}/{item['name']}"
                            else:
                                item_path = item['name']

                            # Validate path for security
                            validated_path = self._validate_path(item_path)

                            if item['mimeType'] == 'application/vnd.google-apps.folder':
                                # Recursively list folder contents
                                list_folder(item['id'], validated_path)
                            else:
                                item['path'] = validated_path
                                all_files.append(item)

                        except SecurityError as e:
                            print(f"Skipping unsafe path: {e}")
                            continue

                    page_token = response.get('nextPageToken')
                    if not page_token:
                        break

                except HttpError as e:
                    print(f"HTTP error listing folder: {e}")
                    raise

        list_folder(folder_id)
        return all_files

    def _download_file(self, file_id: str, local_path: Path, file_size: int) -> bool:
        """
        Download a file from Google Drive atomically

        Downloads to a temp file first, then renames to avoid partial files
        """
        # Validate file size
        max_size_bytes = self.config.get('max_file_size_mb', MAX_FILE_SIZE_MB) * 1024 * 1024
        if file_size > max_size_bytes:
            print(f"Skipping {local_path}: file too large ({file_size / (1024*1024):.1f} MB > {max_size_bytes / (1024*1024):.1f} MB)")
            return False

        try:
            # Create parent directory if needed
            local_path.parent.mkdir(parents=True, exist_ok=True)

            # Download to temporary file first (atomic download)
            temp_fd, temp_path = tempfile.mkstemp(
                dir=local_path.parent,
                prefix=f'.{local_path.name}_',
                suffix='.tmp'
            )

            try:
                request = self.service.files().get_media(fileId=file_id)

                with os.fdopen(temp_fd, 'wb') as fh:
                    downloader = MediaIoBaseDownload(fh, request)
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()

                # Verify downloaded file size matches expected
                actual_size = os.path.getsize(temp_path)
                if actual_size != file_size:
                    print(f"Warning: Size mismatch for {local_path} (expected {file_size}, got {actual_size})")

                # Atomic rename to final location
                os.replace(temp_path, local_path)
                return True

            except Exception:
                # Clean up temp file on error
                try:
                    os.unlink(temp_path)
                except:
                    pass
                raise

        except HttpError as e:
            print(f"HTTP error downloading {local_path}: {e}")
            return False
        except IOError as e:
            print(f"IO error downloading {local_path}: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error downloading {local_path}: {e}")
            return False

    def check_for_new_files(self) -> Dict:
        """Check what files need to be synced"""
        if not self.service:
            if not self.authenticate():
                return {"error": "Authentication failed"}

        try:
            folder_id = self.config.get('google_drive_folder_id')
            if not folder_id:
                return {"error": "Missing folder ID in config"}

            print(f"Checking Google Drive folder for new files...")
            drive_files = self._list_drive_files(folder_id)
            sync_state = self._load_sync_state()

            files_to_sync = []
            for file_info in drive_files:
                file_key = file_info['id']
                drive_modified = file_info['modifiedTime']

                # Check if file needs sync
                if file_key not in sync_state['synced_files']:
                    files_to_sync.append(file_info)
                elif sync_state['synced_files'][file_key]['modified'] != drive_modified:
                    files_to_sync.append(file_info)

            return {
                'total_drive_files': len(drive_files),
                'files_to_sync': files_to_sync,
                'up_to_date': len(drive_files) - len(files_to_sync)
            }

        except HttpError as e:
            return {"error": f"Google Drive API error: {e}"}
        except SecurityError as e:
            return {"error": f"Security validation failed: {e}"}
        except Exception as e:
            return {"error": f"Unexpected error: {e}"}

    def sync_files(self, dry_run: bool = False) -> Dict:
        """Sync files from Google Drive to local directory"""
        if not self.service:
            if not self.authenticate():
                return {"error": "Authentication failed"}

        check_result = self.check_for_new_files()
        if 'error' in check_result:
            return check_result

        files_to_sync = check_result['files_to_sync']

        if not files_to_sync:
            print("✓ All files are up to date. No sync needed.")
            return {"synced": 0, "skipped": check_result['total_drive_files']}

        print(f"\nFound {len(files_to_sync)} file(s) to sync:")

        synced_count = 0
        failed_count = 0
        sync_state = self._load_sync_state()

        for file_info in files_to_sync:
            relative_path = file_info['path']
            local_path = self.local_data_dir / relative_path

            size_mb = int(file_info.get('size', 0)) / (1024 * 1024)
            print(f"  • {relative_path} ({size_mb:.2f} MB)")

            if not dry_run:
                try:
                    if self._download_file(file_info['id'], local_path, int(file_info.get('size', 0))):
                        # Update sync state
                        sync_state['synced_files'][file_info['id']] = {
                            'path': relative_path,
                            'modified': file_info['modifiedTime'],
                            'synced_at': datetime.now().isoformat()
                        }
                        synced_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    print(f"Error syncing {relative_path}: {e}")
                    failed_count += 1

        if not dry_run:
            try:
                self._save_sync_state(sync_state)
                print(f"\n✓ Synced {synced_count} file(s) from Google Drive")
                if failed_count > 0:
                    print(f"⚠ Failed to sync {failed_count} file(s)")
            except Exception as e:
                print(f"Warning: Could not save sync state: {e}")
        else:
            print(f"\n(Dry run - no files downloaded)")

        return {
            "synced": synced_count if not dry_run else 0,
            "failed": failed_count if not dry_run else 0,
            "would_sync": len(files_to_sync) if dry_run else 0,
            "up_to_date": check_result['up_to_date']
        }


def main():
    parser = argparse.ArgumentParser(
        description="Sync Health Connect data from Google Drive"
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Run OAuth setup flow"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Check what would be synced without downloading"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress output"
    )

    args = parser.parse_args()

    try:
        syncer = GoogleDriveHealthSync()
    except ConfigurationError as e:
        print(f"Configuration error: {e}")
        return 1

    if args.setup:
        print("Running OAuth setup...")
        if syncer.authenticate():
            print("✓ Setup complete! You can now sync files.")
            return 0
        else:
            return 1

    # Sync files
    result = syncer.sync_files(dry_run=args.check_only)

    if 'error' in result:
        print(f"ERROR: {result['error']}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
