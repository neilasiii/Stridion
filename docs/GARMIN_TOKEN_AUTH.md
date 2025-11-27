# Garmin Connect Token-Based Authentication

## Overview

Token-based authentication provides a more reliable way to access Garmin Connect from automated environments (like Claude Code bots) where password-based authentication may be blocked by Garmin's security measures.

## Why Token-Based Authentication?

**Password Authentication Issues:**
- Garmin Connect uses aggressive bot protection (Cloudflare, etc.)
- Automated login attempts often receive 403 Forbidden errors
- 2FA/CAPTCHA challenges can't be completed in headless environments
- Rate limiting may block repeated authentication attempts

**Token Authentication Benefits:**
- Bypasses initial login flow that triggers bot protection
- OAuth tokens valid for ~1 year without re-authentication
- More reliable for automated/scheduled syncs
- Works in headless/bot environments

## Quick Start

> **Mobile Users:** See [GARMIN_TOKEN_AUTH_MOBILE.md](GARMIN_TOKEN_AUTH_MOBILE.md) for iOS/Android-specific instructions.

### Option 1: Generate Tokens on Local Machine (Recommended)

1. **On your LOCAL machine** (with browser access), run:
   ```bash
   python3 bin/generate_garmin_tokens.py
   ```

2. **Enter your credentials** when prompted

3. **Transfer tokens to server:**
   ```bash
   scp -r ~/garmin_tokens/* user@server:~/.garminconnect/
   ```

4. **Test on server:**
   ```bash
   python3 src/garmin_token_auth.py --test
   ```

5. **Run sync:**
   ```bash
   bash bin/sync_garmin_data.sh
   ```

### Option 2: Manual Token Extraction

If automated token generation fails, you can extract tokens manually from your browser:

1. **Run the extraction guide:**
   ```bash
   python3 src/garmin_token_auth.py --extract
   ```

2. **Follow the step-by-step instructions** to:
   - Log into Garmin Connect in a browser
   - Extract OAuth tokens from browser storage
   - Save tokens to `~/.garminconnect/`

3. **Test tokens:**
   ```bash
   python3 src/garmin_token_auth.py --test
   ```

## How It Works

### Authentication Flow

1. **Token Check**: System first checks for existing tokens in `~/.garminconnect/`

2. **Token Validation**: If tokens exist, validates them with a test API call

3. **Fallback**: If tokens are invalid or missing, falls back to password authentication

4. **Token Save**: Successful password auth automatically saves tokens for future use

### Token Storage

Tokens are stored in `~/.garminconnect/` directory:

```
~/.garminconnect/
├── oauth1_token.json     # OAuth 1.0 token
└── oauth2_token.json     # OAuth 2.0 token (primary)
```

**Token Contents:**
- **OAuth1Token**: `oauth_token`, `oauth_token_secret`, optional MFA data
- **OAuth2Token**: `access_token`, `refresh_token`, expiration timestamps

**Security:**
- Tokens are stored with restrictive permissions (600)
- Contain same access level as your account
- Should be kept secure like passwords

### Token Expiration

- **Access Token**: Expires after a short period (minutes to hours)
- **Refresh Token**: Valid for ~1 year
- **Auto-Refresh**: Library automatically refreshes access token using refresh token
- **Manual Refresh**: If all tokens expire, re-run token generation

## Usage in Scripts

### Python API

```python
from garmin_token_auth import authenticate_with_tokens

# Authenticate with tokens (or fall back to password)
client = authenticate_with_tokens()

if client:
    # Use authenticated client
    activities = client.get_activities(0, 10)
else:
    print("Authentication failed")
```

### Automatic Integration

The `garmin_sync.py` script automatically uses token authentication:

```bash
# Will use tokens if available, otherwise tries password auth
bash bin/sync_garmin_data.sh
```

## Troubleshooting

### 403 Forbidden Error

**Symptom:**
```
Error: Login failed: 403 Client Error: Forbidden
```

**Solution:**
Password authentication is being blocked. Use token-based auth:
```bash
python3 src/garmin_token_auth.py --extract
```

### Tokens Not Found

**Symptom:**
```
No valid tokens found and GARMIN_EMAIL/GARMIN_PASSWORD not set
```

**Solution:**
Either generate tokens or set environment variables:
```bash
# Option 1: Generate tokens
python3 bin/generate_garmin_tokens.py

# Option 2: Set credentials
export GARMIN_EMAIL=your@email.com
export GARMIN_PASSWORD=yourpassword
```

### Invalid/Expired Tokens

**Symptom:**
```
Tokens found but invalid
```

**Solution:**
Re-generate tokens:
```bash
rm -rf ~/.garminconnect
python3 bin/generate_garmin_tokens.py
```

### 2FA Enabled

**Issue:**
Garmin account has two-factor authentication enabled

**Solutions:**

1. **Use local token generation** (recommended):
   - Run `python3 bin/generate_garmin_tokens.py` on local machine
   - Complete 2FA challenge when prompted
   - Transfer tokens to server

2. **Disable 2FA temporarily**:
   - Log into Garmin Connect
   - Disable 2FA in account settings
   - Generate tokens
   - Re-enable 2FA

3. **Use app-specific password** (if Garmin supports):
   - Generate app-specific password in account settings
   - Use that instead of main password

### Token Transfer Fails

**Issue:**
Can't transfer tokens from local machine to server

**Solution:**
Manually create token files on server:

1. On local machine after running `generate_garmin_tokens.py`:
   ```bash
   cat ~/garmin_tokens/oauth1_token.json
   cat ~/garmin_tokens/oauth2_token.json
   ```

2. On server, create files:
   ```bash
   mkdir -p ~/.garminconnect
   nano ~/.garminconnect/oauth1_token.json
   # Paste content, save (Ctrl+X, Y, Enter)

   nano ~/.garminconnect/oauth2_token.json
   # Paste content, save
   ```

3. Test:
   ```bash
   python3 src/garmin_token_auth.py --test
   ```

## Advanced Usage

### Custom Token Location

```python
from garminconnect import Garmin

client = Garmin()
client.garth.load('/path/to/token/directory')
```

### Programmatic Token Save

```python
from garminconnect import Garmin
from garmin_token_auth import save_tokens

# After successful authentication
client = Garmin(email, password)
client.login()

# Save tokens for reuse
save_tokens(client)
```

### Token Inspection

```python
import json
from pathlib import Path

token_dir = Path.home() / '.garminconnect'

# Read OAuth2 token
with open(token_dir / 'oauth2_token.json') as f:
    oauth2 = json.load(f)
    print(f"Access token expires: {oauth2['expires_at']}")
    print(f"Refresh token expires: {oauth2['refresh_token_expires_at']}")
```

## Security Considerations

1. **Token Protection**
   - Store tokens securely (use file permissions 600)
   - Don't commit tokens to git
   - Don't share tokens publicly

2. **Access Level**
   - Tokens have same access as your account
   - Can read all health data
   - Can write/modify activities
   - Treat like passwords

3. **Revocation**
   - Delete tokens to revoke: `rm -rf ~/.garminconnect`
   - Change Garmin password to invalidate all tokens
   - Log out of all devices in Garmin Connect settings

4. **Environment Variables**
   - Credentials in environment variables only used for initial auth
   - Not stored permanently
   - Use token-based auth in production

## Best Practices

1. **Use token-based auth for automated systems**
   - More reliable than password auth
   - Avoids bot protection issues
   - Tokens last ~1 year

2. **Generate tokens on local machine**
   - Easier to handle 2FA/CAPTCHA
   - More secure than disabling 2FA
   - One-time setup

3. **Monitor token expiration**
   - Set reminder for ~11 months
   - Re-generate before expiration
   - Test auth periodically

4. **Secure token storage**
   - Use restrictive file permissions
   - Don't expose in logs
   - Rotate regularly

## Related Documentation

- [Health Data System](HEALTH_DATA_SYSTEM.md) - Overall health data architecture
- [Troubleshooting Guide](#troubleshooting) - Common issues and solutions
- [CLAUDE.md](../CLAUDE.md) - Project overview and commands
