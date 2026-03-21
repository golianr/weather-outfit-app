export async function getUserLocation() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject("Geolocation is not supported by your browser");
    } else {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const lat = pos.coords.latitude;
          const lon = pos.coords.longitude;
          resolve({ lat, lon });
        },
        (err) => reject(err)
      );
    }
  });
}

export async function fetchWeather(lat, lon) {
  try {
    const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
    const url = `${API_URL}/weather?lat=${lat}&lon=${lon}`;
    const res = await fetch(url);

    if (!res.ok) {
      throw new Error("Request failed: " + res.status);
    }

    const data = await res.json();
    return data;
  } catch (error) {
    console.error("Weather API error:", error);
    throw error;
  }
}