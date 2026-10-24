# Third-Party Notices

OmniGridX project source, documentation, styles, and synthetic fixtures are original repository assets under the root `LICENSE`. No third-party logos, brand artwork, music, photographs, customer files, or publisher files/bulk datasets are bundled. Textual product and publisher names are used nominatively for dependency notices and source attribution. The hackathon snapshot contains a small project-authored transcription of attributed public facts and links.

## Software

| Component | Owner/publisher | Source | License | Distribution scope |
|---|---|---|---|---|
| Python | Python Software Foundation | https://www.python.org/ | PSF License | Runtime platform; not bundled. |
| React, React DOM, Scheduler | Meta Platforms, Inc. and contributors | https://github.com/facebook/react | MIT | Included in the generated browser bundle; full notice in `THIRD_PARTY_LICENSES.md`. |
| Vite | Vite contributors | https://github.com/vitejs/vite | MIT | Build-only dependency; not included as a runtime library. |
| @vitejs/plugin-react | Vite contributors | https://github.com/vitejs/vite-plugin-react | MIT | Build-only dependency. |
| Starlette | Encode OSS Ltd. and contributors | https://github.com/encode/starlette | BSD-3-Clause | Installed separately by the Python package manager. |
| Uvicorn | Encode OSS Ltd. and contributors | https://github.com/encode/uvicorn | BSD-3-Clause | Installed separately by the Python package manager. |
| Jinja2 | Pallets contributors | https://github.com/pallets/jinja | BSD-3-Clause | Installed separately by the Python package manager. |
| SciPy | SciPy developers | https://github.com/scipy/scipy | BSD-3-Clause | Installed separately by the Python package manager. |
| NumPy | NumPy developers and third-party licensors | https://github.com/numpy/numpy | Composite metadata: BSD-3-Clause, 0BSD, MIT, Zlib, CC0-1.0 | Installed as SciPy dependency; consult its installed distribution notices. |
| setuptools | Python Packaging Authority and contributors | https://github.com/pypa/setuptools | MIT | Build-only dependency. |
| build | Python Packaging Authority and contributors | https://github.com/pypa/build | MIT | Local build tool. |
| pytest | pytest contributors | https://github.com/pytest-dev/pytest | MIT | Test-only dependency. |
| Hypothesis | David R. MacIver and contributors | https://github.com/HypothesisWorks/hypothesis | MPL-2.0 | Test-only dependency; no modified Hypothesis source is distributed. |
| mypy | Jukka Lehtosalo and contributors | https://github.com/python/mypy | MIT | Test-only static analysis dependency. |
| Render | Render Services, Inc. | https://render.com/ | Service terms | Hosting service; no Render software or artwork is bundled. |

Exact direct dependency versions are pinned in `pyproject.toml`, `frontend/package.json`, and `frontend/package-lock.json`. All 115 npm dependency records declare a license: 107 MIT, five ISC, one Apache-2.0, one CC-BY-4.0, and one BSD-3-Clause. Vite/Babel/Browserslist data, including `caniuse-lite`, is build-time input and was not found in the generated runtime assets. Python dependencies are installed as separate distributions and retain their own metadata/notices; the project wheel does not vendor their source.

## Public-source fact snapshot

`src/omnigridx/infrastructure/data/hackathon/official-data-v1.json` contains limited factual values, project-authored summaries, canonical links, periods, units, and caveats. It does not contain copied publisher reports, images, charts, or bulk datasets. Publisher terms govern use of linked sources. The snapshot remains explicitly `pending_human_validation`; it must not be described as publisher-approved. Content was rephrased for compliance with licensing restrictions.

Referenced first-party publishers and pages:

- ISO New England: https://www.iso-ne.com/about/where-we-are-going/regional-electricity-outlook/celt-report/
- ISO New England state profiles: https://www.iso-ne.com/about/public-affairs/new-england-state-profiles
- Commonwealth storage reporting: https://www.mass.gov/info-details/esi-goals-storage-target
- Commonwealth clean-power report card: https://www.mass.gov/info-details/2025-massachusetts-climate-report-card-clean-power
- Commonwealth energy-future action: https://www.mass.gov/news/governor-healey-takes-action-to-bring-in-10-gw-of-new-energy-save-10-billion-and-promote-energy-independence
- Commonwealth load-management report: https://www.mass.gov/info-details/peak-potential-load-management-for-an-affordable-net-zero-grid
- U.S. EIA Massachusetts profile: https://www.eia.gov/electricity/state/massachusetts/

The Massachusetts reference pack contains project-authored discovery metadata and does not redistribute publisher values. The public-business JSON/CSV files are project-authored synthetic schema fixtures, as declared in their adjacent `README.md`.

## Bundled project assets

| Asset | Origin | License / permission | Intended use |
|---|---|---|---|
| `data/sample/judge-scenario-v1.json` | Original fictional OmniGridX sample | Root `LICENSE` | Deterministic calculation; no real site, person, account, bill, meter, or customer measurement. |
| `data/public_business/2026.1/*` | Original synthetic OmniGridX fixtures | Root `LICENSE` | Schema development only; not official or current data. |
| `data/hackathon/official-data-v1.json` | Project-authored transcription of attributed public facts | Factual use with source links; publisher terms apply | Context-only simulated report and review workflow. |
| `frontend/src/` and generated static HTML/CSS | Original OmniGridX interface | Root `LICENSE` | Full-stack demo presentation. |
| `src/omnigridx/web/static/assets/app.js` | Vite bundle of original UI plus React/React DOM/Scheduler | Root `LICENSE` for original portions; Meta MIT for framework code | Browser interface; reproducible from the pinned lockfile. |

## Technical review record — October 24, 2026

A repository-wide technical review covered all tracked files and Git-history blobs for common credential, private-key, SSN, email, customer-data, binary, media, font, and logo patterns; dependency declarations; generated assets; source/data provenance; license files; notices; and submission disclosures.

No credential, private key, SSN, real customer record, tracked media/font file, or third-party logo/artwork was found. The only email-shaped fixture uses the reserved `.invalid` domain. Generated React code retains upstream license headers, and the full Meta MIT text is distributed in `THIRD_PARTY_LICENSES.md`.

This record is a technical audit, not legal advice, a plagiarism determination, source-website terms acceptance, or trademark clearance. Contributors remain responsible for confirming ownership and authorization to license their work, acceptance of public Git/Kiro metadata, source terms, nominative brand use, and availability of the OmniGridX name. Submission metadata remains draft until its human-owned team, representative, video, and final-commit fields are populated.
