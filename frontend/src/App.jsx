import { useState } from "react";
import { getUserLocation, fetchWeather } from "./geolocation";

const getWeatherIcon = (main = "") => {
  const m = main.toLowerCase();
  if (m.includes("clear") || m.includes("sunny")) return "☀️";
  if (m.includes("cloud")) return "☁️";
  if (m.includes("rain")) return "🌧️";
  if (m.includes("drizzle")) return "🌦️";
  if (m.includes("snow") || m.includes("sleet")) return "❄️";
  if (m.includes("thunder")) return "⛈️";
  if (m.includes("fog") || m.includes("mist") || m.includes("haze")) return "🌫️";
  return "🌡️";
};

const CONFIDENCE_LABEL = {
  high:   { label: "Presné",     color: "#6b8f6b", bg: "rgba(107,143,107,0.15)" },
  medium: { label: "Odhadované", color: "#a08060", bg: "rgba(160,128,96,0.15)"  },
  low:    { label: "Orientačné", color: "#a06060", bg: "rgba(160,96,96,0.15)"   },
};

const MODE_OPTIONS = [
  { value: "casual",   emoji: "👜", label: "Casual" },
  { value: "standing", emoji: "🍺", label: "Pivko" },
  { value: "cycling",  emoji: "🚴", label: "Cyklistika" },
  { value: "running",  emoji: "🏃", label: "Beh / šport" },
];

const LAYER_CONFIG = [
  { key: "base_layer",  icon: "🩱", label: "Spodná vrstva" },
  { key: "mid_layer",   icon: "👚", label: "Stredná vrstva" },
  { key: "outer_layer", icon: "🧥", label: "Vrchná vrstva" },
  { key: "bottom",      icon: "👖", label: "Spodok" },
  { key: "footwear",    icon: "👟", label: "Obuv" },
];

export default function App() {
  const [weather, setWeather] = useState(null);
  const [rec, setRec]         = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);
  const [mode, setMode]       = useState("casual");

  const handleFetch = async () => {
    setLoading(true);
    setError(null);
    try {
      const { lat, lon } = await getUserLocation();
      const data = await fetchWeather(lat, lon);
      setWeather(data);

      const res = await fetch("http://localhost:8000/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          temp:             data.temperature,
          feels_like:       data.feels_like,
          wind:             data.wind_speed,
          humidity:         data.humidity,
          weather:          data.weather_main,
          hour:             data.hour_local,
          mode,
          uv_index:         data.uv_index        ?? 0,
          cloud_cover:      data.cloud_cover      ?? 50,
          rain_probability: data.rain_probability ?? 0,
          alerts:           data.alerts           ?? [],
        }),
      });
      if (!res.ok) throw new Error("Server error: " + res.status);
      setRec(await res.json());
    } catch (e) {
      setError(e.message ?? "Niečo sa pokazilo.");
    } finally {
      setLoading(false);
    }
  };

  const outfit = rec?.outfit;
  const conf   = CONFIDENCE_LABEL[rec?.confidence] ?? CONFIDENCE_LABEL.medium;

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Jost:wght@300;400;500&display=swap');

        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

        html, body {
          min-height: 100%;
          /* warm off-white parchment background */
          background: #f5f0e8;
          font-family: 'Jost', sans-serif;
          color: #2c2520;
          -webkit-font-smoothing: antialiased;
        }

        /* subtle texture overlay */
        body::before {
          content: '';
          position: fixed; inset: 0; z-index: 0;
          background-image:
            radial-gradient(ellipse 80% 60% at 15% 10%, rgba(180,155,120,0.18) 0%, transparent 60%),
            radial-gradient(ellipse 60% 50% at 85% 80%, rgba(140,165,140,0.15) 0%, transparent 55%),
            radial-gradient(ellipse 50% 40% at 50% 50%, rgba(200,185,160,0.1) 0%, transparent 70%);
          pointer-events: none;
        }

        .page {
          position: relative; z-index: 1;
          width: 100%;
          max-width: 460px;
          margin: 0 auto;
          padding: 2.5rem 1rem 5rem;
          display: flex;
          flex-direction: column;
          gap: 0.85rem;
        }

        /* ── header ── */
        .header { text-align: center; padding-bottom: 0.4rem; }
        .logo {
          font-family: 'Cormorant Garamond', serif;
          font-size: clamp(2.4rem, 9vw, 3.4rem);
          font-weight: 700;
          color: #3d2e22;
          letter-spacing: -0.01em;
          line-height: 1.1;
        }
        .tagline {
          font-size: clamp(0.72rem, 2.4vw, 0.8rem);
          color: #9c8672;
          margin-top: 0.3rem;
          letter-spacing: 0.1em;
          font-weight: 300;
          text-transform: uppercase;
        }

        /* ── card ── */
        .card {
          background: rgba(255, 252, 246, 0.75);
          border: 1px solid rgba(180, 155, 120, 0.3);
          border-radius: 1.4rem;
          padding: 1.25rem;
          box-shadow: 0 2px 20px rgba(100, 70, 40, 0.07), 0 1px 3px rgba(100,70,40,0.04);
        }
        .card-label {
          font-size: 0.6rem;
          font-weight: 500;
          text-transform: uppercase;
          letter-spacing: 0.16em;
          color: #b09070;
          margin-bottom: 0.85rem;
        }

        /* ── mode buttons ── */
        .mode-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 0.45rem;
          margin-bottom: 0.8rem;
        }
        .mode-btn {
          padding: 0.65rem 0.5rem;
          border-radius: 0.85rem;
          border: 1.5px solid rgba(160, 130, 100, 0.2);
          background: rgba(245, 238, 228, 0.6);
          color: #7a6555;
          cursor: pointer;
          font-size: clamp(0.78rem, 2.5vw, 0.84rem);
          font-family: 'Jost', sans-serif;
          font-weight: 400;
          transition: all 0.15s;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.38rem;
          -webkit-tap-highlight-color: transparent;
        }
        .mode-btn:hover  { border-color: rgba(140,100,60,0.4); color: #3d2e22; background: rgba(235,225,210,0.8); }
        .mode-btn.active {
          border-color: #8c7355;
          background: rgba(140,115,85,0.12);
          color: #5c3d1e;
          font-weight: 500;
        }

        /* ── cta button ── */
        .cta-btn {
          width: 100%;
          padding: 0.88rem;
          border-radius: 0.95rem;
          border: none;
          background: linear-gradient(135deg, #7a5c3a, #a07850);
          color: #fdf6ec;
          font-family: 'Jost', sans-serif;
          font-weight: 500;
          font-size: clamp(0.88rem, 3vw, 0.95rem);
          cursor: pointer;
          letter-spacing: 0.04em;
          transition: opacity 0.2s, transform 0.12s;
          box-shadow: 0 4px 16px rgba(100,65,25,0.22);
          -webkit-tap-highlight-color: transparent;
        }
        .cta-btn:active   { transform: scale(0.985); }
        .cta-btn:disabled { opacity: 0.5; cursor: not-allowed; }

        .error-msg { color: #a05040; font-size: 0.8rem; margin-top: 0.55rem; text-align: center; }

        /* ── weather ── */
        .weather-hero { display: flex; align-items: center; gap: 1rem; margin-bottom: 1rem; }
        .w-icon { font-size: clamp(2.8rem, 9vw, 3.2rem); line-height: 1; }
        .w-temp {
          font-family: 'Cormorant Garamond', serif;
          font-size: clamp(2.2rem, 8vw, 2.8rem);
          font-weight: 700;
          color: #2c2015;
          line-height: 1;
        }
        .w-city  { color: #8c7355; font-size: 0.82rem; margin-top: 0.2rem; font-weight: 300; }
        .w-desc  { color: #b09a80; font-size: 0.72rem; text-transform: capitalize; }

        .stats-row { display: grid; grid-template-columns: repeat(3,1fr); gap: 0.45rem; }
        .stat-box  {
          background: rgba(230,218,200,0.45);
          border: 1px solid rgba(180,155,120,0.2);
          border-radius: 0.8rem;
          padding: 0.6rem 0.35rem;
          text-align: center;
        }
        .stat-val  { font-size: clamp(0.95rem, 3vw, 1.05rem); font-weight: 500; color: #3d2e1e; }
        .stat-lbl  { font-size: 0.58rem; color: #a08870; text-transform: uppercase; letter-spacing: 0.07em; margin-top: 0.15rem; }

        /* ── recommendation ── */
        .rf-row   { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 1rem; }
        .rf-label { font-size: 0.62rem; color: #b09070; text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 0.15rem; }
        .rf-temp  {
          font-family: 'Cormorant Garamond', serif;
          font-size: clamp(1.7rem, 6vw, 2.1rem);
          font-weight: 700;
          color: #5c3d1e;
        }
        .conf-badge { font-size: 0.64rem; font-weight: 500; padding: 0.22rem 0.62rem; border-radius: 999px; letter-spacing: 0.04em; }

        .layer-row  { display: flex; align-items: center; gap: 0.75rem; padding: 0.6rem 0; border-bottom: 1px solid rgba(180,155,120,0.15); }
        .layer-row:last-of-type { border-bottom: none; }
        .layer-icon { font-size: 1.3rem; width: 2rem; text-align: center; flex-shrink: 0; }
        .layer-lbl  { font-size: 0.58rem; color: #a08870; text-transform: uppercase; letter-spacing: 0.09em; }
        .layer-val  { font-size: clamp(0.82rem, 2.8vw, 0.9rem); color: #2c2015; font-weight: 500; margin-top: 0.1rem; }

        .acc-section { margin-top: 0.85rem; }
        .acc-title   { font-size: 0.58rem; color: #a08870; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.45rem; }
        .acc-chips   { display: flex; flex-wrap: wrap; gap: 0.38rem; }
        .acc-chip {
          background: rgba(140,115,85,0.1);
          border: 1px solid rgba(140,115,85,0.25);
          color: #6b4e2e;
          border-radius: 999px;
          padding: 0.25rem 0.65rem;
          font-size: clamp(0.72rem, 2.4vw, 0.78rem);
          font-weight: 400;
        }

        /* ── tips ── */
        .tips-card {
          background: rgba(255,248,232,0.8);
          border: 1px solid rgba(180,148,80,0.25);
          border-radius: 1.4rem;
          padding: 1.1rem 1.2rem;
          box-shadow: 0 2px 14px rgba(140,100,30,0.06);
        }
        .tips-title { font-size: 0.6rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.14em; color: #9a7030; margin-bottom: 0.65rem; }
        .tip-item   { font-size: clamp(0.8rem, 2.6vw, 0.86rem); color: #6b5020; line-height: 1.6; margin-bottom: 0.3rem; }
        .tip-item:last-child { margin-bottom: 0; }

        /* ── spinner ── */
        @keyframes spin { to { transform: rotate(360deg); } }
        .spinner {
          display: inline-block; width: 13px; height: 13px;
          border: 2px solid rgba(253,246,236,0.35);
          border-top-color: #fdf6ec;
          border-radius: 50%;
          animation: spin 0.7s linear infinite;
          vertical-align: middle; margin-right: 0.4rem;
        }

        /* ── fade in ── */
        @keyframes fadeUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
        .fade-in { animation: fadeUp 0.3s ease both; }

        @media (max-width: 380px) {
          .page { padding: 1.8rem 0.85rem 4rem; gap: 0.75rem; }
          .mode-btn { padding: 0.7rem 0.4rem; }
        }
      `}</style>

      <div className="page">

        {/* Header */}
        <div className="header">
          <div className="logo">What To Wear</div>
          <div className="tagline">MADE WITH LOVE FOR MY GF</div>
        </div>

        {/* Controls */}
        <div className="card">
          <div className="card-label">Aktivita</div>
          <div className="mode-grid">
            {MODE_OPTIONS.map((m) => (
              <button
                key={m.value}
                className={`mode-btn${mode === m.value ? " active" : ""}`}
                onClick={() => setMode(m.value)}
              >
                <span>{m.emoji}</span>{m.label}
              </button>
            ))}
          </div>
          <button className="cta-btn" onClick={handleFetch} disabled={loading}>
            {loading
              ? <><span className="spinner" />Načítavam...</>
              : "📍 Zobraziť odporúčanie"}
          </button>
          {error && <p className="error-msg">⚠️ {error}</p>}
        </div>

        {/* Weather */}
        {weather && (
          <div className="card fade-in">
            <div className="card-label">Aktuálne počasie</div>
            <div className="weather-hero">
              <span className="w-icon">{getWeatherIcon(weather.weather_main)}</span>
              <div>
                <div className="w-temp">{weather.temperature}°C</div>
                <div className="w-city">{weather.city}</div>
                <div className="w-desc">{weather.weather_description}</div>
              </div>
            </div>
            <div className="stats-row">
              <div className="stat-box">
                <div className="stat-val">{weather.feels_like}°C</div>
                <div className="stat-lbl">Pocitovo</div>
              </div>
              <div className="stat-box">
                <div className="stat-val">{(weather.wind_speed * 3.6).toFixed(0)}</div>
                <div className="stat-lbl">km/h vietor</div>
              </div>
              <div className="stat-box">
                <div className="stat-val">{weather.humidity}%</div>
                <div className="stat-lbl">Vlhkosť</div>
              </div>
            </div>
          </div>
        )}

        {/* Recommendation */}
        {rec && outfit && (
          <div className="card fade-in">
            <div className="card-label">Odporúčané oblečenie</div>
            <div className="rf-row">
              <div>
                <div className="rf-label">Real feel</div>
                <div className="rf-temp">{rec.real_feel}°C</div>
              </div>
              <span className="conf-badge" style={{ background: conf.bg, color: conf.color }}>
                {conf.label}
              </span>
            </div>

            {LAYER_CONFIG.filter(({ key }) => outfit[key]).map(({ key, icon, label }) => (
              <div key={key} className="layer-row">
                <span className="layer-icon">{icon}</span>
                <div>
                  <div className="layer-lbl">{label}</div>
                  <div className="layer-val">{outfit[key]}</div>
                </div>
              </div>
            ))}

            {outfit.accessories?.length > 0 && (
              <div className="acc-section">
                <div className="acc-title">Doplnky</div>
                <div className="acc-chips">
                  {outfit.accessories.map((acc, i) => (
                    <span key={i} className="acc-chip">{acc}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tips */}
        {rec?.tips?.length > 0 && (
          <div className="tips-card fade-in">
            <div className="tips-title">✦ Tipy pre dnešný deň</div>
            {rec.tips.map((tip, i) => (
              <p key={i} className="tip-item">{tip}</p>
            ))}
          </div>
        )}

      </div>
    </>
  );
}