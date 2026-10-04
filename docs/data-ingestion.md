# Provider-Independent Data Ingestion Architecture

## 1. Purpose of the Ingestion Layer

The data ingestion layer provides a decoupled, boundary-protected entry point for external agricultural measurements and market intelligence. Real-world weather APIs (e.g. Open-Meteo, IMD, AccuWeather) and commodity platforms (e.g. Agmarknet, eNAM) evolve independently: their data contracts, field nomenclatures, serialization schemas, and transport protocols frequently shift.

The ingestion layer isolates the core domain, models, decision rules, and SQLite persistence layer from external API churn by introducing an explicit translation and validation boundary.

---

## 2. Ingestion Pipeline & Data Flow

Data flows strictly in one direction from the outside inward:

```text
External Provider (API/JSON)
        ↓
Provider Adapter (Pure transformation)
        ↓
Normalized Data (Strict, decoupled data contracts)
        ↓
Validation Layer (Physical bounds & domain sanity checks)
        ↓
Existing Observation Service (Business authorization & parent existence)
        ↓
Existing Repository (SQLAlchemy ORM operations)
        ↓
SQLite Database
```

At no point does an external provider payload directly map onto an ORM model or issue a direct database query.

---

## 3. Normalized Data Contracts

All normalized data models reside in `app.ingestion.common.types` and have **zero dependencies** on SQLAlchemy or FastAPI.

### Weather Normalization Contract (`NormalizedWeatherData`)

| Field | Type | Unit / Range | Description |
|---|---|---|---|
| `observed_at` | `datetime` | ISO-8601 UTC / local | Physical timestamp of the measurement |
| `temperature_c` | `float` | -50.0°C to +60.0°C | Ambient dry-bulb temperature in Celsius |
| `humidity_percent` | `float` | 0.0% to 100.0% | Relative humidity percentage |
| `rainfall_mm` | `float` | ≥ 0.0 mm | Cumulative precipitation |
| `wind_speed_kmh` | `float` | ≥ 0.0 km/h | Mean wind speed |

### Market Normalization Contract (`NormalizedMarketData`)

| Field | Type | Unit / Constraints | Description |
|---|---|---|---|
| `crop_name` | `str` | Non-empty string | Standardized commodity name (e.g. "Onion") |
| `market_name` | `str` | Non-empty string | Standardized APMC market name (e.g. "Lasalgaon APMC") |
| `observed_date` | `date` | Valid calendar date | Date of market price quote |
| `price` | `float` | > 0.0 (strictly positive) | Modal or traded price quote |
| `unit` | `str` | Non-empty string | Trading quantity unit (e.g. "Rs/Quintal") |

---

## 4. Provider Interface Responsibilities

Provider interfaces are defined as Python Abstract Base Classes (`ABC`):

- **`WeatherProvider`** (`app.ingestion.weather.base`):
  - Declares `fetch_current_observation(location_query: str) -> NormalizedWeatherData`.
  - Declares `fetch_historical_observations(location_query: str, start_date: date, end_date: date) -> List[NormalizedWeatherData]`.
- **`MarketProvider`** (`app.ingestion.market.base`):
  - Declares `fetch_market_observations(crop_name: str, market_name: Optional[str]) -> List[NormalizedMarketData]`.

### Provider Rules:
1. **Single Responsibility**: Communicates only with the external service or transport layer.
2. **Zero Database Couplings**: Absolutely no imports of SQLAlchemy, database sessions, or ORM models.
3. **Zero Web Framework Couplings**: Absolutely no imports of FastAPI, router primitives, or HTTP request objects.
4. **Normalized Return Types**: Always outputs validated `NormalizedWeatherData` or `NormalizedMarketData`.

---

## 5. Validation Responsibility

Validation occurs at two complementary stages:

1. **Syntactic & Physical Validation (Ingestion Layer)**:
   - Enforced by `NormalizedWeatherData` and `NormalizedMarketData` during ingestion instantiation.
   - Rejects non-physical readings (e.g. humidity > 100%, negative rainfall, negative wind speed, price ≤ 0).
   - Rejects non-finite values (NaN, Inf) and empty string whitespace.
2. **Domain & Referential Validation (Service Layer)**:
   - Enforced by `WeatherObservationService` and `MarketObservationService`.
   - Verifies referenced entities exist in the database (e.g., verifying `farm_id` exists before attaching weather data).
   - Coordinates transactional persistence via repositories.

---

## 6. Why Providers Must Remain Independent from the Database

- **Pluggability**: Switching from a simulated provider to Open-Meteo or IMD requires writing only a single adapter class without touching domain tables, schemas, or tests.
- **Resilience**: If an external provider introduces breaking schema changes (e.g. renaming `temp` to `ambient_temp_k`), only the provider adapter changes. The rest of the platform remains insulated.
- **Testability**: Ingestion adapters can be tested with plain Python dictionaries and unit tests without requiring SQLite files or database connections.
- **Safety**: Prevents external API responses from creating invalid, corrupted, or unvalidated rows in the database.

---

## 7. Real Weather Provider: Open-Meteo (`OpenMeteoAdapter`)

The platform integrates Open-Meteo for physical atmospheric measurements:
- **Endpoint**: `https://api.open-meteo.com/v1/forecast`
- **Authentication**: Free for non-commercial open data queries; no API key required.
- **Parameters**: `latitude`, `longitude`, `hourly=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m`, `past_days=1`, `forecast_days=1`.
- **Normalization**: Maps Open-Meteo hourly/current fields directly into `NormalizedWeatherData`.
- **Location Policy**: Requires explicit numeric coordinates (`lat, lon`). In accordance with system safety principles, automatic geocoding is disabled, preventing inaccurate coordinate guessing or dependency on paid/unreliable geocoders.

---

## 8. Real Market Provider: Government of India OGD Mandi Data (`OgdMandiAdapter`)

The platform defines a clean adapter boundary for the official Government of India Open Government Data (data.gov.in) Agricultural Commodities dataset:
- **Resource Title**: Current Daily Price and Arrival of Agricultural Commodities
- **Resource ID**: `9ef84268-d588-465a-a308-a864a43d0070`
- **Base Endpoint**: `https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070`
- **Data Normalization**: Translates official OGD JSON records (`commodity`, `market`, `arrival_date`, `modal_price`) to `NormalizedMarketData` with standard unit `Rs/Quintal`.

### Documented Blocker & Security Compliance:
1. **Mandatory API Key Requirement**: The official OGD platform requires all API consumers to supply a registered personal API key via the `api-key` query parameter. Without this key, requests fail with authorization errors (`401 Unauthorized` / connection refused).
2. **Platform Safety Protocol**:
   - No personal credentials or secrets are committed to the codebase or hard-coded.
   - The platform strictly rejects unauthenticated scraping of HTML portals (e.g. Agmarknet) or reverse-engineering private mobile APIs.
   - No unofficial third-party APIs are substituted.
3. **Operational Configuration**:
   - The adapter safely inspects the `OGD_API_KEY` environment variable.
   - When configured, it connects directly to the official endpoint and normalizes data.
   - When unconfigured, it cleanly raises a descriptive error explaining that `OGD_API_KEY` is required by data.gov.in, preventing unauthorized network traffic and preserving system integrity.

---

## 9. Duplicate Protection Strategy

To prevent accidental double-recording during manual synchronizations without mutating the database schema:
1. **Weather Observations**:
   - Identical `(farm_id, observed_at)` pairs are checked against `WeatherObservationRepository.find_by_farm_and_time`.
   - In-batch duplicates are filtered via a tracking set before insertion.
   - Duplicates increment `records_rejected` and are skipped.
2. **Market Observations**:
   - Identical `(crop_name, market_name, observed_date)` triples are checked against `MarketObservationRepository.find_by_crop_market_date`.
   - In-batch duplicates are filtered via a tracking set before insertion.
   - Duplicates increment `records_rejected` and are skipped.
3. **Zero Schema Alteration**: Existing SQLite tables and foreign key constraints remain completely unmodified.

---

## 10. Manual Synchronization Endpoints

Synchronizations are purely on-demand and user-initiated (no background daemons or scheduled cron jobs):
- `POST /api/v1/farms/{farm_id}/weather/sync`: Pulls recent Open-Meteo observations for a farm's coordinates.
- `POST /api/v1/market/sync`: Pulls commodity quotes from Government of India OGD Mandi API.
- Standard response contract:
  ```json
  {
    "provider": "open-meteo",
    "records_received": 24,
    "records_accepted": 24,
    "records_rejected": 0,
    "message": "Weather sync complete for Farm #1."
  }
  ```
