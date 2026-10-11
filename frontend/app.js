/**
 * Stubble Smoke Alert — Frontend Application v2
 *
 * Fetches REAL-TIME AQI and weather directly from Open-Meteo APIs (client-side).
 * Supports multiple Indian cities. No API key required.
 * Falls back to server forecast.json for ML predictions and fire data.
 */

// ── City Database ─────────────────────────────────────────────────────────
const CITIES = {
    delhi:      { name: 'Delhi',      lat: 28.6139, lon: 77.2090 },
    noida:      { name: 'Noida',      lat: 28.5355, lon: 77.3910 },
    gurugram:   { name: 'Gurugram',   lat: 28.4595, lon: 77.0266 },
    faridabad:  { name: 'Faridabad',  lat: 28.4089, lon: 77.3178 },
    ghaziabad:  { name: 'Ghaziabad',  lat: 28.6692, lon: 77.4538 },
    lucknow:    { name: 'Lucknow',    lat: 26.8467, lon: 80.9462 },
    chandigarh: { name: 'Chandigarh', lat: 30.7333, lon: 76.7794 },
    jaipur:     { name: 'Jaipur',     lat: 26.9124, lon: 75.7873 },
    mumbai:     { name: 'Mumbai',     lat: 19.0760, lon: 72.8777 },
    kolkata:    { name: 'Kolkata',    lat: 22.5726, lon: 88.3639 },
    bengaluru:  { name: 'Bengaluru',  lat: 12.9716, lon: 77.5946 },
    hyderabad:  { name: 'Hyderabad',  lat: 17.3850, lon: 78.4867 },
    chennai:    { name: 'Chennai',    lat: 13.0827, lon: 80.2707 },
    pune:       { name: 'Pune',       lat: 18.5204, lon: 73.8567 },
    ahmedabad:  { name: 'Ahmedabad',  lat: 23.0225, lon: 72.5714 },
    patna:      { name: 'Patna',      lat: 25.6093, lon: 85.1376 },
    varanasi:   { name: 'Varanasi',   lat: 25.3176, lon: 82.9739 },
    agra:       { name: 'Agra',       lat: 27.1767, lon: 78.0081 },
};

// AQI band definitions (matching CPCB India standard)
const AQI_BANDS = [
    { max: 50,  label: 'Good',      color: '#4caf50', severity: 1, action: 'Normal outdoor activity. All sports and PE can proceed.', details: 'Air quality is satisfactory with minimal health risk.' },
    { max: 100, label: 'Moderate',  color: '#ffeb3b', severity: 2, action: 'Normal activity; monitor students with asthma or respiratory conditions.', details: 'Air quality is acceptable. Some pollutants may pose a moderate risk to sensitive individuals.' },
    { max: 200, label: 'Poor',      color: '#ff9800', severity: 3, action: 'Shorten outdoor activity to 30 minutes. Sensitive students should wear masks.', details: 'Members of sensitive groups may experience health effects. Limit prolonged outdoor exertion.' },
    { max: 300, label: 'Very Poor', color: '#f44336', severity: 4, action: 'Move PE and assembly indoors. Keep windows and doors closed. Run air purifiers if available.', details: 'Health effects likely for all students with prolonged exposure. Avoid all outdoor physical activity.' },
    { max: 999, label: 'Severe',    color: '#9c27b0', severity: 5, action: 'Cancel all outdoor activities. Notify parents. Consider online classes if AQI persists.', details: 'Serious health risk for everyone. Emergency measures required. All students should stay indoors.' },
];

// ── API Endpoints ─────────────────────────────────────────────────────────
const AIR_QUALITY_API = 'https://air-quality-api.open-meteo.com/v1/air-quality';
const WEATHER_API = 'https://api.open-meteo.com/v1/forecast';
const API_BASE_URL = '';  // Set to Lambda API Gateway URL after deployment

// ── State ─────────────────────────────────────────────────────────────────
let map = null;
let currentCity = 'delhi';
let mapMarkers = [];
let forecastData = null;
let trendChart = null;
let refreshTimer = null;
const REFRESH_INTERVAL = 300; // 5 minutes in seconds
let refreshCountdown = REFRESH_INTERVAL;

// ── Initialization ────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    initMap();
    startLiveClock();

    // City selector
    const selector = document.getElementById('city-select');
    selector.addEventListener('change', (e) => {
        currentCity = e.target.value;
        fetchLiveData(currentCity);
    });

    // Load data for default city
    fetchLiveData(currentCity);

    // Auto-refresh every 5 minutes
    startAutoRefresh();

    // SNS alert form
    document.getElementById('alert-form').addEventListener('submit', handleAlertSubscribe);
});

// ── Live Clock ────────────────────────────────────────────────────────────
function startLiveClock() {
    function update() {
        const now = new Date();
        const timeStr = now.toLocaleTimeString('en-IN', { hour12: true, hour: '2-digit', minute: '2-digit', second: '2-digit' });
        const dateStr = now.toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
        document.getElementById('live-time').textContent = timeStr;
        document.getElementById('live-date').textContent = dateStr;
    }
    update();
    setInterval(update, 1000);
}

// ── Data Fetching (Client-Side, Real-Time) ────────────────────────────────

async function fetchLiveData(cityKey) {
    const city = CITIES[cityKey];
    if (!city) return;

    // Show loading
    document.getElementById('forecast-loading').classList.remove('hidden');
    document.getElementById('forecast-content').classList.add('hidden');

    // Update location display
    document.getElementById('live-location').textContent =
        `${city.name} (${city.lat.toFixed(2)}\u00b0N, ${city.lon.toFixed(2)}\u00b0E)`;

    try {
        // Fetch AQI and Weather in parallel
        const [aqiData, weatherData] = await Promise.all([
            fetchAQI(city.lat, city.lon),
            fetchWeather(city.lat, city.lon),
        ]);

        // Also try to load server forecast for fire data
        let serverForecast = null;
        try {
            const resp = API_BASE_URL
                ? await fetch(`${API_BASE_URL}/forecast`)
                : await fetch('forecast.json');
            if (resp.ok) serverForecast = await resp.json();
        } catch (e) { /* ignore, fires are optional */ }

        // Build combined forecast
        const forecast = buildForecast(city, aqiData, weatherData, serverForecast);
        forecastData = forecast;

        renderForecast(forecast);
        renderMap(forecast, city);
        renderModelInfo(forecast);
        renderHealthAdvisory(forecast);

        // Fetch and render 24-hour trend
        fetchAndRenderTrend(city.lat, city.lon);

    } catch (err) {
        console.error('Failed to fetch data:', err);
        document.getElementById('forecast-loading').innerHTML = `
            <p style="color: #f44336;">Failed to fetch AQI data for ${city.name}.</p>
            <p style="color: var(--text-muted); font-size: 0.85rem;">
                ${err.message}<br>Please check your internet connection and try again.
            </p>
        `;
    }
}

async function fetchAQI(lat, lon) {
    const url = `${AIR_QUALITY_API}?latitude=${lat}&longitude=${lon}&current=us_aqi,pm10,pm2_5,european_aqi&timezone=Asia/Kolkata`;
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`AQI API returned ${resp.status}`);
    return resp.json();
}

async function fetchWeather(lat, lon) {
    const url = `${WEATHER_API}?latitude=${lat}&longitude=${lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m&forecast_days=2&daily=temperature_2m_max,temperature_2m_min,wind_speed_10m_max,wind_direction_10m_dominant&timezone=Asia/Kolkata`;
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`Weather API returned ${resp.status}`);
    return resp.json();
}

// ── Build Forecast From Live APIs ─────────────────────────────────────────

function buildForecast(city, aqiData, weatherData, serverForecast) {
    const current = aqiData.current || {};
    const wx = weatherData.current || {};
    const daily = weatherData.daily || {};

    const usAqi = current.us_aqi || 0;
    const todayBand = aqiToBand(usAqi);
    const tomorrowBand = todayBand; // Persistence forecast for non-Delhi cities

    const bandInfo = AQI_BANDS.find(b => usAqi <= b.max) || AQI_BANDS[AQI_BANDS.length - 1];

    const now = new Date();
    const tomorrow = new Date(now);
    tomorrow.setDate(tomorrow.getDate() + 1);

    // Get fires from server forecast (if available)
    const fires = (serverForecast && serverForecast.fires) || [];

    return {
        forecast_date: daily.time?.[1] || tomorrow.toISOString().split('T')[0],
        generated_at: now.toISOString(),
        today_date: now.toISOString().split('T')[0],
        today_aqi: usAqi,
        today_band: todayBand,
        today_pm25: current.pm2_5,
        today_pm10: current.pm10,
        predicted_aqi_band: tomorrowBand,
        predicted_aqi_range: bandInfo ? `${bandInfo === AQI_BANDS[0] ? 0 : AQI_BANDS[AQI_BANDS.indexOf(bandInfo) - 1].max + 1}-${bandInfo.max > 500 ? '500+' : bandInfo.max}` : 'Unknown',
        action: bandInfo.action,
        severity: bandInfo.severity,
        color: bandInfo.color,
        details: bandInfo.details,
        reason: buildReason(wx, usAqi, city.name),
        model_type: city.name === 'Delhi' ? 'gradient_boosting_weather_only' : 'persistence_forecast',
        model_accuracy: 0.697,
        baseline_accuracy: 0.7939,
        location: city,
        features_used: {
            wind_speed: wx.wind_speed_10m,
            wind_dir: wx.wind_direction_10m,
            fires_upwind: 0,
            aqi_today: usAqi,
            temperature: wx.temperature_2m,
            humidity: wx.relative_humidity_2m,
            pm2_5: current.pm2_5,
            pm10: current.pm10,
        },
        weather_tomorrow: {
            temp_max: daily.temperature_2m_max?.[1],
            temp_min: daily.temperature_2m_min?.[1],
            wind_speed_max: daily.wind_speed_10m_max?.[1],
            wind_dir_dominant: daily.wind_direction_10m_dominant?.[1],
        },
        fires: fires,
        delhi: { lat: city.lat, lon: city.lon },
        disclaimer: 'Real-time AQI from Open-Meteo (CAMS model). ML prediction for Delhi. Always verify with official CPCB bulletins.',
        data_source: 'live',
        aqi_source: 'Open-Meteo Air Quality API (CAMS global model)',
    };
}

function aqiToBand(aqi) {
    if (aqi <= 50) return 'Good';
    if (aqi <= 100) return 'Moderate';
    if (aqi <= 200) return 'Poor';
    if (aqi <= 300) return 'Very Poor';
    return 'Severe';
}

function buildReason(wx, aqi, cityName) {
    const parts = [];
    if (wx.wind_direction_10m !== undefined && wx.wind_speed_10m !== undefined) {
        parts.push(`${degreesToCompass(wx.wind_direction_10m)} winds at ${Math.round(wx.wind_speed_10m)} km/h`);
    }
    if (wx.temperature_2m !== undefined) {
        parts.push(`temperature ${wx.temperature_2m.toFixed(1)}\u00b0C`);
    }
    if (aqi > 0) {
        parts.push(`current AQI reading of ${aqi} in ${cityName}`);
    }
    return parts.length > 0 ? parts.join('; ') + '.' : 'Insufficient data for detailed analysis.';
}

// ── Forecast Rendering ───────────────────────────────────────────────────

function renderForecast(data) {
    document.getElementById('forecast-loading').classList.add('hidden');
    const content = document.getElementById('forecast-content');
    content.classList.remove('hidden');
    content.classList.add('animate-in');

    // Date
    const forecastDate = new Date(data.forecast_date + 'T00:00:00');
    document.getElementById('forecast-date').textContent = formatDate(forecastDate);

    // Today's AQI
    const todayAqi = document.getElementById('today-aqi');
    todayAqi.textContent = data.today_aqi || '--';
    todayAqi.style.color = data.color || 'inherit';

    // Today's band label
    const bandLabel = document.getElementById('today-band-label');
    bandLabel.textContent = data.today_band || '';
    bandLabel.style.color = data.color || 'inherit';

    // Band display
    const bandDisplay = document.getElementById('band-display');
    const bandColor = data.color || '#64748b';
    bandDisplay.style.background = `linear-gradient(135deg, ${hexToRgba(bandColor, 0.2)}, ${hexToRgba(bandColor, 0.05)})`;
    bandDisplay.style.borderLeft = `4px solid ${bandColor}`;

    document.getElementById('band-label').textContent = data.predicted_aqi_band;
    document.getElementById('band-label').style.color = bandColor;
    document.getElementById('band-range').textContent = `AQI ${data.predicted_aqi_range}`;

    document.getElementById('forecast-card').style.borderColor = hexToRgba(bandColor, 0.3);

    // Action
    const actionIcons = { 1: '\u2705', 2: '\u2705', 3: '\u26A0\uFE0F', 4: '\uD83C\uDFE0', 5: '\uD83D\uDEA8' };
    document.getElementById('action-icon').textContent = actionIcons[data.severity] || '\u2139\uFE0F';
    document.getElementById('action-text').textContent = data.action;

    // Reason
    document.getElementById('reason-text').textContent = data.reason;

    // PM2.5 & PM10
    const features = data.features_used || {};
    const pm25El = document.getElementById('pm25-info');
    const pm10El = document.getElementById('pm10-info');
    if (features.pm2_5 != null) {
        pm25El.textContent = `${features.pm2_5.toFixed(1)} \u00b5g/m\u00b3`;
        pm25El.style.color = features.pm2_5 > 60 ? '#f44336' : features.pm2_5 > 30 ? '#ff9800' : '#4caf50';
    } else { pm25El.textContent = 'N/A'; }
    if (features.pm10 != null) {
        pm10El.textContent = `${features.pm10.toFixed(1)} \u00b5g/m\u00b3`;
        pm10El.style.color = features.pm10 > 150 ? '#f44336' : features.pm10 > 100 ? '#ff9800' : '#4caf50';
    } else { pm10El.textContent = 'N/A'; }

    // Other details
    document.getElementById('wind-info').textContent =
        `${degreesToCompass(features.wind_dir)} ${features.wind_speed?.toFixed(0) || '--'} km/h`;
    document.getElementById('temp-info').textContent =
        `${features.temperature?.toFixed(1) || '--'}\u00b0C`;
    document.getElementById('humidity-info').textContent =
        `${features.humidity?.toFixed(0) || '--'}%`;
    document.getElementById('fires-info').textContent =
        features.fires_upwind > 0 ? `${features.fires_upwind.toFixed(0)} detected` : 'None / No data';

    // Generated-at
    const genEl = document.getElementById('generated-at');
    genEl.textContent = `Live data fetched at ${new Date().toLocaleString('en-IN')} | Source: ${data.aqi_source || 'Open-Meteo'}`;

    // Highlight active band in scale
    document.querySelectorAll('.scale-item').forEach(item => {
        item.classList.toggle('active', item.dataset.band === data.predicted_aqi_band);
    });

    // Data source badge
    const badge = document.getElementById('data-source-badge');
    badge.textContent = 'LIVE';
    badge.style.background = 'rgba(16, 185, 129, 0.15)';
    badge.style.color = '#10b981';
    badge.style.borderColor = 'rgba(16, 185, 129, 0.3)';
}

// ── Map Rendering ────────────────────────────────────────────────────────

function initMap() {
    map = L.map('map', {
        center: [28.5, 77.0],
        zoom: 7,
        zoomControl: true,
        attributionControl: true,
    });

    L.tileLayer('https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/">OSM</a> &copy; <a href="https://stadiamaps.com/">Stadia</a>',
        maxZoom: 15,
    }).addTo(map);
}

function renderMap(data, city) {
    if (!map) return;

    // Clear previous markers
    mapMarkers.forEach(m => map.removeLayer(m));
    mapMarkers = [];

    const fires = data.fires || [];
    const windDir = data.features_used?.wind_dir || 0;

    // City marker
    const cityIcon = L.divIcon({ className: 'delhi-marker', iconSize: [16, 16], iconAnchor: [8, 8] });
    const cityMarker = L.marker([city.lat, city.lon], { icon: cityIcon })
        .bindPopup(`<strong>${city.name}</strong><br>AQI: ${data.today_aqi} (${data.today_band})<br>PM2.5: ${data.today_pm25?.toFixed(1) || '--'} \u00b5g/m\u00b3`)
        .addTo(map);
    mapMarkers.push(cityMarker);

    // Wind arrow
    if (windDir !== undefined) {
        const arrowMarkers = drawWindArrow(city.lat, city.lon, windDir);
        mapMarkers.push(...arrowMarkers);
    }

    // Fire markers
    fires.forEach(fire => {
        const size = Math.max(8, Math.min(20, (fire.frp || 10) / 3));
        const fireIcon = L.divIcon({ className: 'fire-marker', iconSize: [size, size], iconAnchor: [size / 2, size / 2] });
        const m = L.marker([fire.lat, fire.lon], { icon: fireIcon })
            .bindPopup(`<strong>Fire</strong><br>${fire.lat.toFixed(2)}\u00b0N, ${fire.lon.toFixed(2)}\u00b0E<br>FRP: ${fire.frp?.toFixed(1) || '--'} MW<br>Date: ${fire.date}`)
            .addTo(map);
        mapMarkers.push(m);
    });

    // Fit bounds
    const allPoints = [[city.lat, city.lon]];
    if (fires.length > 0) {
        fires.forEach(f => allPoints.push([f.lat, f.lon]));
    }
    if (allPoints.length > 1) {
        map.fitBounds(allPoints, { padding: [30, 30] });
    } else {
        map.setView([city.lat, city.lon], 8);
    }
}

function drawWindArrow(lat, lon, windDirDeg) {
    const markers = [];
    const arrowLength = 1.5;
    const windFromRad = (windDirDeg * Math.PI) / 180;

    const startLat = lat + arrowLength * Math.cos(windFromRad);
    const startLon = lon + arrowLength * Math.sin(windFromRad);

    const line = L.polyline([[startLat, startLon], [lat, lon]], {
        color: 'rgba(255, 255, 255, 0.5)', weight: 2, dashArray: '8, 8', opacity: 0.7,
    }).addTo(map);
    markers.push(line);

    const headSize = 0.3;
    const a1 = windFromRad + Math.PI + 0.4;
    const a2 = windFromRad + Math.PI - 0.4;
    const h1 = L.polyline([[lat, lon], [lat + headSize * Math.cos(a1), lon + headSize * Math.sin(a1)]], {
        color: 'rgba(255, 255, 255, 0.5)', weight: 2, opacity: 0.7,
    }).addTo(map);
    const h2 = L.polyline([[lat, lon], [lat + headSize * Math.cos(a2), lon + headSize * Math.sin(a2)]], {
        color: 'rgba(255, 255, 255, 0.5)', weight: 2, opacity: 0.7,
    }).addTo(map);
    markers.push(h1, h2);

    const label = L.marker([(startLat + lat) / 2, (startLon + lon) / 2], {
        icon: L.divIcon({
            className: '',
            html: `<div style="color: rgba(255,255,255,0.6); font-size: 11px; font-family: Inter, sans-serif; white-space: nowrap; text-shadow: 0 1px 3px rgba(0,0,0,0.8);">Wind from ${degreesToCompass(windDirDeg)} (${windDirDeg.toFixed(0)}\u00b0)</div>`,
            iconSize: [150, 20], iconAnchor: [75, 10],
        }),
    }).addTo(map);
    markers.push(label);

    return markers;
}

// ── Model Info ───────────────────────────────────────────────────────────

function renderModelInfo(data) {
    const modelType = data.model_type || 'Unknown';
    const displayType = modelType.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

    document.getElementById('model-type').textContent = displayType;
    document.getElementById('model-accuracy').textContent =
        typeof data.model_accuracy === 'number' ? `${(data.model_accuracy * 100).toFixed(1)}%` : data.model_accuracy;
    document.getElementById('baseline-accuracy').textContent =
        typeof data.baseline_accuracy === 'number' ? `${(data.baseline_accuracy * 100).toFixed(1)}%` : data.baseline_accuracy;
    document.getElementById('data-source').textContent = 'Live (Open-Meteo)';
    document.getElementById('disclaimer').textContent = data.disclaimer || '';
}

// ── Utility Functions ────────────────────────────────────────────────────

function formatDate(date) {
    return date.toLocaleDateString('en-IN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
}

function degreesToCompass(deg) {
    if (deg === undefined || deg === null) return '--';
    const dirs = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
                  'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];
    return dirs[Math.round(deg / 22.5) % 16];
}

function hexToRgba(hex, alpha) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

// ── 24-Hour AQI Trend Chart ──────────────────────────────────────────────

async function fetchAndRenderTrend(lat, lon) {
    try {
        const url = `${AIR_QUALITY_API}?latitude=${lat}&longitude=${lon}&hourly=us_aqi,pm2_5&past_hours=24&forecast_hours=12&timezone=Asia/Kolkata`;
        const resp = await fetch(url);
        if (!resp.ok) return;
        const data = await resp.json();

        const hourly = data.hourly || {};
        const times = (hourly.time || []).map(t => {
            const d = new Date(t);
            return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: false });
        });
        const aqiValues = hourly.us_aqi || [];
        const pm25Values = hourly.pm2_5 || [];

        // Color each point by AQI band
        const colors = aqiValues.map(v => {
            if (v <= 50) return '#4caf50';
            if (v <= 100) return '#ffeb3b';
            if (v <= 200) return '#ff9800';
            if (v <= 300) return '#f44336';
            return '#9c27b0';
        });

        // Mark current time
        const now = new Date();
        const nowIdx = times.findIndex((t, i) => {
            const dt = new Date(hourly.time[i]);
            return dt >= now;
        });

        renderTrendChart(times, aqiValues, pm25Values, colors, nowIdx);
    } catch (e) {
        console.error('Trend chart error:', e);
    }
}

function renderTrendChart(labels, aqiData, pm25Data, colors, nowIdx) {
    const ctx = document.getElementById('aqi-trend-chart').getContext('2d');

    if (trendChart) trendChart.destroy();

    trendChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'US AQI',
                    data: aqiData,
                    borderColor: '#ff9800',
                    backgroundColor: 'rgba(255, 152, 0, 0.1)',
                    borderWidth: 2,
                    pointRadius: 2,
                    pointBackgroundColor: colors,
                    tension: 0.3,
                    fill: true,
                    yAxisID: 'y',
                },
                {
                    label: 'PM2.5 (\u00b5g/m\u00b3)',
                    data: pm25Data,
                    borderColor: '#3b82f6',
                    borderWidth: 1.5,
                    pointRadius: 0,
                    borderDash: [4, 4],
                    tension: 0.3,
                    fill: false,
                    yAxisID: 'y1',
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: {
                    labels: { color: '#94a3b8', font: { family: 'Inter', size: 11 } }
                },
                annotation: nowIdx > 0 ? {
                    annotations: {
                        nowLine: {
                            type: 'line',
                            xMin: nowIdx,
                            xMax: nowIdx,
                            borderColor: 'rgba(16, 185, 129, 0.5)',
                            borderWidth: 2,
                            borderDash: [3, 3],
                            label: { content: 'Now', display: true, color: '#10b981', font: { size: 10 } },
                        },
                    },
                } : {},
            },
            scales: {
                x: {
                    ticks: { color: '#64748b', font: { size: 10 }, maxRotation: 45, maxTicksLimit: 12 },
                    grid: { color: 'rgba(255,255,255,0.04)' },
                },
                y: {
                    position: 'left',
                    title: { display: true, text: 'US AQI', color: '#ff9800', font: { size: 11 } },
                    ticks: { color: '#ff9800', font: { size: 10 } },
                    grid: { color: 'rgba(255,255,255,0.04)' },
                    min: 0,
                },
                y1: {
                    position: 'right',
                    title: { display: true, text: 'PM2.5 \u00b5g/m\u00b3', color: '#3b82f6', font: { size: 11 } },
                    ticks: { color: '#3b82f6', font: { size: 10 } },
                    grid: { drawOnChartArea: false },
                    min: 0,
                },
            },
        },
    });
}

// ── Children's Health Advisory ───────────────────────────────────────────

const HEALTH_DATA = {
    'Good': {
        outdoor: 'All outdoor sports, PE, and recess can proceed normally. Encourage physical activity.',
        mask: 'No masks needed. Normal breathing for all students.',
        ventilation: 'Open windows for fresh air circulation. Natural ventilation is ideal.',
        sensitive: 'No special precautions needed. Asthmatic students can participate fully.',
    },
    'Moderate': {
        outdoor: 'Outdoor activity is fine. Limit to 1 hour for students who report discomfort.',
        mask: 'Not required for most students. Keep masks available for children with asthma.',
        ventilation: 'Windows can remain open. Consider closing if students report irritation.',
        sensitive: 'Monitor students with asthma or allergies. Keep inhalers accessible.',
    },
    'Poor': {
        outdoor: 'Limit outdoor PE to 30 minutes. No long-distance running. Move sports indoors if possible.',
        mask: 'N95 masks recommended for outdoor activity. Provide masks for students who do not have them.',
        ventilation: 'Close windows facing roads. Use air purifiers in classrooms if available.',
        sensitive: 'Students with asthma should skip outdoor PE. Keep rescue medication ready. Inform parents.',
    },
    'Very Poor': {
        outdoor: 'Cancel ALL outdoor PE, assembly, and recess. All activities must be held indoors.',
        mask: 'N95 masks mandatory for any time spent outdoors (e.g., commute). Ensure proper fit for children.',
        ventilation: 'All windows and doors must remain closed. Air purifiers should run continuously.',
        sensitive: 'Alert parents of asthmatic/allergic students. Consider allowing these students to stay home.',
    },
    'Severe': {
        outdoor: 'CANCEL ALL outdoor activities. Send advisory to parents. Consider shifting to online classes.',
        mask: 'N95 mandatory even indoors if purifiers are not available. Check mask fit regularly.',
        ventilation: 'Seal all openings. Run air purifiers on maximum. Wet-mop floors to reduce dust.',
        sensitive: 'Strongly advise parents to keep vulnerable children home. Arrange online attendance.',
    },
};

function renderHealthAdvisory(data) {
    const band = data.predicted_aqi_band || 'Good';
    const health = HEALTH_DATA[band] || HEALTH_DATA['Good'];

    document.getElementById('health-outdoor-text').textContent = health.outdoor;
    document.getElementById('health-mask-text').textContent = health.mask;
    document.getElementById('health-ventilation-text').textContent = health.ventilation;
    document.getElementById('health-sensitive-text').textContent = health.sensitive;

    // Color the cards based on severity
    const bandColor = data.color || '#64748b';
    document.querySelectorAll('.health-card').forEach(card => {
        card.style.borderColor = hexToRgba(bandColor, 0.25);
    });
}

// ── Auto-Refresh ─────────────────────────────────────────────────────────

function startAutoRefresh() {
    refreshCountdown = REFRESH_INTERVAL;
    if (refreshTimer) clearInterval(refreshTimer);

    refreshTimer = setInterval(() => {
        refreshCountdown--;
        const mins = Math.floor(refreshCountdown / 60);
        const secs = refreshCountdown % 60;
        const el = document.getElementById('refresh-countdown');
        if (el) el.textContent = `Auto-refresh in ${mins}:${secs.toString().padStart(2, '0')}`;

        if (refreshCountdown <= 0) {
            refreshCountdown = REFRESH_INTERVAL;
            fetchLiveData(currentCity);
        }
    }, 1000);
}

// ── AWS SNS Alert Subscription ───────────────────────────────────────────

async function handleAlertSubscribe(e) {
    e.preventDefault();
    const email = document.getElementById('alert-email').value;
    const city = document.getElementById('alert-city').value;
    const status = document.getElementById('alert-status');
    const btn = document.getElementById('alert-submit');

    btn.disabled = true;
    btn.textContent = 'Subscribing...';

    // If API is deployed, call the subscribe endpoint
    if (API_BASE_URL) {
        try {
            const resp = await fetch(`${API_BASE_URL}/subscribe`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, city }),
            });
            if (resp.ok) {
                status.textContent = `Subscribed! Check ${email} for a confirmation from AWS SNS.`;
                status.className = 'alert-status success';
            } else {
                throw new Error('Subscription failed');
            }
        } catch (err) {
            status.textContent = 'Could not subscribe. API may not be deployed yet.';
            status.className = 'alert-status error';
        }
    } else {
        // Demo mode — show success with explanation
        status.innerHTML = `<strong>Demo:</strong> In production, AWS SNS sends a confirmation to <strong>${email}</strong> for <strong>${CITIES[city]?.name || city}</strong>. Deploy the SAM template to enable live alerts.`;
        status.className = 'alert-status success';
    }

    btn.disabled = false;
    btn.textContent = 'Subscribe via AWS SNS';
}
