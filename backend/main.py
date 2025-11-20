from fastapi import FastAPI
import requests
from dotenv import load_dotenv
import os
from math import floor
from datetime import datetime, timedelta
from fastapi.middleware.cors import CORSMiddleware

# Load env
load_dotenv()
api_key = os.getenv("WEATHER_API_KEY")

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===============================
#   REAL FEEL CALCULATIONS
# ===============================
def compute_real_feel(temp, feels_like, humidity, wind_speed, hour, mode):
    """
    Výpočet maximálne presnej 'real feel' teploty.
    """

    adjusted = feels_like
    wind_kmh = wind_speed * 3.6  # prepočet

    # --- WIND CHILL (NOAA) ---
    if temp < 10 and wind_kmh > 5:
        wc = (
            13.12
            + 0.6215 * temp
            - 11.37 * (wind_kmh ** 0.16)
            + 0.3965 * temp * (wind_kmh ** 0.16)
        )
        adjusted = wc

    # --- HEAT INDEX (NOAA) ---
    if temp > 27 and humidity > 40:
        T = temp
        RH = humidity
        HI = (
            -8.784
            + 1.611 * T
            + 2.338 * RH
            - 0.146 * T**2
            - 0.0123 * RH**2
            + 0.0164 * T * RH
        )
        adjusted = HI

    # --- Vlhkosť ---
    if humidity > 80 and temp < 15:
        adjusted -= 1

    # --- Ranný / večerný chlad ---
    if 6 <= hour <= 8 or 20 <= hour <= 23:
        adjusted -= 2

    # --- Režimy ---
    mode = mode.lower()
    if mode == "standing":
        adjusted -= 3
    elif mode == "running":
        adjusted += 10

    return round(adjusted, 1)


# ===============================
#   GET WEATHER (OPENWEATHER)
# ===============================
def get_weather_stats(city: str = None, lat: float = None, lon: float = None):
    if lat is not None and lon is not None:
        url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
    else:
        city = city or "brno"
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"

    response = requests.get(url).json()

    # UTC → local time
    utc_time = datetime.utcfromtimestamp(response["dt"])
    offset_sec = response["timezone"]
    local_time = utc_time + timedelta(seconds=offset_sec)

    return {
        "temperature": floor(response["main"]["temp"]),
        "temp_max": response["main"]["temp_max"],
        "temp_min": response["main"]["temp_min"],
        "feels_like": response["main"]["feels_like"],
        "weather_main": response["weather"][0]["main"],
        "weather_description": response["weather"][0]["description"],
        "weather_code": response["weather"][0]["icon"],
        "humidity": response["main"]["humidity"],
        "wind_speed": response["wind"]["speed"],  # m/s
        "pressure": response["main"]["pressure"],
        "hour_local": local_time.hour,
        "datetime_local": local_time.isoformat(),
        "city": response.get("name", city),
        "lat": response["coord"]["lat"],
        "lon": response["coord"]["lon"],
    }


# ===============================
#   WEATHER ROUTE
# ===============================
@app.get("/weather")
def weather(city: str = None, lat: float = None, lon: float = None):
    return get_weather_stats(city, lat, lon)


# ===============================
# OUTIFT RECOMMENDATION
# ===============================
@app.get("/recommend")
def recommend_outfit(
    temp: float,
    feels_like: float,
    wind: float,
    humidity: float,
    weather: str,
    hour: int,
    mode: str = "casual",
):
    # Real feel
    adjusted = compute_real_feel(
        temp=temp,
        feels_like=feels_like,
        humidity=humidity,
        wind_speed=wind,
        hour=hour,
        mode=mode
    )

    # -------------------
    #  TOP CLOTHING
    # -------------------
    layers = []

    if adjusted < -5:
        top = "Hrubá zimná bunda"
        layers += ["Termo vrstva", "Mikina"]
    elif adjusted < 5:
        top = "Zimná bunda"
        layers += ["Termo vrstva"]
    elif adjusted < 12:
        top = "Softshell / jesenná bunda"
        layers += ["Mikina"]
    elif adjusted < 17:
        top = "Mikina alebo ľahká bunda"
    elif adjusted < 22:
        top = "Tričko + prípadná mikina"
    else:
        top = "Tričko"

    # -------------------
    #  BOTTOM
    # -------------------
    if adjusted < 0:
        bottom = "Zateplené nohavice"
    elif adjusted < 15:
        bottom = "Dlhé nohavice"
    elif adjusted < 22:
        bottom = "Ľahké dlhé nohavice"
    else:
        bottom = "Kraťasy"

    # -------------------
    #  ACCESSORIES
    # -------------------
    accessories = []

    if weather.lower() == "rain":
        accessories += ["Dážďnik", "Nepremokavá bunda"]

    if weather.lower() == "snow":
        accessories += ["Rukavice", "Čiapka", "Zimná obuv"]

    if wind > 10:
        accessories.append("Čiapka proti vetru")

    if humidity > 90 and adjusted < 12:
        accessories.append("Nepremokavá obuv")

    return {
        "real_feel": adjusted,
        "top": top,
        "layers": layers,
        "bottom": bottom,
        "accessories": accessories,
        "mode_used": mode,
    }


# Debug direct run
if __name__ == "__main__":
    print(get_weather_stats("brno"))
