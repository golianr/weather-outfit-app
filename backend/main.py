from fastapi import FastAPI
import pandas as pd
import requests
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()
api_key = os.getenv("WEATHER_API_KEY")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_weather_stats(city: str = None, lat: float = None, lon: float = None):
    if lat is not None and lon is not None:
        url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
    else:
        city = city or "brno"
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    response = requests.get(url).json()
    
    utc_time = datetime.utcfromtimestamp(response["dt"])
    offset_sec = response["timezone"]
    local_time = utc_time + timedelta(seconds=offset_sec)

    return {
        "temperature": response["main"]["temp"],
        "temp_max": response["main"]["temp_max"],
        "temp_min": response["main"]["temp_min"],
        "feels_like": response["main"]["feels_like"],
        "weather_main": response["weather"][0]["main"],
        "weather_description": response["weather"][0]["description"],
        "weather_code": response["weather"][0]["icon"],
        "humidity": response["main"]["humidity"],
        "hour_local": local_time.hour,
        "datetime_local": local_time.isoformat(),
        "city": response.get("name", city)
    }

@app.get("/weather")
def weather(city: str = None, lat: float = None, lon: float = None):
    return get_weather_stats(city, lat, lon)


# Debug run: allow running the script directly
if __name__ == "__main__":
    print(get_weather_stats("brno"))
