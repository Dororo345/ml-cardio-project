"""Reproduce metrics from raw GitHub issue/comment exports; no invented dates."""
import csv
import json
import math
import statistics
from datetime import datetime, timedelta
from pathlib import Path
import argparse

STATES = ['Backlog','Ready','In Progress','Waiting Review','Review','Testing','Done']
ACTIVE = STATES[2:-1]
def dt(s):
    return datetime.fromisoformat(s.replace('Z','+00:00'))
def write_csv(path, rows):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def analyze(raw, sprint, out):
    events=[]; cycles=[]; durations=[]
    for task in raw:
        n=task['n']
        e=[dict(sprint=sprint,issue=n,status=c['body'][6:],time=c['created_at'],source=c['html_url']) for c in task['comments'] if c['body'] in ['FLOW: '+s for s in STATES]]
        if task['issue']['closed_at']:
            e.append(dict(sprint=sprint,issue=n,status='Done',time=task['issue']['closed_at'],source=task['issue']['url']))
        e.sort(key=lambda x:x['time'])
        start=next(dt(x['time']) for x in e if x['status']=='In Progress')
        done=next(dt(x['time']) for x in e if x['status']=='Done')
        cycles.append(dict(sprint=sprint,issue=n,start=start.isoformat(),done=done.isoformat(),cycle_minutes=(done-start).total_seconds()/60))
        d=dict(sprint=sprint,issue=n,**{s:0. for s in STATES[:-1]})
        for a,b in zip(e,e[1:]): d[a['status']]+=(dt(b['time'])-dt(a['time'])).total_seconds()/60
        durations.append(d);events+=e
    events.sort(key=lambda e:(e['time'],e['issue']))
    start=min(dt(e['time']) for e in events);end=max(dt(e['time']) for e in events)
    for d in durations:
        first=min(dt(e['time']) for e in events if e['issue']==d['issue'])
        d['Backlog']=(first-start).total_seconds()/60
    instants=sorted(set(dt(e['time']) for e in events))
    snapshots=[];area=0;violation=0;max_wip=0
    for i,t in enumerate(instants):
        counts={s:0 for s in STATES}
        for task in raw:
            hist=[e for e in events if e['issue']==task['n'] and dt(e['time'])<=t]
            counts[hist[-1]['status'] if hist else 'Backlog']+=1
        wip=sum(counts[s] for s in ACTIVE); max_wip=max(max_wip,wip)
        minutes=(instants[i+1]-t).total_seconds()/60 if i+1<len(instants) else 0
        area+=wip*minutes
        if wip>1:violation+=minutes
        snapshots.append(dict(sprint=sprint,time=t.isoformat(),elapsed_minutes=(t-start).total_seconds()/60,**counts,WIP=wip))
    T=(end-start).total_seconds()/60; values=[x['cycle_minutes'] for x in cycles]
    rate=len(cycles)/T; mean=statistics.mean(values)
    summary=dict(start=start.isoformat(),end=end.isoformat(),duration_minutes=T,throughput=len(cycles),throughput_per_minute=rate,mean_cycle_minutes=mean,p85_nearest_rank=sorted(values)[math.ceil(.85*len(values))-1],p85_linear=sorted(values)[-2]+.55*(sorted(values)[-1]-sorted(values)[-2]) if len(values)==4 else None,mean_time_weighted_wip=area/T,max_wip=max_wip,minutes_wip_over_one=violation,little_rhs=rate*mean,little_residual=area/T-rate*mean,status_total_minutes={s:sum(x[s] for x in durations) for s in STATES[:-1]})
    # Daily EOD in UTC+6: both iterations finish on one local date. A terminal
    # daily snapshot is not an estimate of time-weighted WIP for short sessions.
    local_end=end+timedelta(hours=6)
    daily=[dict(sprint=sprint,date_local=local_end.date().isoformat(),snapshot='end of observed session',WIP=0,Done=len(raw))]
    summary['mean_daily_terminal_wip']=0
    summary['mean_daily_integrated_wip_within_session']=area/T
    daily[0]['time_weighted_wip_within_session']=area/T
    for name,rows in [('transitions',events),('cycles',cycles),('status_times',durations),('cfd',snapshots),('daily',daily)]:write_csv(out/f'{sprint}_{name}.csv',rows)
    (out/f'{sprint}_metrics.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    return summary

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--sprint',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    print(json.dumps(analyze(json.loads(a.input.read_text()),a.sprint,a.out),indent=2))
if __name__=='__main__':main()
