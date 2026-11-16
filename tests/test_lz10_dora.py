"""Unit tests for change failure classification with synthetic GitHub data only."""
import csv
import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("lz10_dora", ROOT / "scripts" / "dora.py")
dora = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dora)

NOW = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)
DEPLOYED = datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc)
COMMIT_TIME = datetime(2026, 11, 15, 11, 50, tzinfo=timezone.utc)


def create_incidents(tmp_path, incidents):
    path = tmp_path / "incidents.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=[
            "incident_id", "started_at_utc", "restored_at_utc",
            "linked_deployment_id", "remediation_action", "repair_hours", "description"
        ])
        w.writeheader()
        w.writerows(incidents)
    return path


def incident(number, deployment_id="12", hours_after=2, action="fix"):
    started = DEPLOYED + timedelta(hours=hours_after)
    return {
        "incident_id": f"INC-{number}",
        "started_at_utc": started.isoformat(),
        "restored_at_utc": (started + timedelta(minutes=30)).isoformat(),
        "linked_deployment_id": deployment_id,
        "remediation_action": action,
        "repair_hours": "1.0",
        "description": "Synthetic regression",
    }


def run_collect(monkeypatch, tmp_path, states, incidents):
    fake_deployments = []
    for deployment_id in states:
        fake_deployments.append({
            "id": int(deployment_id),
            "sha": f"sha{deployment_id}",
            "created_at": DEPLOYED.isoformat(),
        })

    def fake_pages(path, token, limit=10):
        if "/statuses" in path:
            deployment_id = path.split("/deployments/")[1].split("/")[0]
            return [{"state": states[deployment_id], "created_at": DEPLOYED.isoformat()}]
        return fake_deployments

    monkeypatch.setattr(dora, "collect_pages", fake_pages)
    monkeypatch.setattr(
        dora, "request_json",
        lambda path, token: {"commit": {"committer": {"date": COMMIT_TIME.isoformat()}}},
    )
    return dora.collect(
        "test/example", "lz10-ci-staging", 30, "synthetic-token",
        create_incidents(tmp_path, incidents), NOW
    )


def test_success_with_fix_after_two_hours_counts_as_failed_change(monkeypatch, tmp_path):
    result = run_collect(monkeypatch, tmp_path, {"12": "success"}, [incident(1)])
    assert result["change_failure_rate_percent"] == 100
    assert result["failed_changes_including_incidents"] == 1
    assert result["successful_deployments_with_fix_or_rollback"] == 1
    assert result["restore_time_hours_median"] == 0.5


def test_duplicate_incidents_on_same_deployment_count_once(monkeypatch, tmp_path):
    result = run_collect(
        monkeypatch, tmp_path, {"12": "success", "13": "success"},
        [incident(1, action="rollback"), incident(2, action="fix", hours_after=3)]
    )
    assert result["change_failure_rate_percent"] == 50
    assert result["failed_changes_including_incidents"] == 1


def test_git_failure_with_incident_not_double_counted(monkeypatch, tmp_path):
    result = run_collect(
        monkeypatch, tmp_path, {"12": "failure", "13": "success"},
        [incident(1)]
    )
    assert result["change_failure_rate_percent"] == 50
    assert result["failed_changes_including_incidents"] == 1


def test_unlinked_or_late_incident_is_not_attributed(monkeypatch, tmp_path):
    result = run_collect(
        monkeypatch, tmp_path, {"12": "success", "13": "success"},
        [incident(1, deployment_id="missing"), incident(2, hours_after=30)]
    )
    assert result["change_failure_rate_percent"] == 0
    assert result["incidents_not_attributed_to_change_failure"] == 2


def test_no_deployments_has_unavailable_cfr(monkeypatch, tmp_path):
    result = run_collect(monkeypatch, tmp_path, {}, [])
    assert result["change_failure_rate_percent"] is None
    assert result["restore_time_hours_median"] is None


def test_no_incident_column_backwards_compatible(monkeypatch, tmp_path):
    path = tmp_path / "old_incidents.csv"
    path.write_text(
        "incident_id,started_at_utc,restored_at_utc,failed_deployment_id,repair_hours,description\n"
        "INC-1,2026-11-15T13:00:00Z,2026-11-15T14:00:00Z,12,1,synthetic\n",
        encoding="utf-8",
    )
    rows = dora.load_incidents(path, NOW - timedelta(days=30), NOW)
    assert rows[0]["linked_deployment_id"] == "12"
    assert rows[0]["remediation_action"] == ""
