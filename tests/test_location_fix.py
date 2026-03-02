#!/usr/bin/env python3
"""Test the improved location geocoding logic."""

import subprocess
import json
import re
import urllib.parse

def test_location_query(location):
    """Test geocoding with fallback logic."""
    print(f"\n{'='*60}")
    print(f"Testing: '{location}'")
    print('='*60)

    queries_to_try = [location]

    # If location contains state abbreviation or full state name, also try without it
    state_pattern = r'^(.+?)[\s,]+(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|New Hampshire|New Jersey|New Mexico|New York|North Carolina|North Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode Island|South Carolina|South Dakota|Tennessee|Texas|Utah|Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming)[\s,]*$'
    match = re.match(state_pattern, location, re.IGNORECASE)
    if match:
        city_only = match.group(1).strip()
        if city_only not in queries_to_try:
            queries_to_try.append(city_only)
            print(f"  → Will also try: '{city_only}' (without state)")

    geo_data = None
    for i, query in enumerate(queries_to_try, 1):
        print(f"\n  Attempt {i}/{len(queries_to_try)}: '{query}'")
        encoded_city = urllib.parse.quote(query)
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={encoded_city}&count=1&language=en&format=json"

        result = subprocess.run(
            ["curl", "-s", url],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            geo_data = json.loads(result.stdout)
            if geo_data.get('results'):
                print(f"  ✓ SUCCESS!")
                break
            else:
                print(f"  ✗ No results")

    if geo_data and geo_data.get('results'):
        r = geo_data['results'][0]
        print(f"\n✓ FINAL RESULT:")
        print(f"  Location: {r['name']}, {r.get('admin1', '')}")
        print(f"  Coordinates: {r['latitude']}, {r['longitude']}")
    else:
        print(f"\n✗ FAILED: No location found")

# Test cases
test_cases = [
    "Altamonte Springs, FL",
    "Altamonte Springs Florida",
    "Orlando, FL",
    "Miami FL",
    "New York, New York",
    "YourCity, YourState",
]

print("="*60)
print("LOCATION GEOCODING FIX TEST")
print("="*60)

for test in test_cases:
    test_location_query(test)

print("\n" + "="*60)
print("Test complete!")
print("="*60)
