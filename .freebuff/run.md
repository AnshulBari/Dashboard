# Preview Run Doc

## How to reproduce artifacts
- `cd frontend && npm install` (already done)
- Database seeded via `python setup.py` (already done at data/cricket_intelligence.db)

## How to run the server
- Port: 5175 (5173 and 5174 were in use)
- Command: `cd frontend && npm run dev`
- The Vite dev server proxies `/api` to `http://localhost:8000` (backend)
- Backend must be running separately: `DATABASE_URL='sqlite:///data/cricket_intelligence.db' uvicorn backend.main:app --port 8000`
