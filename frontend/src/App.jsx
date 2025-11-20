import { useState } from "react";
import "./App.css";
import { getUserLocation, fetchWeather } from "./geolocation";

function App() {
  const [weather, setWeather] = useState(null);
  const [recommendation, setRecommendation] = useState(null);
  const [loading, setLoading] = useState(false);

  const [mode, setMode] = useState("casual");

  const handleGetWeather = async () => {
    setLoading(true);
    try {
      const { lat, lon } = await getUserLocation();
      const data = await fetchWeather(lat, lon);
      setWeather(data);

      const rec = await fetch(
        `http://localhost:8000/recommend?temp=${data.temperature}&feels_like=${data.feels_like}&wind=${data.wind_speed}&humidity=${data.humidity}&weather=${data.weather_main}&hour=${data.hour_local}&mode=${mode}`
      );
      const recJson = await rec.json();
      setRecommendation(recJson);
    } catch (err) {
      console.log("Error:", err);
    }
    setLoading(false);
  };

  return (
    <div className="container">
      <h1 className="title">Outfit Odporúčanie</h1>

      <div className="card">
        <label className="label">Režim:</label>
        <select
          value={mode}
          onChange={(e) => setMode(e.target.value)}
          className="select"
        >
          <option value="casual">Casual</option>
          <option value="standing">Dlhšie státie vonku</option>
          <option value="running">Beh / šport</option>
        </select>

        <button onClick={handleGetWeather} className="button">
          {loading ? "Načítavam..." : "Zobraziť odporúčanie"}
        </button>
      </div>

      {weather && (
        <div className="card weather-card">
          <h2>Počasie – {weather.city}</h2>
          <p><b>Teplota:</b> {weather.temperature}°C</p>
          <p><b>Pocitovo:</b> {weather.feels_like}°C</p>
          <p><b>Vietor:</b> {(weather.wind_speed * 3.6).toFixed(1)} km/h</p>
          <p><b>Vlhkosť:</b> {weather.humidity}%</p>
          <p><b>Podmienky:</b> {weather.weather_main}</p>
        </div>
      )}

      {recommendation && (
        <div className="card rec-card">
          <h2>Doporučené oblečenie</h2>

          <p><b>Real feel:</b> {recommendation.real_feel}°C</p>
          <p><b>Vrch:</b> {recommendation.top}</p>
          <p><b>Spodok:</b> {recommendation.bottom}</p>

          {recommendation.layers.length > 0 && (
            <>
              <b>Extra vrstvy:</b>
              <ul>
                {recommendation.layers.map((layer, i) => (
                  <li key={i}>{layer}</li>
                ))}
              </ul>
            </>
          )}

          {recommendation.accessories.length > 0 && (
            <>
              <b>Doplnky:</b>
              <ul>
                {recommendation.accessories.map((acc, i) => (
                  <li key={i}>{acc}</li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default App;
