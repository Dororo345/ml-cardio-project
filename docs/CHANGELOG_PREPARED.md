# Prepared changes (not pushed)

## Code
- `app.py`: disabled debugger, added localhost bind, JSON limit, error codes/request IDs, safe error response, health endpoint, security headers.
- `validation.py`: strict server-side feature validation.
- `tests/test_validation.py` and `tests/test_http_security.py`: targeted negative and API tests.
- Existing `xai.py`, `templates/index.html`, `models/`, `data/`, `tests/test_mvp.py` kept from the earlier archive. The three original `docs/` files from `ml-cardio-project-main.zip` were retained unchanged.

## GitHub
- `.github/workflows/ci.yml`, `.github/workflows/security.yml` (must be enabled and run in target repository).
- `docs/backlog_LZ4.csv` (20 stories from the old report), `docs/security_issues.csv` (3 tasks).
- `scripts/create_github_issues.py` defaults to **dry-run**, only `--apply` creates issues.
- `README.md`, `SECURITY.md`, `requirements.txt`, `.gitignore`, `docs/GITHUB_SETUP.md`, `docs/STATUS_W9.md`.

## Verification limitations
- The provided GitHub ZIP was reviewed and merged locally; the **remote current branch and Git history are not verified**.
- Full Flask/ML tests and Trivy/Gitleaks were **not run** when preparing this offline package. Confirm in GitHub CI/local Windows environment before merging.
