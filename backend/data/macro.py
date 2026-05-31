import requests
import os
from datetime import datetime, timedelta

FRED_API_KEY = os.getenv("FRED_API_KEY", "")
FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"

# Klíčové makro ukazatele pro NASDAQ
MACRO_SERIES = {
    "Sazba Fedu": "FEDFUNDS",
    "Inflace CPI (YoY)": "CPIAUCSL",
    "Jádrová PCE": "PCEPILFE",
    "Nezaměstnanost": "UNRATE",
    "Výnos 10Y dluhopis": "DGS10",
    "Výnos 2Y dluhopis": "DGS2",
    "Růst HDP": "A191RL1Q225SBEA",
    "ISM Manufacturing": "MANEMP",
}


def get_macro_data() -> list:
    if not FRED_API_KEY or FRED_API_KEY == "your_key_here":
        return _get_macro_fallback()

    results = []
    for name, series_id in MACRO_SERIES.items():
        try:
            resp = requests.get(
                FRED_BASE,
                params={
                    "series_id": series_id,
                    "api_key": FRED_API_KEY,
                    "file_type": "json",
                    "limit": 2,
                    "sort_order": "desc",
                },
                timeout=5,
            )
            data = resp.json()
            obs = data.get("observations", [])
            if obs:
                latest = obs[0]
                previous = obs[1] if len(obs) > 1 else None
                current_val = float(latest["value"]) if latest["value"] != "." else None
                prev_val = float(previous["value"]) if previous and previous["value"] != "." else None
                change = round(current_val - prev_val, 3) if current_val and prev_val else None
                results.append({
                    "name": name,
                    "value": current_val,
                    "previous": prev_val,
                    "change": change,
                    "date": latest["date"],
                    "trend": "up" if change and change > 0 else "down" if change and change < 0 else "flat",
                })
        except Exception as e:
            results.append({"name": name, "error": str(e)})
    return results


def _get_macro_fallback() -> list:
    # Vrátí statická data pokud není FRED klíč — jako placeholder
    return [
        {"name": "Sazba Fedu", "value": 5.33, "previous": 5.33, "change": 0.0, "date": "2024-12-01", "trend": "flat", "note": "Přidej FRED API klíč pro živá data"},
        {"name": "Výnos 10Y dluhopis", "value": 4.25, "previous": 4.20, "change": 0.05, "date": "2024-12-01", "trend": "up", "note": "Přidej FRED API klíč pro živá data"},
        {"name": "Inflace CPI (YoY)", "value": 2.7, "previous": 2.6, "change": 0.1, "date": "2024-11-01", "trend": "up", "note": "Přidej FRED API klíč pro živá data"},
        {"name": "Nezaměstnanost", "value": 4.2, "previous": 4.1, "change": 0.1, "date": "2024-11-01", "trend": "up", "note": "Přidej FRED API klíč pro živá data"},
    ]


def get_upcoming_events() -> list:
    # Ekonomický kalendář — klíčové události pro NASDAQ
    return [
        {"event": "Zasedání FOMC", "impact": "HIGH", "description": "Rozhodnutí Fedu o úrokových sazbách"},
        {"event": "Inflace CPI", "impact": "HIGH", "description": "Index spotřebitelských cen"},
        {"event": "NFP (Pracovní trh)", "impact": "HIGH", "description": "Non-Farm Payrolls — počet nových pracovních míst"},
        {"event": "HDP (předběžný)", "impact": "MEDIUM", "description": "Odhad růstu ekonomiky USA"},
        {"event": "Jádrová PCE", "impact": "HIGH", "description": "Preferovaný inflační ukazatel Fedu"},
        {"event": "ISM Services PMI", "impact": "MEDIUM", "description": "Aktivita v sektoru služeb"},
    ]
