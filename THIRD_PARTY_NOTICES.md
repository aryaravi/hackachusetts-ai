# Third-Party Notices

OmniGridX project source, documentation, styles, and synthetic judge scenario are original repository assets under the root `LICENSE`. No third-party marks, music, photographs, customer files, or publisher files/bulk datasets are bundled. The hackathon snapshot contains a small project-authored transcription of attributed public facts and links.

## Software

| Component | Owner/publisher | Source | License | Use / attribution |
|---|---|---|---|---|
| Python | Python Software Foundation | https://www.python.org/ | PSF License | Runtime; retain upstream license notice. |
| React and React DOM | Meta Platforms, Inc. and contributors | https://github.com/facebook/react | MIT | UI and compiled bundle; retain copyright/license. |
| Vite | Vite contributors | https://github.com/vitejs/vite | MIT | Frontend build; retain copyright/license. |
| @vitejs/plugin-react | Vite contributors | https://github.com/vitejs/vite-plugin-react | MIT | React build integration; retain copyright/license. |
| Starlette | Encode OSS Ltd. and contributors | https://github.com/encode/starlette | BSD-3-Clause | HTTP application; retain copyright/license. |
| Uvicorn | Encode OSS Ltd. and contributors | https://github.com/encode/uvicorn | BSD-3-Clause | ASGI server; retain copyright/license. |
| Jinja2 | Pallets contributors | https://github.com/pallets/jinja | BSD-3-Clause | Deterministic report export; retain copyright/license. |
| SciPy | SciPy developers | https://github.com/scipy/scipy | BSD-3-Clause | MILP adapter; retain copyright/license. |
| NumPy | NumPy developers | https://github.com/numpy/numpy | BSD-3-Clause | SciPy runtime dependency; retain copyright/license. |
| setuptools | Python Packaging Authority and contributors | https://github.com/pypa/setuptools | MIT | Package build; retain copyright/license. |
| build | Python Packaging Authority and contributors | https://github.com/pypa/build | MIT | Package build frontend; retain copyright/license. |
| pytest | pytest contributors | https://github.com/pytest-dev/pytest | MIT | Test runner; retain copyright/license. |
| Hypothesis | David R. MacIver and contributors | https://github.com/HypothesisWorks/hypothesis | MPL-2.0 | Property tests; modifications to covered files remain MPL-2.0. |
| mypy | Jukka Lehtosalo and contributors | https://github.com/python/mypy | MIT | Static type checking; retain copyright/license. |
| Render | Render Services, Inc. | https://render.com/ | Service terms | Optional free-tier hosting; no Render code or marks are bundled. |

Exact direct dependency versions are pinned in `pyproject.toml`, `frontend/package.json`, and `frontend/package-lock.json`. The compiled UI is reproducible with `make frontend-build`.

## Public-source fact snapshot

`src/omnigridx/infrastructure/data/hackathon/official-data-v1.json` contains limited factual values, project-authored summaries, canonical links, periods, units, and caveats. It does not contain copied publisher reports, images, charts, or bulk datasets. Publisher terms govern use of the linked sources. Content was rephrased for compliance with licensing restrictions.

Referenced first-party publishers and pages:

- ISO New England: https://www.iso-ne.com/about/where-we-are-going/regional-electricity-outlook/celt-report/
- ISO New England state profiles: https://www.iso-ne.com/about/public-affairs/new-england-state-profiles
- Commonwealth storage reporting: https://www.mass.gov/info-details/esi-goals-storage-target
- Commonwealth clean-power report card: https://www.mass.gov/info-details/2025-massachusetts-climate-report-card-clean-power
- Commonwealth energy-future action: https://www.mass.gov/news/governor-healey-takes-action-to-bring-in-10-gw-of-new-energy-save-10-billion-and-promote-energy-independence
- Commonwealth load-management report: https://www.mass.gov/info-details/peak-potential-load-management-for-an-affordable-net-zero-grid
- U.S. EIA Massachusetts profile: https://www.eia.gov/electricity/state/massachusetts/

The separate Massachusetts reference pack contains project-authored discovery metadata for additional publishers and does not redistribute their source values.

## Bundled project assets

| Asset | Origin | License / permission | Intended use |
|---|---|---|---|
| `data/sample/judge-scenario-v1.json` | Original fictional OmniGridX sample | Root `LICENSE` | Deterministic calculation; no real site, person, account, bill, meter, or customer measurement. |
| `data/hackathon/official-data-v1.json` | Project-authored transcription of attributed public facts | Factual use with source links; publisher terms apply | Context-only simulated report and review workflow. |
| `frontend/src/` and `src/omnigridx/web/static/index.html` / `assets/index.css` | Original OmniGridX interface | Root `LICENSE` | Full-stack demo presentation. |
| `src/omnigridx/web/static/assets/app.js` | Vite bundle of original UI plus React/React DOM | Root `LICENSE` for original portions; React MIT for framework code | Browser interface; reproducible from the pinned lockfile. |
