from fastapi import FastAPI
import pandas as pd
import requests
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta

load_dotenv()
api_key = os.getenv("WEATHER_API_KEY")

app = FastAPI()

def get_weather_stats(city: str = "brno"):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    response = requests.get(url).json()

    # UTC timestamp from API
    utc_time = datetime.utcfromtimestamp(response["dt"])

    # timezone offset in seconds (example: +3600 for CET)
    offset_sec = response["timezone"]

    # Calculate local time of the city
    local_time = utc_time + timedelta(seconds=offset_sec)

    # Structured ML-friendly data
    values = {
        "temperature": response["main"]["temp"],
        "temp_max": response["main"]["temp_max"],
        "temp_min": response["main"]["temp_min"],
        "feels_like": response["main"]["feels_like"],
        "weather_main": response["weather"][0]["main"],         # Rain / Clouds / Clear
        "weather_description": response["weather"][0]["description"],
        "weather_code": response["weather"][0]["icon"],         # icon ID (rain, snow...)
        "humidity": response["main"]["humidity"],
        "hour_local": local_time.hour,
        "datetime_local": local_time.isoformat(),
        "city": city
    }

    return values


# FastAPI route so browser or frontend can call it
@app.get("/weather")
def weather(city: str = "brno"):
    return get_weather_stats(city)


# Debug run: allow running the script directly
if __name__ == "__main__":
    print(get_weather_stats("brno"))
