"""
Dataset loading and validation module for historical agricultural data.
Decoupled entirely from database models and web framework logic.
"""

from datetime import date, datetime
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


def get_default_dataset_path() -> Path:
    """Returns absolute path to default historical mandi dataset: data/raw/mandi_rates.json."""
    current_dir = Path(__file__).resolve().parent
    # ml/datasets -> ml -> app -> backend -> root
    project_root = current_dir.parent.parent.parent.parent
    return project_root / "data" / "raw" / "mandi_rates.json"


def load_raw_mandi_dataset(file_path: Optional[str | Path] = None) -> List[Dict[str, Any]]:
    """
    Loads, validates, and cleans the historical mandi dataset.

    Args:
        file_path: Path to mandi_rates.json file (defaults to data/raw/mandi_rates.json).

    Returns:
        List of validated, deduplicated, chronologically sorted observation records.

    Raises:
        FileNotFoundError: If the data file does not exist.
        ValueError: If required columns or fields are missing or malformed.
    """
    target_path = Path(file_path) if file_path else get_default_dataset_path()

    if not target_path.exists():
        raise FileNotFoundError(f"Historical dataset file not found at: {target_path}")

    try:
        with open(target_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Historical dataset contains invalid JSON: {exc}") from exc

    if not isinstance(raw_data, dict):
        raise ValueError("Historical dataset root must be a JSON object.")

    # Validate top-level schema
    required_top_keys = ["commodity", "unit", "mandis"]
    for k in required_top_keys:
        if k not in raw_data:
            raise ValueError(f"Missing required top-level attribute '{k}' in historical dataset.")

    commodity = str(raw_data["commodity"]).strip()
    unit = str(raw_data["unit"]).strip()
    mandis_dict = raw_data["mandis"]

    if not isinstance(mandis_dict, dict) or not mandis_dict:
        raise ValueError("Attribute 'mandis' must be a non-empty dictionary of market yards.")

    cleaned_records: List[Dict[str, Any]] = []
    seen_keys: Set[Tuple[str, date]] = set()

    for market_name, market_info in mandis_dict.items():
        if not isinstance(market_info, dict):
            raise ValueError(f"Market '{market_name}' payload must be a dictionary.")

        district = str(market_info.get("district", "Unknown")).strip()
        try:
            distance_km = float(market_info.get("distance_km_nashik", 0.0))
        except (ValueError, TypeError):
            raise ValueError(f"Invalid distance_km_nashik for market '{market_name}'.")

        rates_list = market_info.get("recent_rates")
        if not isinstance(rates_list, list):
            raise ValueError(f"Market '{market_name}' is missing 'recent_rates' list.")

        for idx, item in enumerate(rates_list):
            if not isinstance(item, dict):
                raise ValueError(f"Rate record at index {idx} in market '{market_name}' is not an object.")

            required_rate_fields = ["date", "min", "modal", "max", "arrivals_tonnes"]
            for rf in required_rate_fields:
                if rf not in item:
                    raise ValueError(
                        f"Rate record at index {idx} in market '{market_name}' missing required field '{rf}'."
                    )

            # Date parsing
            raw_date = str(item["date"]).strip()
            try:
                obs_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
            except ValueError as exc:
                raise ValueError(
                    f"Invalid date format '{raw_date}' in market '{market_name}'. Expected YYYY-MM-DD."
                ) from exc

            # Numeric conversion & sanity check
            try:
                min_p = float(item["min"])
                modal_p = float(item["modal"])
                max_p = float(item["max"])
                arrivals = float(item["arrivals_tonnes"])
            except (ValueError, TypeError) as exc:
                raise ValueError(
                    f"Non-numeric values in rate record '{raw_date}' for market '{market_name}': {exc}"
                ) from exc

            if min_p <= 0 or modal_p <= 0 or max_p <= 0:
                raise ValueError(
                    f"Prices must be strictly positive in record '{raw_date}' for market '{market_name}'."
                )

            if not (min_p <= modal_p <= max_p):
                raise ValueError(
                    f"Price consistency violation (min <= modal <= max failed) in record '{raw_date}' for '{market_name}'."
                )

            if arrivals < 0:
                raise ValueError(
                    f"Arrivals cannot be negative in record '{raw_date}' for market '{market_name}'."
                )

            # Deduplication
            dedup_key = (market_name.strip().lower(), obs_date)
            if dedup_key in seen_keys:
                continue  # Skip duplicate record safely
            seen_keys.add(dedup_key)

            cleaned_records.append({
                "commodity": commodity,
                "market": market_name.strip(),
                "district": district,
                "distance_km_nashik": round(distance_km, 1),
                "date": obs_date,
                "min_price": round(min_p, 2),
                "modal_price": round(modal_p, 2),
                "max_price": round(max_p, 2),
                "arrivals_tonnes": round(arrivals, 2),
                "unit": unit,
            })

    # Sort deterministically by market and chronological date
    cleaned_records.sort(key=lambda r: (r["market"], r["date"]))
    return cleaned_records
