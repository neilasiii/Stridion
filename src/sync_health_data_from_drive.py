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
"""

import os
import sys
import json
import pickle
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
except ImportError:
    print("ERROR: Google Drive dependencies not installed.")
    print("Please run: pip install -r requirements.txt")
    sys.exit(1)

# If modifying these scopes, delete the token.pickle file
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

class GoogleDriveHealthSync:
    """Manages syncing health data from Google Drive"""

    def __init__(self, config_file: str = "config/.drive_sync_config.json"):
        self.config_file = Path(config_file)
        self.token_file = Path("config/.drive_token.pickle")
        self.credentials_file = Path("config/credentials.json")
        self.local_data_dir = Path("health_connect_export")
        self.sync_state_file = Path("config/.drive_sync_state.json")

        self.config = self._load_config()
        self.service = None

    def _load_config(self) -> Dict:
        """Load configuration file"""
        if not self.config_file.exists():
            print(f"ERROR: Config file not found: {self.config_file}")
            print("Please create config/.drive_sync_config.json from the template in config/")
            sys.exit(1)

        with open(self.config_file, 'r') as f:
            return json.load(f)

    def _load_sync_state(self) -> Dict:
        """Load sync state to track downloaded files"""
        if not self.sync_state_file.exists():
            return {"synced_files": {}}

        with open(self.sync_state_file, 'r') as f:
            return json.load(f)

    def _save_sync_state(self, state: Dict):
        """Save sync state"""
        with open(self.sync_state_file, 'w') as f:
            json.dump(state, f, indent=2)

    def authenticate(self) -> bool:
        """Authenticate with Google Drive using OAuth2"""
        creds = None

        # Load existing token
        if self.token_file.exists():
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)

        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("Refreshing access token...")
                creds.refresh(Request())
            else:
                if not self.credentials_file.exists():
                    print(f"ERROR: OAuth credentials file not found: {self.credentials_file}")
                    print("Please follow the setup instructions in docs/GOOGLE_DRIVE_SETUP.md")
                    return False

                print("Starting OAuth authentication flow...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_file), SCOPES)
                creds = flow.run_local_server(port=0)

            # Save credentials for next run
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
            print("✓ Authentication successful!")

        # Build Drive service
        self.service = build('drive', 'v3', credentials=creds)
        return True

    def _list_drive_files(self, folder_id: str) -> List[Dict]:
        """List all files in a Google Drive folder recursively"""
        all_files = []

        def list_folder(parent_id: str, path_prefix: str = ""):
            page_token = None
            while True:
                query = f"'{parent_id}' in parents and trashed=false"
                response = self.service.files().list(
                    q=query,
                    spaces='drive',
                    fields='nextPageToken, files(id, name, mimeType, modifiedTime, size)',
                    pageToken=page_token
                ).execute()

                for item in response.get('files', []):
                    item_path = f"{path_prefix}/{item['name']}" if path_prefix else item['name']

                    if item['mimeType'] == 'application/vnd.google-apps.folder':
                        # Recursively list folder contents
                        list_folder(item['id'], item_path)
                    else:
                        item['path'] = item_path
                        all_files.append(item)

                page_token = response.get('nextPageToken')
                if not page_token:
                    break

        list_folder(folder_id)
        return all_files

    def _download_file(self, file_id: str, local_path: Path) -> bool:
        """Download a file from Google Drive"""
        try:
            # Create parent directory if needed
            local_path.parent.mkdir(parents=True, exist_ok=True)

            request = self.service.files().get_media(fileId=file_id)

            with open(local_path, 'wb') as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()

            return True
        except Exception as e:
            print(f"ERROR downloading {local_path}: {e}")
            return False

    def check_for_new_files(self) -> Dict:
        """Check what files need to be synced"""
        if not self.service:
            if not self.authenticate():
                return {"error": "Authentication failed"}

        folder_id = self.config.get('google_drive_folder_id')
        if not folder_id:
            print("ERROR: google_drive_folder_id not set in config")
            return {"error": "Missing folder ID"}

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
        sync_state = self._load_sync_state()

        for file_info in files_to_sync:
            relative_path = file_info['path']
            local_path = self.local_data_dir / relative_path

            size_mb = int(file_info.get('size', 0)) / (1024 * 1024)
            print(f"  • {relative_path} ({size_mb:.2f} MB)")

            if not dry_run:
                if self._download_file(file_info['id'], local_path):
                    # Update sync state
                    sync_state['synced_files'][file_info['id']] = {
                        'path': relative_path,
                        'modified': file_info['modifiedTime'],
                        'synced_at': datetime.now().isoformat()
                    }
                    synced_count += 1

        if not dry_run:
            self._save_sync_state(sync_state)
            print(f"\n✓ Synced {synced_count} file(s) from Google Drive")
        else:
            print(f"\n(Dry run - no files downloaded)")

        return {
            "synced": synced_count if not dry_run else 0,
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

    syncer = GoogleDriveHealthSync()

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
