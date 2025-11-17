import { useState } from "react";
import "./App.css";
import { getUserLocation, fetchWeather } from "./geolocation";

function App() {
  const [weather, setWeather] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleGetWeather = async () => {
    setLoading(true);
    try {
      const { lat, lon } = await getUserLocation();
      const data = await fetchWeather(lat, lon);
      setWeather(data);
    } catch (err) {
      console.log("Error getting weather:", err);
    }
    setLoading(false);
  };

  return (
    <div>
      <h1>Moja aplikácia</h1>
      <button onClick={handleGetWeather}>
        {loading ? "Načítavam..." : "Získať počasie"}
      </button>

      {weather && (
        <div>
          <p>Teplota: {weather.temperature}°C</p>
          <p>Počasie: {weather.weather_main}</p>
        </div>
      )}
    </div>
  );
}

export default App;
