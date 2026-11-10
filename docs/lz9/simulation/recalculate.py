"""Rebuild metrics and charts from the explicitly simulated event log."""
import csv
import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent
STAGES = ['Backlog', 'Ready', 'In Progress', 'Waiting Review', 'Review', 'Testing', 'Done']
ACTIVE = STAGES[2:6]
WEEKS = {'S1': date(2026, 11, 9), 'S2': date(2026, 11, 16)}
TZ = timezone(timedelta(hours=6))
HOURS = 40


def timestamp(sprint, hour):
    day = min(int(hour // 8), 4)
    day_start = datetime.combine(WEEKS[sprint] + timedelta(days=day), time(9), TZ)
    return (day_start + timedelta(hours=hour - day * 8)).isoformat(timespec='minutes')


def write_csv(name, rows):
    with (ROOT / name).open('w', encoding='utf-8-sig', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def calculate(sprint, source):
    by_issue = {}
    for row in source:
        if row['sprint'] == sprint:
            assert row['source'] == 'simulation'
            hour = float(row['working_hour'])
            assert row['model_local_time'] == timestamp(sprint, hour)
            by_issue.setdefault(int(row['issue']), {})[row['status']] = hour
    expected = range(14, 18) if sprint == 'S1' else range(18, 22)
    assert sorted(by_issue) == list(expected)
    cycles = []
    residence = []
    for issue, item in sorted(by_issue.items()):
        values = [item[stage] for stage in STAGES]
        assert values[0] == 0 and values[1] >= 0
        assert all(a < b for a, b in zip(values[1:], values[2:])) and values[-1] < HOURS
        cycles.append(dict(sprint=sprint, issue=issue, start=timestamp(sprint, values[2]),
                           done=timestamp(sprint, values[-1]), cycle_h=values[-1] - values[2]))
        for stage, start, end in zip(STAGES, values, values[1:] + [HOURS]):
            residence.append(dict(sprint=sprint, issue=issue, status=stage, hours=end - start))

    def counts(at, inclusive=True):
        values = dict.fromkeys(STAGES, 0)
        for item in by_issue.values():
            statuses = [s for s in STAGES if item[s] < at or (inclusive and item[s] == at)]
            values[statuses[-1] if statuses else 'Backlog'] += 1
        return values

    grid = sorted({*range(0, HOURS + 1, 8), *(v for item in by_issue.values() for v in item.values())})
    cfd = [dict(working_hour=x, **counts(x), wip=sum(counts(x)[s] for s in ACTIVE)) for x in grid]
    intervals = [(a['working_hour'], b['working_hour'], a['wip']) for a, b in zip(cfd, cfd[1:])]
    daily = []
    for d in range(5):
        lo, hi = 8*d, 8*(d+1)
        area = sum(max(0, min(b, hi)-max(a, lo))*w for a,b,w in intervals)
        end = counts(hi, inclusive=False)
        daily.append(dict(day=d+1, date=(WEEKS[sprint]+timedelta(days=d)).isoformat(),
                          mean_wip=area/8, end_wip=sum(end[s] for s in ACTIVE), **end))
    times = sorted(row['cycle_h'] for row in cycles)
    avg_wip = sum((b-a)*w for a,b,w in intervals)/HOURS
    total = {s:sum(r['hours'] for r in residence if r['status']==s) for s in STAGES}
    peaks = {s:max(r[s] for r in cfd) for s in STAGES}
    assert sum(total.values()) == len(by_issue) * HOURS
    assert sum(total[s] for s in ACTIVE) == sum(times)
    assert mean(d['mean_wip'] for d in daily) == avg_wip
    assert all(peaks[s] <= limit for s,limit in zip(ACTIVE,[2,2,1,2]))
    assert all(r['Waiting Review']+r['Review'] <= 3 for r in cfd)
    assert cfd[-1]['Done'] == 4 and cfd[0]['wip'] == cfd[-1]['wip'] == 0
    if sprint == 'S2':
        assert max(r['wip'] for r in cfd) == 1
    metrics = dict(throughput=len(times), rate_day=len(times)/5, mean_cycle_h=mean(times),
                   p85_h=times[2]+0.55*(times[3]-times[2]), p85_nearest_h=times[3],
                   mean_wip=avg_wip, max_wip=max(r['wip'] for r in cfd),
                   snapshot_wip=mean(r['end_wip'] for r in daily),
                   over_one_h=sum(b-a for a,b,w in intervals if w>1),
                   little_rhs=len(times)/5*mean(times)/8, status_h=total, status_peaks=peaks)
    assert abs(metrics['little_rhs']-avg_wip)<1e-12
    for suffix, rows in [('cycles', cycles), ('status_hours',residence), ('daily',daily), ('cfd',cfd)]:
        write_csv(f'{sprint}_{suffix}.csv', [dict(source='simulation', **r) for r in rows])
    return metrics, cfd


def draw(sprint, rows):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    stages = list(reversed(STAGES))
    colors = ['#34916e','#e7b447','#a17cba','#cb7895','#367bb4','#80b9d1','#e1e6eb']
    fig, ax = plt.subplots(figsize=(9.0, 4.0))
    ax.stackplot([r['working_hour']/8 for r in rows],
                 *[[r[s] for r in rows] for s in stages], labels=stages, colors=colors, step='post')
    ax.set(xlim=(0,5), ylim=(0,4.15), ylabel='Карточки, шт.',
           xlabel='Границы рабочих дней (09:00–17:00 UTC+6)', title=f'{sprint} · CFD по смоделированным переходам')
    ax.set_xticks(range(6), ['Старт'] + [f'{i}-й день' for i in range(1,6)])
    ax.set_yticks(range(5))
    ax.grid(alpha=.24)
    ax.legend(loc='upper center', bbox_to_anchor=(.5,-.21), ncol=4, frameon=False, fontsize=8.5)
    fig.tight_layout()
    fig.savefig(ROOT / f'CFD_{sprint}_simulation.png', dpi=180)
    plt.close(fig)


def main():
    with (ROOT / 'model_transitions.csv').open(encoding='utf-8-sig',newline='') as file:
        source = list(csv.DictReader(file))
    assert len(source) == 56
    result = {}
    for sprint in WEEKS:
        result[sprint], cfd = calculate(sprint, source)
        draw(sprint, cfd)
    (ROOT/'metrics.json').write_text(json.dumps({'source':'simulation', **result}, ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__ == '__main__':
    main()
