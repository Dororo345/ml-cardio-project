"""ЛЗ9: выгрузка реальных переходов Issues из GitHub API. Никакой симуляции."""
import argparse
import csv
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import re
from urllib.request import Request, urlopen

SPRINTS = {
    "S1": ("2026-11-09", "2026-11-14", [14, 15, 16, 17]),
    "S2": ("2026-11-16", "2026-11-21", [18, 19, 20, 21]),
}
STATES = ("Ready", "In Progress", "Waiting Review", "Review", "Testing", "Done")
ACTIVE = set(STATES[1:-1])
FLOW = re.compile(r"^FLOW: (Ready|In Progress|Waiting Review|Review|Testing)$", re.MULTILINE)

def parse_dt(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)

def get(url):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "CardioPrognoz-LZ9", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    with urlopen(Request(url, headers=headers), timeout=30) as response:
        return json.load(response)

def paginate(url):
    rows, page = [], 1
    while True:
        join = "&" if "?" in url else "?"
        part = get(f"{url}{join}per_page=100&page={page}")
        rows += part
        if len(part) < 100:
            return rows
        page += 1

def export(repo):
    rows, warnings = [], []
    for sprint, (_, _, ids) in SPRINTS.items():
        for number in ids:
            url = f"https://api.github.com/repos/{repo}/issues/{number}"
            issue = get(url)
            found = []
            for comment in paginate(url + "/comments"):
                match = FLOW.findall(comment.get("body") or "")
                if len(match) == 1:
                    found.append((comment["created_at"], match[0], f"comment:{comment['id']}"))
                elif len(match) > 1:
                    warnings.append(f"#{number}: неоднозначный FLOW comment")
            for event in paginate(url + "/events"):
                if event["event"] in ("closed", "reopened"):
                    status = "Done" if event["event"] == "closed" else "Ready"
                    found.append((event["created_at"], status, f"event:{event['id']}"))
            for when, status, ref in found:
                rows.append(dict(sprint=sprint, issue_id=number, title=issue["title"], event_time=parse_dt(when).isoformat(), status=status, source="GITHUB_API", event_ref=ref, issue_url=issue["html_url"]))
            if not found:
                warnings.append(f"#{number}: нет событий перехода")
    return sorted(rows, key=lambda r: (r["event_time"], r["issue_id"])), warnings

def metrics(events):
    summary, daily, cycles = {}, [], []
    for sprint, (a, b, ids) in SPRINTS.items():
        start = datetime.fromisoformat(a).replace(tzinfo=timezone.utc)
        end = datetime.fromisoformat(b).replace(tzinfo=timezone.utc)
        times, completed = [], 0
        for number in ids:
            task = sorted((r for r in events if r["issue_id"] == number and r["sprint"] == sprint), key=lambda r: r["event_time"])
            begun = next((parse_dt(r["event_time"]) for r in task if r["status"] == "In Progress"), None)
            finished = next((parse_dt(r["event_time"]) for r in task if r["status"] == "Done" and start <= parse_dt(r["event_time"]) < end), None)
            if finished:
                completed += 1
                if begun and begun <= finished:
                    days = round((finished-begun).total_seconds()/86400, 5)
                    times.append(days)
                    cycles.append(dict(sprint=sprint, issue_id=number, cycle_days=days, start=begun.isoformat(), done=finished.isoformat()))
        snapshots = []
        current = start
        while current < end:
            instant = current.replace(hour=17)
            state_counts = {state: 0 for state in STATES}
            for number in ids:
                history = sorted((r for r in events if r["sprint"] == sprint and r["issue_id"] == number and parse_dt(r["event_time"]) <= instant), key=lambda r: r["event_time"])
                if history:
                    state_counts[history[-1]["status"]] += 1
            wip = sum(state_counts[s] for s in ACTIVE)
            daily.append(dict(sprint=sprint, date_utc=current.date().isoformat(), **state_counts, WIP=wip))
            snapshots.append(wip)
            current += timedelta(days=1)
        ordered = sorted(times)
        summary[sprint] = {
            "planned_issues": ids, "throughput": completed, "cycle_time_samples": len(times),
            "mean_cycle_days": round(sum(times)/len(times), 3) if times else None,
            "p85_cycle_days_nearest_rank": ordered[math.ceil(len(ordered)*.85)-1] if times else None,
            "mean_daily_wip": round(sum(snapshots)/len(snapshots), 3) if any(r["sprint"] == sprint for r in events) else None,
            "source": "GITHUB_API",
        }
    return summary, daily, cycles

def csv_write(path, rows, fields):
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        w = csv.DictWriter(file, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="Dororo345/ml-cardio-project")
    parser.add_argument("--out", type=Path, default=Path("lz9_real_results"))
    args = parser.parse_args()
    events, warnings = export(args.repo)
    summary, daily, cycles = metrics(events)
    args.out.mkdir(parents=True, exist_ok=True)
    csv_write(args.out / "github_transitions.csv", events, ["sprint", "issue_id", "title", "event_time", "status", "source", "event_ref", "issue_url"])
    csv_write(args.out / "daily_cfd.csv", daily, ["sprint", "date_utc", *STATES, "WIP"])
    csv_write(args.out / "cycle_times.csv", cycles, ["sprint", "issue_id", "cycle_days", "start", "done"])
    (args.out / "metrics.json").write_text(json.dumps(dict(metrics=summary, warnings=warnings), ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        for sprint in SPRINTS:
            rows = [r for r in daily if r["sprint"] == sprint]
            order = ["Done", "Testing", "Review", "Waiting Review", "In Progress", "Ready"]
            fig, ax = plt.subplots(figsize=(9, 4.5))
            ax.stackplot(range(len(rows)), *[[r[s] for r in rows] for s in order], labels=order)
            ax.set_xticks(range(len(rows)), [r["date_utc"][5:] for r in rows])
            ax.set_title(f"CardioPrognoz {sprint} | real GitHub issue events")
            ax.set_ylabel("Issues")
            ax.legend(fontsize=7)
            fig.tight_layout()
            fig.savefig(args.out / f"cfd_{sprint}.png", dpi=160)
            plt.close(fig)
    except ImportError:
        print("matplotlib not installed; CSV and JSON created")
    print(json.dumps(dict(metrics=summary, warnings=warnings), ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
