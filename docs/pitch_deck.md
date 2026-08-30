# 🌆 UrbanTwin — Pitch Deck

**AI Infrastructure Consequence & Decision Simulator**
*Budget → Ranked Strategies → Cascade Map → Plain-Language Recommendation*

---

## Slide 1 — The Problem

> **"Cities spend ₹1,000 Cr/year on flood infrastructure. Most investment decisions are made without simulation."**

- Chennai 2015 floods: ₹20,000 Cr economic damage
- Flood projects evaluated in isolation — no cross-domain cascade modeling
- Decision-makers lack tools to answer: *"Which ₹5 crore investment saves the most lives?"*

---

## Slide 2 — The Solution

**UrbanTwin** — A digital twin that simulates the full cascade of infrastructure decisions:

```
Budget → Simulate Consequences → Rank Strategies → Explain Recommendation
```

Built on:
- 🗺️ **Real city graph** (OpenStreetMap + DEM elevation)
- 🌊 **Physics flood model** (mass conservation, drain capacity, cascading inundation)
- ⚡ **OR-Tools optimizer** (multi-objective knapsack under budget)
- ✨ **Plain-language AI explanation** (Jinja2 template + optional LLM)

---

## Slide 3 — Architecture at a Glance

```
Frontend (React + MapLibre)
    ↕ REST API
FastAPI Backend
    ├── GraphService  (OSM + PostGIS)
    ├── ConsequenceEngine  (Flood + Mobility + Coupling)
    ├── BudgetSolver  (OR-Tools CP-SAT Knapsack)
    └── Explainer  (Jinja2 → LLM)
```

All components have **mock → real swap** fallbacks so the demo is always alive.

---

## Slide 4 — Live Demo

> *See the demo script: [docs/demo_script.md](demo_script.md)*

**The golden path:**
1. 🗺️ Real T.Nagar city graph renders (2,296 nodes, 5,481 edges)
2. 🌊 Toggle a drain upgrade → flood cascade animates on map
3. 💡 Enter ₹5 crore → 3 ranked strategies + trade-off radar chart
4. 📄 Plain-language AI recommendation explains *why* Strategy A wins

---

## Slide 5 — Validation Proof

> *See the full proof: [docs/validation_slide.md](validation_slide.md)*

**3 correctness guarantees — all verified:**

| Property | Test | Status |
|---|---|---|
| Targeted > Irrelevant | Flood intervention on low-elevation node > dry node | ✅ PASS |
| Monotonicity | More interventions → equal or fewer flooded nodes | ✅ PASS |
| Conservation | Risk reduction ∈ [0,1], population never increases after intervention | ✅ PASS |

**35 automated tests. 100% pass rate. Reproducible (seed=42).**

---

## Slide 6 — Impact Metrics (Demo Run)

| Metric | Value |
|---|---|
| Budget | ₹5 crore |
| Interventions considered | 20 |
| Flood risk reduction | 28–34% |
| Population protected | 8,000–14,000 residents |
| Simulation time | < 2 seconds |
| Optimization time | < 5 seconds |

---

## Slide 7 — Roadmap

| Horizon | Feature |
|---|---|
| **Now (MVP)** | T.Nagar twin, physics simulation, OR-Tools optimizer, AI explanation |
| **3 months** | Historical calibration (Chennai 2015 flood data) |
| **6 months** | Multi-city (any OSM city in < 1 day) |
| **12 months** | Real-time IoT sensor ingestion, water quality + power grid domains |
| **Platform** | SaaS for municipal corporations — pay per city twin |

---

## Slide 8 — The Team

| Role | Focus |
|---|---|
| Data & Digital Twin Engineer | OSM pipeline, PostGIS, graph schema |
| Consequence / ML Engineer | Flood + Mobility physics, Monte Carlo uncertainty |
| Backend & Optimization Engineer | FastAPI, OR-Tools knapsack, MarginalCache |
| Frontend Engineer | React, MapLibre, cascade animation, AI UX |
| Integration & Demo Lead | Explanation, validation, DevOps, this deck |

---

## Call to Action

> **"Give us 6 months and we'll calibrate against real historical data. Give us 12 months and we'll have every major Indian city on the platform."**

*UrbanTwin — Built in 96 hours. Designed for the next 10 years.*
