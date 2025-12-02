#!/usr/bin/env python3
"""
Garmin Token-Based Authentication Helper

This script provides token-based authentication for Garmin Connect, which is more
suitable for automated/bot access than password-based authentication.

Usage:
    1. Extract tokens manually (one-time setup):
       python3 src/garmin_token_auth.py --extract

    2. Test token authentication:
       python3 src/garmin_token_auth.py --test

    3. Use in garmin_sync.py (automatic)

Token Storage:
    Tokens are stored in ~/.garminconnect/ directory and can be reused
    for ~1 year without re-authentication.
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional, Tuple

try:
    from garminconnect import Garmin
    import garth
    from garth.auth_tokens import OAuth1Token, OAuth2Token
except ImportError:
    print("Error: garminconnect library not installed.", file=sys.stderr)
    print("Install with: pip3 install garminconnect", file=sys.stderr)
    sys.exit(1)


# Token storage directory
TOKEN_DIR = Path.home() / ".garminconnect"
TOKEN_FILE = TOKEN_DIR / "tokens.json"


def save_tokens(client: Garmin) -> bool:
    """
    Save OAuth tokens from an authenticated Garmin client.

    Args:
        client: Authenticated Garmin client

    Returns:
        True if tokens were saved successfully
    """
    try:
        TOKEN_DIR.mkdir(parents=True, exist_ok=True)

        # Use garth's built-in dump method to save tokens
        client.garth.dump(str(TOKEN_DIR))

        print(f"✓ Tokens saved to {TOKEN_DIR}")
        return True

    except Exception as e:
        print(f"Error saving tokens: {e}", file=sys.stderr)
        return False


def load_tokens() -> Optional[Garmin]:
    """
    Load OAuth tokens and create an authenticated Garmin client.

    Returns:
        Authenticated Garmin client or None if tokens not found/invalid
    """
    try:
        if not TOKEN_DIR.exists():
            return None

        # Create Garmin client without credentials
        client = Garmin()

        # Load tokens using garth's built-in load method
        client.garth.load(str(TOKEN_DIR))

        # Set display_name and username from garth profile (required for some API calls)
        try:
            profile = client.garth.profile
            client.display_name = profile.get('displayName')
            client.username = profile.get('userName')
        except Exception:
            # If we can't get profile, continue anyway - some API calls may still work
            pass

        # Verify tokens are valid by making a test API call
        try:
            client.get_full_name()
            print(f"✓ Loaded valid tokens from {TOKEN_DIR}")
            return client
        except Exception as e:
            print(f"⚠ Tokens found but invalid: {e}", file=sys.stderr)
            return None

    except Exception as e:
        print(f"⚠ Could not load tokens: {e}", file=sys.stderr)
        return None


def authenticate_with_tokens() -> Optional[Garmin]:
    """
    Authenticate with Garmin Connect using stored tokens or credentials.

    Returns:
        Authenticated Garmin client or None if authentication fails
    """
    # First, try to load existing tokens
    client = load_tokens()
    if client:
        return client

    # If no tokens, try password authentication
    email = os.getenv("GARMIN_EMAIL")
    password = os.getenv("GARMIN_PASSWORD")

    if not email or not password:
        print("Error: No tokens found and GARMIN_EMAIL/GARMIN_PASSWORD not set", file=sys.stderr)
        return None

    try:
        print("No valid tokens found, attempting password authentication...")
        client = Garmin(email, password)

        # Try to login and save tokens
        client.login()

        # Save tokens for future use
        save_tokens(client)

        print("✓ Authentication successful")
        return client

    except Exception as e:
        print(f"Error: Authentication failed: {e}", file=sys.stderr)
        return None


def extract_tokens_manual():
    """
    Interactive guide for manually extracting Garmin Connect tokens.

    This method works when automated authentication fails due to bot protection.
    """
    print("\n" + "="*70)
    print("Manual Token Extraction Guide")
    print("="*70)
    print("\nFollow these steps to extract Garmin Connect OAuth tokens:\n")

    print("MOBILE USERS: See docs/GARMIN_TOKEN_AUTH_MOBILE.md for mobile-specific")
    print("              instructions (iOS/Android)")
    print()

    print("1. Open a browser and navigate to:")
    print("   https://connect.garmin.com/")
    print()

    print("2. Log in with your Garmin Connect credentials")
    print()

    print("3. Open Browser Developer Tools:")
    print("   - Chrome/Edge: Press F12 or Ctrl+Shift+I")
    print("   - Firefox: Press F12 or Ctrl+Shift+I")
    print("   - Safari: Enable Developer Menu, then press Cmd+Option+I")
    print()

    print("4. Go to the 'Application' or 'Storage' tab")
    print()

    print("5. Find the following cookies for connect.garmin.com:")
    print("   - OAuth1Token (oauth_token and oauth_token_secret)")
    print("   - OAuth2Token (access_token, refresh_token, etc.)")
    print()

    print("6. Alternative method using Python on your LOCAL machine:")
    print("   Run the following code on a machine with browser access:")
    print()
    print("```python")
    print("from garminconnect import Garmin")
    print("import os")
    print()
    print("# Authenticate (this will open browser if needed)")
    print("client = Garmin('your_email@example.com', 'your_password')")
    print("client.login()")
    print()
    print("# Save tokens")
    print("client.garth.dump('/tmp/garmin_tokens')")
    print("print('Tokens saved to /tmp/garmin_tokens')")
    print("```")
    print()

    print("7. Copy the token files to this server:")
    print(f"   {TOKEN_DIR}/")
    print()

    print("8. Test the tokens:")
    print("   python3 src/garmin_token_auth.py --test")
    print()

    print("="*70)
    print()


def test_authentication():
    """Test authentication with current tokens or credentials."""
    print("\n" + "="*70)
    print("Testing Garmin Connect Authentication")
    print("="*70 + "\n")

    client = authenticate_with_tokens()

    if not client:
        print("\n❌ Authentication FAILED")
        print("\nOptions:")
        print("1. Set credentials: export GARMIN_EMAIL=... GARMIN_PASSWORD=...")
        print("2. Extract tokens manually: python3 src/garmin_token_auth.py --extract")
        return False

    # Test API access
    try:
        full_name = client.get_full_name()
        print(f"✓ Authenticated as: {full_name}")

        # Try to fetch recent activity
        activities = client.get_activities(0, 1)
        if activities:
            print(f"✓ API access working - can fetch activities")

        print("\n✅ Authentication SUCCESS")
        print(f"\nTokens stored in: {TOKEN_DIR}")
        print("These tokens can be used for ~1 year without re-authentication")
        return True

    except Exception as e:
        print(f"\n❌ Authentication failed: {e}")
        return False


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Garmin Connect Token Authentication Helper')
    parser.add_argument('--extract', action='store_true',
                        help='Show guide for manual token extraction')
    parser.add_argument('--test', action='store_true',
                        help='Test authentication with current tokens/credentials')

    args = parser.parse_args()

    if args.extract:
        extract_tokens_manual()
        return 0
    elif args.test:
        success = test_authentication()
        return 0 if success else 1
    else:
        parser.print_help()
        return 0


if __name__ == '__main__':
    sys.exit(main())
