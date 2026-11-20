#!/usr/bin/env python3
import json,gzip,hashlib,pathlib,sys,re
from datetime import datetime,timedelta,timezone

ROOT=pathlib.Path('.')
EVENTS='docs/evidence/phase57-msh-entry-long-v1-preimplementation-feasibility-events.ndjson.gz'
PATHS='docs/evidence/phase57-msh-entry-long-v2-development/paths.json.gz'
JST=timezone(timedelta(hours=9))

def sha(b): return hashlib.sha256(b).hexdigest()
def num(r,*ks):
    for k in ks:
        v=r.get(k)
        if v in (None,'') or isinstance(v,bool): continue
        try:
            x=float(v)
            if x==x: return x
        except: pass
    return None

def minute_of(v):
    m=re.search(r'(\d{2}):(\d{2})',str(v or ''))
    return int(m.group(1))*60+int(m.group(2)) if m else None

def regular(m): return (540<=m<690) or (750<=m<930)
def main(cache,out):
    out=pathlib.Path(out)
    if out.exists(): raise SystemExit('NEW_OUTPUT_REQUIRED')
    rows=[json.loads(x) for x in gzip.open(EVENTS,'rt') if x.strip()]
    if len(rows)!=3800 or len({r['selectorEventId'] for r in rows})!=3800: raise SystemExit('EVENT_IDENTITY')
    first={}
    for r in sorted(rows,key=lambda x:(x['sessionDate'],x['symbol'],x['decisionTimestamp'])):
        first.setdefault((r['sessionDate'],r['symbol']),r)
    anchors=list(first.values())
    if len(anchors)!=2743: raise SystemExit(f'FIRST_ANCHOR_COUNT:{len(anchors)}')
    lineage=json.load(gzip.open(PATHS,'rt'))
    bydate={}
    for a in anchors: bydate.setdefault(a['sessionDate'],[]).append(a)
    result=[]; sources=[]
    for date,evs in sorted(bydate.items()):
        p=pathlib.Path(cache)/'phase57-long-only/raw/jquants-v2'/date/'minute-pages.json'
        rawb=p.read_bytes(); saved=next(x for x in lineage['sources'] if x['sessionDate']==date)
        if sha(rawb)!=saved['rawPagesSHA']: raise SystemExit('RAW_SHA')
        pages=json.loads(rawb); raw=[]
        for pg in pages:
            if sha(pg['responseText'].encode())!=pg['responseSha256']: raise SystemExit('PAGE_SHA')
            raw += json.loads(pg['responseText']).get('data',[])
        wanted={str(e['symbol']).strip().upper() for e in evs}; mp={s:{} for s in wanted}
        for r in raw:
            s=str(r.get('Code',r.get('code',r.get('symbol','')))).strip().upper()
            if s not in wanted: continue
            m=minute_of(r.get('Time',r.get('time')))
            if m is None or not regular(m): continue
            o=num(r,'O','Open','open'); h=num(r,'H','High','high'); l=num(r,'L','Low','low'); c=num(r,'C','Close','close')
            if None in (o,h,l,c) or min(o,h,l,c)<=0 or h<max(o,c) or l>min(o,c): continue
            v=num(r,'Vo','Volume','volume','V')
            t=num(r,'Va','Turnover','turnover')
            mp[s][m]={'m':m,'o':o,'h':h,'l':l,'c':c,'v':v,'turnover':t}
        for e in evs:
            dm=minute_of(e['decisionTimestamp']); ref=float(e['decisionPrice']); seq=[]
            for m in range(dm-10,dm+31):
                if not regular(m): continue
                z=mp[e['symbol']].get(m)
                if not z: seq.append({'m':m,'missing':True}); continue
                seq.append({'m':m,'missing':False,
                    'o':100*(z['o']/ref-1),'h':100*(z['h']/ref-1),'l':100*(z['l']/ref-1),'c':100*(z['c']/ref-1),
                    'v':z['v'],'turnover':z['turnover']})
            result.append({'eventId':e['selectorEventId'],'sessionDate':date,'symbol':e['symbol'],'decisionTimestamp':e['decisionTimestamp'],'decisionPrice':ref,'ridgeScore':e.get('ridgeScore'),'ridgeRank':e.get('ridgeRank'),'minutePath':seq})
        sources.append({'sessionDate':date,'rawPagesSHA':saved['rawPagesSHA'],'candidateAnchors':len(evs),'providerRequests':0})
    if len(result)!=2743: raise SystemExit('OUTPUT_COUNT')
    out.mkdir(parents=True)
    payload=gzip.compress((json.dumps(result,separators=(',',':'))+'\n').encode())
    (out/'minute-entry-paths.json.gz').write_bytes(payload)
    audit={'id':'PHASE57_NEW_LONG_ENTRY_MINUTE_EXPORT_V1','role':'HISTORICAL_DEVELOPMENT_EVALUATOR_AND_CAUSAL_SEQUENTIAL_REPLAY_ONLY','anchors':2743,'sessions':76,'window':'decision-10m through decision+30m regular 1m rows','sourceHead':'7599df41199a8c4d1ea86d5f3cb595edd599dd21','payloadSHA256':sha(payload),'sources':sources,'modelFit':0,'modelPrediction':0,'providerRequests':0,'freshAccess':0,'oosAccess':0,'tradingEnabled':False}
    (out/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps({'status':'PASS','anchors':2743,'sessions':76,'sha256':sha(payload),'providerRequests':0}))
if __name__=='__main__': main(sys.argv[1],sys.argv[2])
