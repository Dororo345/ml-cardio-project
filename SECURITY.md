# Security: КардиоПрогноз

This is an **educational prototype**, not for real patient data or clinical use.

- Do not send/upload patient records or identifiers; use only synthetic data.
- Keep the Flask debugger disabled. Demo is bound to `127.0.0.1`.
- Never commit `.env`, API keys, passwords, tokens or backups containing them.
- `joblib.load` uses pickle and can execute code: only load the trusted artifact in `models/`.
- Validation accepts only the 13 known input fields, numeric values and allowed ranges.
- Requests larger than 16 KiB are rejected; use a production reverse proxy and rate limiting before any Internet deployment.
- `README.md` and model metadata must **not** claim future disease risk or clinical validation.
- GitHub Actions includes CI and security workflows; until Actions successfully run, results are **not verified**.

To scan locally when tools are installed:

```powershell
gitleaks detect --source . --verbose
trivy fs --scanners vuln,secret,misconfig .
```

If a token is accidentally pushed, revoke it immediately, then remove it from repo and history as appropriate.
Security reports should not contain real patient inputs.
