/**
 * Stubble Smoke Alert — Frontend Application
 *
 * Fetches forecast data from the API (or local JSON fallback),
 * renders the AQI forecast card and Leaflet fire map.
 */

// ── Configuration ─────────────────────────────────────────────────────────
// API URL: set to deployed API Gateway URL, or empty for local fallback
const API_BASE_URL = '';  // Will be updated after AWS deployment

// Local fallback path (for development)
const LOCAL_FORECAST_URL = 'forecast.json';

// ── State ─────────────────────────────────────────────────────────────────
let map = null;
let forecastData = null;

// ── Initialization ────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    initMap();
    loadForecast();
});

// ── Data Loading ──────────────────────────────────────────────────────────

async function loadForecast() {
    try {
        let data;

        if (API_BASE_URL) {
            // Try API first
            const resp = await fetch(`${API_BASE_URL}/forecast`);
            if (!resp.ok) throw new Error(`API returned ${resp.status}`);
            data = await resp.json();
        } else {
            // Local fallback
            const resp = await fetch(LOCAL_FORECAST_URL);
            if (!resp.ok) throw new Error(`Local file returned ${resp.status}`);
            data = await resp.json();
        }

        forecastData = data;
        renderForecast(data);
        renderMap(data);
        renderModelInfo(data);

    } catch (err) {
        console.error('Failed to load forecast:', err);
        document.getElementById('forecast-loading').innerHTML = `
            <p style="color: #f44336;">Failed to load forecast data.</p>
            <p style="color: var(--text-muted); font-size: 0.85rem;">
                ${err.message}<br>
                Make sure forecast.json is in the same directory, or configure API_BASE_URL.
            </p>
        `;
    }
}

// ── Forecast Rendering ───────────────────────────────────────────────────

function renderForecast(data) {
    // Hide loading, show content
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

    // Band display
    const bandDisplay = document.getElementById('band-display');
    const bandColor = data.color || '#64748b';
    bandDisplay.style.background = `linear-gradient(135deg, ${hexToRgba(bandColor, 0.2)}, ${hexToRgba(bandColor, 0.05)})`;
    bandDisplay.style.borderLeft = `4px solid ${bandColor}`;

    document.getElementById('band-label').textContent = data.predicted_aqi_band;
    document.getElementById('band-label').style.color = bandColor;
    document.getElementById('band-range').textContent = `AQI ${data.predicted_aqi_range}`;

    // Update forecast card border
    document.getElementById('forecast-card').style.borderColor = hexToRgba(bandColor, 0.3);

    // Action
    const actionIcons = {
        1: '\u2705',  // Good
        2: '\u2705',  // Moderate
        3: '\u26A0\uFE0F',  // Poor
        4: '\uD83C\uDFE0', // Very Poor (house)
        5: '\uD83D\uDEA8', // Severe
    };
    document.getElementById('action-icon').textContent = actionIcons[data.severity] || '\u2139\uFE0F';
    document.getElementById('action-text').textContent = data.action;

    // Reason
    document.getElementById('reason-text').textContent = data.reason;

    // Details
    const features = data.features_used || {};
    document.getElementById('wind-info').textContent =
        `${degreesToCompass(features.wind_dir)} ${features.wind_speed?.toFixed(0) || '--'} km/h`;
    document.getElementById('temp-info').textContent =
        `${features.temperature?.toFixed(1) || '--'}°C`;
    document.getElementById('humidity-info').textContent =
        `${features.humidity?.toFixed(0) || '--'}%`;
    document.getElementById('fires-info').textContent =
        features.fires_upwind > 0 ? `${features.fires_upwind.toFixed(0)} detected` : 'None / No data';

    // Highlight active band in scale
    document.querySelectorAll('.scale-item').forEach(item => {
        item.classList.toggle('active', item.dataset.band === data.predicted_aqi_band);
    });

    // Data source badge
    const badge = document.getElementById('data-source-badge');
    if (data.data_source === 'synthetic') {
        badge.textContent = 'Demo Data';
        badge.style.background = 'rgba(255, 193, 7, 0.15)';
        badge.style.color = '#ffc107';
        badge.style.borderColor = 'rgba(255, 193, 7, 0.3)';
    } else {
        badge.textContent = 'Live Data';
        badge.style.background = 'rgba(76, 175, 80, 0.15)';
        badge.style.color = '#4caf50';
        badge.style.borderColor = 'rgba(76, 175, 80, 0.3)';
    }
}

// ── Map Rendering ────────────────────────────────────────────────────────

function initMap() {
    map = L.map('map', {
        center: [29.5, 76.5],
        zoom: 7,
        zoomControl: true,
        attributionControl: true,
    });

    // Dark tile layer (free, no API key required)
    L.tileLayer('https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/">OSM</a> &copy; <a href="https://stadiamaps.com/">Stadia</a>',
        maxZoom: 15,
    }).addTo(map);
}

function renderMap(data) {
    if (!map || !data) return;

    const delhi = data.delhi || { lat: 28.6139, lon: 77.209 };
    const fires = data.fires || [];
    const windDir = data.features_used?.wind_dir || 0;

    // Delhi marker
    const delhiIcon = L.divIcon({
        className: 'delhi-marker',
        iconSize: [16, 16],
        iconAnchor: [8, 8],
    });

    L.marker([delhi.lat, delhi.lon], { icon: delhiIcon })
        .bindPopup(`
            <strong>Delhi</strong><br>
            Today's AQI: ${data.today_aqi || '--'} (${data.today_band || '--'})<br>
            Tomorrow: <strong>${data.predicted_aqi_band}</strong>
        `)
        .addTo(map);

    // Wind direction arrow from Delhi
    if (windDir !== undefined) {
        drawWindArrow(delhi.lat, delhi.lon, windDir);
    }

    // Fire markers
    fires.forEach(fire => {
        const size = Math.max(8, Math.min(20, (fire.frp || 10) / 3));
        const fireIcon = L.divIcon({
            className: 'fire-marker',
            iconSize: [size, size],
            iconAnchor: [size / 2, size / 2],
        });

        L.marker([fire.lat, fire.lon], { icon: fireIcon })
            .bindPopup(`
                <strong>Fire Detection</strong><br>
                Location: ${fire.lat.toFixed(2)}°N, ${fire.lon.toFixed(2)}°E<br>
                FRP: ${fire.frp?.toFixed(1) || '--'} MW<br>
                Date: ${fire.date}
            `)
            .addTo(map);
    });

    // Fit bounds to show all markers
    if (fires.length > 0) {
        const allPoints = [[delhi.lat, delhi.lon], ...fires.map(f => [f.lat, f.lon])];
        map.fitBounds(allPoints, { padding: [30, 30] });
    }
}

function drawWindArrow(lat, lon, windDirDeg) {
    // Wind direction = direction wind blows FROM
    // Arrow shows the path smoke would travel (downwind toward Delhi)
    // So we draw from upwind (where wind comes from) toward Delhi

    const arrowLength = 1.5; // degrees (visual only)
    const windFromRad = (windDirDeg * Math.PI) / 180;

    // Start point: upwind of Delhi
    const startLat = lat + arrowLength * Math.cos(windFromRad);
    const startLon = lon + arrowLength * Math.sin(windFromRad);

    // Draw line from upwind direction toward Delhi
    const line = L.polyline(
        [[startLat, startLon], [lat, lon]],
        {
            color: 'rgba(255, 255, 255, 0.5)',
            weight: 2,
            dashArray: '8, 8',
            opacity: 0.7,
        }
    ).addTo(map);

    // Arrow head at Delhi end
    const headSize = 0.3;
    const angle1 = windFromRad + Math.PI + 0.4;
    const angle2 = windFromRad + Math.PI - 0.4;

    const head1 = [
        lat + headSize * Math.cos(angle1),
        lon + headSize * Math.sin(angle1),
    ];
    const head2 = [
        lat + headSize * Math.cos(angle2),
        lon + headSize * Math.sin(angle2),
    ];

    L.polyline([[lat, lon], head1], {
        color: 'rgba(255, 255, 255, 0.5)',
        weight: 2,
        opacity: 0.7,
    }).addTo(map);

    L.polyline([[lat, lon], head2], {
        color: 'rgba(255, 255, 255, 0.5)',
        weight: 2,
        opacity: 0.7,
    }).addTo(map);

    // Label
    L.marker([(startLat + lat) / 2, (startLon + lon) / 2], {
        icon: L.divIcon({
            className: '',
            html: `<div style="color: rgba(255,255,255,0.6); font-size: 11px; font-family: Inter, sans-serif; white-space: nowrap; text-shadow: 0 1px 3px rgba(0,0,0,0.8);">Wind from ${degreesToCompass(windDirDeg)} (${windDirDeg.toFixed(0)}°)</div>`,
            iconSize: [150, 20],
            iconAnchor: [75, 10],
        }),
    }).addTo(map);
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
    document.getElementById('data-source').textContent =
        data.data_source === 'synthetic' ? 'Synthetic (demo)' : 'Real observations';
    document.getElementById('disclaimer').textContent = data.disclaimer || '';
}

// ── Utility Functions ────────────────────────────────────────────────────

function formatDate(date) {
    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    return date.toLocaleDateString('en-IN', options);
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
