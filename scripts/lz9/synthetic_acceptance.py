"""50 unique synthetic HTTP cases. No patient records and no manual-UAT claims."""
import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))

def cases():
    rows=[]
    for i in range(40):
        payload=dict(age=40+i,sex=i%2,cp=1+i%4,trestbps=110+(i*3)%60,chol=170+(i*7)%140,fbs=i%2,restecg=i%3,thalach=100+(i*5)%90,exang=(i//2)%2,oldpeak=round(i%21*.2,1),slope=1+i%3,ca=i%4,thal=[3,6,7][i%3])
        rows.append((f'valid_{i+1:02}',payload,200,None))
    base=rows[0][1]
    mutations=[('age',-1,'OUT_OF_RANGE'),('age',121,'OUT_OF_RANGE'),('age','59','INVALID_FIELD'),('chol',79,'OUT_OF_RANGE'),('trestbps',261,'OUT_OF_RANGE'),('cp',9,'INVALID_CATEGORY'),('thal',99,'INVALID_CATEGORY'),('oldpeak',8,'OUT_OF_RANGE'),('sex',True,'INVALID_FIELD'),('ca',None,'INVALID_FIELD')]
    for i,(field,value,code) in enumerate(mutations):rows.append((f'invalid_{i+1:02}',{**base,field:value},400,code))
    return rows

def run(base_url):
    results=[]
    for name,payload,expected,code in cases():
        request=Request(base_url+'/predict',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
        try: response=urlopen(request,timeout=15)
        except HTTPError as error: response=error
        with response:
            actual=response.status;result=json.load(response)
            passed=actual==expected and bool(result.get('request_id')) and result.get('request_id')==response.headers['X-Request-ID']
        if expected==200:
            passed=passed and 0<=result.get('probability',-1)<=1 and result.get('predicted_class') in [0,1] and bool(result.get('model_version')) and result.get('xai_status')=='available' and len(result.get('factors',[]))==3
        else:
            passed=passed and result.get('code')==code and not ({'probability','predicted_class','factors'} & result.keys())
        results.append(dict(case=name,expected=expected,actual=actual,passed=bool(passed),request_id=result.get('request_id'),model_version=result.get('model_version',''),error_code=result.get('code',''),input_json=json.dumps(payload,sort_keys=True),observed_utc=datetime.now(timezone.utc).isoformat()))
    return results

def main():
    from werkzeug.serving import make_server
    from app import app
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=Path('test-results/synthetic_50.csv'));args=parser.parse_args()
    server=make_server('127.0.0.1',0,app);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:results=run(f'http://127.0.0.1:{server.server_port}')
    finally:server.shutdown();thread.join(timeout=5);server.server_close()
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(results[0]));writer.writeheader();writer.writerows(results)
    good=sum(r['passed'] for r in results);negative=sum(r['expected']!=200 for r in results)
    print(f'{good}/{len(results)} passed; {negative} negative; {len(results)-negative} positive; unique inputs={len({r["input_json"] for r in results})}')
    return 0 if good==len(results) else 1
if __name__=='__main__':raise SystemExit(main())
