#!/usr/bin/env python3
"""Reproducible DORA metrics using GitHub deployments, not CI runs as deployments.

A passing CI workflow is never counted as a release unless GitHub recorded a
deployment to the explicitly named environment. Missing data stays N/A.
Requires GH_TOKEN (read-only for local use) or GITHUB_TOKEN in Actions.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median
from urllib.parse import urlencode
from urllib.request import Request, urlopen

UTC = timezone.utc


def timestamp(value):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def request_json(path, token):
    req = Request(
        "https://api.github.com" + path,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + token,
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "cardioprognoz-lz10-dora",
        },
    )
    with urlopen(req, timeout=30) as response:
        return json.load(response)


def collect_pages(path, token, limit=10):
    items = []
    for page in range(1, limit + 1):
        separator = "&" if "?" in path else "?"
        data = request_json(path + separator + urlencode({"per_page": 100, "page": page}), token)
        if not isinstance(data, list):
            raise ValueError("Expected a list from GitHub API")
        items.extend(data)
        if len(data) < 100:
            break
    return items


def duration_hours(start, end):
    return round((end - start).total_seconds() / 3600, 3)


def load_incidents(path, start, end):
    result = []
    if not path.exists():
        return result
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if not row.get("incident_id"):
                continue
            a, b = timestamp(row.get("started_at_utc")), timestamp(row.get("restored_at_utc"))
            if a is None:
                continue
            if start <= a <= end:
                result.append({
                    "id": row["incident_id"],
                    "started_at_utc": a.isoformat(),
                    "restored_at_utc": b.isoformat() if b else None,
                    "restore_hours": duration_hours(a, b) if b and b >= a else None,
                    "repair_hours": float(row.get("repair_hours") or 0),
                    # Existing files can still use the legacy failed_deployment_id header.
                    "linked_deployment_id": str(
                        row.get("linked_deployment_id") or row.get("failed_deployment_id") or ""
                    ).strip(),
                    "remediation_action": (row.get("remediation_action") or "").strip().lower(),
                })
    return result


def collect(repo, environment, days, token, incident_file, end):
    cutoff = end - timedelta(days=days)
    deployments = collect_pages(
        "/repos/" + repo + "/deployments?" + urlencode({"environment": environment}),
        token,
    )
    records = []
    for dep in deployments:
        created = timestamp(dep.get("created_at"))
        if not created or created < cutoff or created > end:
            continue
        statuses = collect_pages("/repos/" + repo + "/deployments/" + str(dep["id"]) + "/statuses", token, limit=2)
        # GitHub returns statuses newest first. 'inactive' is an old successful
        # deployment replaced by another, not a deployment failure.
        terminal = next((s for s in statuses if s.get("state") in {"success", "failure", "error"}), None)
        state = terminal["state"] if terminal else "unknown"
        finished = timestamp(terminal.get("created_at")) if terminal else None
        records.append({
            "id": dep["id"],
            "sha": dep.get("sha"),
            "created_at": created.isoformat(),
            "finished_at": finished.isoformat() if finished else None,
            "state": state,
        })

    successes = [r for r in records if r["state"] == "success"]
    failures = [r for r in records if r["state"] in {"failure", "error"}]
    lead_hours = []
    for r in successes:
        if not r.get("sha"):
            continue
        commit = request_json("/repos/" + repo + "/commits/" + r["sha"], token)
        committed = timestamp(commit["commit"]["committer"]["date"])
        deployed = timestamp(r["finished_at"])
        if committed and deployed and deployed >= committed:
            lead_hours.append(duration_hours(committed, deployed))

    incidents = load_incidents(incident_file, cutoff, end)
    restored = [i["restore_hours"] for i in incidents if i["restore_hours"] is not None]
    freq = round(len(successes) / (days / 7), 3) if records else None

    # Count a changed deployment at most ONCE. A GitHub failed deployment is
    # a failure; so is a successful deployment with a documented fix/rollback
    # within 24 hours of that same deployment. An incident without a precise
    # deployment ID and remediation action cannot be attributed reliably.
    completed = {str(r["id"]): r for r in successes + failures}
    failed_change_ids = {str(r["id"]) for r in failures}
    corrected_success_ids = set()
    unattributed_incidents = 0
    for incident in incidents:
        deployment_id = incident["linked_deployment_id"]
        action = incident["remediation_action"]
        if action not in {"fix", "rollback"}:
            if incident["id"]:
                unattributed_incidents += 1
            continue
        deployment = completed.get(deployment_id)
        if deployment is None:
            unattributed_incidents += 1
            continue
        # Github already records a failure; do not double count an incident.
        if deployment["state"] != "success":
            continue
        incident_time = timestamp(incident["started_at_utc"])
        delivered_time = timestamp(deployment["finished_at"])
        if delivered_time is None or incident_time is None:
            unattributed_incidents += 1
            continue
        interval = incident_time - delivered_time
        if timedelta(0) <= interval <= timedelta(hours=24):
            failed_change_ids.add(deployment_id)
            corrected_success_ids.add(deployment_id)
        else:
            unattributed_incidents += 1

    cfr_denominator = len(completed)
    cfr = round(100 * len(failed_change_ids) / cfr_denominator, 2) if cfr_denominator else None
    # MTTR not reported as 0 when no incident exists.
    return {
        "source": "GitHub deployments and deployment statuses API; local incident register",
        "repo": repo, "environment": environment,
        "window_start_utc": cutoff.isoformat(), "window_end_utc": end.isoformat(),
        "deployment_frequency_per_week": freq,
        "lead_time_hours_median": round(median(lead_hours), 3) if lead_hours else None,
        "change_failure_rate_percent": cfr,
        "restore_time_hours_median": round(median(restored), 3) if restored else None,
        "deployment_records": len(records),
        "successful_deployments": len(successes),
        "failed_deployments": len(failures),
        "failed_changes_including_incidents": len(failed_change_ids),
        "successful_deployments_with_fix_or_rollback": len(corrected_success_ids),
        "change_failure_denominator": cfr_denominator,
        "incidents_not_attributed_to_change_failure": unattributed_incidents,
        "unknown_deployments": len(records) - len(successes) - len(failures),
        "recorded_incidents": len(incidents),
        "recovered_incidents": len(restored),
        "repair_hours": round(sum(i["repair_hours"] for i in incidents), 2),
        "deployment_events": records,
        "incidents": incidents,
        "notes": [
            "Environment is ephemeral CI staging (container smoke test), NOT public production.",
            "Passing workflow runs are not treated as deployments.",
            "Failure rate combines GitHub failure/error and linked fix/rollback incidents within 24h (unique deployment IDs).",
            "Incidents without a documented action, matching deployment ID or 24h time window are excluded and counted separately.",
            "The incident register must be kept complete for meaningful CFR; missing incident reports can understate CFR.",
            "Time to restore remains N/A without an observed resolved incident.",
            "Null means unavailable or no relevant observations, not zero.",
            "Small sample sizes are not representative.",
        ],
    }


def save_chart(data, target):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    metrics = [
        ("Deployments / week", "deployment_frequency_per_week"),
        ("Lead time, hours (median)", "lead_time_hours_median"),
        ("Change failure rate, %", "change_failure_rate_percent"),
        ("Restore time, hours (median)", "restore_time_hours_median"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(10, 6.5))
    for ax, (label, key) in zip(axes.flatten(), metrics):
        value = data[key]
        ax.set_title(label)
        ax.set_xticks([])
        if value is None:
            ax.text(0.5, 0.5, "N/A — no observed data", ha="center", va="center", transform=ax.transAxes)
        else:
            ax.bar([0], [value], width=0.45)
            ax.set_xlim(-0.8, 0.8)
            ax.set_ylim(0, max(1, value * 1.4))
            ax.text(0, value + max(0.02, value * 0.03), str(value), ha="center")
    fig.suptitle("CardioPrognoz DORA — " + data["environment"] + "\\n" + data["window_start_utc"][:10] + " to " + data["window_end_utc"][:10])
    fig.tight_layout()
    fig.savefig(target, dpi=160)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", "Dororo345/ml-cardio-project"))
    parser.add_argument("--environment", default="lz10-ci-staging")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--output-dir", default="lz10-results")
    parser.add_argument("--incidents", default="docs/ops/INCIDENTS.csv")
    args = parser.parse_args()
    if args.days < 1:
        parser.error("--days must be >= 1")
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        parser.error("Set GH_TOKEN locally or GITHUB_TOKEN in GitHub Actions. Never commit it.")
    now = datetime.now(UTC)
    report = collect(args.repo, args.environment, args.days, token, Path(args.incidents), now)
    dest = Path(args.output_dir)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "dora.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    with (dest / "deployments.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["id", "sha", "created_at", "finished_at", "state"])
        writer.writeheader()
        writer.writerows(report["deployment_events"])
    save_chart(report, dest / "dora_dashboard.png")
    print(json.dumps({k: v for k, v in report.items() if k not in ("deployment_events", "incidents", "notes")}, indent=2))


if __name__ == "__main__":
    main()
