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
  const res = await fetch(`http://localhost:8000/weather?lat=${lat}&lon=${lon}`);
  const data = await res.json();
  return data;
}
