# 🧅 Onion Harvest & Mandi Decision Engine (Nashik / Dhule Belt)

> A lightweight, field-tested decision support tool for onion farmers in Maharashtra. Given sowing date and region, it computes the exact harvest window, scores 7-day weather curing risk, analyzes local APMC mandi price trends, and delivers **one clear actionable recommendation** in Marathi, Hindi, or English.

---

## 🚀 Key Features

1. **Clear Single-Verdict Hero Screen**:
   - Green / Amber / Red indicator for harvest safety and field curing.
   - Specific recommended harvest dates (e.g. *15 Oct — 19 Oct*).
   - Recommended APMC market (e.g. *Lasalgaon APMC*) with expected price range.
   - Plain-language reason in **Marathi (मराठी)**, **Hindi (हिंदी)**, or **English**.
2. **Crop Calendar Intelligence**:
   - Calibrated for Kharif, Late Kharif (Rangda), and Rabi onion cycles in Maharashtra (ICAR-DOGR standards).
   - Tracks vegetative, early neck fall (५०% मान पडणे), and optimal bulb maturity.
3. **Live Open-Meteo Weather Scoring**:
   - Fetches 7-day precipitation, humidity, wind, and temperatures for Nashik and Dhule.
   - Highlights rain hazards that cause fungal neck rot or field waterlogging during curing.
4. **Agmarknet Mandi Price Outlook**:
   - 14-day trailing modal price analysis for Lasalgaon, Pimpalgaon Baswant, Nashik, Dhule, and Malegaon.
   - Computes price momentum and transparent projected price bands.
   - Features a clean pluggable data seam for swapping in live `data.gov.in` feeds or CSV files.
5. **Zero Bloat / Ponytail Architecture**:
   - Built with Python standard library + Streamlit + Requests + Pandas + Plotly.
   - No unnecessary abstractions or heavy dependencies.
   - Assert-based self-check test file (`test_core.py`).

---

## 📦 Quick Start

### 1. Requirements
Ensure Python 3.10+ is installed with `streamlit`, `pandas`, `requests`, and `plotly`:
```bash
pip install streamlit pandas requests plotly
```

### 2. Run Core Tests
```bash
python test_core.py
```

### 3. Launch the Web App
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 💻 2-Minute Demo Presets
In the app sidebar, three quick presets are provided for rapid laptop demonstrations:
- **Ready (तयार)**: Demonstrates an optimal maturity crop with clear 5-day weather and rising Lasalgaon rates (`GREEN` verdict).
- **Rain Alert (पाऊस इशारा)**: Demonstrates incoming heavy rain on Day 3, prompting the engine to advise early harvest and sheltered curing (`AMBER` warning).
- **Early (कच्चा कांदा)**: Demonstrates a 65-day premature crop, advising the farmer to wait for neck fall to preserve bulb weight (`AMBER` wait).

---

## 📁 Repository Structure
```
├── app.py                 # Streamlit web application & farmer interface
├── core.py                # Crop calendar, Open-Meteo scoring, mandi analysis & decision engine
├── test_core.py           # Single runnable assert-based verification test suite
├── data/
│   └── mandi_rates.json   # Seed Agmarknet mandi rates (Lasalgaon, Pimpalgaon, Nashik, Dhule, etc.)
├── demo_script.md         # Step-by-step laptop presentation script
├── PROJECT_STATE.md       # Architectural notes and milestones
├── README.md              # Project documentation
└── .env.example           # Environment template
```
