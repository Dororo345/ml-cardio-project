"""Reproduce explicitly simulated LZ9 metrics, with no GitHub event mutation."""
from pathlib import Path
import csv,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'simulation';OUT.mkdir(exist_ok=True)
STATES=['Backlog','Ready','In Progress','Waiting Review','Review','Testing','Done']
SPECS={'S1':{'CARD-13':[1,8,14,16,20],'CARD-14':[3,12,16,18,24],'CARD-17':[20,25,29,30,34]},'S2':{'CARD-19':[1,10,11,13,17],'CARD-20':[18,28,29,31,37]}}
def write(name,rows):
 with (OUT/name).open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
all_events=[];summary=[]
for sprint,tasks in SPECS.items():
 events=[]
 for card,ts in tasks.items():
  for state,t in zip(STATES,[0,.5]+ts):
   events.append(dict(source='simulation',sprint=sprint,card=card,work_hour=t,day=min(int(t//8)+1,5),hour_in_day=t%8,to_status=state))
 events.sort(key=lambda x:(x['work_hour'],x['card']));all_events+=events
 def status(card,t):return [e['to_status'] for e in events if e['card']==card and e['work_hour']<=t][-1]
 def counts(t):return {s:sum(status(c,t)==s for c in tasks) for s in STATES}
 times=sorted({0,40}|{e['work_hour'] for e in events})
 area={s:0. for s in STATES};daily=[];mx=0;violation=0
 for a,b in zip(times,times[1:]):
  c=counts(a);w=sum(c[s] for s in STATES[2:6]);mx=max(mx,w);violation+=(b-a)*(w>1)
  for s in STATES:area[s]+=(b-a)*c[s]
 for d in range(5):
  a,b=d*8,(d+1)*8;cuts=sorted({a,b}|{t for t in times if a<t<b});ar=0
  for x,y in zip(cuts,cuts[1:]):ar+=(y-x)*sum(counts(x)[s] for s in STATES[2:6])
  daily.append(dict(sprint=sprint,day=d+1,mean_wip=ar/8,snapshot_wip=sum(counts(b)[s] for s in STATES[2:6]),**counts(b)))
 cycles=[dict(sprint=sprint,card=c,start=ts[0],done=ts[-1],cycle=ts[-1]-ts[0],lead_from_ready=ts[-1]-.5) for c,ts in tasks.items()]
 vals=[x['cycle'] for x in cycles];n=len(vals);avg=float(np.mean(vals));L=sum(area[s] for s in STATES[2:6])/40
 assert abs(L-(n/5)*(avg/8))<1e-10
 summary.append(dict(sprint=sprint,tasks=n,days=5,throughput_day=n/5,mean_cycle=avg,p85_linear=float(np.percentile(vals,85)),p85_nearest=sorted(vals)[int(np.ceil(.85*n))-1],mean_wip=L,max_wip=mx,hours_wip_gt1=violation,mean_lead=float(np.mean([x['lead_from_ready'] for x in cycles])),**{'area_'+s:area[s] for s in STATES}))
 write(sprint+'_cycles.csv',cycles);write(sprint+'_daily.csv',daily);write(sprint+'_status_hours.csv',[dict(status=s,task_hours=area[s],mean_per_task=area[s]/n) for s in STATES])
 write(sprint+'_cfd.csv',[dict(work_hour=t,**counts(t)) for t in times])
 order=list(reversed(STATES));ys=np.array([[counts(t)[s] for t in times] for s in order]);base=np.zeros(len(times))
 fig,ax=plt.subplots(figsize=(10.8,5));colors=['#20745a','#70a4c3','#4a709b','#dca558','#c5d9ed','#dbe4ec','#eef1f5']
 for s,y,color in zip(order,ys,colors):
  ax.fill_between(times,base,base+y,step='post',label=s,color=color,edgecolor='white',linewidth=.5);base+=y
 ax.set(xlim=(0,40),ylim=(0,n),xlabel='Рабочие часы от начала модельного спринта',ylabel='Число карточек',title=f'{sprint} — CFD по симулированным событиям')
 ax.set_xticks([0,8,16,24,32,40]);ax.set_yticks(range(n+1));ax.legend(loc='upper center',bbox_to_anchor=(.5,-.17),ncol=4,frameon=False);ax.grid(axis='x',alpha=.15);fig.tight_layout();fig.savefig(OUT/f'{sprint}_CFD.png',dpi=180);plt.close(fig)
write('model_transitions.csv',all_events);write('summary.csv',summary)
(OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
print(json.dumps(summary,ensure_ascii=False,indent=2))
