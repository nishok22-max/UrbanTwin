# 🎤 UrbanTwin Demo Script — 5-Minute Pitch

**Event:** AI Hackathon Demo
**City:** T.Nagar, Chennai
**Tagline:** *"A flight simulator for infrastructure decisions."*

---

## Pre-Demo Checklist (15 min before)

- [ ] `docker compose up` or `uvicorn` + `vite dev` both running
- [ ] Open browser to `http://localhost:5173`
- [ ] Map is loaded and showing T.Nagar graph (watch for "Ready" status dot)
- [ ] Verify: ≥ 2,296 nodes and 5,481 edges shown in topbar chips
- [ ] Backup video ready on second screen/device
- [ ] Projector aspect ratio: 16:9, resolution at least 1280×720

---

## The Script

### 🎬 Segment 1 — Hook (30 seconds)

> *"Cities spend billions on flood defenses every year — and most of it is guesswork. Today I'm showing you something different. This is **UrbanTwin** — a flight simulator for infrastructure decisions. Instead of flying blind, Chennai's city planners can now see exactly what happens before they sign a check."*

**Action:** Point to the glowing map. Let the scanline animation and neon cyan edges speak for themselves.

---

### 🗺️ Segment 2 — Show the Twin (45 seconds)

> *"This is T.Nagar — Chennai's densest commercial ward. Every dot is a real infrastructure asset: a road junction, a drain node, a utility hub. Every edge is a physical dependency — flood water can travel here, and mobility breaks here."*

**Action:**
1. Click **📍 Panagal Park** hotspot → map flies to the commercial core
2. Click any node → Asset Telemetry HUD appears: elevation, population served, flood depth
3. *"See this node — 7.2 meters above sea level. That's in a known flood basin. 3,400 residents depend on this drainage junction."*

---

### 🌊 Segment 3 — What-If Toggle (60 seconds)

> *"Now watch what happens when the monsoon hits. I'm going to apply a drain upgrade to this vulnerable node and simulate a 160mm rainfall event — the kind that paralyzed Chennai in 2015."*

**Action:**
1. Switch to **What-If** tab → scroll to first intervention in the list (e.g., "Upgrade Drain")
2. Check the checkbox to select it
3. Click **▶ Simulate Cascade** button
4. *Wait for cascade animation* → red/orange flood depth colors appear on map
5. Point to the Result panel: **Risk Reduction**, **Population Protected**, **Uncertainty Range**

> *"That's the cascade — in real-time. And see those p10/p90 confidence bands — we're not hiding uncertainty. We're quantifying it with 50-run Monte Carlo so you know exactly how reliable this prediction is."*

---

### 🎯 Segment 4 — Budget Decision (90 seconds)

> *"Here's where it gets powerful. I'm the Finance Minister. I have ₹5 crore. What do I actually build?"*

**Action:**
1. Click **✨ Ask AI** preset: **"⚡ ₹5Cr Monsoon Deluge"**
2. Watch the AI reasoning animation: [1/4] … [2/4] … [3/4] … [4/4] …
3. Switch to **Optimize** tab
4. Three strategy cards appear. Point to #1 (Recommended)

> *"In under 3 seconds, UrbanTwin evaluated every possible combination of interventions under this budget, across 4 objectives — flood risk, population protection, mobility, and service availability — and gave me 3 ranked strategies."*

5. Point to the **Radar Chart** showing trade-off balance
6. Read the **AI Decision Justification** box aloud

> *"Strategy A reduces flood risk by 34% and shields 12,000 residents — for ₹4.8 crore. Strategy B costs slightly more but protects an extra 3,000 residents in a hospital corridor. The AI explains the tradeoff in plain English. No PhD required."*

---

### ✅ Segment 5 — Proof (45 seconds)

> *"You might ask — how do we know this ranking is correct? We ran a synthetic-twin validation."*

**Reference `docs/validation_slide.md`** (or show on slide)

> *"We constructed a controlled experiment: interventions targeting known flood basins must protect more population than identical interventions on high-elevation safe ground. Our engine passes this test 100% of the time, every run. The optimizer is monotonic — more budget always produces equal or better outcomes. 35 automated tests. All pass. Green."*

Show the terminal / test results screenshot.

---

### 🚀 Segment 6 — Vision (30 seconds)

> *"Today it's T.Nagar. Tomorrow, any ward in any city. The graph can absorb water data, air quality, power grids, real-time IoT sensors. The optimizer stays the same. The insight scales. We built UrbanTwin in 96 hours. Imagine what 6 months looks like."*

**Action:** Zoom out the map. Pause.

---

## Key Numbers to Remember

| Stat | Value |
|---|---|
| Graph nodes | 2,296 |
| Graph edges | 5,481 |
| Simulation time | < 2 seconds |
| Optimization time | < 5 seconds |
| Test suite | 35 tests, 100% pass |
| Monte Carlo runs | 50 per simulation |
| Demo budget | ₹5 crore |
| Backup video | Ready ✅ |

---

## Q&A Prep

| Question | Answer |
|---|---|
| "How accurate is the flood model?" | Physics-based (mass conservation, Manning's equation-inspired), validated on synthetic twin. Historical calibration is roadmap item. |
| "Is this real OSM data?" | Yes — T.Nagar road network from OpenStreetMap + SRTM DEM elevation |
| "Can you add more cities?" | Yes — the pipeline is parameterized by `city_id`. New city = new OSM download + graph load. |
| "What about real-time data?" | Architecture has sensor ingestion hooks. Not built in 96h but designed for it. |
| "How does the AI explanation work?" | Jinja2 template (deterministic, always on) + optional LLM narration (GPT/Gemini API key). |
