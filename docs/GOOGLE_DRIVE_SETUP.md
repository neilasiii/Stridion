# Google Drive Health Data Sync Setup

This guide walks you through setting up automatic syncing of Health Connect data from Google Drive.

## Overview

Instead of manually downloading health data exports from Google Drive, this system automatically syncs files directly from your Drive folder where Health Sync uploads them.

## Prerequisites

- Python 3.6 or higher
- A Google account with Health Connect data being synced to Google Drive via Health Sync app
- Internet connection

## Setup Steps

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs the Google Drive API client libraries.

### 2. Create a Google Cloud Project and Enable Drive API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use an existing one)
   - Click "Select a project" → "New Project"
   - Name it something like "Running Coach Health Sync"
   - Click "Create"

3. Enable the Google Drive API
   - In the search bar, search for "Google Drive API"
   - Click on "Google Drive API"
   - Click "Enable"

### 3. Create OAuth 2.0 Credentials

1. In Google Cloud Console, go to "APIs & Services" → "Credentials"

2. Click "Create Credentials" → "OAuth client ID"

3. If prompted to configure the OAuth consent screen:
   - Click "Configure Consent Screen"
   - Select "External" (unless you have a Google Workspace account)
   - Fill in the required fields:
     - App name: "Running Coach Health Sync"
     - User support email: your email
     - Developer contact: your email
   - Click "Save and Continue"
   - Skip adding scopes (click "Save and Continue")
   - Add yourself as a test user
   - Click "Save and Continue"

4. Back on the "Create OAuth client ID" page:
   - Application type: "Desktop app"
   - Name: "Running Coach Desktop Client"
   - Click "Create"

5. Download the credentials:
   - Click "Download JSON" on the popup
   - Save the file as `credentials.json` in your running-coach directory

### 4. Find Your Google Drive Folder ID

1. Open Google Drive in your web browser
2. Navigate to the folder where Health Sync uploads your data
   - This is typically named something like "Health Sync" or "Health Connect"
3. Look at the URL in your browser's address bar:
   ```
   https://drive.google.com/drive/folders/1a2b3c4d5e6f7g8h9i0j
                                           ^^^^^^^^^^^^^^^^^^^
                                           This is your folder ID
   ```
4. Copy the folder ID (the long string after `/folders/`)

### 5. Configure the Sync Settings

1. Copy the config template:
   ```bash
   cp .drive_sync_config.json.template .drive_sync_config.json
   ```

2. Edit `.drive_sync_config.json`:
   ```json
   {
     "google_drive_folder_id": "PASTE_YOUR_FOLDER_ID_HERE",
     "sync_options": {
       "auto_update_cache": true,
       "delete_local_if_removed_from_drive": false
     }
   }
   ```

3. Replace `PASTE_YOUR_FOLDER_ID_HERE` with the folder ID you copied

### 6. Authenticate

Run the setup command to complete OAuth authentication:

```bash
python3 sync_health_data_from_drive.py --setup
```

This will:
1. Open your web browser
2. Ask you to sign in to your Google account
3. Request permission to read your Google Drive files
4. Save an authentication token locally (`.drive_token.json`)

**Important**: You only need to do this once. The token will be automatically refreshed when needed.

## Usage

### Sync and Update in One Command

The simplest way to sync your data:

```bash
bash sync_and_update.sh
```

This will:
1. Download new/updated files from Google Drive
2. Update the health data cache
3. Show a summary of your recent activity

### Check What Would Be Synced

To see what files would be downloaded without actually downloading them:

```bash
bash sync_and_update.sh --check-only
```

### Sync Only (Without Updating Cache)

To just download files from Google Drive:

```bash
python3 sync_health_data_from_drive.py
```

### Manual Cache Update

To update the cache from already-downloaded files:

```bash
python3 update_health_data.py
```

## Integration with Coaching Agents

The coaching agents can now call:

```bash
bash sync_and_update.sh
```

This replaces the old workflow of:
1. Manually downloading from Google Drive
2. Running `bash check_health_data.sh`

## File Structure

After setup, you'll have these files:

```
running-coach/
├── credentials.json                    # OAuth credentials (from Google Cloud)
├── .drive_token.json                 # Authentication token (auto-generated)
├── .drive_sync_config.json            # Your folder ID and settings
├── .drive_sync_state.json             # Tracks synced files (auto-generated)
├── sync_health_data_from_drive.py     # Main sync script
├── sync_and_update.sh                 # Convenience wrapper
└── health_connect_export/             # Local copy of Drive data
    ├── Health Sync Activities/
    ├── Health Sync Sleep/
    ├── Health Sync Heart rate/
    └── ...
```

## Security Notes

- **credentials.json**: Contains your OAuth client ID and secret. Keep this private.
- **.drive_token.json**: Contains your authentication token. Keep this private.
- Both files should be added to `.gitignore` to avoid committing them to version control.
- The system only requests READ-ONLY access to your Drive files.

## Troubleshooting

### "credentials.json not found"

Make sure you downloaded the OAuth credentials from Google Cloud Console and saved them as `credentials.json` in the running-coach directory.

### "Authentication failed"

Try deleting `.drive_token.json` and running the setup again:

```bash
rm .drive_token.json
python3 sync_health_data_from_drive.py --setup
```

### "Config file not found"

Make sure you copied the template and added your folder ID:

```bash
cp .drive_sync_config.json.template .drive_sync_config.json
# Then edit .drive_sync_config.json with your folder ID
```

### "Folder ID not set"

Edit `.drive_sync_config.json` and replace `YOUR_FOLDER_ID_HERE` with your actual Google Drive folder ID.

### Permission Denied Error

If you see a permission error during OAuth flow, make sure:
1. You added yourself as a test user in the OAuth consent screen
2. The app is in "Testing" mode (not "Published")
3. You're signing in with the same Google account that owns the Drive folder

## Automation (Optional)

To automatically sync on a schedule, you can set up a cron job:

```bash
# Edit your crontab
crontab -e

# Add this line to sync every 6 hours
0 */6 * * * cd /path/to/running-coach && bash sync_and_update.sh >> logs/sync.log 2>&1
```

Or use a systemd timer on Linux systems.

## Update CLAUDE.md Reference

The `CLAUDE.md` file should now reference the new sync command:

```bash
# OLD: Manually download from Drive, then:
bash check_health_data.sh

# NEW: Automatically sync from Drive and update:
bash sync_and_update.sh
```

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Verify your Google Cloud project settings
3. Make sure the Drive API is enabled
4. Confirm your folder ID is correct
