import requests
from datetime import datetime


# ============================================================
# TEST FLIGHT
# ============================================================

LATITUDE = 52.52
LONGITUDE = 13.41

FLIGHT_DATE = "2015-01-01"
FLIGHT_TIME = "00:05"


# ============================================================
# GET WEATHER FOR THE FLIGHT DATE
# ============================================================

url = "https://archive-api.open-meteo.com/v1/archive"

params = {
    "latitude": LATITUDE,
    "longitude": LONGITUDE,
    "start_date": FLIGHT_DATE,
    "end_date": FLIGHT_DATE,

    "hourly": ",".join([
        "temperature_2m",
        "precipitation",
        "rain",
        "snowfall",
        "cloud_cover",
        "wind_speed_10m",
        "visibility"
    ]),

    "timezone": "auto"
}


print("=" * 70)
print("FLITZZ - HISTORICAL WEATHER TEST")
print("=" * 70)

print(f"Date      : {FLIGHT_DATE}")
print(f"Time      : {FLIGHT_TIME}")
print(f"Latitude  : {LATITUDE}")
print(f"Longitude : {LONGITUDE}")

print("\n[INFO] Requesting Open-Meteo...")


# ============================================================
# API REQUEST
# ============================================================

try:

    response = requests.get(
        url,
        params=params,
        timeout=30
    )

    print(
        f"[INFO] HTTP status: {response.status_code}"
    )

    response.raise_for_status()

    data = response.json()

except Exception as e:

    print("\n[ERROR] Open-Meteo request failed")
    print(e)
    raise SystemExit(1)


# ============================================================
# API RESPONSE
# ============================================================

print("\n[OK] Open-Meteo response received")

print(
    f"Latitude returned : {data.get('latitude')}"
)

print(
    f"Longitude returned: {data.get('longitude')}"
)

print(
    f"Timezone returned : {data.get('timezone')}"
)


# ============================================================
# CONVERT HOURLY DATA
# ============================================================

hourly = data.get("hourly")

if not hourly:

    print("\n[ERROR] No hourly weather data returned.")
    raise SystemExit(1)


times = hourly["time"]

print(
    f"\n[OK] Weather records returned: {len(times)}"
)


# ============================================================
# FIND FLIGHT HOUR
# ============================================================

flight_hour = int(
    FLIGHT_TIME.split(":")[0]
)

target_time = (
    f"{FLIGHT_DATE}T"
    f"{flight_hour:02d}:00"
)


print(
    f"[INFO] Looking for weather hour: "
    f"{target_time}"
)


try:

    index = times.index(target_time)

except ValueError:

    print(
        "\n[ERROR] Flight hour was not found."
    )

    print("\nAvailable times:")

    for t in times[:10]:
        print(" ", t)

    raise SystemExit(1)


# ============================================================
# EXTRACT WEATHER
# ============================================================

weather = {

    "timestamp": times[index],

    "temperature_2m":
        hourly["temperature_2m"][index],

    "precipitation":
        hourly["precipitation"][index],

    "rain":
        hourly["rain"][index],

    "snowfall":
        hourly["snowfall"][index],

    "cloud_cover":
        hourly["cloud_cover"][index],

    "wind_speed_10m":
        hourly["wind_speed_10m"][index],

    "visibility":
        hourly["visibility"][index],
}


# ============================================================
# DISPLAY
# ============================================================

print("\n" + "=" * 70)
print("HISTORICAL WEATHER")
print("=" * 70)

for key, value in weather.items():

    print(
        f"{key:<20}: {value}"
    )


print("\n" + "=" * 70)
print("WEATHER TEST SUCCESSFUL")
print("=" * 70)