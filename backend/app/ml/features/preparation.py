"""
Feature preparation and chronological splitting for market price forecasting.
Enforces zero data leakage and strict temporal ordering.
"""

from collections import defaultdict
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple


def prepare_market_price_features(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Constructs feature-target samples from consecutive daily mandi observations.

    Target:
        next_modal_price: The modal mandi rate recorded on day t+1 (Rs/Quintal).

    Input Features (at day t):
        current_modal_price: Modal price on day t.
        price_spread: Intraday spread (max_price - min_price) on day t.
        arrivals_tonnes: Quantity traded/arrived in tonnes on day t.
        day_of_week: Day of week index (0=Monday ... 6=Sunday).

    Returns:
        List of feature-target records.
    """
    if not records:
        return []

    # Group by market to construct time-series lags strictly within the same market
    market_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in records:
        market_groups[r["market"]].append(r)

    samples: List[Dict[str, Any]] = []

    for market_name, m_records in market_groups.items():
        # Sort chronologically
        m_records.sort(key=lambda x: x["date"])

        for i in range(len(m_records) - 1):
            curr = m_records[i]
            nxt = m_records[i + 1]

            # Verify consecutive daily progression (day t and day t+1)
            date_diff = (nxt["date"] - curr["date"]).days
            if date_diff != 1:
                # If there is a calendar gap, do not form an invalid t+1 prediction pair
                continue

            current_modal = float(curr["modal_price"])
            price_spread = round(float(curr["max_price"]) - float(curr["min_price"]), 2)
            arrivals = float(curr["arrivals_tonnes"])
            target = float(nxt["modal_price"])

            samples.append({
                "market": market_name,
                "date": curr["date"],
                "next_date": nxt["date"],
                # Features
                "current_modal_price": current_modal,
                "price_spread": price_spread,
                "arrivals_tonnes": arrivals,
                "day_of_week": curr["date"].weekday(),
                # Target
                "target_next_modal_price": target,
            })

    # Sort all samples chronologically by observation date
    samples.sort(key=lambda s: (s["date"], s["market"]))
    return samples


def split_train_validation_chronological(
    samples: List[Dict[str, Any]],
    split_ratio: float = 0.75,
    split_date: Optional[date] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Splits samples chronologically into training and validation sets.
    Never shuffles; strictly preserves temporal causality.

    Args:
        samples: Output from prepare_market_price_features.
        split_ratio: Fraction of dates to allocate to training (default 0.75).
        split_date: Explicit calendar cutoff date. Samples on or before this date are in train.

    Returns:
        Tuple of (train_samples, val_samples).
    """
    if not samples:
        return [], []

    # Identify unique distinct dates sorted chronologically
    distinct_dates = sorted(list(set(s["date"] for s in samples)))

    if len(distinct_dates) < 2:
        # Not enough temporal steps to split into train and validation
        return samples, []

    if split_date is None:
        split_idx = max(1, int(len(distinct_dates) * split_ratio))
        cutoff_date = distinct_dates[split_idx - 1]
    else:
        cutoff_date = split_date

    train = [s for s in samples if s["date"] <= cutoff_date]
    val = [s for s in samples if s["date"] > cutoff_date]

    return train, val
