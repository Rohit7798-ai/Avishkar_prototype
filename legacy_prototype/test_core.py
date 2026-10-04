"""
test_core.py - Self-contained assert-based verification for onion decision engine.
Run directly with: python test_core.py
"""

from datetime import date, timedelta
from core import (
    calculate_harvest_window,
    _score_weather_risk,
    MandiDataProvider,
    evaluate_harvest_decision,
    UI_TEXT
)


def test_harvest_window_calculation():
    print("[1/5] Testing harvest window calculation...")
    today = date(2026, 9, 29)
    
    # 1. Optimal maturity for Rabi (125 days)
    sowing_date_optimal = today - timedelta(days=120)
    res_opt = calculate_harvest_window(sowing_date_optimal, season="Rabi", ref_date=today)
    assert res_opt["readiness"] == "Optimal", f"Expected Optimal, got {res_opt['readiness']}"
    assert res_opt["days_elapsed"] == 120
    assert res_opt["earliest_date"] == sowing_date_optimal + timedelta(days=115)
    assert res_opt["optimal_date"] == sowing_date_optimal + timedelta(days=125)

    # 2. Premature crop (50 days)
    sowing_date_premature = today - timedelta(days=50)
    res_pre = calculate_harvest_window(sowing_date_premature, season="Rabi", ref_date=today)
    assert res_pre["readiness"] == "Premature", f"Expected Premature, got {res_pre['readiness']}"

    # 3. Overdue crop (145 days)
    sowing_date_overdue = today - timedelta(days=145)
    res_over = calculate_harvest_window(sowing_date_overdue, season="Rabi", ref_date=today)
    assert res_over["readiness"] == "Overdue", f"Expected Overdue, got {res_over['readiness']}"
    print("  -> Harvest window calculations verified successfully.")


def test_weather_risk_scoring():
    print("[2/5] Testing weather risk classification...")
    # Clear / Dry
    lvl_clear, _ = _score_weather_risk(0.0, 5)
    assert lvl_clear == "GREEN", f"Expected GREEN for dry weather, got {lvl_clear}"

    # Light showers / moderate rain
    lvl_amber, _ = _score_weather_risk(3.5, 60)
    assert lvl_amber == "AMBER", f"Expected AMBER for moderate rain, got {lvl_amber}"

    # Heavy downpour (>10mm)
    lvl_red, _ = _score_weather_risk(14.0, 90)
    assert lvl_red == "RED", f"Expected RED for downpour, got {lvl_red}"
    print("  -> Weather risk scoring verified successfully.")


def test_mandi_data_provider():
    print("[3/5] Testing MandiDataProvider seam...")
    provider = MandiDataProvider()
    summaries = provider.get_mandi_summaries()
    assert "Lasalgaon" in summaries, "Lasalgaon must be in summaries"
    assert "Pimpalgaon" in summaries, "Pimpalgaon must be in summaries"
    assert summaries["Lasalgaon"]["current_modal"] > 0
    assert summaries["Lasalgaon"]["expected_range"][0] <= summaries["Lasalgaon"]["current_modal"] <= summaries["Lasalgaon"]["expected_range"][2]

    best_mandi, info = provider.find_best_mandi("Nashik")
    assert best_mandi == "Lasalgaon", f"Lasalgaon should be highest paying mandi in seed data, got {best_mandi}"
    print("  -> MandiDataProvider verified successfully.")


def test_decision_engine_scenarios():
    print("[4/5] Testing decision engine scenarios...")
    today = date(2026, 9, 29)

    # Scenario A: Optimal crop + sunny weather -> GREEN
    sowing_ready = today - timedelta(days=120)
    clear_weather = [
        {"date": today + timedelta(days=i), "precipitation_mm": 0.0, "precipitation_prob": 0, "risk_level": "GREEN", "risk_desc": "Sunny"}
        for i in range(7)
    ]
    dec_a = evaluate_harvest_decision(sowing_ready, region="Nashik", season="Rabi", ref_date=today, weather_override=clear_weather)
    assert dec_a["status"] == "GREEN", f"Expected GREEN for optimal crop and clear weather, got {dec_a['status']}"
    assert dec_a["recommended_mandi"] == "Lasalgaon"
    assert len(dec_a["reasons"]["en"]) > 20
    assert len(dec_a["reasons"]["mr"]) > 20
    assert len(dec_a["reasons"]["hi"]) > 20

    # Scenario B: Premature crop -> AMBER (Wait)
    sowing_early = today - timedelta(days=50)
    dec_b = evaluate_harvest_decision(sowing_early, region="Nashik", season="Rabi", ref_date=today, weather_override=clear_weather)
    assert dec_b["status"] == "AMBER"
    assert "Wait until" in dec_b["reasons"]["en"]

    # Scenario C: Approaching severe rain -> AMBER (Harvest early before rain hits)
    rainy_weather = [
        {"date": today + timedelta(days=0), "precipitation_mm": 0.0, "precipitation_prob": 5, "risk_level": "GREEN", "risk_desc": "Dry"},
        {"date": today + timedelta(days=1), "precipitation_mm": 0.0, "precipitation_prob": 10, "risk_level": "GREEN", "risk_desc": "Dry"},
        {"date": today + timedelta(days=2), "precipitation_mm": 18.0, "precipitation_prob": 90, "risk_level": "RED", "risk_desc": "Heavy Rain"}
    ]
    dec_c = evaluate_harvest_decision(sowing_ready, region="Nashik", season="Rabi", ref_date=today, weather_override=rainy_weather)
    assert dec_c["status"] == "AMBER"
    assert "Rain alert" in dec_c["reasons"]["en"]
    print("  -> Decision engine scenarios verified successfully.")


def test_localization_keys():
    print("[5/5] Testing localization keys...")
    for lang in ["en", "mr", "hi"]:
        assert lang in UI_TEXT, f"Missing language: {lang}"
        assert "title" in UI_TEXT[lang]
        assert "verdict_title" in UI_TEXT[lang]
        assert "harvest_window" in UI_TEXT[lang]
        assert "best_mandi" in UI_TEXT[lang]
    print("  -> Localization dictionary verified successfully.")


if __name__ == "__main__":
    print("=== Running Onion Decision Engine Self-Check ===")
    test_harvest_window_calculation()
    test_weather_risk_scoring()
    test_mandi_data_provider()
    test_decision_engine_scenarios()
    test_localization_keys()
    print("=== ALL TESTS PASSED! ===")
