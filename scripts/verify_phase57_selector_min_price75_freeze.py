"""Hash-only verification of the new research baseline; no evaluation or trading."""
import collections,hashlib,json,sys
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
SPEC=ROOT/'predict/research/phase57-long-only-frozen-selector-min-price75-v1.json'
POINTER=ROOT/'predict/research/phase57-long-only-active-research-selector.json'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def audit_measurement():
    from scripts import phase57_selector_min_price75 as m
    from scripts import phase57_selector_min_price75_downstream as d
    root=ROOT/'docs/evidence/phase57-selector-min-price75-v1/measurement'
    s=m.read(root/'selector/selector-summary.json');l=m.read(root/'selector/selector-ledger.json.gz')
    ds=m.read(root/'downstream/downstream-summary.json');e=m.read(root/'downstream/entry-ledger.json.gz')
    decisions=m.read(root/'downstream/entry-decisions.json.gz');paths=m.read(root/'new-paths.json.gz')
    sm=m.read(root/'selector/selector-manifest.json');dm=m.read(root/'downstream/downstream-manifest.json')
    for rel,h in {**sm['sourcePins'],**sm['codePins']}.items():assert sha(ROOT/rel)==h,rel
    for part,manifest in [('selector',sm),('downstream',dm)]:
        for rel,h in manifest['outputPins'].items():assert sha(root/part/rel)==h,rel
    for rel,h in dm['sourcePins'].items():assert sha(root/'selector'/rel)==h,rel
    assert sha(root/'new-paths.json.gz')==dm['newPathsSHA256']
    assert sha(ROOT/'scripts/phase57_selector_min_price75_downstream.py')==dm['codePin']
    by={arm:{r['selectorEventId']:r for r in rows} for arm,rows in l.items()}
    assert all(len(by[arm])==len(rows) for arm,rows in l.items())
    old=set(by['old']);new=set(by['new'])
    assert old-new==set(by['removedOldTop5']) and new-old==set(by['replacements'])
    assert set(by['removedOldTop5'])<=set(by['excludedCandidates'])
    assert not new&set(by['excludedCandidates'])
    assert len(old)==len(new)==3800 and len(old-new)==len(new-old)==1107
    assert len(by['excludedCandidates'])==18790
    for arm in ['old','new']:
        groups=collections.defaultdict(list)
        for r in l[arm]:
            age=(datetime.fromisoformat(r['decisionTimestamp'])-datetime.fromisoformat(r['decisionPriceAvailableAtJst'])).total_seconds()/60
            assert 0<=age<=5 and age==r['referenceAgeMin'] and r['decisionPriceValid']==1
            assert r['decisionPriceKind'] in ('LATEST_ACCEPTED_MINUTE_CLOSE','TERMINAL_AUCTION_CLOSE')
            if r['decisionPriceKind']=='TERMINAL_AUCTION_CLOSE':assert r['decisionTimeJst']=='11:30' and age==0
            if arm=='new':assert m.gate.causal_status(r)=='ELIGIBLE_MIN_PRICE'
            groups[r['decisionTimestamp']].append(r)
        assert len(groups)==760 and len({r['sessionDate'] for r in l[arm]})==76
        for rows in groups.values():
            assert len(rows)==5
            rank='oldEligibleRank' if arm=='old' else 'newEligibleRank'
            assert [r[rank] for r in sorted(rows,key=lambda r:(-r['savedV1Score'],r['symbol']))]==[1,2,3,4,5]
        for k in m.LEVELS:
            hits=sum(r['futureBarCount']>0 and r[f'highOpportunity{k}']==1 for r in l[arm])
            assert hits==s['opportunity'][arm][str(k)]['high']['metrics']['selectedHits']
    assert all(0<r['decisionPrice']<=75 for r in l['excludedCandidates'])
    for eid in old&new:
        for key in by['old'][eid]:assert by['old'][eid][key]==by['new'][eid][key],(eid,key)
    assert len({r['decisionTimestamp'] for r in l['removedOldTop5']})==617
    assert len(paths['events'])==3800 and {r['selectorEventId'] for r in paths['events']}==new
    assert paths['newProjected']==1107 and paths['reused']==2693
    for arm in ['old','new']:
        assert {r['anchorId'] for r in decisions[arm]}=={r['selectorEventId'] for r in d.anchors(l[arm])}
        assert json.loads(json.dumps(d.panels(e[arm])))==ds[arm]
        dec={r['anchorId']:r for r in decisions[arm]}
        for r in e[arm]:
            op=dec[r['anchorId']]['decision']['initialEvent' if r['cohort']==d.mae.INITIAL else 'secondaryEvent']
            assert op['eventType']==r['cohort'] and op.get('referencePrice')==r['entryPrice']
            assert op['referenceStatus']==r['referenceStatus']
    er={a:{(r['anchorId'],r['cohort']):r for r in rows} for a,rows in e.items()}
    assert all(len(er[a])==len(rows) for a,rows in e.items())
    common=set(er['old'])&set(er['new'])
    assert all(er['old'][i]==er['new'][i] for i in common)
    for arm,ids,source in [('retained',common,'new'),('removed',set(er['old'])-common,'old'),('added',set(er['new'])-common,'new')]:
        # Keep source ordering for deterministic frequency ties and summaries.
        rows=[r for r in e[source] if (r['anchorId'],r['cohort']) in ids]
        assert json.loads(json.dumps(d.panels(rows)))==ds[arm]
    assert ds['worst17Identity']['removedFromSelector'] and ds['worst17Identity']['anchorId'] not in new
    assert sum(r['anchorMinPriceIneligible'] for r in ds['oldDeep10Identities'])==17
    assert ds['new']['ALL']['tails']['10']['n']==9
    for report in [s,ds]:
        assert len(report['safety'])==9 and all(v is False for v in report['safety'].values())
        assert report['freshOOSOpened'] is False
    return {'status':'IMMUTABLE_LEDGER_CAUSAL_AND_AGGREGATION_AUDIT_PASS','selectedPerArm':3800,'oldEntry':3284,'newEntry':3508,'oldStrict30':1697,'newStrict30':1872,'retainedEntryIdentityExact':len(common)}
def verify():
    s=json.loads(SPEC.read_text());p=json.loads(POINTER.read_text());f=s['freezePayload']
    assert s['status']=='FROZEN_LONG_SELECTOR_WITH_MIN_PRICE_75'
    assert hashlib.sha256(canonical(f)).hexdigest()==s['freezePayloadSHA256']
    assert f['MIN_DECISION_PRICE_JPY']==75 and f['eligibleComparator']=='decisionPrice > 75'
    assert all(v is True for v in f['freezeGates'].values()) and len(f['freezeGates'])==14
    for path,h in f['filePins'].items():assert sha(ROOT/path)==h,path
    assert all(v is False for v in f['safety'].values()) and len(f['safety'])==9
    assert f['freshOOSOpened'] is False and f['fitCalls']==0 and f['providerRequests']==0
    assert p['selectorSpec']==str(SPEC.relative_to(ROOT)) and p['selectorSpecSHA256']==sha(SPEC)
    assert p['scope']=='LONG_ONLY_RESEARCH_ONLY' and p['productionUpdateAllowed'] is False
    assert p['parentEvidenceRewriteAllowed'] is False
    audit=audit_measurement()
    print(json.dumps({'status':'PRICE75_RESEARCH_FREEZE_INTEGRITY_PASS','freezePayloadSHA256':s['freezePayloadSHA256'],'testedImplementationHead':f['testedImplementationHead'],'safety':f['safety'],'freshOOSOpened':False},sort_keys=True))
    print(json.dumps(audit,sort_keys=True))
    return s
if __name__=='__main__':verify()
