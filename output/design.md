# Campus Customs Agent Desk: design notes

The dashboard (`frontend/`, React + Vite + TypeScript) is designed like a real **operations desk**, not an admin table. You sit down, see what landed on the board, send the team to work, watch them talk to each other, and sign for money. It talks to the FastAPI backend at `http://localhost:8000`, set by `VITE_API_URL` in `frontend/.env`.

## Layout: three columns that match how the work flows

| Left: **the inbox** | Center: **the floor** | Right: **the money** |
|---|---|---|
| Ticket board, then "#id up close" with the customer's own words and the one big **Start the team** button | A room where the five agents sit. Below it, **Desk chatter** (live feed) and **Who did what** (summary) | The **Checking** register, then **Needs your signature** (the approval inbox) |

Read left to right, that's the life of a ticket: *it arrives → the team works it → a human signs off on any money.* Your eye goes where the action is: the floor is in the middle and largest, and the money is on the right where a manager's eye checks last before signing. Below 1250px the columns stack in the same order.

## How the agents read differently

- **Each agent is a Labubu with its own accessory and shade of pink**, so you can tell who's talking before you read a word:
  - **Boss**: a crown, hot pink, sitting at the head of the room and drawn larger
  - **Inventory**: carrying a stock box
  - **Accounting**: round glasses, rose pink
  - **Facilities**: a hard hat, violet-pink
  - **Customer Service**: a headset, soft pink

  The same color runs through everything that agent touches: the nameplate, the left border of each feed line, its summary card and the "prepared by" name on an approval.
- **Mood shows state, not decoration.** An agent that's using tools bobs. One that's speaking (the model returned text) squishes like it's talking. A finished agent goes back to slow breathing. Every Labubu blinks now and then.
- **Speech bubbles** show each active agent's latest step in plain English, such as "🔧 check_stock(sku=CC-TEE-WHITE, size=S)", "📋 check_vendor_can_ship → Bulldog Print Co blocked by invoice #501" or "📨 Asks Accounting: …". Bubbles of finished agents tuck away and come back on hover, so the room never turns into a wall of text.
- **Delegation is drawn on the floor.** Each handoff draws a dashed line between the two desks, and an open handoff glows and runs ("marching ants") until the answer comes back. After a run you can see the route the Boss took at a glance.
- **Agents that weren't needed stay grey** and are labeled "sat this one out". On the rent ticket, Inventory and Customer Service fade, which shows that the Boss didn't send everyone on every ticket.
- **Desk chatter** is the full timeline: time, agent, icon, then text. Tool calls and results use a monospace font so they read as machine actions, while what agents say reads as prose. Delegated agents are indented by depth, so you can see who's working for whom.

## Resolved tickets

- Every ticket card has a **status pill**: Open → *Agents working…* (the card glows while the team is on it) → **Needs you** (bright pink and pulsing when the Boss set `waiting_approval`) → **Resolved** or Declined.
- When the Boss resolves a ticket, a **RESOLVED rubber stamp slams onto the card** (it scales down from 2.4× and rotates into place), and the progress bar at the top of the board fills ("2/3 resolved").
- When a run finishes, **Who did what** opens with the Boss's decision banner (status, decision and the exact next step for the human). Below that is a card for each agent: who called it, who it handed off to, the tools it used (as chips with counts) and its last words. Any **drafts** written on the ticket appear as pale "paper" notes labeled *saved, never sent*.
- The ticket status always comes from the Boss's `set_ticket_status` in the database. The desk never fakes "resolved". If the Boss is waiting on a payment, the card says **Needs you**, and once you approve, the toast offers **Hand #101 back to the team** so the Boss can finish the job.

## Cash

- **Checking** looks like a glowing cash-register display. When a payment is approved, the number **rolls down** (eased count), the display shakes once, and a red **−$840.00** drops and fades away. You *feel* money leaving, which fits the rule that cash only goes out.
- A split bar shows **free cash after pending** (solid pink) vs. **waiting on you** (hatched), using `cash_after_pending` and `pending_total` from `/api/cash`. You can see before signing that rent plus the overdue invoice would leave only $160.
- A **receipt tape** lists every payment that went through (invoice, rent or PO, the payee, the amount, and the human who approved it).

## Approvals: signing for money

- Approval requests look like **paper checks with a torn edge**, light on the dark desk so they're the brightest thing on screen when something needs you. The panel header gets a pulsing count badge and a pink outline.
- Each check shows what it's for (🧾 invoice, 🏠 rent, 📦 purchase order), the amount, the payee, which agent prepared it, which ticket, and the agent's reason. If the amount is more than the balance, it warns that the backend will refuse it.
- **"Signing as"** takes your name in a script font, like a signature. It's saved in the browser, and both buttons stay disabled until there's a name. That name is written to `payments.approved_by`. **Approve & pay $X** is the only control in the app that moves money. Reject asks for an optional reason.

## Small touches that make it pleasant to sit at

- The header shows the **shop's date** (Mon, Aug 31, 2026 from `desk.date_today`), not the computer's, so everyone works on shop time.
- A **toast** confirms every action in plain language ("Paid $840.00 to Bulldog Print Co. Checking is now $2,560.00."), with a one-click follow-up when one makes sense.
- **↺ Reset shop** (with a confirm) restores the original database. The view then ignores runs from before the reset, so old history never confuses the current state.
- If the backend is down, a banner says exactly what command to run instead of showing a broken page.
- The board polls quickly (1.2s) while agents work and slowly (5s) when idle, so it feels live without hammering the backend.
- `prefers-reduced-motion` turns off all animation for people who don't want it.
- The visual language is black and pink with friendly creatures, which matches the course's house style. It's calm and dark for long sessions, and the pink is saved for things that need attention: live work, approvals and money.
