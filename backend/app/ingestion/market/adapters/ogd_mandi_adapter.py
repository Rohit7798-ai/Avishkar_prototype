"""
Government of India Open Government Data (OGD / data.gov.in) Mandi Rate Provider Adapter.
Fetches official APMC daily commodity price quotes and arrival records.
Decoupled entirely from database models, ORM, and web transport layers.
"""

from datetime import date, datetime
import json
from typing import List, Optional
import urllib.error
import urllib.parse
import urllib.request

from app.core.config import settings
from app.ingestion.common.types import NormalizedMarketData
from app.ingestion.market.base import MarketProvider


class OgdMandiAdapter(MarketProvider):
    """
    Adapter implementing MarketProvider contract for Government of India OGD (data.gov.in)
    Agricultural Commodities API (Resource ID: 9ef84268-d588-465a-a308-a864a43d0070).
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.base_url = (base_url or settings.OGD_MANDI_API_URL).rstrip("/")
        self.api_key = api_key if api_key is not None else settings.OGD_API_KEY
        self.timeout = timeout if timeout is not None else settings.OGD_TIMEOUT_SECONDS

    @property
    def provider_name(self) -> str:
        return "data.gov.in-ogd"

    def fetch_market_observations(
        self,
        crop_name: str,
        market_name: Optional[str] = None,
        limit: int = 50,
    ) -> List[NormalizedMarketData]:
        """
        Fetches official mandi rate records for a crop commodity from data.gov.in.

        Args:
            crop_name: Commodity name (e.g. "Onion", "Tomato").
            market_name: Optional APMC market yard filter (e.g. "Lasalgaon").
            limit: Maximum records to request (default 50).

        Returns:
            List[NormalizedMarketData]: Validated normalized market price quotes.

        Raises:
            ValueError: If crop_name is missing or invalid.
            RuntimeError: If API key is missing, or network/HTTP transport fails.
        """
        if not crop_name or not crop_name.strip():
            raise ValueError("crop_name must be a non-empty string.")

        if not self.api_key:
            raise RuntimeError(
                "Government of India Open Government Data (data.gov.in) API key is required "
                "but not configured. Set OGD_API_KEY in the environment to connect to the "
                "official Mandi Price API. No unofficial scraping or third-party APIs are permitted."
            )

        params = {
            "api-key": self.api_key,
            "format": "json",
            "limit": str(max(1, min(limit, 100))),
            "filters[commodity]": crop_name.strip(),
        }
        if market_name and market_name.strip():
            params["filters[market]"] = market_name.strip()

        query_string = urllib.parse.urlencode(params)
        url = f"{self.base_url}?{query_string}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "FarmerDecisionSupport/1.0",
                "Accept": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"OGD API HTTP error {exc.code}: {exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"OGD API connection failure: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise ValueError(f"OGD API returned invalid JSON: {exc}") from exc
        except Exception as exc:
            raise RuntimeError(f"OGD API request failure: {exc}") from exc

        return self._normalize_records_payload(payload, default_crop=crop_name)

    def _normalize_records_payload(self, payload: dict, default_crop: str) -> List[NormalizedMarketData]:
        """
        Parses OGD JSON records array into NormalizedMarketData list.
        """
        if not isinstance(payload, dict):
            raise ValueError("Malformed OGD payload: top-level element is not an object.")

        # Check for OGD failure response
        status = payload.get("status")
        if status and str(status).lower() in ("failure", "error"):
            msg = payload.get("message", "OGD API reported an error.")
            raise RuntimeError(f"OGD API error response: {msg}")

        records = payload.get("records")
        if records is None or not isinstance(records, list):
            raise ValueError("Malformed OGD response: 'records' array is missing.")

        normalized_list: List[NormalizedMarketData] = []
        for r in records:
            if not isinstance(r, dict):
                continue

            # Field names in OGD data can be lowercase or title case
            crop = (
                r.get("commodity")
                or r.get("Commodity")
                or default_crop
            )
            market = (
                r.get("market")
                or r.get("Market")
                or "General Market"
            )
            raw_date = r.get("arrival_date") or r.get("Arrival_Date") or r.get("date")
            raw_price = (
                r.get("modal_price")
                or r.get("Modal_Price")
                or r.get("price")
            )

            if not raw_date or raw_price is None:
                continue

            # Parse date
            parsed_date: Optional[date] = None
            if isinstance(raw_date, str):
                raw_date = raw_date.strip()
                # Try DD/MM/YYYY
                for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
                    try:
                        parsed_date = datetime.strptime(raw_date, fmt).date()
                        break
                    except ValueError:
                        continue
            elif isinstance(raw_date, date):
                parsed_date = raw_date

            if not parsed_date:
                continue

            # Parse price
            try:
                price = float(raw_price)
                if price <= 0:
                    continue
            except (ValueError, TypeError):
                continue

            # Standard unit for OGD mandi rates is Rs/Quintal
            unit = r.get("unit") or "Rs/Quintal"

            try:
                item = NormalizedMarketData(
                    crop_name=str(crop).strip(),
                    market_name=str(market).strip(),
                    observed_date=parsed_date,
                    price=price,
                    unit=str(unit).strip(),
                )
                normalized_list.append(item)
            except ValueError:
                continue

        return normalized_list
