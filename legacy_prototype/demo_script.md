# 🎬 Demo Walkthrough Script (2-Minute Laptop Presentation)

> **Audience**: Hackathon Judges / Mentors / Farmers  
> **Goal**: Show how a farmer picks a crop, enters sowing date, and gets ONE clear recommendation with reasons in Marathi/Hindi/English.

---

## ⏱️ Step-by-Step Presentation Flow (120 Seconds)

### **0:00 - 0:20 | The Problem & Setup**
1. **Open the browser** at `http://localhost:8501`.
2. **Opening Hook**:
   > *"In Maharashtra's Nashik-Dhule onion belt, timing is everything. A farmer harvesting two days too late during unseasonal rain loses 30% of their crop to rot. Harvesting without knowing mandi trends loses ₹200–300 per quintal. Farmers don't want 20 charts or complex dashboards — they need ONE clear answer: When to harvest, where to sell, and why."*

### **0:20 - 0:45 | Marathi / Multilingual Experience**
1. Point to the top right language selector: **मराठी (Marathi)** is default.
2. Switch to **English** or **हिंदी (Hindi)** to show instant localization across all metrics, alerts, and justifications.
3. Show the **Hero Card**:
   - Highlight the **Green Badge**: *IDEAL HARVEST WINDOW*
   - Highlight the **Recommended Window**: *e.g., 29 Sep 2026 — 03 Oct 2026*
   - Highlight the **Target Mandi**: *Lasalgaon APMC (₹2,560/qtl modal rate)*
   - Read the **Plain-Language Reason**:
     > *"Weather is dry and sunny over next 5 days, perfect for field curing. Sell at Lasalgaon because it offers the highest regional rates and strong upward momentum."*

### **0:45 - 1:15 | Testing Dynamic Situations (The Demo Presets)**
1. Click the **"Rain Alert"** preset in the sidebar:
   - Notice the Hero card turns **🟡 AMBER**.
   - The engine automatically changes the advice:
     > *"Rain alert (18.5mm) arriving in 2 days. Harvest immediately before rain hits, and move bulbs to a covered curing shed. Sell at Lasalgaon where rates are firm."*
   - Show the **7-Day Weather Strip**: Day 3 clearly flags in Red with 18.5mm rainfall.
2. Click the **"Early (कच्चा)"** preset in the sidebar:
   - The card advises waiting:
     > *"Crop has only been in the field for 65 days. Wait until bulb maturity and neck fall (५०% मान पडणे). Premature harvesting reduces bulb size and storage life."*

### **1:15 - 1:45 | Mandi Trends & Data Seams**
1. Scroll down to the **14-Day Mandi Price Trajectory Chart**:
   - Show how Lasalgaon (red line) leads Pimpalgaon, Nashik, and Dhule.
   - Show the summary comparison table with 7-day price trends (+4.5% to +5.2%) and projected price bands.
2. Open the sidebar **"Mandi Data Seam"** expander:
   - Explain: *"This uses a decoupled seam. Right now it runs on validated Agmarknet APMC records and live Open-Meteo weather. When data.gov.in APIs are available or a farmer uploads local CSVs, the engine seamlessly ingests it."*

### **1:45 - 2:00 | Wrap Up & Value Proposition**
- *"One crop, one region, zero fluff. Built with Python and Streamlit, running completely locally on this laptop, and validated with automated tests. Ready to deploy to every farmer's phone."*
