#!/usr/bin/env python3
"""
Save Garmin Connect OAuth tokens for use with sync script

After logging into Garmin Connect in your browser, extract the OAuth tokens
and run this script to save them for the garminconnect library to use.

Usage:
    python3 bin/save_garmin_tokens.py <oauth1_token> <oauth2_token>
"""

import sys
import json
from pathlib import Path

def save_tokens(oauth1_token, oauth2_token):
    """Save OAuth tokens to garth's token directory"""

    # Create .garminconnect directory
    token_dir = Path.home() / '.garminconnect'
    token_dir.mkdir(exist_ok=True, mode=0o700)

    # Save tokens in the format garth expects
    token_file = token_dir / 'tokens.json'

    tokens = {
        "oauth1": oauth1_token,
        "oauth2": oauth2_token
    }

    with open(token_file, 'w') as f:
        json.dump(tokens, f, indent=2)

    # Set restrictive permissions
    token_file.chmod(0o600)

    print(f"✓ Tokens saved to: {token_file}")
    print("\nYou can now run the sync script:")
    print("  bash bin/sync_garmin_data.sh --days 7")

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 bin/save_garmin_tokens.py <oauth1_token> <oauth2_token>")
        print("\nTo get your tokens:")
        print("1. Login to https://connect.garmin.com in your browser")
        print("2. Open Developer Tools (F12)")
        print("3. Go to Application tab -> Cookies -> https://connect.garmin.com")
        print("4. Find these cookies:")
        print("   - oauth_token (this is oauth1)")
        print("   - oauth_token_secret (this is oauth2)")
        print("\nExample:")
        print("  python3 bin/save_garmin_tokens.py 'abc123...' 'xyz789...'")
        return 1

    oauth1 = sys.argv[1]
    oauth2 = sys.argv[2]

    if not oauth1 or not oauth2:
        print("Error: Both tokens are required")
        return 1

    save_tokens(oauth1, oauth2)
    return 0

if __name__ == '__main__':
    sys.exit(main())
