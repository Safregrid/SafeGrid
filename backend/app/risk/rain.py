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

Presentation (badges, summaries, disclaimers, human-readable factor prose) is
NOT produced here — that belongs to the API/frontend layer.

Scientific Threshold Justifications:
- Hourly precipitation thresholds follow the India Meteorological Department (IMD)
  rainfall spell-rate classification (IMD expresses intensity as a spell rate in
  cm/h; 1 cm = 10 mm):
    - Light spell: < 1 cm/h (< 10 mm/h) -> LOW (Score 0.0 - 3.9)
    - Moderate spell: 1 - 2 cm/h (10 - 20 mm/h) -> MODERATE (Score 4.0 - 6.9)
    - Intense spell: 2 - 3 cm/h (20 - 30 mm/h) -> HIGH (Score 7.0 - 8.4)
    - Very intense spell: 3 - 5 cm/h (30 - 50 mm/h) -> HIGH (Score 8.5 - 9.4)
    - Extremely intense spell: 5 - 10 cm/h (50 - 100 mm/h) -> HIGH (Score 9.5 - 10.0)
    - Cloudburst: > 10 cm/h (> 100 mm/h) -> HIGH (Score 10.0)
- 24-Hour accumulation thresholds follow the India Meteorological Department (IMD)
  standard rainfall classification:
    - Light: < 15.5 mm / 24h (LOW)
    - Moderate: 15.6 - 64.4 mm / 24h (MODERATE)
    - Heavy: 64.5 - 115.5 mm / 24h (HIGH)
    - Very heavy: > 115.5 mm / 24h (HIGH)
- Weather codes are the WMO weather interpretation codes (WW, WMO-No. 306) as
  returned by Open-Meteo; IMD, as a WMO member, uses the same synoptic codes.
- Compounding factors (Open-Meteo meteorological parameters):
    - Wind gusts >= 65 km/h or sustained speed >= 50 km/h: adds power-line /
      infrastructure failure hazard modifier (+1.5 score).
    - Moderate wind gusts >= 45 km/h: (+0.8 modifier).
    - WMO Convective Storm codes (95, 96, 97, 99: Thunderstorms; 82: Violent showers):
      imposes a HIGH risk floor (score >= 7.0).

MANDATORY SAFETY RULE:
Low risk (GREEN) indicates low hazard relative to the threshold;
it must NEVER be described as absolute safety.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import sys
from typing import Any, Optional

from app.risk.geometry import compute_rainfall_polygon


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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# WMO Weather Interpretation Codes (WW) as returned by Open-Meteo's weather_code
# field (source: WMO-No. 306 / Open-Meteo docs). IMD, as a WMO member, uses the
# same synoptic codes. Descriptions updated for accuracy on 2026-10-11.
WMO_DESCRIPTIONS: dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    97: "Heavy thunderstorm",
    99: "Thunderstorm with heavy hail",
}


def calculate_precipitation_risk(data: PrecipitationInput) -> PrecipitationRiskResult:
    """
    Computes deterministic risk level and severity score.

    Returns:
        PrecipitationRiskResult with risk_level in {"HIGH", "MODERATE", "LOW"}
    """
    precip = max(0.0, data.precipitation_mm)
    window = 1 if data.time_window_hours <= 1 else 24

    # 1. Base score derived from precipitation intensity
    if window == 1:
        # Hourly intensity (mm/h) — IMD rainfall spell-rate classification,
        # expressed in cm/h by IMD and converted to mm/h (1 cm = 10 mm).
        if precip < 10.0:
            # Light spell (< 1 cm/h)
            base_score = (precip / 10.0) * 3.9
        elif precip < 20.0:
            # Moderate spell (1 - 2 cm/h)
            base_score = 4.0 + ((precip - 10.0) / 10.0) * 2.9
        elif precip < 30.0:
            # Intense spell (2 - 3 cm/h)
            base_score = 7.0 + ((precip - 20.0) / 10.0) * 1.4
        elif precip < 50.0:
            # Very intense spell (3 - 5 cm/h)
            base_score = 8.5 + ((precip - 30.0) / 20.0) * 0.9
        elif precip < 100.0:
            # Extremely intense spell (5 - 10 cm/h)
            base_score = 9.5 + ((precip - 50.0) / 50.0) * 0.5
        else:
            # Cloudburst (> 10 cm/h)
            base_score = 10.0
    else:
        # 24-Hour accumulation (mm/24h)
        if precip < 15.5:
            base_score = (precip / 15.5) * 3.5
        elif precip < 64.5:
            base_score = 4.0 + ((precip - 15.5) / (64.5 - 15.5)) * 2.5
        elif precip < 115.5:
            base_score = 7.0 + ((precip - 64.5) / (115.5 - 64.5)) * 1.5
        else:
            base_score = 8.5 + min(1.5, ((precip - 115.5) / 50.0) * 1.5)

    score = base_score

    # 2. Compounding factor: wind speed & gusts
    # High winds combine with rain to cause downed power lines, structural risk,
    # and drainage blockages.
    if data.wind_gusts_kmh >= 65.0 or data.wind_speed_kmh >= 50.0:
        score += 1.5
    elif data.wind_gusts_kmh >= 45.0 or data.wind_speed_kmh >= 35.0:
        score += 0.8

    # 3. Compounding factor: WMO weather code (thunderstorms / violent showers)
    if data.weather_code is not None:
        if data.weather_code in (95, 96, 97, 99):  # thunderstorms
            score = max(score + 1.0, 7.0)  # thunderstorms elevate the HIGH floor
        elif data.weather_code == 82:  # violent rain showers
            score = max(score, 7.0)

    # Clamp severity score to [0.0, 10.0]
    final_score = round(min(10.0, max(0.0, score)), 2)

    # 4. Determine SafeGrid risk level (thresholds: docs/RISK_MODEL.md)
    if final_score >= 7.0:
        risk_level = "HIGH"
    elif final_score >= 4.0:
        risk_level = "MODERATE"
    else:
        risk_level = "LOW"

    return PrecipitationRiskResult(
        location={"latitude": data.latitude, "longitude": data.longitude},
        time=data.time,
        precipitation_mm=precip,
        time_window=f"{window} hour(s)",
        risk_level=risk_level,
        severity_score=final_score,
    )


def process_precipitation_hazard(hazard: dict[str, Any] | Any) -> dict[str, Any]:
    """
    Primary engine function for precipitation risk calculation.

    Accepts a normalized hazard dictionary (from Person 1's ingestion layer or
    Person 4's database) or a Pydantic Hazard model. String parsing is a CLI
    concern and lives in main(); the engine takes structured input only.

    Returns a structured dictionary with risk_level, severity_score, GeoJSON
    affected_area, and metadata ready for Person 3 (Frontend / MapLibre) and
    Person 4 (Database).
    """
    # 1. Normalize the input into a plain dict
    if hasattr(hazard, "model_dump"):
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
    window = specific.get("time_window_hours") or data.get("time_window_hours") or 1
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

    # Probability is a percentage (0-100) across providers. Treat every value as
    # a percentage and clamp it — never guess a 0-1 fraction (that misreads a
    # genuine 1% as 100%).
    prob = data.get("probability")
    if prob is None:
        prob = specific.get("precipitation_probability")
    if prob is None:
        prob = data.get("precipitation_probability")
    try:
        prob_float = float(prob)
    except (TypeError, ValueError):
        prob_float = 100.0
    prob_float = min(100.0, max(0.0, prob_float))

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
        f"Score: {result.severity_score:.2f}/10."
    )

    # 10. Formulate final output dictionary for Person 3 (Frontend) & Person 4 (Database)
    return {
        "hazard_id": hazard_id,
        "hazard_type": "rainfall",
        "source": source,
        "timestamp": time_str,
        "latitude": latitude,
        "longitude": longitude,
        "risk_level": result.risk_level,
        "severity_score": result.severity_score,
        "calculated_at": calc_now,
        "affected_area": affected_area,
        "notes": notes,
    }


def main() -> None:
    # UTF-8 output so emoji badges render on Windows consoles (CLI entry only).
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

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
        try:
            parsed = json.loads(raw_input)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Could not parse input as JSON: {exc}")
        output = process_precipitation_hazard(parsed)
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
            'specific_data': {'precipitation_mm': 0.0},
            'created_at': '2026-10-08T05:21:21.446033+00:00',
        }
        output = process_precipitation_hazard(hazard_data)

    print("output :")
    print(output)


if __name__ == "__main__":
    main()