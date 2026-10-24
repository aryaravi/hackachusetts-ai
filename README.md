# OmniGridX

Electrification and new clean generation are changing when New England needs power. OmniGridX connects recent official Massachusetts and ISO New England context to a checked, sample-only commercial-site dispatch model, then demonstrates how a human-in-the-loop review could govern an AI-drafted report.

The app presents solar, wind, hydro, nuclear, geothermal, storage, demand flexibility, and efficiency as distinct options. Its calculation engine still compares exactly three schedules over one synthetic site: existing operation, a clean-generation-first rule, and SciPy MILP–optimized dispatch. This optimization is constrained grid intelligence, not AI forecasting. Every published schedule passes a separate constraint checker.

> The Fast Judge MVP uses synthetic bundled calculation data only. Cost is a `Screening_Estimate`; outage results are deterministic `Outage_Service_Screening`. It has no AI, weather, or demand forecasting. It also has no verified tariff, customer data, upload path, local-grid feasibility assessment, or autonomous control.

> The additional `Simulated_AI_Draft` is a deterministic template: no model or external AI service is called. All people, approvals, financial limits, and operational actions are fictional. They have no legal, financial, regulatory, procurement, or control effect.

## Local setup

Requirements: Git, Python **3.13.13**, Node **18.20.8**, and npm. From a fresh machine:

```bash
git clone https://github.com/aryaravi/hackachusetts-ai.git
cd hackachusetts-ai
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
make demo
```

Open <http://127.0.0.1:8000>. `make demo` installs the exact frontend lockfile, builds React, and starts the full-stack Python service on loopback. Stop it with `Ctrl-C`.

## Pages and API

The React app has six explicit pages:

- `/overview` — regional context, checked site results, and review progress
- `/grid-data` — 14 pinned official-source metrics with periods and limitations
- `/clean-options` — eight generation/flexibility options and the three checked schedules
- `/ai-draft` — deterministic simulated AI narrative with evidence IDs
- `/approvals` — ordered analyst, provider, government-data, and manager acknowledgements
- `/sources` — publisher, period, limitation, and snapshot provenance

The bounded API surface is:

- `GET /healthz` — ready only after the report, official snapshot, draft, and workflow initialize
- `GET /api/sample-report` — unchanged deterministic Fast Judge report JSON
- `POST /api/sample-run` — rerun bundled bytes; request bodies are rejected
- `GET /api/simulation` — official-context, draft, and approval simulation envelope
- `POST /api/simulation/approvals` — record the one expected synthetic role
- `POST /api/simulation/reset` — clear only the simulated review sequence

Uploads, caller scenarios, arbitrary source URLs, customer data, authentication claims, real approvals, spending, and equipment control remain unavailable.

## Data and review limits

`src/omnigridx/infrastructure/data/hackathon/official-data-v1.json` is a manually curated, pinned fact snapshot retrieved on October 24, 2026. It cites ISO New England, the Commonwealth of Massachusetts, and the U.S. Energy Information Administration. It is not a live feed or archive of publisher files. Queue, pipeline, forecast, policy-target, historical, and site values remain separate and are marked pending human validation.

The approval state is shared in one process, unauthenticated, and erased on restart or redeploy. It exists only to demonstrate ordering and separation of review roles. A production workflow would require real identity, MFA, role authorization, tenant isolation, durable audit storage, signatures, and controlled integrations.

## Verification and packaging

With the virtual environment active, run:

```bash
make check
```

This builds the frontend, runs Python tests and strict typing, builds both package formats, and validates draft submission structure. It performs no live source retrieval and sends no customer data.

## Architecture

- `frontend/` — React 19 multi-page interface built with Vite
- `src/omnigridx/domain/` — immutable units, records, simulation, and constraints
- `src/omnigridx/application/` — dispatch, optimization, metrics, orchestration, and reporting
- `src/omnigridx/infrastructure/` — pinned context, synthetic sample, SciPy, SQLite, and local snapshots
- `src/omnigridx/web/` — Starlette API, React static host, and hosted smoke validator

The app is one modular monolith. React presents backend values; it does not recalculate energy results.

## Render deployment

`render.yaml` defines one free Python web service. Link the public repository in Render and deploy the blueprint. The build installs locked React dependencies, emits static assets, packages the pinned JSON snapshot, and installs Python. Startup binds Uvicorn to platform `$PORT` with `OMNIGRIDX_MODE=demo-public` and one worker.

Free hosting may cold-start for several minutes. All state is ephemeral, and simulated approvals are shared between visitors until restart. Free-tier limits and availability can change. If hosted access is unavailable, use `make demo` locally.

After deployment, record the HTTPS URL and public-mode report fingerprint in `submission-metadata.json`, then run:

```bash
make smoke PUBLIC_DEMO_URL=https://YOUR-SERVICE.onrender.com REPORT_FINGERPRINT=YOUR_SHA256
```

## Submission evidence and assets

See `SUBMISSION_WRITEUP.md`, `THIRD_PARTY_NOTICES.md`, `submission-metadata.json`, `LICENSE`, and `.kiro/specs/omnigridx/`. The calculation scenario is fictional and contains no person, site, account, bill, meter identifier, or customer measurement.
