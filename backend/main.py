from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from dotenv import load_dotenv
import os
from math import floor
from datetime import datetime, timedelta
from time import time

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
#   CACHE (10 minút)
# ===============================
_cache: dict = {}
CACHE_TTL = 600  # sekundy


def cache_get(key: str):
    entry = _cache.get(key)
    if entry and time() - entry["ts"] < CACHE_TTL:
        return entry["data"]
    return None


def cache_set(key: str, data: dict):
    _cache[key] = {"data": data, "ts": time()}


# ===============================
#   REAL FEEL CALCULATIONS
# ===============================
def compute_real_feel(
    temp: float,
    feels_like: float,
    humidity: float,
    wind_speed: float,
    hour: int,
    mode: str,
    uv_index: float = 0,
    cloud_cover: float = 50,
) -> float:
    """
    Vrstvený výpočet 'real feel' teploty.
    Základ z OpenWeather feels_like, korigovaný fyzikálnymi modelmi.
    """
    adjusted = feels_like
    wind_kmh = wind_speed * 3.6

    # --- WIND CHILL (NOAA) — priorita pri chlade ---
    if temp < 10 and wind_kmh > 5:
        adjusted = (
            13.12
            + 0.6215 * temp
            - 11.37 * (wind_kmh ** 0.16)
            + 0.3965 * temp * (wind_kmh ** 0.16)
        )

    # --- HEAT INDEX (NOAA) — priorita pri teple ---
    elif temp > 27 and humidity > 40:
        T, RH = temp, humidity
        adjusted = (
            -8.784
            + 1.611 * T
            + 2.338 * RH
            - 0.146 * T ** 2
            - 0.0123 * RH ** 2
            + 0.0164 * T * RH
        )

    # --- UV / priame slnko ---
    if uv_index > 5 and cloud_cover < 30:
        adjusted += 2.5
    elif uv_index > 3 and cloud_cover < 50:
        adjusted += 1.0

    # --- Vysoká vlhkosť pri chlade (chlad na koži) ---
    if humidity > 85 and temp < 15:
        adjusted -= 1.5
    elif humidity > 80 and temp < 15:
        adjusted -= 0.8

    # --- Nočný / ranný chlad ---
    if 0 <= hour <= 5:
        adjusted -= 2.5
    elif 20 <= hour <= 23:
        adjusted -= 1.5
    elif 6 <= hour <= 8:
        adjusted -= 1.0

    # --- Úprava podľa aktivity ---
    mode_adjustments = {
        "standing": -4,
        "casual":    0,
        "cycling":  -2,
        "running":  +10,
    }
    adjusted += mode_adjustments.get(mode.lower(), 0)

    return round(adjusted, 1)


# ===============================
#   OBUV
# ===============================
def get_footwear(adjusted: float, weather: str) -> str:
    w = weather.lower()
    if w in ["snow", "sleet"]:
        return "Zimné topánky / snehule"
    if w == "rain":
        return "Nepremokavá obuv"
    if adjusted < 0:
        return "Zateplená nepremokavá obuv"
    if adjusted < 8:
        return "Zateplená obuv"
    if adjusted < 15:
        return "Uzavretá obuv / tenisky"
    if adjusted < 25:
        return "Ľahké tenisky"
    return "Sandále / ľahká obuv"


# ===============================
#   KONTEXTOVÉ TIPY
# ===============================
def generate_tips(
    adjusted: float,
    weather: str,
    hour: int,
    humidity: float,
    wind_kmh: float,
    rain_probability: float = 0,
    alerts: list = None,
) -> list[str]:
    tips = []
    w = weather.lower()
    alerts = alerts or []

    # Výstrahy z API
    for alert in alerts:
        tips.append(f"⚠️ Výstraha: {alert.get('event', 'Neznáma výstraha')}")

    if w == "rain" and hour < 9:
        tips.append("🌧️ Ráno prší — počítaj s predĺženou cestou.")

    if rain_probability > 60:
        tips.append(f"☔ {int(rain_probability)}% šanca dažďa — vezmi dáždnik.")
    elif rain_probability > 35:
        tips.append(f"🌦️ {int(rain_probability)}% šanca dažďa — možno sa zíde dáždnik.")

    if adjusted < -15:
        tips.append("🥶 Extrémny mráz — zakryj tvár šálom, obmedz pobyt vonku.")
    elif adjusted < -5:
        tips.append("🧣 Veľmi chladné počasie — nezabudni na šál a rukavice.")

    if wind_kmh > 50:
        tips.append("💨 Silný vietor — vyhni sa dáždniku, radšej pršiplášť.")
    elif wind_kmh > 30:
        tips.append("🌬️ Vietor — pevne drž čiapku a ľahké veci.")

    if humidity > 90 and adjusted > 25:
        tips.append("🌫️ Dusno a vlhko — hrozí rýchle prehriatia, pi viac vody.")

    if 6 <= hour <= 9 and adjusted < 10:
        tips.append("🌅 Ráno je chladnejšie ako cez deň — vezmi vrstvu navyše.")

    if w == "thunderstorm":
        tips.append("⛈️ Búrka — vyhni sa otvoreným priestorom a stromom.")

    if w in ["fog", "mist"] and hour < 10:
        tips.append("🌫️ Hmla — buď opatrný v premávke, slabá viditeľnosť.")

    return tips


# ===============================
#   GET WEATHER (BASIC)
# ===============================
def get_weather_stats(city: str = None, lat: float = None, lon: float = None) -> dict:
    cache_key = f"basic_{city or f'{lat},{lon}'}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    if lat is not None and lon is not None:
        url = (
            f"http://api.openweathermap.org/data/2.5/weather"
            f"?lat={lat}&lon={lon}&appid={api_key}&units=metric"
        )
    else:
        city = city or "brno"
        url = (
            f"http://api.openweathermap.org/data/2.5/weather"
            f"?q={city}&appid={api_key}&units=metric"
        )

    response = requests.get(url)
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Chyba pri získavaní počasia.")
    data = response.json()

    utc_time = datetime.utcfromtimestamp(data["dt"])
    offset_sec = data["timezone"]
    local_time = utc_time + timedelta(seconds=offset_sec)

    result = {
        "temperature": floor(data["main"]["temp"]),
        "temp_max": data["main"]["temp_max"],
        "temp_min": data["main"]["temp_min"],
        "feels_like": data["main"]["feels_like"],
        "weather_main": data["weather"][0]["main"],
        "weather_description": data["weather"][0]["description"],
        "weather_code": data["weather"][0]["icon"],
        "humidity": data["main"]["humidity"],
        "wind_speed": data["wind"]["speed"],
        "pressure": data["main"]["pressure"],
        "hour_local": local_time.hour,
        "datetime_local": local_time.isoformat(),
        "city": data.get("name", city),
        "lat": data["coord"]["lat"],
        "lon": data["coord"]["lon"],
        # Defaulty — doplní sa cez OneCall ak je dostupný
        "uv_index": 0,
        "cloud_cover": data.get("clouds", {}).get("all", 50),
        "rain_probability": 0,
        "alerts": [],
    }

    cache_set(cache_key, result)
    return result


# ===============================
#   GET WEATHER (ONECALL — rozšírený)
# ===============================
def get_weather_extended(lat: float, lon: float) -> dict:
    """
    Používa OneCall API 3.0 pre UV index, oblačnosť,
    pravdepodobnosť dažďa a výstrahy.
    Fallback na basic weather ak OneCall zlyhá.
    """
    cache_key = f"extended_{lat},{lon}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    basic = get_weather_stats(lat=lat, lon=lon)

    try:
        url = (
            f"https://api.openweathermap.org/data/3.0/onecall"
            f"?lat={lat}&lon={lon}&appid={api_key}&units=metric"
            f"&exclude=minutely,daily"
        )
        resp = requests.get(url)
        if resp.status_code != 200:
            return basic  # graceful fallback

        oc = resp.json()
        current = oc.get("current", {})
        hourly_0 = oc.get("hourly", [{}])[0]

        basic["uv_index"] = current.get("uvi", 0)
        basic["cloud_cover"] = current.get("clouds", basic["cloud_cover"])
        basic["rain_probability"] = hourly_0.get("pop", 0) * 100
        basic["alerts"] = [
            {"event": a.get("event", ""), "description": a.get("description", "")}
            for a in oc.get("alerts", [])
        ]

    except Exception:
        pass  # vráti basic bez pádu

    cache_set(cache_key, basic)
    return basic


# ===============================
#   OUTFIT LOGIKA
# ===============================
def build_outfit(adjusted: float, weather: str, wind_kmh: float, humidity: float) -> dict:
    w = weather.lower()

    # --- Base layer ---
    base_layer = None
    if adjusted < 0:
        base_layer = "Termo tričko + termo spodky"
    elif adjusted < 8:
        base_layer = "Termo tričko"

    # --- Mid layer ---
    if adjusted < -5:
        mid_layer = "Hrubá fleece mikina"
    elif adjusted < 5:
        mid_layer = "Mikina / fleece"
    elif adjusted < 14:
        mid_layer = "Tenká mikina / svetrík"
    elif adjusted < 19:
        mid_layer = "Ľahká mikina alebo dlhé tričko"
    else:
        mid_layer = None

    # --- Outer layer ---
    if adjusted < -5:
        outer_layer = "Hrubá zimná bunda (páperová / syntetická)"
    elif adjusted < 2:
        outer_layer = "Zimná bunda"
    elif adjusted < 10:
        outer_layer = "Softshell / jesenná bunda"
    elif adjusted < 15:
        outer_layer = "Ľahká vetrovka"
    elif w == "rain":
        outer_layer = "Nepremokavá bunda / pršiplášť"
    else:
        outer_layer = None

    # --- Bottom ---
    if adjusted < -5:
        bottom = "Zateplené nohavice (s termo vrstvou)"
    elif adjusted < 5:
        bottom = "Zateplené nohavice"
    elif adjusted < 15:
        bottom = "Dlhé nohavice (džínsy / cargo)"
    elif adjusted < 21:
        bottom = "Ľahké dlhé nohavice"
    else:
        bottom = "Kraťasy"

    # --- Accessories ---
    accessories = []

    if adjusted < -5:
        accessories += ["Čiapka", "Šál", "Teplé rukavice"]
    elif adjusted < 5:
        accessories += ["Čiapka", "Rukavice"]
    elif adjusted < 10:
        accessories.append("Čiapka")

    if wind_kmh > 25:
        accessories.append("Čiapka / kukla proti vetru")

    if w == "rain":
        accessories.append("Dáždnik")
    if w == "snow":
        accessories += ["Rukavice", "Zimná čiapka", "Šál"] if "Rukavice" not in accessories else []
    if w == "sunny" and adjusted > 20:
        accessories += ["Slnečné okuliare", "Čiapka so šiltom"]

    if humidity > 90:
        accessories.append("Nepremokavá obuv")

    return {
        "base_layer": base_layer,
        "mid_layer": mid_layer,
        "outer_layer": outer_layer,
        "bottom": bottom,
        "footwear": get_footwear(adjusted, weather),
        "accessories": list(set(accessories)),  # dedup
    }


# ===============================
#   PYDANTIC MODEL pre /recommend
# ===============================
class RecommendRequest(BaseModel):
    temp: float
    feels_like: float
    wind: float          # m/s
    humidity: float
    weather: str
    hour: int
    mode: str = "casual"
    uv_index: float = 0
    cloud_cover: float = 50
    rain_probability: float = 0
    alerts: list = []


# ===============================
#   ROUTES
# ===============================
@app.get("/weather")
def weather(city: str = None, lat: float = None, lon: float = None):
    """Základné počasie. Ak sú zadané koordináty, pokúsi sa o OneCall."""
    if lat is not None and lon is not None:
        return get_weather_extended(lat, lon)
    return get_weather_stats(city=city)


@app.post("/recommend")
def recommend_outfit(req: RecommendRequest):
    """
    Vráti outfit odporúčanie vrátane real feel, vrstiev, obuvi a tipov.
    """
    wind_kmh = req.wind * 3.6

    real_feel = compute_real_feel(
        temp=req.temp,
        feels_like=req.feels_like,
        humidity=req.humidity,
        wind_speed=req.wind,
        hour=req.hour,
        mode=req.mode,
        uv_index=req.uv_index,
        cloud_cover=req.cloud_cover,
    )

    outfit = build_outfit(
        adjusted=real_feel,
        weather=req.weather,
        wind_kmh=wind_kmh,
        humidity=req.humidity,
    )

    tips = generate_tips(
        adjusted=real_feel,
        weather=req.weather,
        hour=req.hour,
        humidity=req.humidity,
        wind_kmh=wind_kmh,
        rain_probability=req.rain_probability,
        alerts=req.alerts,
    )

    # Spoľahlivosť odporúčania
    confidence = "high" if abs(req.temp - real_feel) < 6 else "medium" if abs(req.temp - real_feel) < 12 else "low"

    return {
        "real_feel": real_feel,
        "outfit": outfit,
        "tips": tips,
        "mode_used": req.mode,
        "confidence": confidence,
    }


# ===============================
#   KOMBINOVANÝ ENDPOINT (weather + recommend naraz)
# ===============================
@app.get("/full")
def full_recommendation(
    city: str = None,
    lat: float = None,
    lon: float = None,
    mode: str = "casual",
):
    """
    Jeden endpoint — vráti počasie aj outfit odporúčanie naraz.
    Ideálne pre frontend (jeden API call).
    """
    if lat is not None and lon is not None:
        w = get_weather_extended(lat, lon)
    else:
        w = get_weather_stats(city=city)

    req = RecommendRequest(
        temp=w["temperature"],
        feels_like=w["feels_like"],
        wind=w["wind_speed"],
        humidity=w["humidity"],
        weather=w["weather_main"],
        hour=w["hour_local"],
        mode=mode,
        uv_index=w.get("uv_index", 0),
        cloud_cover=w.get("cloud_cover", 50),
        rain_probability=w.get("rain_probability", 0),
        alerts=w.get("alerts", []),
    )

    recommendation = recommend_outfit(req)

    return {
        "weather": w,
        **recommendation,
    }


# Debug
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)