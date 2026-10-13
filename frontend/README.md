# Campus Customs Agent Desk (frontend)

React + Vite + TypeScript dashboard for the Campus Customs multi-agent team.

1. Start the backend first: from `backend/`, run `uvicorn main:app --reload --port 8000`
2. Start the desk: from `frontend/`, run `npm install` (first time) and then `npm run dev`

It opens at http://localhost:5173 (or the next free port) and calls the backend at `VITE_API_URL` (default `http://localhost:8000`, see `.env`).

See `../output/design.md` for the design choices.
