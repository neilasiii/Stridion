# Garmin Connect Token Extraction - Mobile Guide

## Overview

This guide shows how to extract Garmin Connect OAuth tokens using mobile devices (iOS/Android). This is useful if you don't have easy access to a desktop/laptop computer.

## Method 1: Mobile Browser (Easiest)

### iOS (Safari/Chrome)

1. **Open Safari or Chrome** on your iPhone/iPad

2. **Navigate to Garmin Connect:**
   ```
   https://connect.garmin.com/
   ```

3. **Log in** with your Garmin credentials

4. **Enable Web Inspector (Safari):**
   - On your Mac: Safari → Settings → Advanced → Show Develop menu
   - Connect iPhone to Mac via cable
   - On Mac: Develop → [Your iPhone] → connect.garmin.com
   - Go to Storage tab to view tokens

5. **Alternative - Chrome DevTools:**
   - Chrome on iOS doesn't support full DevTools
   - Use desktop Chrome with remote debugging instead
   - Chrome → More Tools → Remote devices

### Android (Chrome)

1. **Open Chrome** on your Android device

2. **Navigate to Garmin Connect:**
   ```
   https://connect.garmin.com/
   ```

3. **Log in** with your Garmin credentials

4. **Enable Desktop Site:**
   - Tap menu (⋮) → "Desktop site" checkbox

5. **Open DevTools via USB Debugging:**
   - Enable Developer Options on Android
   - Enable USB Debugging
   - Connect to computer via USB
   - On computer: chrome://inspect
   - Select your device and inspect the Garmin Connect tab

6. **Alternative - View Page Source:**
   - Some tokens might be visible in cookies
   - chrome://inspect/#devices

## Method 2: Python on Mobile (Advanced)

### Android - Termux

**Install Termux:**
```bash
# Install from F-Droid (recommended) or Google Play
```

**Set up Python environment:**
```bash
pkg update
pkg install python
pip install garminconnect
```

**Run token generator:**
```bash
# Download the script
curl -O https://raw.githubusercontent.com/neilasiii/running-coach/main/bin/generate_garmin_tokens.py

# Run it
python generate_garmin_tokens.py
```

**Tokens saved to:** `~/garmin_tokens/`

**Transfer to server:**
```bash
# Install SSH client
pkg install openssh

# Transfer tokens
scp -r ~/garmin_tokens/* user@server:~/.garminconnect/
```

### iOS - Pythonista

**Install Pythonista** (paid app from App Store)

**Install garminconnect:**
```python
import pip
pip.main(['install', 'garminconnect'])
```

**Create and run script:**
```python
from garminconnect import Garmin
import os

email = input("Garmin email: ")
password = input("Garmin password: ")

client = Garmin(email, password)
client.login()

# Save to iCloud Drive or local storage
output_dir = os.path.expanduser('~/Documents/garmin_tokens')
os.makedirs(output_dir, exist_ok=True)
client.garth.dump(output_dir)

print(f"Tokens saved to {output_dir}")
```

**Transfer tokens:**
- Upload to iCloud Drive
- Download on computer
- Transfer to server

## Method 3: Extract from Garmin Connect App (Advanced)

### Android (Requires Root or ADB)

**Option A - ADB Backup (No Root):**

1. **Enable USB Debugging** on Android

2. **Connect to computer** via USB

3. **Create app backup:**
   ```bash
   # On computer
   adb backup -f garmin.ab com.garmin.android.apps.connectmobile
   ```

4. **Extract backup:**
   ```bash
   # Convert to tar
   dd if=garmin.ab bs=24 skip=1 | openssl zlib -d > garmin.tar

   # Extract
   tar -xvf garmin.tar
   ```

5. **Find tokens:**
   - Look in app data directory
   - Tokens stored in: `apps/com.garmin.android.apps.connectmobile/sp/`
   - May be in SharedPreferences XML files

**Option B - Root Access:**

1. **Root your device** (device-specific)

2. **Use root file explorer:**
   ```bash
   # Via ADB with root
   adb shell
   su
   cd /data/data/com.garmin.android.apps.connectmobile
   find . -name "*token*" -o -name "*oauth*"
   ```

3. **Copy token files:**
   ```bash
   adb pull /data/data/com.garmin.android.apps.connectmobile/files/oauth
   ```

### iOS (Requires Jailbreak)

**Jailbroken iOS:**

1. **Install file manager** (Filza, iFile)

2. **Navigate to app directory:**
   ```
   /var/mobile/Containers/Data/Application/[Garmin-UUID]/
   ```

3. **Find token files:**
   - Library/Preferences/
   - Library/Caches/
   - Documents/

4. **Export via SSH or file sharing**

## Method 4: Mobile Browser Cookie Export (Simplest)

### Using Cookie Export Extensions

**Android Chrome:**

1. **Install Kiwi Browser** (supports Chrome extensions)

2. **Install Cookie Editor extension**

3. **Log into Garmin Connect**

4. **Open Cookie Editor:**
   - View all cookies for connect.garmin.com
   - Look for oauth tokens in cookies

5. **Export cookies:**
   - Copy cookie values
   - Save to text file
   - Transfer to computer

**iOS Safari:**

Safari on iOS doesn't support extensions for cookie viewing. Use the remote debugging method instead.

## Method 5: Request Desktop Page

Some mobile browsers can request desktop versions of pages, which might make token extraction easier:

1. **Open mobile browser** (Chrome/Safari)

2. **Navigate to:**
   ```
   https://connect.garmin.com/
   ```

3. **Request Desktop Site:**
   - Chrome: Menu → "Desktop site"
   - Safari: Tap 'AA' in address bar → "Request Desktop Website"

4. **Log in** if needed

5. **View page source** or inspect elements (if available)

## Recommended Approach

**For most users, the easiest mobile method is:**

1. **Use Termux on Android** (Method 2)
   - Fully functional Python environment
   - Can run the token generator script directly
   - Easy to transfer tokens via SCP

2. **Use mobile browser + desktop remote debugging** (Method 1)
   - Works on both iOS and Android
   - Requires connecting to a computer
   - Most reliable token extraction

3. **Manual cookie viewing** (Method 4)
   - Simplest if you just need to view tokens
   - Works on rooted/jailbroken devices

## After Token Extraction

Once you have tokens on your mobile device:

**Transfer options:**
1. **Email to yourself** (secure email only!)
2. **Cloud storage** (Dropbox, Google Drive, iCloud)
3. **Direct transfer via SSH/SCP**
4. **USB cable + file transfer**

**On server:**
```bash
# Create directory
mkdir -p ~/.garminconnect

# Copy token files
# (transfer oauth1_token.json and oauth2_token.json)

# Test
python3 src/garmin_token_auth.py --test
```

## Security Notes

- **Don't share tokens** - treat them like passwords
- **Use secure transfer** - encrypted email, HTTPS, SSH
- **Delete from mobile** after transferring
- **Set file permissions** on server: `chmod 600 ~/.garminconnect/*`

## Troubleshooting

**Tokens not visible in browser:**
- Some tokens may be httpOnly (not accessible via JavaScript)
- Use remote debugging to access DevTools properly
- Try multiple browsers

**App data extraction fails:**
- ADB backup may be disabled by manufacturer
- Some apps prevent backup
- Root/jailbreak may be only option

**Termux garminconnect install fails:**
- Update packages: `pkg update && pkg upgrade`
- Install build tools: `pkg install clang python-dev`
- Try older version: `pip install garminconnect==0.2.33`

## Related Documentation

- [Token Auth Guide](GARMIN_TOKEN_AUTH.md) - Desktop/server setup
- [Health Data System](HEALTH_DATA_SYSTEM.md) - Overall system architecture
