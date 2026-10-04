"""
app.py - Onion Harvest & Mandi Decision Engine (Nashik/Dhule Belt).
Built with Streamlit. Provides clear, single-verdict advice in Marathi, Hindi, and English.
"""

from datetime import date, datetime, timedelta
import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from core import (
    calculate_harvest_window,
    fetch_weather_forecast,
    evaluate_harvest_decision,
    MandiDataProvider,
    REGIONAL_COORDS,
    CROP_CALENDAR,
    UI_TEXT
)

# Page configuration
st.set_page_config(
    page_title="कांदा काढणी व बाजार सल्लागार | Onion Harvest Advisor",
    page_icon="🧅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom styling for high contrast field-friendly demo presentation
st.markdown("""
<style>
    .main-header {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        margin-bottom: 0.5rem;
    }
    .hero-verdict {
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    }
    .hero-green {
        background-color: #E8F5E9;
        border: 2px solid #2E7D32;
        color: #1B5E20;
    }
    .hero-amber {
        background-color: #FFF8E1;
        border: 2px solid #F57F17;
        color: #E65100;
    }
    .hero-red {
        background-color: #FFEBEE;
        border: 2px solid #C62828;
        color: #B71C1C;
    }
    .metric-pill {
        display: inline-block;
        background: white;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 600;
        margin-right: 8px;
        border: 1px solid #ddd;
    }
    .weather-card {
        background: #fdfdfd;
        border-radius: 8px;
        padding: 10px;
        border: 1px solid #e0e0e0;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# -----------------
# 1. State & Language Selection
# -----------------
if "lang" not in st.session_state:
    st.session_state["lang"] = "mr"  # Default to Marathi for Maharashtra farmer demo

top_col1, top_col2 = st.columns([3, 1])
with top_col2:
    selected_lang = st.radio(
        "🌐 भाषा / Language",
        options=["mr", "hi", "en"],
        format_func=lambda x: {"mr": "मराठी (Marathi)", "hi": "हिंदी (Hindi)", "en": "English"}[x],
        horizontal=True,
        index=["mr", "hi", "en"].index(st.session_state["lang"])
    )
    st.session_state["lang"] = selected_lang

t = UI_TEXT[st.session_state["lang"]]

with top_col1:
    st.title(f"🧅 {t['title']}")
    st.caption(f"📍 {t['subtitle']}")

# -----------------
# 2. Sidebar Inputs
# -----------------
st.sidebar.header(f"⚙️ {t['farmer_inputs']}")

# Region dropdown
region_options = list(REGIONAL_COORDS.keys())
selected_region = st.sidebar.selectbox(
    t["region_label"],
    options=region_options,
    index=0
)

# Season dropdown
season_options = list(CROP_CALENDAR.keys())
selected_season = st.sidebar.selectbox(
    t["season_label"],
    options=season_options,
    index=2  # Rabi as default
)

# Demo presets for rapid laptop walkthrough
st.sidebar.markdown("---")
st.sidebar.subheader("⚡ Quick Demo Presets (लॅपटॉप डेमो)")
preset_cols = st.sidebar.columns(3)

today = date.today()
default_sowing = today - timedelta(days=120)

if preset_cols[0].button("Ready (तयार)"):
    st.session_state["sowing_date"] = today - timedelta(days=120)
    st.session_state["sim_rain"] = False
if preset_cols[1].button("Rain Alert"):
    st.session_state["sowing_date"] = today - timedelta(days=118)
    st.session_state["sim_rain"] = True
if preset_cols[2].button("Early (कच्चा)"):
    st.session_state["sowing_date"] = today - timedelta(days=65)
    st.session_state["sim_rain"] = False

if "sowing_date" not in st.session_state:
    st.session_state["sowing_date"] = default_sowing

sowing_date = st.sidebar.date_input(
    t["sowing_date_label"],
    value=st.session_state["sowing_date"],
    max_value=today,
    min_value=today - timedelta(days=200)
)

# Data Seam / Test Overrides in Sidebar Expander
with st.sidebar.expander(f"🛠️ {t['seam_expander']}", expanded=False):
    sim_rain = st.checkbox(
        t["simulate_rain"],
        value=st.session_state.get("sim_rain", False)
    )
    st.session_state["sim_rain"] = sim_rain

    uploaded_mandi_file = st.file_uploader("Upload Agmarknet CSV / JSON", type=["json", "csv"])
    st.info("Agmarknet API Seam: Currently using authenticated cached APMC data with automatic JSON parser.")

# -----------------
# 3. Decision Engine Processing
# -----------------
# Optional weather simulation if toggled
simulated_weather = None
if sim_rain:
    simulated_weather = [
        {"date": today, "precipitation_mm": 0.0, "precipitation_prob": 5, "risk_level": "GREEN", "risk_desc": "Dry"},
        {"date": today + timedelta(days=1), "precipitation_mm": 1.5, "precipitation_prob": 25, "risk_level": "GREEN", "risk_desc": "Cloudy"},
        {"date": today + timedelta(days=2), "precipitation_mm": 18.5, "precipitation_prob": 90, "risk_level": "RED", "risk_desc": "Heavy Downpour (18.5mm)"},
        {"date": today + timedelta(days=3), "precipitation_mm": 8.0, "precipitation_prob": 70, "risk_level": "RED", "risk_desc": "Rain & Wet Field (8mm)"},
        {"date": today + timedelta(days=4), "precipitation_mm": 0.5, "precipitation_prob": 15, "risk_level": "AMBER", "risk_desc": "Drying"},
        {"date": today + timedelta(days=5), "precipitation_mm": 0.0, "precipitation_prob": 0, "risk_level": "GREEN", "risk_desc": "Clear"},
        {"date": today + timedelta(days=6), "precipitation_mm": 0.0, "precipitation_prob": 0, "risk_level": "GREEN", "risk_desc": "Clear"}
    ]

decision = evaluate_harvest_decision(
    sowing_date=sowing_date,
    region=selected_region,
    season=selected_season,
    ref_date=today,
    weather_override=simulated_weather
)

status = decision["status"]
rec_start, rec_end = decision["recommended_window"]
best_mandi = decision["recommended_mandi"]
best_info = decision["mandi_details"]
harvest_info = decision["harvest_info"]
reason = decision["reasons"][st.session_state["lang"]]

# -----------------
# 4. Hero Recommendation Card (Farmer Screen)
# -----------------
status_class = f"hero-{status.lower()}"
status_badge_text = t[f"status_{status.lower()}"]
status_emoji = {"GREEN": "🟢", "AMBER": "🟡", "RED": "🔴"}[status]

st.markdown(f"""
<div class="hero-verdict {status_class}">
    <div style="font-size: 1.1rem; font-weight: 700; text-transform: uppercase; margin-bottom: 8px;">
        {status_emoji} {status_badge_text}
    </div>
    <div style="font-size: 1.8rem; font-weight: 800; line-height: 1.3; margin-bottom: 12px;">
        📅 {t['harvest_window']}: <u>{rec_start.strftime('%d %b %Y')}</u> — <u>{rec_end.strftime('%d %b %Y')}</u>
    </div>
    <div style="font-size: 1.4rem; font-weight: 700; margin-bottom: 15px;">
        🏪 {t['best_mandi']}: <b>{best_mandi} APMC</b> &nbsp;|&nbsp; 
        💰 {t['expected_price']}: ₹{best_info['current_modal']} / क्विंटल (अपेक्षित पट्टा: ₹{best_info['expected_range'][0]} - ₹{best_info['expected_range'][2]})
    </div>
    <div style="font-size: 1.15rem; background: white; padding: 14px 18px; border-radius: 8px; border-left: 5px solid #333; color: #222;">
        💡 <b>सल्ला / Why:</b> {reason}
    </div>
</div>
""", unsafe_allow_html=True)

# Key Crop Metrics Row
m_col1, m_col2, m_col3, m_col4 = st.columns(4)
m_col1.metric(t["crop_age"], f"{harvest_info['days_elapsed']} {t['days']}")
m_col2.metric("५०% मान पडणे (Earliest)", harvest_info["earliest_date"].strftime("%d %b"))
m_col3.metric("उत्तम पक्वता (Optimal)", harvest_info["optimal_date"].strftime("%d %b"))
m_col4.metric(t["crop_stage"], harvest_info["readiness"])

st.markdown("---")

# -----------------
# 5. Weather & Curing Safety Row (7-Day Forecast)
# -----------------
st.subheader(f"🌦️ {t['weather_title']}")
st.caption(f"Open-Meteo live endpoint: Lat {REGIONAL_COORDS[selected_region]['lat']}, Lon {REGIONAL_COORDS[selected_region]['lon']}")

w_cols = st.columns(7)
for idx, w_day in enumerate(decision["weather_days"][:7]):
    col = w_cols[idx]
    w_date = w_day["date"]
    precip = w_day["precipitation_mm"]
    risk = w_day["risk_level"]
    risk_color = "#2E7D32" if risk == "GREEN" else ("#F57F17" if risk == "AMBER" else "#C62828")
    card_bg = "#F1F8E9" if risk == "GREEN" else ("#FFFDE7" if risk == "AMBER" else "#FFEBEE")

    with col:
        st.markdown(f"""
        <div style="background-color: {card_bg}; border: 1px solid {risk_color}; border-radius: 8px; padding: 8px; text-align: center;">
            <div style="font-weight: 700; font-size: 0.95rem;">{w_date.strftime('%a')}</div>
            <div style="font-size: 0.8rem; color: #666;">{w_date.strftime('%d %b')}</div>
            <div style="font-size: 1.3rem; margin: 4px 0;">{'☀️' if precip == 0 else ('🌧️' if precip >= 5 else '🌦️')}</div>
            <div style="font-size: 0.85rem; font-weight: 700; color: {risk_color};">{precip} mm</div>
            <div style="font-size: 0.75rem; color: #444;">{w_day.get('temp_max', 32):.0f}° / {w_day.get('temp_min', 20):.0f}°C</div>
            <div style="font-size: 0.7rem; font-weight: 600; margin-top: 4px; color: {risk_color};">
                {'सुरक्षित (Safe)' if risk == 'GREEN' else ('सावधान (Warning)' if risk == 'AMBER' else 'धोका (Rain Risk)')}
            </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# -----------------
# 6. Mandi Price Outlook & Comparative Chart (14-Day Trajectory)
# -----------------
st.subheader(f"📈 {t['mandi_title']}")

chart_col, table_col = st.columns([3, 2])

with chart_col:
    # Build DataFrame from all mandis for comparative plotting
    records = []
    for mandi_name, m_data in decision["all_mandis"].items():
        for r in m_data["history"]:
            records.append({
                "Date": r["date"],
                "Mandi": mandi_name,
                "Modal Price (₹/Qtl)": r["modal"],
                "Min Price": r["min"],
                "Max Price": r["max"]
            })
    df_prices = pd.DataFrame(records)

    fig = px.line(
        df_prices,
        x="Date",
        y="Modal Price (₹/Qtl)",
        color="Mandi",
        markers=True,
        title="14-Day Daily Modal Rates Comparison (Nashik / Dhule APMCs)",
        color_discrete_map={
            "Lasalgaon": "#D32F2F",
            "Pimpalgaon": "#1976D2",
            "Nashik": "#388E3C",
            "Dhule": "#F57C00",
            "Malegaon": "#7B1FA2"
        }
    )
    fig.update_layout(
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis_title="",
        yaxis_title="₹ / Quintal"
    )
    st.plotly_chart(fig, use_container_width=True)

with table_col:
    st.markdown("##### 🏛️ बाजार समिती दर तुलना (Mandi Comparison)")
    mandi_table_rows = []
    for mandi_name, m_data in decision["all_mandis"].items():
        is_rec = " ⭐" if mandi_name == best_mandi else ""
        mandi_table_rows.append({
            "Mandi (बाजार)": f"{mandi_name}{is_rec}",
            "Modal Rate (₹)": f"₹{m_data['current_modal']}",
            "7-Day Trend": f"{'+' if m_data['pct_change_7d'] > 0 else ''}{m_data['pct_change_7d']}%",
            "Expected Range (₹)": f"₹{m_data['expected_range'][0]} - ₹{m_data['expected_range'][2]}"
        })
    df_mandi_table = pd.DataFrame(mandi_table_rows)
    st.dataframe(df_mandi_table, use_container_width=True, hide_index=True)
    st.caption("⭐ = शिफारस केलेली बाजार समिती (Highest net realization)")

# Footer
st.markdown("---")
st.caption(f"🌾 {t['data_source_badge']} • Ponytail Architecture: Lean, Zero-bloat, Resilient.")
