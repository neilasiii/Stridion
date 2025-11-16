#!/usr/bin/env python3
"""
One-time Garmin Connect authentication with MFA support

This script handles the initial login with 2FA and saves tokens for future use.
After running this once, the regular sync script will work without needing MFA again.

Usage:
    python3 bin/garmin_login_with_mfa.py
"""

import json
from pathlib import Path
import garth

def main():
    # Load credentials
    creds_file = Path(__file__).parent.parent / ".garmin_credentials.json"

    if creds_file.exists():
        with open(creds_file, 'r') as f:
            creds = json.load(f)
            email = creds.get('garmin_email')
            password = creds.get('garmin_password')
    else:
        print("Credentials file not found. Please enter credentials:")
        email = input("Garmin email: ")
        password = input("Garmin password: ")

    if not email or not password:
        print("Error: Email and password required")
        return 1

    print(f"\nAttempting to authenticate with Garmin Connect...")
    print(f"Email: {email}")

    try:
        # Initialize garth
        garth.configure(domain="garmin.com")

        # Attempt login
        print("\nLogging in...")
        tokens = garth.login(email, password)

        print("\n✓ Login successful!")
        print(f"OAuth1 token: {tokens[0][:20]}...")
        print(f"OAuth2 token: {tokens[1][:20]}...")

        # Tokens are automatically saved to ~/.garminconnect/
        print(f"\nTokens saved to: {Path.home() / '.garminconnect'}")
        print("\nYou can now use the regular sync script without MFA!")
        print("Run: bash bin/sync_garmin_data.sh")

        return 0

    except Exception as e:
        error_str = str(e).lower()

        if "mfa" in error_str or "two" in error_str or "2fa" in error_str:
            print("\n⚠ Two-Factor Authentication (MFA) detected!")
            print("\nPlease enter your MFA code when prompted:")

            try:
                # Retry with MFA
                mfa_code = input("MFA Code: ")
                tokens = garth.login(email, password, mfa_code=mfa_code)

                print("\n✓ MFA authentication successful!")
                print(f"\nTokens saved to: {Path.home() / '.garminconnect'}")
                print("\nYou can now use the regular sync script without MFA!")
                print("Run: bash bin/sync_garmin_data.sh")

                return 0

            except Exception as e2:
                print(f"\n❌ MFA authentication failed: {e2}")
                return 1

        else:
            print(f"\n❌ Authentication failed: {e}")
            print("\nPossible issues:")
            print("1. Incorrect email/password")
            print("2. Account locked or requires CAPTCHA")
            print("3. Garmin Connect API issues")
            print("\nTry logging in manually at: https://connect.garmin.com")
            return 1

if __name__ == '__main__':
    exit(main())
