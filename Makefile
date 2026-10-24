PYTHON ?= python3
NPM ?= npm

.PHONY: demo frontend-build test type-check package submission-check check smoke

demo: frontend-build
	OMNIGRIDX_MODE=demo-local HOST=127.0.0.1 PORT=8000 $(PYTHON) -m uvicorn omnigridx.web.app:app --host 127.0.0.1 --port 8000 --workers 1

frontend-build:
	$(NPM) --prefix frontend ci --no-audit --no-fund
	$(NPM) --prefix frontend run build

test:
	$(PYTHON) -m pytest

type-check:
	$(PYTHON) -m mypy

package: frontend-build
	$(PYTHON) -c "import shutil; shutil.rmtree('dist', ignore_errors=True)"
	$(PYTHON) -m build --no-isolation
	$(PYTHON) -m zipfile -t dist/*.whl
	$(PYTHON) -m tarfile -t dist/*.tar.gz

submission-check:
	$(PYTHON) -m omnigridx.submission --allow-draft

check: test type-check package submission-check

smoke:
	$(PYTHON) -m omnigridx.web.smoke "$(PUBLIC_DEMO_URL)" "$(REPORT_FINGERPRINT)"
