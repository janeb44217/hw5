# AI Prompts — Homework 5: Campus Customs Multi-Agent Operations

The prompts I gave my vibe coder (Claude Code), with one section per problem.

---

## Problem 1 — Vibe Coder prompts

**Prompt:**
> Problem 1: Vibe Coder prompts. create AI_prompts.md and keep it updated as we work

**Follow-up prompt:**
> Still part of problem 1: put one section for each problem, each section must include 1) the problem number and title 2) at least one prompt typed and 2) one follow-up prompt if needed and one sentence on what was lacking after the first.

**What was lacking after the first:** The first version was just a flat, chronological list of every prompt, with no per-problem sections, no split between first prompt and follow-up, and no note on what the first attempt missed.

---

## Problem 2 — Study the Campus Customs database

**Prompt:**
> Problem 2: Study the campus customs database, open data/campus_customs.db and look through every table and its fields. copy the original file to data/campus_customs_new.db - later problems will update that working copy. study the three open tickets so you see how they link to other tables. start output/harness.md. for each table, list the fields and one short line on why that table matters for the agents. the harness file will keep growing in later problems.

---

## Problem 3 — Build the MCP server

**Prompt:**
> Problem 3: Build the MCP server. Write an MCP server in mcp_server/ using FastMCP. it will talk to data/campus_customs_new.db. you do not need to connect or run it in this problem. every agent in this homework uses the tools in this MCP server. you will add more tools later; for now write 3 tools you know you will need for the tickets in the database, keeping the names clear. Never invent data, only use info in the database. In output/harness.md, list each of your 3 MCP tools. for every tool include: 1) which table it reads 2) which ticket it helps unlock (101, 102, 103) and 3) one sentence on why that tool is the right one for that ticket. don't give vague lines like "reads inventory" that will get a low score on the assignment, you should tie the tool to the ticket. Add a short mcp_server/README.md file that explains what the MCP server is for and which database file it uses and the 3 tools it has

---

## Problem 4 — Add the MCP server to the vibe coder and test each tool

**Prompt:**
> Problem 4: Add the MCP server to vibe coder and test each tool. Add the MCP server to this project so the vibe coder can call the tools. save the connection JSON text in .mcp.json at the project root (or however vibe coder saves local MCP server lists) with the vibe coder, test each of your 3 MCP tools. save the evidence in output/mcp_smoke.json, every tool should include 1) the prompt you asked the vibe coder 2) the tool name 3) the tool ouput (must match values in data/campus_customs_new.db

**Follow-up prompt:**
> do it for me

**What was lacking after the first:** The vibe coder wrote `.mcp.json` but stopped before testing, asking me to restart the session so the tools would load, so `output/mcp_smoke.json` didn't exist yet.

---

## Problem 5 — Build the agent team and grow the MCP tools

**Prompt:**
> Problem 5: Build the agent team and grow the MCP tools. build the agentic team for Campus Customs using PydanticAI: Boss, Inventory, Accounting, Facilities and Customer Service. include prompts, models, and agent loops so they can delegate work to each other with full connectivity. put the agent prompts in backend/prompts/ - one file per agent. put data types in backend/models.py and the agent files under backend/ (your layout can vary as long as the 5. roles are clear. use your portkey_api_key and only gpt-6-luna for every agent. write each prompt in own words with the shop rules that the agent needs. more detailed prompts convering all aspects of an agent's work and scope will score higher than a short generic prompt. add any tools the agent needs to your MCP server so they can work on the open tickets. shop facts come from the MCP server over data/campus_customs_new.db - do not invent a second shop tools layer that bypasses MCP. wire the agents so they append to output/audit_trail.json as they run. for each agent loop step, record enough to audit later. append to this file - do not wipe it each run. in output/harness.md, list each agent and each MCP tool (including ones you add in this problem) along with which table the tool uses. add a short safety section: the guardrails a real business would want when agents touch real customers and real money plus limits that keep token use in check. update mcp_server/README.md so the tool matches what you have now

---

## Problem 6 — Plan the three tickets

**Prompt:**
> Problem 6: Plan the three tickets. Before you wire the backend, write down what you expect the team to do on each open ticket. build output/desk_tickets.html - a page you can double click with one tab per ticket (101, 102, 103). add empty Cash and Reflection tabs for later problems (leave them blank or with a short coming later for now). on each ticket tab, fill an Expected section only (leave room for an Actual section that will get filled after running the agent) for each  ticket's Expected section, write in your own words: 1) who the Boss should call first 2) all the agent declarations you expect - not "boss calls everyone" 3) which MCP tools you expect that run to use. plans that send every specialist on every ticket score low. you will compare this plan to what actually happens when your agents resolve the three tickets.

---

## Problem 7 — Backend routes

**Prompt:**
> Problem 7: Backend routes. your react frontend dashboard (next problem) needs a backend it can call. in backend/main.py, use FastAPI and add routes that do the following: return the 3 tickets and whether each is open and resolved 2) take a ticket ID and run your agent team on that ticket 3) return recent agent events - what each agent said and which tools they used - so the board can refresh. 4) approve a payment and purchase after a human clicks approve (agents only prepare the pay; this route is what actually changes cash) 5) return the current checking balance from cash_accounts 6) reset the database to the original values when you want to try a fresh run.  from the backend/ folder, start the server with uvicorn main:app --reload --port 8000 this turns on your backend at http://localhost:8000 so the frontend dashboard can call those routes. in output/harness.md, list each route in one line (what IRL/what it does)

**Follow-up prompt:**
> u can stop on homework 4

**What was lacking after the first:** The server couldn't start on port 8000 because my old homework 4 backend was still running there, so the vibe coder had only tested on port 8001 and needed my OK to stop it.

---

## Problem 8 — Agent dashboard

**Prompt:**
> Problem 8: Agent dashboard. build the frontend dashboard in frontend/ with react + vite + typescript. the page should call the routes you built in problem 7. at minimum the board should 1) list all 3 tickets 2) let you pick one ticket and start the agent team on it 3) show each agent and they are saying/doing while the ticket runs 4) mark a ticket resolved when the run finishes 5) show a short summary of what each agent did on that ticket 6) let a human approve a pay or purchase when asked 7) show the checking balance (it should drop after an approved pay) make the dashboard look good - be creative with the layout and feel - this is a real desk people would want to sit at. tell the front end to talk to your backend at http://localhost:8000. on the backend, allow the vite page origin (usually http://localhost:5173) so the browser is allowed to call those routes. start the board with npm run dev. this opens the react desk in your browser so you can pick tickets and watch agents. write output/design.md with what you chose for the dashboard look (layout, how agents read differently, how resolved tickets and cash show up) and why, including the creative choices that make it feel special and something humans would actually enjoy using

---

## Problem 9 — Resolve the tickets

**Prompt:**
> Problem 9: Resolve the tickets. before testing the agents on a full run over the 3 tickets, reset the working database data/campus_customs_new.db again so you start clean. note the starting checking balance. then run all 3 tickets on the board (101, 102, 103) until each is resolved. open output/desk_tickets.html from problem 6. on each ticket tab, fill the Actual section from this run: which agents worked, what they delegated, and which tools they used. keep your expected section so you can compare the two. on the cash tab of the same output/desk_tickets.html, itemize the money: starting checking balance (after the reset), for each ticket, how cash changed when that ticket resolved and why (which pay/purchase, dollar amount), ending checking balance - it must match cash_accounts in the working database. wrong cash math loses points even if the board shows every ticket resolved. also save: output/resolved_tickets.json: for each ticket: id, final status, short outcome, what each agent contributed, and any human approvals; output/resolved_board.html: a page you can double click with a screenshot of your react board for each resolved ticket (101, 102, 103). append real runs to output/audit_trail.json. finish output/harness.md so it overs tables, MCP tools, the 5 agents, API routes, the dashboard and safety rules

**Follow-up prompt:**
> done

**What was lacking after the first:** After I approved the $8 purchase order, the Boss still left ticket 101 `in_progress` because the tools never showed a paid PO as "placed / on order". The vibe coder had to fix `check_stock` and the Boss prompt before a final rerun could resolve it.

---

## Problem 10 — Reflection

**Prompt:**
> Problem 10: Reflection. Open output/desk_tickets.html and fill the reflection tab. 1) How would you evaluate the performance of the agents on each ticket and why? 2) for each ticket, how did actual compare to the expected plan written earlier? 3) what would have been simpler as one agent with tools and why? 4) describe 3 new problems campus customs might face that this agent could solve with the tools built 5) describe 3 new problems campus customs might face that this agent team could not solve with the tools you built and explain the tools and agents you would need to solve them

**My contributions to reflection:** overly complicated the system, especially for ticket 1, wasteful with tickets. appreciated diligence when it came to drafting emails to first customer, Tauhid but seemed overkill to be providing so many updates to customer. Thought the other two processes were better. Don't fault the system for being more conservative though with effort and multiple email drafts, verifying with multiple stakeholders, etc.

---

## Problem 11 — Submit to GitHub

**Prompt:**
> Problem 11: Submit to GitHub. Push your code to a public GitHub repository so graders can clone it. submit the repo URL to canvas and also put it in outout/hithub_url.txt. do not push your real .env to the GitHub repo. Do include both database files under data/ (the original and your working copy) so graders can run the app easily.

**Follow-up prompt:**
> first make sure these requirements are all included

**What was lacking after the first:** The repo was missing the root README.md and output/github_url.txt from the required file tree, so I had the vibe coder check against the tree before I pushed it myself.
