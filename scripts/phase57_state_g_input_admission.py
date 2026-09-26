#!/usr/bin/env python3
import gzip, json, hashlib, pathlib, collections
ROOT=pathlib.Path(__file__).resolve().parents[1]
BASE=ROOT/'docs/evidence/phase57-entry-timing-signal-census-v1/measurement'
OUT=ROOT/'tmp-phase57-state-g-admission'
def read(p):
    p=ROOT/p if not pathlib.Path(p).is_absolute() else pathlib.Path(p)
    op=gzip.open if p.suffix=='.gz' else open
    with op(p,'rt',encoding='utf-8') as f:return json.load(f)
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def shape(x,depth=0):
    if depth>2:return type(x).__name__
    if isinstance(x,dict):return {k:shape(v,depth+1) for k,v in list(x.items())[:40]}
    if isinstance(x,list):return {'type':'list','n':len(x),'sample':shape(x[0],depth+1) if x else None}
    return type(x).__name__
def main():
    OUT.mkdir(exist_ok=False)
    cohort=read(BASE/'cohort.json')
    opp=read(BASE/'opportunity-records.json.gz')
    # raw paths source used by prior audits
    paths=read('docs/evidence/phase57-entry-pattern-v2/ci-result/substrate/raw-paths-evaluator-only.json.gz')
    opportunities=read('docs/evidence/phase57-entry-pattern-v2/ci-result/substrate/opportunities.json.gz')
    protocol=read('docs/evidence/phase57-entry-timing-signal-census-v1/protocol.json')
    ids=list(protocol['opportunityIds'])
    assert len(ids)==len(set(ids))==protocol['count']==cohort['population']==2155
    by_id={o.get('id'):o for o in opportunities}
    assert len(by_id)==len(opportunities)
    selected=[by_id[i] for i in ids if i in by_id]
    assert len(selected)==2155
    # inventory dates and data availability, without emitting price rows
    path_keys=set(paths)
    p2155=sum(i in path_keys for i in ids)
    prev=collections.Counter(); today=collections.Counter(); prev_session=collections.Counter()
    for i in ids:
        z=paths.get(i,{})
        prev['present' if z.get('previous') else 'missing']+=1
        today['present' if z.get('today') else 'missing']+=1
        prev_session['present' if z.get('previousSession') else 'missing']+=1
    # inspect whether opportunity records already carry daily context
    dailyish=set()
    def walk(v,p=''):
        if isinstance(v,dict):
            for k,x in v.items():
                q=(p+'/'+k).lower()
                if any(t in k.lower() for t in ('daily','recent','d-1','d1','previousday')): dailyish.add(q)
                if p.count('/')<3: walk(x,p+'/'+k)
        elif isinstance(v,list) and v and p.count('/')<3: walk(v[0],p+'[]')
    if opp: walk(opp[0])
    report={
      'status':'INPUT_ADMISSION_SCHEMA_AUDIT_ONLY',
      'population':2155,
      'cohortOpportunityIdsSHA256':cohort.get('opportunityIdsSHA256'),
      'opportunityRecordsType':type(opp).__name__,
      'opportunityRecordsN':len(opp) if isinstance(opp,list) else None,
      'opportunityRecordShape':shape(opp[0]) if isinstance(opp,list) and opp else None,
      'opportunitySubstrateN':len(opportunities),
      'selectedOpportunityN':len(selected),
      'opportunityShape':shape(selected[0]),
      'rawPathShape':shape(next(iter(paths.values()))),
      'rawPathCoverage':p2155,
      'previousMinuteAvailability':dict(prev),
      'todayMinuteAvailability':dict(today),
      'previousSessionIdentityAvailability':dict(prev_session),
      'dailyLikeFieldsInOpportunityRecordSample':sorted(dailyish),
      'sourceHashes':{
        'cohort.json':sha(BASE/'cohort.json'),
        'opportunity-records.json.gz':sha(BASE/'opportunity-records.json.gz'),
        'raw-paths-evaluator-only.json.gz':sha(ROOT/'docs/evidence/phase57-entry-pattern-v2/ci-result/substrate/raw-paths-evaluator-only.json.gz'),
        'opportunities.json.gz':sha(ROOT/'docs/evidence/phase57-entry-pattern-v2/ci-result/substrate/opportunities.json.gz')
      },
      'marketRowsGenerated':0,'providerRequests':0,'holdoutOpened':0
    }
    (OUT/'admission.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
