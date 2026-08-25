# Run Doc — Cricket Intelligence Platform

## Reproduce

1. The SQLite database with real Cricsheet IPL data (200 matches) already exists at `data/cricket_intelligence.db`.
2. No pipeline re-run needed.

## Backend

```bash
DATABASE_URL="sqlite:///data/cricket_intelligence.db" python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

## Frontend

```bash
cd frontend
VITE_API_URL="http://localhost:8000/api" npx vite --port 5176 --host 0.0.0.0
```

## Key Endpoints

- Dashboard: http://localhost:5176/
- API docs: http://localhost:8000/docs
- Players: http://localhost:5176/players
- Teams: http://localhost:5176/teams
- Venues: http://localhost:5176/venues

## Data

Real Cricsheet IPL data (2008-2017), 200 matches, 47,542 deliveries, 261 players, 11 teams.
