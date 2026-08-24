# Implementation Plan — 96 Hours, 5 People
## AI Infrastructure Consequence & Decision Simulator — **UrbanTwin**

| Field | Value |
|---|---|
| **Companion docs** | [PRD.md](PRD.md) · [ARCHITECTURE.md](ARCHITECTURE.md) · [TEAM_ROLES.md](TEAM_ROLES.md) |
| **Version** | 1.0 |
| **Date** | 2026-08-24 |
| **Team size** | 5 |
| **Duration** | 96 hours (4 days) |
| **Goal** | A demoable, explainable MVP: *budget → ranked strategies → cascade map → plain-language recommendation*, with a validation proof |

> This plan is built to be executed **in parallel by 5 people**. Each person's detailed responsibilities live in [TEAM_ROLES.md](TEAM_ROLES.md). This file is the **timeline + integration contract**.

---

## 1. The 5 Roles at a Glance

| # | Role | Owns (from ARCHITECTURE.md) |
|---|---|---|
| **R1** | **Data & Digital Twin Engineer** | Offline data pipeline, Graph Service, PostGIS, graph schema |
| **R2** | **Consequence / ML Engineer** | Flood + Mobility modules, CouplingResolver, Uncertainty, GNN |
| **R3** | **Backend & Optimization Engineer** | FastAPI API layer, Optimizer Service (OR-Tools), MarginalCache |
| **R4** | **Frontend Engineer** | React app, MapLibre/Deck.gl, ScenarioBuilder, TradeoffTable, charts |
| **R5** | **Integration, Explainability & Demo Lead** | Explanation (LLM), validation, DevOps/compose, demo & coordination |

Full role detail → [TEAM_ROLES.md](TEAM_ROLES.md).

---

## 2. Execution Principles (read before Hour 0)

1. **Contracts first, mocks early.** Freeze the API/JSON schemas in Hour 0 so all 5 can work in parallel against mocks — never block waiting on another person.
2. **Physics before ML.** Get a correct deterministic result on Day 2. GNN, local search, and LLM are **additive stretch** — not on the critical path.
3. **Integrate every single day.** End of each day = a running, demoable state on `main`. No "big bang" merge on Day 4.
4. **Every layer has a fallback** (see §9). If a fancy part isn't ready, the simple part still demos.
5. **Cut ruthlessly.** Protect the P0 golden path (§8). The cut-list (§10) is pre-agreed so nobody debates it at 3 a.m.

---

## 3. Hour 0 — Kickoff & Setup (all 5, ~2–3h) 🔴 critical

Do this together before splitting up.

- [ ] **Pick the demo city/ward** — good OSM coverage + a known past flood (R1 leads, R5 confirms).
- [ ] **Create the repo** (structure per ARCHITECTURE.md §13); `main` protected, feature branches.
- [ ] **Freeze API contracts** — write the Pydantic models & JSON shapes for `/graph`, `/interventions`, `/scenarios`, `/simulate`, `/optimize`, `/recommendation` (see ARCHITECTURE.md §8). **This is the single most important 60 minutes of the project.**
- [ ] **Stand up skeleton** — `docker-compose.yml` (postgres+postgis, backend, frontend) boots with `docker compose up` (R5).
- [ ] **Shared mock fixtures** — one small hand-made graph JSON + one sample intervention catalog everyone codes against until real data lands.
- [ ] **Agree the demo script's one sentence** so every decision serves it: *"For ₹5 crore, here are 3 strategies; we recommend B; here's why; here's proof the ranking is right."*

---

## 4. Milestone Map

| Milestone | When | Definition (demoable state) |
|---|---|---|
| **M0 — Skeleton up** | End of Hour 0 | `docker compose up` runs; all endpoints return mock JSON; map shows mock graph |
| **M1 — Digital Twin live** | End of Day 1 | Real city graph renders on the map from real data |
| **M2 — Consequences live** | End of Day 2 | Toggle an intervention → downstream flood + mobility change, with uncertainty |
| **M3 — Decisions live (feature-complete)** | End of Day 3 | Enter budget → ranked strategies + trade-off table + draft explanation |
| **M4 — Demo-ready** | End of Day 4 | Polished UI + validation proof + rehearsed demo + backup video |

---

## 5. Day-by-Day Plan (parallel swimlanes)

### 🗓️ DAY 1 (Hours 0–24) — Foundation & Digital Twin
**Day goal → M1:** the real city graph on the map.

| Person | Tasks |
|---|---|
| **R1** | Build offline pipeline (OSMnx roads/drains + DEM elevation + population); produce prepared graph; load into PostGIS; make `GET /graph` return **real GeoJSON** |
| **R2** | Implement `FloodModule` + `MobilityModule` against the **mock fixture graph** (don't wait on R1); define `ConsequenceVector` |
| **R3** | FastAPI app factory + all routers **stubbed to frozen contract**; DB session; `/healthz`; error-envelope format |
| **R4** | React + MapLibre skeleton; render graph from `GET /graph` (mock → real); base layout & app state |
| **R5** | `docker-compose` + `.env.example`; repo hygiene/CI-lite; seed script; start building the **intervention catalog** with R1 |

**🔗 Integration checkpoint (EOD1):** `main` boots; map shows the **real** graph; every endpoint reachable with mock/real data.
**✅ DoD:** M1 met; no red builds on `main`.

---

### 🗓️ DAY 2 (Hours 24–48) — Consequence Engine
**Day goal → M2:** cascading consequences visible on the map.

| Person | Tasks |
|---|---|
| **R2** | `CouplingResolver` (bounded 2–3 hops) + `UncertaintyRunner` (Monte Carlo); wire to **real** graph; make `POST /simulate` return real consequence vector + cascade path + confidence |
| **R1** | Finalize graph attributes R2 needs (elevation, capacity, population_served); persist intervention catalog; `GET /interventions` real |
| **R3** | Wire `POST /simulate` → Consequence Engine; scaffold `MarginalCache`; implement **fallbacks** (physics-only if GNN absent) |
| **R4** | Simulate UI: trigger a scenario, show result panel; **animate cascade path** (Deck.gl); **what-if toggle** (US-2) |
| **R5** | Start **synthetic-twin** validation harness; build test fixtures with R2; keep integration green; conservation-check guardrails |

**🔗 Integration checkpoint (EOD2):** toggle intervention → downstream flooding + travel-time change on the map, **with an uncertainty range**.
**✅ DoD:** M2 met; `POST /simulate` end-to-end on real data.

---

### 🗓️ DAY 3 (Hours 48–72) — Decision Engine + Comparison
**Day goal → M3:** budget in → ranked strategies out. **This is the feature-complete line.**

| Person | Tasks |
|---|---|
| **R3** | **Optimizer Service**: OR-Tools knapsack/CP-SAT under budget across weighted objectives; `POST /optimize` + `GET /recommendation` (numbers) |
| **R2** | Precompute marginals feed; **stretch**: `LocalSearch/GA` for interactions **or** GNN refiner; tune physics accuracy |
| **R1** | Scenario auto-generation helper (`POST /scenarios`); marginal precompute support; data QA |
| **R4** | `ScenarioBuilder` (budget input); `TradeoffTable`; radar/bar charts (Recharts); wire `/optimize` + `/recommendation` |
| **R5** | **Explanation Service**: LLM narration + **template fallback**; wire into `GET /recommendation`; own end-to-end integration |

**🔗 Integration checkpoint (EOD3):** enter a budget → ranked strategies + trade-off table + draft "why".
**✅ DoD:** M3 met — **MVP feature-complete**. Everything after is polish + proof.

---

### 🗓️ DAY 4 (Hours 72–96) — Explainability, Validation, Polish, Demo
**Day goal → M4:** a demo that wins, backed by proof.

| Person | Tasks |
|---|---|
| **R5** | Finish **synthetic-twin validation** (model recovers correct ranking) → **validation slide**; polish explanation prompt; write **demo script** + **pitch deck**; record backup video |
| **R4** | UI polish: empty/error/loading states; colorblind-safe palette; responsive; the "wow" cascade animation |
| **R2** | Confidence labels correct; final model tuning; verify uncertainty is honest |
| **R3** | Performance pass (sim <2s, optimize <5s); test all fallback paths; **freeze the API** |
| **R1** | Data QA; backup dataset; verify reproducibility (global seed) |

**🔗 Integration checkpoint (EOD4):** full run-through on a clean machine; backup video recorded.
**✅ DoD:** M4 met. Demo rehearsed ≥2×. Stop building 4h before deadline; only bug-fix after.

---

## 6. Integration Strategy

- **Contract-driven:** the frozen Pydantic schemas are the source of truth; UI and services develop against them independently.
- **Mock → real swap:** each endpoint returns mock data first, then flips to real — the frontend never blocks.
- **Daily merge to `main`:** end-of-day integration is mandatory; `main` must always boot and demo.
- **One integrator (R5):** owns keeping `main` green and the services talking to each other.

---

## 7. Git & Working Workflow

- Branch per feature: `feat/graph-pipeline`, `feat/simulate`, `feat/optimizer`, `feat/frontend-map`, `feat/explanation`.
- Small PRs, fast reviews (buddy reviews buddy — see TEAM_ROLES.md pairing).
- `main` is always demoable. Tag each milestone: `m1`, `m2`, `m3`, `m4`.
- **Standups:** 15 min at the **start and end of each day** — blockers, integration status, cut-line check.

---

## 8. The P0 "Golden Path" (never cut)

This is the demo. Everything else is negotiable.

```
GET /graph  →  map renders city
POST /simulate  →  cascade + consequence with uncertainty
POST /optimize  →  ranked bundles under budget
GET /recommendation  →  trade-off table + explanation
+ synthetic-twin validation slide
```

If the golden path works, you have a winning demo even with every stretch feature cut.

---

## 9. Fallbacks (so nothing hard-fails on stage)

| If not ready | Fall back to | Owner |
|---|---|---|
| GNN refiner | Physics baseline only | R2 |
| Local search / GA | Pure knapsack | R3 |
| LLM explanation | Deterministic template | R5 |
| Live optimization | 2–3 **pre-baked** scenarios compared | R3/R4 |
| Full data pipeline | Cached prepared graph committed to `data/` | R1 |

---

## 10. Pre-Agreed Cut-List (drop in this order if behind)

1. PDF/report export (P2)
2. GNN refiner → physics only
3. Local search/GA → pure knapsack
4. Auto-generated scenarios → hand-authored scenario set
5. LLM narration → template explanation
6. Extra domains stay stubbed (already the plan)

> **Never cut:** the golden path (§8) or the validation slide. Those *are* the project.

---

## 11. Definition of Done (per feature)

- [ ] Matches the frozen API contract
- [ ] Has a fallback path (§9)
- [ ] Merged to `main`; `main` still boots via `docker compose up`
- [ ] Visible in the UI or via `/docs`
- [ ] Reproducible (seeded) where randomness is involved

---

## 12. Final Demo Script (5–6 min)

1. **Hook (30s):** "Cities fund projects in isolation. We built a flight simulator for infrastructure decisions."
2. **Show the twin (45s):** the city graph on the map; explain nodes = assets, edges = dependencies.
3. **What-if (60s):** toggle "Upgrade Drain-17" → watch flooding recede and roads reopen; point at the **uncertainty range**.
4. **Budget decision (90s):** enter ₹5 crore → 3 ranked strategies + trade-off table; read the **plain-language recommendation**.
5. **Proof (60s):** the **synthetic-twin validation** slide — "our ranking matches known ground truth."
6. **Vision (30s):** modular design → add water, economy, real-time sensors; multi-city.

Keep a **backup video** of this exact run.

---

## 13. After the Hackathon (pointer)

Roadmap and validation depth live in [PRD.md](PRD.md) §18–21 (pilot → real historical calibration → multi-city → platform).

*End of Implementation Plan v1.0.*
