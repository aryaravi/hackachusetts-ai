# Third-Party Notices

OmniGridX project source, documentation, styles, and the synthetic judge scenario are original repository assets made available under the root `LICENSE`. No third-party marks, music, photographs, customer files, or publisher dataset values are bundled.

## Software

| Component | Owner/publisher | Source | License | Use / attribution |
|---|---|---|---|---|
| Python | Python Software Foundation | https://www.python.org/ | PSF License | Runtime; retain upstream license notice. |
| React and React DOM | Meta Platforms, Inc. and contributors | https://github.com/facebook/react | MIT | Judge UI and compiled `src/omnigridx/web/static/assets/app.js`; retain copyright/license. |
| Vite | Vite contributors | https://github.com/vitejs/vite | MIT | Frontend build; retain copyright/license. |
| @vitejs/plugin-react | Vite contributors | https://github.com/vitejs/vite-plugin-react | MIT | React build integration; retain copyright/license. |
| Starlette | Encode OSS Ltd. and contributors | https://github.com/encode/starlette | BSD-3-Clause | HTTP application; retain copyright/license. |
| Uvicorn | Encode OSS Ltd. and contributors | https://github.com/encode/uvicorn | BSD-3-Clause | ASGI server; retain copyright/license. |
| Jinja2 | Pallets contributors | https://github.com/pallets/jinja | BSD-3-Clause | HTML templating; retain copyright/license. |
| SciPy | SciPy developers | https://github.com/scipy/scipy | BSD-3-Clause | MILP adapter; retain copyright/license. |
| NumPy | NumPy developers | https://github.com/numpy/numpy | BSD-3-Clause | SciPy runtime dependency; retain copyright/license. |
| setuptools | Python Packaging Authority and contributors | https://github.com/pypa/setuptools | MIT | Package build; retain copyright/license. |
| build | Python Packaging Authority and contributors | https://github.com/pypa/build | MIT | Package build frontend; retain copyright/license. |
| pytest | pytest contributors | https://github.com/pytest-dev/pytest | MIT | Test runner; retain copyright/license. |
| Hypothesis | David R. MacIver and contributors | https://github.com/HypothesisWorks/hypothesis | MPL-2.0 | Property-based tests; modifications to covered files remain under MPL-2.0. |
| mypy | Jukka Lehtosalo and contributors | https://github.com/python/mypy | MIT | Static type checking; retain copyright/license. |
| Render | Render Services, Inc. | https://render.com/ | Service terms | Optional free-tier hosting; no Render code or marks are bundled. |

Exact direct dependency versions are pinned in `pyproject.toml`, `frontend/package.json`, and `frontend/package-lock.json`. JavaScript transitive notices remain in lockfile/package metadata; Python transitive notices remain in installed distribution metadata. The compiled UI asset is reproducible with `make frontend-build` and contains React/React DOM code covered by the notices above.

## Public-source discovery metadata

The Massachusetts pack includes only project-authored JSON records naming public publishers, canonical URLs, categories, and intended/prohibited uses. It does not redistribute source values. Publisher terms apply before any production retrieval or reuse.

Publishers referenced: City of Boston; Commonwealth of Massachusetts; Massachusetts Department of Environmental Protection; Homeland Infrastructure Foundation-Level Data; ISO New England; National Weather Service; National Renewable Energy Laboratory; U.S. Environmental Protection Agency; and U.S. Energy Information Administration. Canonical source URLs and attribution identities are recorded in `src/omnigridx/infrastructure/massachusetts_pack.py` and its versioned metadata files.

## Bundled project assets

| Asset | Origin | License / permission | Intended use |
|---|---|---|---|
| `src/omnigridx/infrastructure/data/sample/judge-scenario-v1.json` | Original fictional OmniGridX sample | Root `LICENSE` | Deterministic judge calculation only; contains no real site, person, account, bill, meter identifier, customer measurement, or externally sourced numeric dataset. |
| `frontend/src/` and `src/omnigridx/web/static/index.html` / `assets/index.css` | Original OmniGridX interface source and generated presentation assets | Root `LICENSE` | Judge interface. |
| `src/omnigridx/web/static/assets/app.js` | Vite-generated bundle from original UI plus React/React DOM | Root `LICENSE` for original portions; React MIT license for bundled framework code | Browser judge interface; reproducible from the pinned frontend lockfile. |
