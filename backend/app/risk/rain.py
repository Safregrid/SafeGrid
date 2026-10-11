"""
SafeGrid - Precipitation Risk Calculation Engine
Module: rain.py

Author / Owner: Person 2 (Risk Engine & Geospatial Processing)
Branch: feature/risk-engine

Accepts normalized precipitation hazard events (produced by Person 1's Open-Meteo
ingestion or Person 4's database layer) and calculates:
1. Deterministic risk level (LOW, MODERATE, HIGH)
2. Continuous severity score (0.0 to 10.0)
3. GeoJSON Polygon affected-area geometry for MapLibre rendering (Person 3)
4. Contextual summary, compounding factors, and threshold explanations

Scientific Threshold Justifications:
- Hourly precipitation thresholds based on UK Met Office & WMO guidelines:
    - Light: < 2.5 mm/h (Score < 4.0 -> LOW)
    - Moderate: 2.5 - 7.6 mm/h (Score 4.0 - 6.9 -> MODERATE)
    - Heavy: 7.6 - 15.0 mm/h (Score 7.0 - 8.5 -> HIGH)
    - Violent / Torrential: > 15.0 mm/h (Score 8.5 - 10.0 -> HIGH)
- 24-Hour accumulation thresholds based on IMD / NOAA standards:
    - Light: < 15.5 mm / 24h (LOW)
    - Moderate: 15.6 - 64.4 mm / 24h (MODERATE)
    - Heavy: 64.5 - 115.5 mm / 24h (HIGH)
    - Very heavy: > 115.5 mm / 24h (HIGH)
- Compounding factors (Open-Meteo meteorological parameters):
    - Wind gusts >= 65 km/h or sustained speed >= 50 km/h: adds power-line /
      infrastructure failure hazard modifier (+1.5 score).
    - Moderate wind gusts >= 45 km/h: (+0.8 modifier).
    - WMO Convective Storm codes (95, 96, 99: Thunderstorms; 82: Violent showers):
      imposes a HIGH risk floor (score >= 7.0).

MANDATORY SAFETY RULE:
Low risk (GREEN) indicates low hazard relative to the threshold;
it must NEVER be described as absolute safety.
"""

from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import math
import sys
from typing import Any, Optional

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


@dataclass
class PrecipitationInput:
    """Normalized input parameters matching Open-Meteo hazard feed."""
    latitude: float
    longitude: float
    time: str
    precipitation_mm: float
    time_window_hours: int = 1
    wind_speed_kmh: float = 0.0
    wind_gusts_kmh: float = 0.0
    weather_code: Optional[int] = None
    precipitation_probability: float = 100.0


@dataclass
class PrecipitationRiskResult:
    """Internal calculation output containing deterministic evaluation details."""
    location: dict[str, float]
    time: str
    precipitation_mm: float
    time_window: str
    risk_level: str          # "HIGH" | "MODERATE" | "LOW"
    severity_score: float    # 0.0 to 10.0
    badge: str               # 🔴 | 🟡 | 🟢
    summary: str
    factors: list[str]
    disclaimer: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# WMO Weather Interpretation Codes relevant to precipitation & convective storms
WMO_DESCRIPTIONS: dict[int, str] = {
    0: "Clear sky",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm (slight or moderate)",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def compute_rainfall_polygon(
    latitude: float,
    longitude: float,
    severity_score: float,
    num_points: int = 16,
) -> dict[str, Any]:
    """
    Computes a valid GeoJSON Polygon representing the precipitation and runoff impact zone.

    The radius scales deterministically with severity score:
    - Low Risk (< 4.0): ~3 km to 5 km buffer (localized shower / grid cell footprint).
    - Moderate Risk (4.0 - 6.9): ~5 km to 10 km buffer (drainage / waterlogging zone).
    - High Risk (>= 7.0): ~10 km to 20 km buffer (flash flood catchment & storm cell).

    Coordinates are formatted as [longitude, latitude] in accordance with RFC 7946 GeoJSON.
    The first and last coordinate points are identical to form a closed linear ring.
    """
    score = max(0.0, min(10.0, float(severity_score)))
    if score < 4.0:
        radius_km = 3.0 + (score / 4.0) * 2.0
    elif score < 7.0:
        radius_km = 5.0 + ((score - 4.0) / 3.0) * 5.0
    else:
        radius_km = 10.0 + ((score - 7.0) / 3.0) * 10.0

    lat_clamped = max(-89.9, min(89.9, float(latitude)))
    lon_clamped = float(longitude)

    lat_rad = math.radians(lat_clamped)
    km_per_deg_lat = 111.32
    # Prevent division by zero near poles
    cos_lat = max(0.0001, math.cos(lat_rad))
    km_per_deg_lon = 111.32 * cos_lat

    delta_lat = radius_km / km_per_deg_lat
    delta_lon = radius_km / km_per_deg_lon

    ring: list[list[float]] = []
    for i in range(num_points):
        angle = (2.0 * math.pi * i) / num_points
        pt_lat = round(lat_clamped + delta_lat * math.sin(angle), 6)
        pt_lon = round(lon_clamped + delta_lon * math.cos(angle), 6)
        # Normalize longitude to [-180, 180]
        pt_lon = round((pt_lon + 180.0) % 360.0 - 180.0, 6)
        ring.append([pt_lon, pt_lat])

    # Close the polygon ring as required by GeoJSON specification
    ring.append(ring[0])

    return {
        "type": "Polygon",
        "coordinates": [ring],
    }


def calculate_precipitation_risk(data: PrecipitationInput) -> PrecipitationRiskResult:
    """
    Computes deterministic risk level, severity score, and contributing factors.

    Returns:
        PrecipitationRiskResult with risk_level in {"HIGH", "MODERATE", "LOW"}
    """
    precip = max(0.0, data.precipitation_mm)
    window = 1 if data.time_window_hours <= 1 else 24
    factors: list[str] = []

    # 1. Base score derived from precipitation intensity
    if window == 1:
        # Hourly rate (mm/h)
        if precip < 2.5:
            # Light rain
            base_score = (precip / 2.5) * 3.5
            factors.append(f"Precipitation of {precip:.1f} mm/h is classified as light.")
        elif precip < 7.6:
            # Moderate rain
            base_score = 4.0 + ((precip - 2.5) / (7.6 - 2.5)) * 2.5
            factors.append(f"Precipitation of {precip:.1f} mm/h is moderate.")
        elif precip < 15.0:
            # Heavy rain
            base_score = 7.0 + ((precip - 7.6) / (15.0 - 7.6)) * 1.5
            factors.append(f"Precipitation of {precip:.1f} mm/h is heavy.")
        else:
            # Torrential / Violent rain, >15.0 mm/h
            base_score = 8.5 + min(1.5, ((precip - 15.0) / 15.0) * 1.5)
            factors.append(f"Precipitation of {precip:.1f} mm/h is torrential, high flash-flood risk.")
    else:
        # 24-Hour accumulation (mm/24h)
        if precip < 15.5:
            base_score = (precip / 15.5) * 3.5
            factors.append(f"24h accumulated rainfall ({precip:.1f} mm) is light (< 15.5 mm).")
        elif precip < 64.5:
            base_score = 4.0 + ((precip - 15.5) / (64.5 - 15.5)) * 2.5
            factors.append(f"24h accumulated rainfall ({precip:.1f} mm) is moderate (15.5 - 64.5 mm).")
        elif precip < 115.5:
            base_score = 7.0 + ((precip - 64.5) / (115.5 - 64.5)) * 1.5
            factors.append(f"24h accumulated rainfall ({precip:.1f} mm) is heavy (64.5 - 115.5 mm).")
        else:
            base_score = 8.5 + min(1.5, ((precip - 115.5) / 50.0) * 1.5)
            factors.append(f"24h accumulated rainfall ({precip:.1f} mm) is very heavy (> 115.5 mm).")

    score = base_score

    # 2. Compounding Factor: Wind speed & gusts
    # High winds combine with rain to cause downed power lines, structural risk, and drainage blockages
    if data.wind_gusts_kmh >= 65.0 or data.wind_speed_kmh >= 50.0:
        wind_modifier = 1.5
        score += wind_modifier
        factors.append(
            f"Compounding wind hazard: speed {data.wind_speed_kmh:.1f} km/h, gusts {data.wind_gusts_kmh:.1f} km/h "
            f"(+{wind_modifier:.1f} severity due to power line / grid disruption hazard)."
        )
    elif data.wind_gusts_kmh >= 45.0 or data.wind_speed_kmh >= 35.0:
        wind_modifier = 0.8
        score += wind_modifier
        factors.append(
            f"Moderate wind gusts ({data.wind_gusts_kmh:.1f} km/h) compound localized storm risk (+{wind_modifier:.1f})."
        )

    # 3. Compounding Factor: WMO Weather Code (Thunderstorms / Violent Showers)
    if data.weather_code is not None:
        code_desc = WMO_DESCRIPTIONS.get(data.weather_code, f"Code {data.weather_code}")
        if data.weather_code in (95, 96, 99):  # Thunderstorms
            score = max(score + 1.0, 7.0)  # Thunderstorms elevate risk floor to HIGH
            factors.append(f"Severe weather code: {code_desc} (WMO {data.weather_code}) imposes HIGH risk floor.")
        elif data.weather_code == 82:  # Violent rain showers
            score = max(score, 7.0)
            factors.append("Violent rain showers (WMO 82) imposes HIGH risk floor.")
        else:
            factors.append(f"Weather condition: {code_desc} (WMO {data.weather_code}).")

    # 4. Precipitation probability factor (if forecast uncertainty is low/high)
    if data.precipitation_probability < 40.0 and precip > 0:
        factors.append(f"Precipitation probability is {data.precipitation_probability:.0f}% (forecast uncertainty noted).")

    # Clamp severity score to [0.0, 10.0]
    final_score = round(min(10.0, max(0.0, score)), 2)

    # 5. Determine SafeGrid Risk Level
    if final_score >= 7.0:
        risk_level = "HIGH"
        badge = "🔴 High Risk"
        summary = (
            "Severe precipitation / storm conditions. High probability of localized flooding, "
            "waterlogging, and power grid / infrastructural disruptions."
        )
    elif final_score >= 4.0:
        risk_level = "MODERATE"
        badge = "🟡 Moderate / Potential Risk"
        summary = (
            "Moderate precipitation observed. Potential for road water accumulation, "
            "minor drainage overflows, and localized grid stress."
        )
    else:
        risk_level = "LOW"
        badge = "🟢 Low Risk"
        summary = (
            "Light or negligible precipitation. Standard environmental conditions. "
            "Minimal infrastructural hazard expected."
        )

    disclaimer = "Green / Low Risk indicates low hazard relative to threshold; it does NOT imply absolute safety."

    return PrecipitationRiskResult(
        location={"latitude": data.latitude, "longitude": data.longitude},
        time=data.time,
        precipitation_mm=precip,
        time_window=f"{window} hour(s)",
        risk_level=risk_level,
        severity_score=final_score,
        badge=badge,
        summary=summary,
        factors=factors,
        disclaimer=disclaimer,
    )


def process_precipitation_hazard(hazard: dict[str, Any] | str | Any) -> dict[str, Any]:
    """
    Primary engine function for precipitation risk calculation.

    Accepts:
    - Normalized hazard dictionary from Person 1 (ingestion layer) or Person 4 (database).
    - String representation (JSON or literal dict string, with optional 'output :' prefix).
    - Pydantic Hazard model.

    Returns:
    - Structured dictionary containing risk_level, severity_score, GeoJSON affected_area,
      and rich metadata ready for Person 3 (Frontend / MapLibre) and Person 4 (Database).
    """
    # 1. Handle string inputs (JSON, python dict literals, or terminal logs)
    if isinstance(hazard, str):
        cleaned = hazard.strip()
        if cleaned.startswith("output :"):
            cleaned = cleaned[len("output :"):].strip()
        try:
            data = json.loads(cleaned)
        except Exception:
            try:
                data = ast.literal_eval(cleaned)
            except Exception as exc:
                raise ValueError(f"Could not parse input string into a dictionary: {exc}")
    elif hasattr(hazard, "model_dump"):
        data = hazard.model_dump()
    elif isinstance(hazard, dict):
        data = hazard.copy()
    else:
        data = dict(hazard)

    hazard_id = str(data.get("id") or data.get("hazard_id") or "open-meteo:unknown")
    source = str(data.get("source") or "open_meteo")

    # 2. Timestamp extraction
    ts = data.get("timestamp") or data.get("time")
    if isinstance(ts, datetime):
        time_str = ts.isoformat()
    elif ts:
        time_str = str(ts)
    else:
        time_str = datetime.now(timezone.utc).isoformat()

    # 3. Coordinate extraction with fallback to GeoJSON location
    lat = data.get("latitude")
    lon = data.get("longitude")
    if lat is None or lon is None:
        loc = data.get("location")
        if isinstance(loc, dict):
            coords = loc.get("coordinates", [0.0, 0.0])
            lon, lat = coords[0], coords[1]
        elif hasattr(loc, "coordinates"):
            coords = loc.coordinates
            lon, lat = coords[0], coords[1]
    latitude = float(lat if lat is not None else 0.0)
    longitude = float(lon if lon is not None else 0.0)

    # 4. Specific data extraction (handles raw dict or JSON string from DB)
    specific = data.get("specific_data")
    if isinstance(specific, str):
        try:
            specific = json.loads(specific)
        except Exception:
            specific = {}
    elif not isinstance(specific, dict):
        specific = {}

    # 5. Precipitation amount in mm
    precip_mm = specific.get("precipitation_mm")
    if precip_mm is None:
        precip_mm = data.get("precipitation_mm", data.get("rain", 0.0))
    precip_mm = max(0.0, float(precip_mm if precip_mm is not None else 0.0))

    # 6. Time window (hours)
    window = specific.get("time_window_hours") or data.get("time_window_hours") or data.get("duration") or 1
    if isinstance(window, str):
        digits = "".join(c for c in window if c.isdigit())
        window_int = int(digits) if digits else 1
    else:
        try:
            window_int = int(window)
            if window_int <= 0:
                window_int = 1
        except (ValueError, TypeError):
            window_int = 1

    # 7. Secondary / compounding parameters (with graceful defaults for missing fields)
    wind_spd = float(specific.get("wind_speed_kmh") or data.get("wind_speed_kmh") or 0.0)
    wind_gst = float(specific.get("wind_gusts_kmh") or data.get("wind_gusts_kmh") or 0.0)

    wmo_code = specific.get("weather_code") or data.get("weather_code") or data.get("wmo")
    if wmo_code is not None:
        try:
            wmo_code = int(wmo_code)
        except (ValueError, TypeError):
            wmo_code = None

    prob = data.get("probability")
    if prob is None:
        prob = specific.get("precipitation_probability") or data.get("precipitation_probability")
    if prob is not None:
        try:
            prob_float = float(prob)
            if 0.0 < prob_float <= 1.0:
                prob_float *= 100.0
        except (ValueError, TypeError):
            prob_float = 100.0
    else:
        prob_float = 100.0

    # 8. Build typed input and compute risk
    calc_input = PrecipitationInput(
        latitude=latitude,
        longitude=longitude,
        time=time_str,
        precipitation_mm=precip_mm,
        time_window_hours=window_int,
        wind_speed_kmh=wind_spd,
        wind_gusts_kmh=wind_gst,
        weather_code=wmo_code,
        precipitation_probability=prob_float,
    )
    result = calculate_precipitation_risk(calc_input)

    # 9. Compute GeoJSON affected area polygon
    affected_area = compute_rainfall_polygon(latitude, longitude, result.severity_score)

    calc_now = datetime.now(timezone.utc).isoformat()
    notes = (
        f"Precipitation: {result.precipitation_mm:.1f} mm ({result.time_window}). "
        f"Score: {result.severity_score:.2f}/10. {result.summary}"
    )

    # 10. Formulate final output dictionary for Person 3 (Frontend) & Person 4 (Database)
    return {
        "id": hazard_id,
        "hazard_id": hazard_id,
        "hazard_type": "rainfall",
        "source": source,
        "timestamp": time_str,
        "latitude": latitude,
        "longitude": longitude,
        "risk_level": result.risk_level,
        "severity_score": result.severity_score,
        "badge": result.badge,
        "calculated_at": calc_now,
        "affected_area": affected_area,
        "summary": result.summary,
        "factors": result.factors,
        "disclaimer": result.disclaimer,
        "notes": notes,
    }


def main() -> None:
    raw_input: Optional[str] = None

    # Check command-line argument
    if len(sys.argv) > 1 and sys.argv[1].strip():
        raw_input = sys.argv[1].strip()
    # Check piped stdin input
    elif not sys.stdin.isatty():
        piped = sys.stdin.read().strip()
        if piped:
            raw_input = piped

    if raw_input:
        output = process_precipitation_hazard(raw_input)
    else:
        # Default representative payload from Open-Meteo ingestion pipeline
        hazard_data = {
            'id': 'open-meteo:12.9716:77.5946:2026-10-08T00:00',
            'hazard_type': 'rainfall',
            'source': 'open_meteo',
            'timestamp': '2026-10-08T00:00:00',
            'latitude': 12.9716,
            'longitude': 77.5946,
            'magnitude': None,
            'probability': 0.0,
            'duration': None,
            'specific_data': {'precipitation_mm': 0.0},
            'created_at': '2026-10-08T05:21:21.446033+00:00',
        }
        output = process_precipitation_hazard(hazard_data)

    print("output :")
    print(output)


if __name__ == "__main__":
    main()