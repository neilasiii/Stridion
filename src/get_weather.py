#!/usr/bin/env python3
"""
Fetch current weather using Termux location and Open-Meteo API.

Uses termux-location to get GPS coordinates, then fetches weather data
from Open-Meteo (free, no API key required, very reliable).

Returns concise weather summary suitable for coaching decisions.
"""

import json
import subprocess
import sys
from pathlib import Path

def get_location():
    """Get current location using termux-location."""
    try:
        # Get location from termux-location (requires termux-api package)
        # Network provider can take 10+ seconds, allow 20 seconds
        result = subprocess.run(
            ['termux-location', '-p', 'network'],
            capture_output=True,
            text=True,
            timeout=20
        )

        if result.returncode != 0:
            print(f"Error getting location: {result.stderr}", file=sys.stderr)
            return None

        location_data = json.loads(result.stdout)
        lat = location_data.get('latitude')
        lon = location_data.get('longitude')

        if lat and lon:
            return lat, lon

        return None

    except subprocess.TimeoutExpired:
        print("Location request timed out", file=sys.stderr)
        return None
    except json.JSONDecodeError:
        print("Invalid location data", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error getting location: {e}", file=sys.stderr)
        return None

def fetch_weather(lat, lon):
    """Fetch weather data from Open-Meteo API for given coordinates."""
    try:
        # Use Open-Meteo API (free, no API key needed, very reliable)
        # Get current weather + hourly forecast
        url = (
            f'https://api.open-meteo.com/v1/forecast?'
            f'latitude={lat}&longitude={lon}&'
            f'current=temperature_2m,relative_humidity_2m,apparent_temperature,'
            f'precipitation,weather_code,wind_speed_10m,wind_direction_10m&'
            f'hourly=temperature_2m,weather_code,uv_index&'
            f'temperature_unit=fahrenheit&wind_speed_unit=mph&'
            f'timezone=auto&forecast_days=1'
        )

        result = subprocess.run(
            ['curl', '-s', '--max-time', '20', url],
            capture_output=True,
            text=True,
            timeout=25
        )

        if result.returncode != 0:
            print(f"Error fetching weather: {result.stderr}", file=sys.stderr)
            return None

        weather_data = json.loads(result.stdout)
        return weather_data

    except subprocess.TimeoutExpired:
        print("Weather request timed out", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"Invalid weather data: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error fetching weather: {e}", file=sys.stderr)
        return None

# WMO Weather interpretation codes
WMO_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail"
}

def format_weather_summary(weather_data):
    """Format weather data into concise summary for coaching."""
    try:
        current = weather_data['current']
        hourly = weather_data['hourly']

        # Extract current conditions
        temp_f = round(current['temperature_2m'])
        feels_like_f = round(current['apparent_temperature'])
        humidity = current['relative_humidity_2m']
        wind_mph = round(current['wind_speed_10m'])
        weather_code = current['weather_code']
        description = WMO_CODES.get(weather_code, "Unknown")

        # Get current hour index
        from datetime import datetime
        current_time = datetime.fromisoformat(current['time'])
        current_hour = current_time.hour

        # Find current hour index in hourly data
        try:
            hour_times = [datetime.fromisoformat(t) for t in hourly['time']]
            current_idx = next(i for i, t in enumerate(hour_times) if t.hour == current_hour)
        except (StopIteration, KeyError):
            current_idx = 0

        # Get UV index for current hour
        uv_index = hourly['uv_index'][current_idx] if current_idx < len(hourly['uv_index']) else 0

        # Build summary
        summary = f"""Current: {temp_f}°F (feels {feels_like_f}°F), {description}
Humidity: {humidity}%, Wind: {wind_mph} mph, UV: {round(uv_index, 1)}

Next 6 hours:"""

        # Show next 3-6 hours
        for i in range(current_idx + 1, min(current_idx + 7, len(hourly['time']))):
            hour_time = datetime.fromisoformat(hourly['time'][i])
            hour_temp = round(hourly['temperature_2m'][i])
            hour_code = hourly['weather_code'][i]
            hour_desc = WMO_CODES.get(hour_code, "Unknown")
            summary += f"\n  {hour_time.strftime('%I%p').lstrip('0')}: {hour_temp}°F, {hour_desc}"

        return summary

    except (KeyError, IndexError) as e:
        print(f"Error parsing weather data: {e}", file=sys.stderr)
        return None

def get_location_from_ip():
    """Get location automatically using IP-based geolocation (free service)."""
    try:
        # Use ipapi.co - free tier allows 1000 requests/day, no API key needed
        result = subprocess.run(
            ['curl', '-s', '--max-time', '10', 'https://ipapi.co/json/'],
            capture_output=True,
            text=True,
            timeout=15
        )

        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)

        # Check for error response
        if 'error' in data:
            print(f"IP geolocation error: {data.get('reason', 'Unknown')}", file=sys.stderr)
            return None

        lat = data.get('latitude')
        lon = data.get('longitude')
        city = data.get('city')
        region = data.get('region')

        if lat and lon:
            print(f"Detected location: {city}, {region} ({lat}, {lon})", file=sys.stderr)
            return float(lat), float(lon)

        return None

    except subprocess.TimeoutExpired:
        print("IP geolocation timed out", file=sys.stderr)
        return None
    except json.JSONDecodeError:
        print("Invalid geolocation response", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error getting location from IP: {e}", file=sys.stderr)
        return None

def get_configured_location():
    """Get location from environment or config file."""
    import os

    # Try environment variables first
    lat = os.environ.get('WEATHER_LATITUDE')
    lon = os.environ.get('WEATHER_LONGITUDE')

    if lat and lon:
        try:
            return float(lat), float(lon)
        except ValueError:
            pass

    # Try user-specific location (set via /location command) - highest priority
    project_root = Path(__file__).parent.parent
    user_config = project_root / 'config' / 'user_location.env'

    if user_config.exists():
        try:
            with open(user_config) as f:
                lat = None
                lon = None
                location_name = None
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if line.startswith('WEATHER_LATITUDE='):
                            lat = line.split('=', 1)[1].strip()
                        elif line.startswith('WEATHER_LONGITUDE='):
                            lon = line.split('=', 1)[1].strip()
                        elif line.startswith('LOCATION_NAME='):
                            location_name = line.split('=', 1)[1].strip()

            if lat and lon:
                if location_name:
                    print(f"Using location: {location_name}", file=sys.stderr)
                return float(lat), float(lon)
        except:
            pass

    # Try default config file
    config_file = project_root / 'config' / 'location.env'

    if config_file.exists():
        try:
            with open(config_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if line.startswith('WEATHER_LATITUDE='):
                            lat = line.split('=', 1)[1].strip()
                        elif line.startswith('WEATHER_LONGITUDE='):
                            lon = line.split('=', 1)[1].strip()

            if lat and lon:
                return float(lat), float(lon)
        except:
            pass

    return None

def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Get weather forecast')
    parser.add_argument('--lat', type=float, help='Latitude')
    parser.add_argument('--lon', type=float, help='Longitude')
    parser.add_argument('--use-termux', action='store_true', help='Use termux-location (Android only)')
    parser.add_argument('--no-auto', action='store_true', help='Disable automatic IP-based location')
    args = parser.parse_args()

    # Determine location source (priority order)
    location = None

    if args.lat and args.lon:
        # 1. Command-line arguments (highest priority)
        location = (args.lat, args.lon)
    elif args.use_termux:
        # 2. Termux-location (Android/Termux only)
        location = get_location()
        if not location:
            print("Unable to get location. Make sure termux-api is installed:", file=sys.stderr)
            print("  pkg install termux-api", file=sys.stderr)
            sys.exit(1)
    else:
        # 3. Try configured location
        location = get_configured_location()

        # 4. Fall back to automatic IP-based geolocation
        if not location and not args.no_auto:
            print("No manual location configured, using automatic IP-based detection...", file=sys.stderr)
            location = get_location_from_ip()

        if not location:
            print("Unable to determine location. Options:", file=sys.stderr)
            print("  1. Let it auto-detect (default - uses IP geolocation)", file=sys.stderr)
            print("  2. Set environment: WEATHER_LATITUDE and WEATHER_LONGITUDE", file=sys.stderr)
            print("  3. Create config/location.env with coordinates", file=sys.stderr)
            print("  4. Pass --lat and --lon arguments", file=sys.stderr)
            print("  5. Use --use-termux on Android", file=sys.stderr)
            sys.exit(1)

    lat, lon = location

    # Fetch weather
    weather_data = fetch_weather(lat, lon)
    if not weather_data:
        print("Unable to fetch weather data", file=sys.stderr)
        sys.exit(1)

    # Format summary
    summary = format_weather_summary(weather_data)
    if not summary:
        print("Unable to format weather data", file=sys.stderr)
        sys.exit(1)

    # Output summary
    print(summary)
    return 0

if __name__ == '__main__':
    sys.exit(main())
