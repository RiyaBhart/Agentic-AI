import argparse,csv,json,time
from pathlib import Path
from datetime import datetime,timezone,timedelta
from urllib.request import urlopen
from statistics import median
p=argparse.ArgumentParser()
p.add_argument('--count',type=int,default=10)
p.add_argument('--tool',choices=['air','weather','heat_index','kb'])
p.add_argument('--summary',action='store_true')
a=p.parse_args()
log=Path(__file__).resolve().parent.parent / 'data' / 'tool_timings.csv'
pk=timezone(timedelta(hours=5))
urls={'air':'https://air-quality-api.open-meteo.com/v1/air-quality?latitude=24.86&longitude=67.01&current=pm2_5,pm10','weather':'https://api.open-meteo.com/v1/forecast?latitude=24.86&longitude=67.01&current=temperature_2m,relative_humidity_2m,wind_speed_10m'}
def remote(kind):
    with urlopen(urls[kind],timeout=8) as response:
        current=json.load(response)['current']
        fields=urls[kind].split('current=')[1].split(',')
        if any(current[k] is None for k in fields):
            raise ValueError('missing reading')
        return response.status
def heat():
    # NWS Rothfusz regression, 95 F, 65 percent RH (no adjustments at this input).
    t,h=95.,65.
    return -42.379+2.04901523*t+10.14333127*h-.22475541*t*h-.00683783*t*t-.05481717*h*h+.00122874*t*t*h+.00085282*t*h*h-.00000199*t*t*h*h
kb={'heat':'https://www.who.int/news-room/fact-sheets/detail/climate-change-heat-and-health','air':'https://www.who.int/health-topics/air-pollution'}
if not a.summary:
    with log.open('a',newline='',encoding='utf8') as f:
        w=csv.writer(f)
        if f.tell()==0: w.writerow(['timestamp_pkt','tool','seconds','status','detail'])
        for i in range(a.count):
            for kind,call in [('air',lambda:remote('air')),('weather',lambda:remote('weather')),('heat_index',heat),('kb',lambda:kb['heat'])]:
                if a.tool and kind != a.tool: continue
                timestamp=datetime.now(pk).isoformat()
                start=time.perf_counter()
                try: detail,status=call(),'ok'
                except Exception as exc: detail,status=str(exc),'error'
                w.writerow([timestamp,kind,time.perf_counter()-start,status,detail]); f.flush()
            time.sleep(.25)
with log.open(encoding='utf8') as f:
    rows=[r for r in csv.DictReader(f) if r['status']=='ok']
complete=True
for kind in ('air','weather','heat_index','kb'):
    subset=[r for r in rows if r['tool']==kind]
    days={r['timestamp_pkt'][:10] for r in subset}
    print(kind,len(subset),sorted(days))
    if kind in urls: complete &= len(subset)>=20 and len(days)>=2
print('complete' if complete else 'provisional',median(float(r['seconds']) for r in rows) if rows else None)

