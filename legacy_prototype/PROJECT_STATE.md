# PROJECT_STATE.md - Onion Harvest & Mandi Decision Engine

## Status: Working Demo Ready (v1.0.0)

### Current Architecture & Components
- **Stack**: Python 3.12+ with Streamlit, Plotly, Pandas, Requests.
- **`core.py`**:
  - `calculate_harvest_window`: Computes earliest (50% neck fall), optimal, and latest harvest dates using ICAR-DOGR Maharashtra onion cycles (Kharif, Rangda, Rabi).
  - `fetch_weather_forecast`: Live Open-Meteo REST integration for Nashik & Dhule coordinates (`20.00N, 73.78E` and `20.90N, 74.77E`) with deterministic offline fallback.
  - `_score_weather_risk`: Scored thresholds for field drying and neck curing (0mm = Green/Ideal, 0.1-4.9mm = Amber/Caution, >=5mm = Red/Rot Risk).
  - `MandiDataProvider`: Clean seam loading representative Agmarknet prices for Lasalgaon, Pimpalgaon, Nashik, Dhule, and Malegaon APMCs with 7-day momentum and expected price intervals.
  - `evaluate_harvest_decision`: Main engine combining harvest maturity, 7-day weather safety, and mandi spreads into a unified Green/Amber/Red verdict with plain-language explanations.
  - `UI_TEXT`: Multilingual catalog supporting Marathi (मराठी), Hindi (हिंदी), and English.
- **`app.py`**: Streamlit dashboard with language switch, quick presets, single-verdict hero card, 7-day weather forecast strip, and 14-day APMC price trajectory comparison chart.
- **`test_core.py`**: Assert-based self-check test suite passing 100% without external test frameworks.
- **`data/mandi_rates.json`**: Seed dataset containing daily modal, min, max, and arrivals for the top 5 regional onion APMCs.

### Seams & Extensibility
1. **Agmarknet Live Seam**: `MandiDataProvider` is decoupled in `core.py`. Real `data.gov.in` API responses or custom CSVs can be passed directly or uploaded in the app drawer.
2. **Weather API**: Fully functional with free Open-Meteo REST endpoint (no keys needed), automatically falling back if offline.

### Verified Steps
- [x] Step 1: Scaffold, README, .env.example, PROJECT_STATE.md
- [x] Step 2: Harvest window from sowing date and crop calendar
- [x] Step 3: Weather risk scoring (Open-Meteo)
- [x] Step 4: Mandi price outlook (14-day history, momentum, ranges)
- [x] Step 5: Unified decision engine with plain-language reasoning
- [x] Step 6: Farmer screen (Green/Amber/Red hero, language toggle, charts)
- [x] Step 7: Tests (`test_core.py`) and demo walkthrough script (`demo_script.md`)
