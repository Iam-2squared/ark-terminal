from __future__ import annotations
import argparse,collections,datetime as dt,gzip,hashlib,json,pathlib,sys
import jsonschema
ROOT=pathlib.Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description='Full Draft-2020-12 schema and transition concentration audit')
p.add_argument('--generation',required=True);p.add_argument('--output',required=True);a=p.parse_args()
GEN=pathlib.Path(a.generation);OUT=pathlib.Path(a.output);OUT.mkdir(parents=True,exist_ok=False)
def records(p):
    with gzip.open(p,'rt') as f:
        for line in f:yield json.loads(line)
def enc(x):return (json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()
validators={k:jsonschema.Draft202012Validator(json.loads((ROOT/'docs/evidence/phase57-state-v2-implementation/schemas'/(k+'.schema.json')).read_text())) for k in ('now_state_reference_v2','future_resolution_v2')}
counts=collections.Counter();cross={k:collections.Counter() for k in ('direction','structure','phase')};by=collections.defaultdict(collections.Counter);values=collections.Counter();defined_loss=[];opportunities=set();delay=collections.Counter();resolution=collections.Counter();examples={}
for p in sorted((GEN/'now_state_reference_v2').glob('*.gz')):
    day=p.name[:10]
    trip=zip(records(p),records(GEN/'future_resolution_v2'/p.name),records(GEN/'transitions'/p.name),strict=True)
    for n,f,t in trip:
        for k,row in [('now_state_reference_v2',n),('future_resolution_v2',f)]:
            validators[k].validate(row);counts['jsonSchema/'+k]+=1
        key=(n['opportunityId'],n['checkpointAsOf']);assert key==(f['opportunityId'],f['checkpointAsOf'])==(t['opportunityId'],t['checkpointAsOf'])
        opportunities.add(n['opportunityId']);before=t['v1'];status=before['structureStatus'];changed=[]
        for a in ('direction','structure','phase'):
            av=before[a];bv=n[a]['value'];newstatus=n[a]['status']
            # v1 did not publish v2 axis statuses. Retain raw identificationStatus,
            # and derive observability only from the immutable v1 reference contract.
            oldstatus='DEFINED' if (av is not None if a=='direction' else status=='IDENTIFIED' if a=='structure' else status not in ('CURRENT_BAR_UNAVAILABLE','SCALE_UNAVAILABLE')) else 'UNRESOLVED_OR_UNAVAILABLE'
            cross[a][oldstatus+' -> '+newstatus]+=1
            normalization=None if a=='structure' and bv in (None,'NONE') else [] if a=='phase' and bv is None else bv
            if av!=normalization:changed.append(a);values[a]+=1
            if oldstatus=='DEFINED' and newstatus!='DEFINED':defined_loss.append({'key':key,'axis':a,'v1DerivedStatus':oldstatus,'v1RawStructureStatus':status,'v1Value':av,'v2Status':newstatus,'v2Value':bv,'changeReasonCodes':t['changeReasonCodes']})
        # Non-DEFINED missing Phase was [] in v1; this is a representation change,
        # not an observed market fact. Both null masking and empty negative stay separate.
        if changed:
            counts['changedAnySemanticAxis']+=1
            for group in ('sessionDate','securityId','opportunityId'):
                for a in changed:by[group+'/'+n[group]][a]+=1
        resolution[f['resolutionStatus']]+=1
        delay[str(f['resolutionActiveMinutes'])]+=1
        classes=('now:'+n['structure']['status']+':'+str(n['structure']['value']), 'future:'+f['resolutionStatus'])
        for cl in classes:
            if cl not in examples:examples[cl]={'opportunityId':key[0],'checkpointAsOf':key[1]}
    print(day,counts['jsonSchema/now_state_reference_v2'],flush=True)
assert len(opportunities)==2155
assert counts['jsonSchema/now_state_reference_v2']==counts['jsonSchema/future_resolution_v2']==77214
lossbytes=enc(defined_loss);(OUT/'defined-to-nondefined-rows.json').write_bytes(lossbytes)
report={'recordedAtJST':dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(),'status':'SUPPLEMENTAL_AUDIT_COMPLETE_NOT_ACCEPTANCE','allJSONSchemaValidation':dict(counts),'semanticAxisChanges':dict(values),'transitionStatusCrossTabs':{a:dict(v) for a,v in cross.items()},'concentrationBySessionSecurityOpportunity':{k:dict(v) for k,v in by.items()},'definedToNondefinedRowN':len(defined_loss),'definedToNondefinedRowsSHA256':hashlib.sha256(lossbytes).hexdigest(),'oldStatusDerivation':'v1 had no v2 axis statuses; v1RawStructureStatus retained; inferred DEFINED meaning disclosed in audit_phase57_state_v2_schema_transitions.py; old artifact mode ORACLE_REFERENCE','futureResolutionStatusCounts':dict(resolution),'futureResolutionDelayCounts':dict(delay),'deterministicFirstStratumExamples':examples,'providerRequests':0,'protectedDataOpened':0,'doesNotResolveA8OrA9':True,'generationManifestSHA256':hashlib.sha256((GEN/'manifest.json').read_bytes()).hexdigest()}
(OUT/'supplemental-receipt.json').write_bytes(enc(report))
print(json.dumps({k:v for k,v in report.items() if k not in ('concentrationBySessionSecurityOpportunity','deterministicFirstStratumExamples')},indent=2),flush=True)
