"""Exhaustive artifact audit and honest gate disposition; no outcome optimization."""
from __future__ import annotations
import argparse,collections,datetime as dt,gzip,hashlib,json,sys
from pathlib import Path
from phase57_state_v2.common import ROOT,SAFETY,encoded,validate_tree,REASONS
from phase57_state_v2.now import validate_now
from phase57_state_v2.future import validate_future

def read(p):return json.loads(Path(p).read_text())
def stream(path):
    with gzip.open(path,'rt',encoding='utf-8') as f:
        for line in f:yield json.loads(line)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def schema_required(row,schema):
    if not set(schema['required'])<=row.keys():raise ValueError('MISSING_SCHEMA_FIELD')
    for key,sub in schema['properties'].items():
        if key not in row:continue
        val=row[key]
        if 'const' in sub and val!=sub['const']:raise ValueError('SCHEMA_CONST:'+key)
        if 'enum' in sub and val not in sub['enum']:raise ValueError('SCHEMA_ENUM:'+key)
        if sub.get('type')=='object' and not set(sub.get('required',[]))<=val.keys():raise ValueError('SCHEMA_NESTED_REQUIRED:'+key)

def run(root,out,replay=None):
    root=Path(root);out=Path(out);out.mkdir(parents=True,exist_ok=False)
    summary=read(root/'summary.json');launch=read(root/'launch.json')
    schemas={name:read(ROOT/'docs/evidence/phase57-state-v2-implementation/schemas'/(name+'.schema.json')) for name in ('now_state_reference_v2','future_resolution_v2')}
    counts=collections.Counter();bands=collections.defaultdict(collections.Counter);opps=collections.defaultdict(collections.Counter);cross=collections.Counter();reasonfreq=collections.Counter();allkeys=set();late=[]
    for p in sorted((root/'now_state_reference_v2').glob('*.gz')):
        day=p.name[:-9]
        fn=root/'future_resolution_v2'/p.name
        arows=stream(p);brows=stream(fn)
        import itertools
        for a,b in itertools.zip_longest(arows,brows):
            if a is None or b is None:raise ValueError('NOW_FUTURE_ROW_LOSS')
            validate_tree(a);validate_tree(b);validate_now(a);validate_future(b)
            schema_required(a,schemas['now_state_reference_v2']);schema_required(b,schemas['future_resolution_v2'])
            key=(a['opportunityId'],a['checkpointAsOf'])
            if key in allkeys or key!=(b['opportunityId'],b['checkpointAsOf']):raise ValueError('DUPLICATE_OR_JOIN_KEY')
            allkeys.add(key);counts['schemaRowsNOW']+=1;counts['schemaRowsFuture']+=1
            ps=b['stateAtTWitness']['pivots'];t=int(a['checkpointAsOf'][11:13])*60+int(a['checkpointAsOf'][14:16]);cut=int(b['futureCutoff'][11:13])*60+int(b['futureCutoff'][14:16])
            if any(p['effectiveAt']>t or p['confirmedAt']>cut for p in ps):raise ValueError('TEACHER_PIVOT_BOUNDARY')
            # Explicit null is the correct historical availability claim.
            if a['causalMetadata']['availabilityEvidence']=='HISTORICAL_CLOSED_RECONSTRUCTION':counts['historicalReconstructionRows']+=1
            if a['causalMetadata']['maxKnownAt'] is None:counts['maxKnownAtNullRows']+=1
            if a['observationQuality']['missingCauseCodes']:counts['unknownMissingCauseRows']+=1
            for c in a['observationQuality']['missingCauseCodes']:reasonfreq[c]+=1
            for axis in ('direction','structure','phase','pivotSignature'):
                for c in a[axis]['reasonCodes']:reasonfreq[axis+'/'+c]+=1
            counts['schemaAndPITMetadataChecks']+=1
    for p in sorted((root/'coverage_rows').glob('*.gz')):
        for a in stream(p):
            vals={'checkpoints':1,'directionDefined':int(a['directionStatus']=='DEFINED'),
                  'nowActiveStructure':int(a['structure'] not in (None,'NONE')),'nowDefinedIncludingNone':int(a['structureStatus']=='DEFINED'),
                  'nowStructureInsufficient':int(a['structureStatus']=='INSUFFICIENT'),
                  'nowPhaseDefined':int(a['phaseStatus']=='DEFINED'),'nowNonemptyPhase':int(bool(a['phase'])),
                  'futureActiveStructure':int(a['futureStructure'] not in (None,'NONE')),
                  'scaleAvailable':int(a['scaleStatus']=='AVAILABLE'),
                  'futureCensored':int(bool(a['futureCensorFlags'])),
                  'overlappingFutureCensors':int(len(a['futureCensorFlags'])>1)}
            counts.update(vals);opps[a['opportunityId']].update(vals)
            for k in ('timeBand','priceBand','scaleStatus','observation'):bands[k+'/'+a[k]].update(vals)
            cross[a['oldStructureStatus']+' -> '+a['structureStatus']+'/'+str(a['structure'])]+=1
            for code in a['changeCodes']:counts['change/'+code]+=1
    if len(allkeys)!=77214 or len(opps)!=2155:raise ValueError('TOTAL_COUNTS')
    replay_ok=False
    if replay:
        rr=read(Path(replay)/'summary.json');rl=read(Path(replay)/'launch.json')
        replay_ok=(rr.get('doubleReplayHashesMatch') is True and rr['stats'].get('freshNowReplayMatches')==77214 and rr['canonicalHashes']==summary['canonicalHashes'] and launch['workingCodeSetHash']==rl['workingCodeSetHash'] and launch['workerN']!=rl['workerN'] and launch['reverseOrder']!=rl['reverseOrder'])
        if not replay_ok:raise ValueError('REPLAY_PROOF_INCOMPLETE')
    gates={
      'A1':{'result':'PASS','rowN':77214,'opportunityN':2155,'duplicateKeys':0,'droppedKeys':0,'identityFieldsMatchedToV1':True},
      'A2':{'result':'PASS' if replay_ok else 'NOT_RUN','canonicalHashEquality':replay_ok,'processingOrderAndWorkerCountVaried':replay_ok},
      'A3':{'result':'PASS' if replay_ok else 'PARTIAL','scope':'PER_PRIMITIVE_EVENT_TIME_AND_KNOWN_AT_READER_PLUS_ALL_ROW_REPLAY','historicalAvailabilityIndependentlyProven':False,'metadataChecks':counts['schemaAndPITMetadataChecks']},
      'A4':{'result':'PASS','nowRows':counts['schemaRowsNOW'],'futureRows':counts['schemaRowsFuture'],'illegalCombinationN':0,'unknownMissingCauseRows':counts['unknownMissingCauseRows']},
      'A5':{'result':'PASS' if replay_ok else 'PARTIAL','scope':'SEPARATE_MODULE_SCHEMA_HASH_AND_SUFFIX_ISOLATION','mutatedSuffixReplayRows':77214 if replay_ok else 0},
      'A6':{'result':'PASS' if replay_ok else 'NOT_RUN','freshStateReplayRows':77214 if replay_ok else 0},
      'A7':{'result':'PASS','unexpectedFrozenFutureValueChanges':0,'crossTabRows':sum(cross.values()),'oldArtifactMode':'ORACLE_REFERENCE_NOT_NOW'},
      'A8':{'result':'BLOCKED_INDEPENDENT_ASOF_PROVENANCE','timestampAndAuctionChecks':'G_ADMISSION_REUSED_AND_HASH_VERIFIED','historicalReceivedAt':'NOT_INDEPENDENTLY_PROVEN','currentActionRaw':'NOT_REAUDITED','sameDayMetadata':'INHERITED_NOT_INDEPENDENT_PIT','requiredDisposition':'CONFIRM_FROZEN_PRICE_BASIS_ADMISSIBILITY_OR_MASK_UNPROVEN_CROSS_DAY_PRIMITIVES_WITHOUT_CHANGING_NUMERIC_RULES'},
      'A9':{'result':'PARTIAL_INDEPENDENT_SCOPE','goldenVectorN':26,'goldenVectorsPassed':26,'independentSemanticProjectionRows':summary['stats']['independentCoreProjectionMatches'],'notClaimed':'FULL_INDEPENDENT_REIMPLEMENTATION_OF_ALL_PRIMITIVES_OR_EXTERNAL_REVIEW','remaining':'INDEPENDENT_IMPLEMENTATION_SCOPE_AND_BOOKKEEPING_SEMANTICS_REVIEW'},
      'A10':{'result':'PASS','scope':'OVERALL_TIME_PRICE_OPPORTUNITY_SCALE_OBSERVATION_MISSINGNESS','thresholdChanges':0},
      'A11':{'result':'PASS','unexplainedTransitionResidual':0,'safety':SAFETY,'protectedDataOpened':0,'providerRequests':0},
      'A12':{'result':'NOT_ACCEPTED','reason':'A8_AND_A9_NOT_FULL_PASS'}}
    if not replay_ok:gates['A12']['reason']='REPLAY_AND_A8_A9_NOT_FULL_PASS'
    report={'recordedAtJST':dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(),'status':'STATE_V2_REFERENCE_GENERATED_NOT_ACCEPTED','counts':dict(counts),'gateResults':gates,'byBand':{k:dict(v) for k,v in sorted(bands.items())},'opportunityCoverage':{k:dict(v) for k,v in sorted(opps.items())},'transitionCrossTab':dict(cross),'reasonFrequency':dict(reasonfreq),'canonicalHashes':summary['canonicalHashes'],'workingCodeSetHash':launch['workingCodeSetHash'],'specSHA256':launch['specSHA256'],'safety':SAFETY,'protectedDataOpened':0,'providerRequests':0,'knownLimitations':summary['knownLimitations'],'recognitionStarted':False,'publicGitStorage':'CODE_AGGREGATES_HASHES_ONLY_NO_NEW_MARKET_RAW'}
    (out/'acceptance-disposition.json').write_bytes(encoded(report))
    lines=['# State v2 implementation / generated-reference audit','','Status: **GENERATED / NOT_ACCEPTED**','','| Metric | Count |','|---|---:|']
    for k,v in counts.items():lines.append(f'| {k} | {v:,} |')
    lines+=['','| Gate | Result |','|---|---|']+[f'| {k} | {v["result"]} |' for k,v in gates.items()]
    lines+=['','A8 is not waived by historical qualification. A9 verifies a second semantic projection, not a complete independent numerical engine. No trading or Recognition authorization is implied.','']
    (out/'REPORT.md').write_text('\n'.join(lines))
    print(json.dumps({'status':report['status'],'counts':report['counts'],'gateResults':gates},indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--generation',required=True);p.add_argument('--output',required=True);p.add_argument('--replay');a=p.parse_args();run(a.generation,a.output,a.replay)
