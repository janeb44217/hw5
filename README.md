# Campus Customs Multi-Agent Operations (HW5)

An agent team that runs a small campus apparel shop. Tickets land on a board: customer orders, rent notices, discount requests. Five PydanticAI agents work them through an MCP server, and a human approves every payment in a React dashboard.

- **MCP server** (`mcp_server/`, FastMCP): the only path to shop data. 18 tools over `data/campus_customs_new.db`.
- **Backend** (`backend/`, FastAPI + PydanticAI): Boss, Inventory, Accounting, Facilities and Customer Service, with full delegation between them. Every step is appended to `output/audit_trail.json`.
- **Dashboard** (`frontend/`, React + Vite + TypeScript): watch the agents work, approve payments and see the cash balance.
- **Model:** `gpt-6-luna` through Portkey, for every agent.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then add your PORTKEY_API_KEY
cd frontend && npm install && cd ..
```

## Run

Run every command from the project root (`hw5/`) unless a step says otherwise. Activate the virtualenv first (`source .venv/bin/activate`).

### 1. Copy the original DB to the working copy (clean run)
`data/campus_customs.db` is the original and is never modified. All tools read and write `data/campus_customs_new.db`. When you need a clean run, copy the original over the working copy:
```bash
cp data/campus_customs.db data/campus_customs_new.db
```

### 2. Start the MCP server
```bash
python mcp_server/server.py
```
It serves 18 shop tools over stdio, pointed at `data/campus_customs_new.db`. You don't have to keep this terminal open for the app: the backend starts its own copy of this same server over stdio for the agents. Claude Code loads it from `.mcp.json`.

### 3. Start the FastAPI backend → http://localhost:8000
```bash
cd backend
uvicorn main:app --reload --port 8000
```
API docs are at http://localhost:8000/docs. It needs `PORTKEY_API_KEY` in `.env`.

### 4. Start the React board → http://localhost:5173
In a second terminal:
```bash
cd frontend
npm run dev
```
It opens in your browser (or uses the next free port if 5173 is busy) and talks to the backend at `http://localhost:8000`. Pick a ticket and press **Start the team** to watch the agents. Approve payments under **Needs your signature**.

### 5. Reset the DB before a full three-ticket run
Always start a full run of tickets 101, 102 and 103 from the original data. Use any one of these:
- the **↺ Reset shop** button on the board
- `curl -X POST http://localhost:8000/api/reset`
- `python -m backend.run reset`
- or the `cp` command from step 1

Then run 101, 102 and 103 on the board. Approve each payment when it shows up, and hand the ticket back to the team after approving until all three are resolved. Resetting keeps `output/audit_trail.json`, which is append-only.

There's also a command-line runner: `python -m backend.run work 101 | work --all | approvals | approve <id> --by "<name>"`.

## Data

Both databases are committed. `data/campus_customs_new.db` is left in its state **after the full run**: all 3 tickets resolved, checking at $152.00. That matches the Cash tab in `output/desk_tickets.html`. Reset it to start over.

## Where to look

| File | What it is |
|---|---|
| `output/harness.md` | Tables, MCP tools, agents, API routes, dashboard, safety rules, run results |
| `output/desk_tickets.html` | Expected vs. Actual per ticket, Cash, Reflection |
| `output/resolved_board.html` | Dashboard screenshots of each resolved ticket |
| `output/resolved_tickets.json` | Final status, outcome, agent contributions and approvals per ticket |
| `output/design.md` | Dashboard design choices |
| `output/mcp_smoke.json` | MCP tool smoke test |
| `output/audit_trail.json` | Append-only log of every agent step |
| `AI_prompts.md` | Prompts given to the vibe coder, by problem |

## File tree

```
hw5/
├── AI_prompts.md
├── requirements.txt
├── .env.example
├── .gitignore
├── .mcp.json
├── README.md
├── data/
│   ├── campus_customs.db
│   └── campus_customs_new.db
├── mcp_server/
│   ├── server.py
│   └── README.md
├── frontend/
│   └── src/ (App.tsx, api.ts, agents.ts, components/…)
├── backend/
│   ├── main.py
│   ├── models.py
│   ├── config.py · mcp_link.py · audit.py · run.py
│   ├── agents/ (base.py, boss.py, inventory.py, accounting.py, facilities.py, customer_service.py)
│   └── prompts/
│       ├── boss.md
│       ├── inventory.md
│       ├── accounting.md
│       ├── facilities.md
│       └── customer_service.md
└── output/
    ├── harness.md
    ├── mcp_smoke.json
    ├── desk_tickets.html
    ├── design.md
    ├── resolved_tickets.json
    ├── resolved_board.html
    ├── audit_trail.json
    ├── github_url.txt
    └── screenshots/
```
