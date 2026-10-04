# Architecture Guide: Farmer Decision Support System

## 1. System Overview

The Farmer Decision Support System is structured as a **modular monolith** with clean separation between the user interface and backend services:
- **Frontend**: React + Vite + Tailwind CSS (SPA)
- **Backend**: FastAPI + Pydantic + SQLAlchemy (RESTful API)
- **Database**: SQLite (Milestone 1 foundation; ready for PostgreSQL)
- **Data Layers**: `data/raw/` for raw ingestion / datasets and `data/processed/` for cleaned assets.

## 2. Directory Structure

```
farmer-decision-system/
├── frontend/             # Single Page Application
│   └── src/
│       ├── components/   # Reusable UI components
│       ├── pages/        # Route page views
│       ├── services/     # API integration & client calls
│       ├── hooks/        # Custom React hooks
│       ├── types/        # JSDoc / Type declarations
│       ├── utils/        # Utility helpers & formatting
│       └── App.jsx       # Root layout & entry point
├── backend/              # RESTful API Service
│   └── app/
│       ├── api/          # Route handlers & endpoints
│       ├── core/         # Config, security, database session
│       ├── models/       # SQLAlchemy ORM models
│       ├── schemas/      # Pydantic request/response validation
│       ├── services/     # Business logic & domain rules
│       ├── repositories/ # Database queries & persistence
│       └── main.py       # FastAPI application factory
├── data/
│   ├── raw/              # Raw data files (e.g. mandi records)
│   └── processed/        # Preprocessed data / clean features
├── docs/                 # Architecture, specifications & guides
├── legacy_prototype/     # Preserved early Streamlit prototype
├── .gitignore
├── .env.example
└── README.md
```

## 3. Backend Architectural Invariants

To keep the application production-grade and maintainable as future features (weather, markets, recommendations) are introduced:

1. **`main.py` is an application factory**:
   Only handles FastAPI instantiation, middleware setup (CORS), and router inclusion. Contains zero business logic or endpoint route declarations.
2. **`api/` layer**:
   Handles HTTP request parsing, status codes, query/body validation via Pydantic schemas, and calling the appropriate service layer.
3. **`services/` layer**:
   Houses all business workflows, calculations, and domain orchestrations. Never directly accesses raw HTTP requests or writes direct SQL.
4. **`repositories/` layer**:
   Encapsulates all database interactions and CRUD operations using SQLAlchemy sessions.
5. **`models/` layer**:
   Declares database tables and relationships.
6. **`schemas/` layer**:
   Declares strictly typed Pydantic models for incoming request bodies and outgoing responses.

## 4. Frontend Architectural Invariants

1. **Independent execution**: Runs on its own dev server (e.g., Vite on port 5173).
2. **Service isolation**: All HTTP calls to the backend are routed through `services/api.js`.
3. **Tailwind utility styling**: Configured with utility classes, zero CSS bloat.
