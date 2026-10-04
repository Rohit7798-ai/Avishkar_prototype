# Farmer Decision Support System

A production-quality, modular-monolith decision support application for agricultural producers and farmers.

This repository represents **Milestone 1**: the foundational architecture, modular separation, and health verification seam.

---

## 1. Architecture Overview

The system is organized as a clean **modular monolith** with decoupled frontend and backend layers, prepared for scalable business services, data repositories, and persistent models:

```
farmer-decision-system/
├── frontend/                 # React + Vite + Tailwind CSS Single Page Application
│   ├── src/
│   │   ├── components/       # Reusable presentation components
│   │   ├── pages/            # Page-level containers / routes
│   │   ├── services/         # API integration services (e.g. api.js)
│   │   ├── hooks/            # Custom React hooks
│   │   ├── types/            # Type definitions & JSDoc schemas
│   │   ├── utils/            # General helpers & formatters
│   │   ├── App.jsx           # Root layout & health status verification
│   │   ├── index.css         # Tailwind base, components & utilities
│   │   └── main.jsx          # React DOM entrypoint
│   ├── index.html            # Vite HTML template
│   ├── package.json          # Frontend dependencies & scripts
│   ├── tailwind.config.js    # Tailwind CSS configuration
│   ├── postcss.config.js     # PostCSS setup
│   ├── vite.config.js        # Vite build & dev server config
│   └── .env.example          # Frontend environment variables template
├── backend/                  # Python + FastAPI REST API
│   ├── app/
│   │   ├── api/              # API routing & endpoint definitions
│   │   │   ├── endpoints/    # Individual route modules (e.g. health.py)
│   │   │   └── api_v1.py     # Aggregated API router
│   │   ├── core/             # Central configuration (Pydantic Settings, CORS)
│   │   ├── models/           # SQLAlchemy database entities (Milestone 2+)
│   │   ├── schemas/          # Pydantic request/response validation schemas
│   │   ├── services/         # Domain business logic (Milestone 2+)
│   │   ├── repositories/     # Data access layer (Milestone 2+)
│   │   └── main.py           # FastAPI application factory (no business logic)
│   ├── requirements.txt      # Minimal Python backend dependencies
│   └── .env.example          # Backend environment variables template
├── data/
│   ├── raw/                  # Ingested raw datasets (e.g. historical mandi rates)
│   └── processed/            # Cleaned, structured data products
├── docs/                     # Architectural guides and technical documentation
│   └── architecture.md       # Modular monolith layer boundary guidelines
├── legacy_prototype/         # Safely preserved previous Streamlit prototype
├── .gitignore                # Rules for node_modules, venvs, caches, .env, SQLite
├── .env.example              # Root environment template
└── README.md                 # Project documentation
```

### Architectural Principles
- **Separation of Concerns**: Frontend and backend run independently with clear contract boundaries.
- **Clean `main.py`**: No business logic or SQL queries inside `main.py`; it serves solely as an application factory.
- **Typed Contracts**: All API endpoints use Pydantic models in `schemas/` for request and response validation.
- **Layered Flow**: `api/` (HTTP) -> `services/` (Domain Logic) -> `repositories/` (Database Access) -> `models/` (SQLAlchemy Entities).

---

## 2. Prerequisites

- **Node.js**: v18+ (tested on Node v22.x) and **npm**
- **Python**: 3.10+ (tested on Python 3.10.x)
- **Git**

---

## 3. Backend Setup

### A. Create and Activate Virtual Environment

From the root directory:

**On Windows (PowerShell):**
```powershell
python -m venv backend/.venv
.\backend\.venv\Scripts\Activate.ps1
```

**On Linux / macOS:**
```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
```

### B. Install Dependencies

```bash
pip install -r backend/requirements.txt
```

### C. Configure Environment Variables (Optional)

```bash
cp backend/.env.example backend/.env
```

---

## 4. Frontend Setup

### A. Install Dependencies

Navigate into the `frontend/` directory and install npm packages:

```bash
cd frontend
npm install
```

### B. Configure Environment Variables (Optional)

```bash
cp .env.example .env
```

---

## 5. Running the Application

To run the local development stack, launch both servers in separate terminal tabs or windows:

### Terminal 1: Run Backend (FastAPI + Uvicorn)

Activate the virtual environment, change to the `backend` directory, and start Uvicorn:

**On Windows (PowerShell):**
```powershell
cd backend
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**On Linux / macOS:**
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The backend will be available at:
- **API Base URL**: `http://127.0.0.1:8000`
- **Interactive OpenAPI Docs**: `http://127.0.0.1:8000/api/docs`
- **ReDoc**: `http://127.0.0.1:8000/api/redoc`

---

### Terminal 2: Run Frontend (React + Vite)

In a second terminal window:

```bash
cd frontend
npm run dev
```

The frontend will be available at:
- **Frontend URL**: `http://localhost:5173`

The frontend automatically communicates with `http://127.0.0.1:8000/api/health` via CORS and displays the operational health status.

---

## 6. API Health Check Example

### Request

```bash
curl -X GET http://127.0.0.1:8000/api/health -H "Accept: application/json"
```

### Response

```json
{
  "status": "ok",
  "service": "farmer-decision-system"
}
```

HTTP Status: `200 OK`

---

## 7. Preserved Legacy Prototype

Existing exploratory prototype work (Streamlit dashboard, onion crop calendar formulas, and Agmarknet seed rates) has been preserved under `legacy_prototype/` and `data/raw/` for future integration into Milestone 2 domain services.
