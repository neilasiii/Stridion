#!/usr/bin/env python3
"""
Garmin Connect Token Generator

Run this script on your LOCAL MACHINE (with browser access) to generate
OAuth tokens that can then be transferred to the server for automated access.

This script is meant to be run OUTSIDE of Claude Code, on a machine where
you can complete 2FA/CAPTCHA challenges if needed.

Usage:
    python3 generate_garmin_tokens.py

After running:
    1. Tokens will be saved to ~/garmin_tokens/
    2. Transfer the entire directory to the server at ~/.garminconnect/
    3. Run sync on the server: bash bin/sync_garmin_data.sh
"""

import os
import sys
from pathlib import Path

try:
    from garminconnect import Garmin
except ImportError:
    print("Error: garminconnect library not installed")
    print("Install with: pip install garminconnect")
    sys.exit(1)


def main():
    print("="*70)
    print("Garmin Connect Token Generator")
    print("="*70)
    print()

    # Get credentials
    email = input("Garmin Connect email: ").strip()
    password = input("Garmin Connect password: ").strip()

    if not email or not password:
        print("Error: Email and password required")
        return 1

    # Output directory
    output_dir = Path.home() / "garmin_tokens"
    output_dir.mkdir(parents=True, exist_ok=True)

    print()
    print(f"Attempting to authenticate with Garmin Connect...")
    print()

    try:
        # Create client
        client = Garmin(email, password)

        # Login (may require MFA/CAPTCHA in some cases)
        print("Logging in...")
        client.login()

        print("✓ Login successful!")
        print()

        # Test API access
        name = client.get_full_name()
        print(f"✓ Authenticated as: {name}")
        print()

        # Save tokens
        print(f"Saving tokens to {output_dir}...")
        client.garth.dump(str(output_dir))

        print("✓ Tokens saved!")
        print()
        print("="*70)
        print("SUCCESS")
        print("="*70)
        print()
        print(f"Tokens saved to: {output_dir}")
        print()
        print("Next steps:")
        print()
        print("1. Transfer the token directory to your server:")
        print(f"   scp -r {output_dir}/* user@server:~/.garminconnect/")
        print()
        print("2. On the server, run:")
        print("   bash bin/sync_garmin_data.sh")
        print()
        print("These tokens are valid for ~1 year and can be reused")
        print("without re-authentication.")
        print()

        return 0

    except Exception as e:
        print()
        print(f"❌ Authentication failed: {e}")
        print()
        print("Common issues:")
        print("- Incorrect email/password")
        print("- 2FA enabled (may require additional setup)")
        print("- Account locked or requires browser verification")
        print("- Garmin Connect service issues")
        print()
        return 1


if __name__ == '__main__':
    sys.exit(main())
