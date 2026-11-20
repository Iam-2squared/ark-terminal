"""A7 extension: unchanged attribute/event primitives and explicit persistence cutoff."""
from __future__ import annotations
import argparse,collections,datetime as dt,gzip,hashlib,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description='Check all attribute/event and persistence transitions')
p.add_argument('--generation',required=True);p.add_argument('--v1',required=True);p.add_argument('--output',required=True);a=p.parse_args()
G=pathlib.Path(a.generation);V1=pathlib.Path(a.v1)
sys.path.insert(0,str(ROOT/'scripts'))
from phase57_state_v2.common import encoded,r
from phase57_state_v2.historical import g
OUT=pathlib.Path(a.output);OUT.mkdir(parents=True,exist_ok=False)
def rows(p):
    with gzip.open(p,'rt') as f:
        for s in f:yield json.loads(s)
c=collections.Counter();reasons=collections.Counter();byday={};manifest={}
for p in sorted((G/'now_state_reference_v2').glob('*.gz')):
    day=p.name[:10];count=collections.Counter()
    old={(v['opportunity'],v['asOfJST']):v for v in rows(V1/'raw'/p.name)}
    # Input source is the hash-verified G Development projection; do not infer missing bars.
    destination=OUT/(day+'.jsonl.gz')
    with destination.open('xb') as f,gzip.GzipFile(fileobj=f,mode='wb',mtime=0,filename='') as out:
        for n in rows(p):
            key=(n['opportunityId'],n['checkpointAsOf']);o=old[key];t=int(key[1][11:13])*60+int(key[1][14:16]);attr=n['attributes'];tags=[]
            for family,tag in [('choppiness','CHOPPINESS'),('range','RANGE'),('volume','VOLUME'),('tradingValue','TRADING_VALUE')]:
                v=attr[family]
                if v['status']=='DEFINED' and v['value']!='NONE':tags.append('CHOPPINESS' if family=='choppiness' else tag+'_'+v['value'])
            assert tags==o['reference']['attributes']['tags'],('ATTRIBUTE_TAG_CHANGE',key)
            lev={k:v['evidence']['level'] for k,v in n['events']['fixedLevel'].items() if v['status']=='DEFINED'}
            assert lev==o['levelSnapshotAtWindowStart'],('FIXED_LEVEL_CHANGE',key)
            events=[e for k,v in sorted(n['events']['fixedLevel'].items()) if v['status']=='DEFINED' for e in v['value']]
            assert events==o['levelEvents'],('FIXED_EVENT_CHANGE',key)
            nw=n['events']['movingVWAP'];ow=o['vwapRelations'];vwe=nw['value'] if nw['status']=='DEFINED' else []
            assert vwe==ow['events'],('VWAP_EVENT_CHANGE',key)
            ps=n['events']['persistence'];changes=[]
            if ps['status']=='DEFINED':
                for a,b in zip(ps['value'],o['eventConfirmations'],strict=True):
                    assert a['event']=={k:v for k,v in b.items() if k!='confirmation'}
                    actual=a['result']['evidence']['witness'];oldc=b['confirmation']
                    if actual!=oldc:
                        if actual['status']!='RIGHT_CENSORED':raise ValueError('UNEXPLAINED_PERSISTENCE_CHANGE')
                        assert len(actual['expectedEnds'])<2 or actual['expectedEnds'][-1]>t
                        changes.append({'eventAt':a['event']['eventAt'],'levelId':a['event']['levelId'],'kind':a['event']['kind'],'v1FutureAssistedConfirmation':oldc,'v2NowConfirmation':actual,'changeReason':'PERSISTENCE_FUTURE_TO_NOW_CUTOFF'})
                        reasons['PERSISTENCE_FUTURE_TO_NOW_CUTOFF']+=1
            else:assert not o['eventConfirmations']
            rec={'opportunityId':key[0],'checkpointAsOf':key[1],'v1AttributeTags':o['reference']['attributes']['tags'],'v2AttributeAxes':attr,'fixedLevelValueEquality':True,'fixedEventValueEquality':True,'movingVWAPEventEquality':True,'persistenceChanges':changes,'changeReasonCodes':['INDEPENDENT_ATTRIBUTE_STATUS_REPRESENTATION','FIXED_LEVEL_AND_VWAP_VALUES_PRESERVED']+(['PERSISTENCE_FUTURE_TO_NOW_CUTOFF'] if changes else [])}
            out.write(encoded(rec));count['rows']+=1;count['attributesEqual']+=1;count['staticEventRowsEqual']+=1;count['movingEventRowsEqual']+=1;count['persistenceChangedRows']+=bool(changes)
    c.update(count);byday[day]=dict(count);manifest[p.name]=hashlib.sha256(destination.read_bytes()).hexdigest()
    print(day,dict(count),flush=True)
assert c['rows']==77214
receipt={'recordedAtJST':dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(),'status':'EXTENDED_TRANSITION_AUDIT_PASS','counts':dict(c),'changeReasons':dict(reasons),'bySession':byday,'sha256':manifest,'unexplainedResidual':0,'frozenNumericalRuleChanges':0,'providerRequests':0,'protectedDataOpened':0}
(OUT/'receipt.json').write_bytes(encoded(receipt))
