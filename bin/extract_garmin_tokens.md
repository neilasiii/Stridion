# Manually Extract Garmin Connect Tokens

Since Garmin's CloudFlare protection is blocking automated logins, you can manually extract authentication tokens from your browser and use them with the sync script.

## Steps to Extract Tokens:

### 1. Open Browser Developer Tools
1. Open Chrome/Firefox
2. Press F12 to open Developer Tools
3. Go to the **Application** tab (Chrome) or **Storage** tab (Firefox)

### 2. Login to Garmin Connect
1. Navigate to https://connect.garmin.com
2. Log in with your credentials (complete any 2FA if needed)
3. Verify you're logged in and can see your dashboard

### 3. Extract Tokens
In Developer Tools:
1. Go to **Cookies** → `https://connect.garmin.com`
2. Look for these cookies and copy their values:
   - `oauth_token`
   - `oauth_token_secret`

### 4. Save Tokens
Create/edit the file: `~/.garminconnect/tokens.json`

```bash
mkdir -p ~/.garminconnect
nano ~/.garminconnect/tokens.json
```

Add this content (replace with your actual token values):
```json
{
  "oauth1_token": "YOUR_OAUTH_TOKEN_VALUE",
  "oauth2_token": "YOUR_OAUTH_TOKEN_SECRET_VALUE"
}
```

### 5. Test
```bash
bash bin/sync_garmin_data.sh --days 7
```

## Token Expiration
- Tokens typically last ~1 year
- If sync fails with auth errors, repeat this process to get fresh tokens

## Alternative: Use Python Script
```python
import garth
from pathlib import Path

# After manually logging in via browser:
# 1. Get tokens from browser cookies
# 2. Save them:

garth.save('path/to/tokens')
```
