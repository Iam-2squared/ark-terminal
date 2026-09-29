"""Append-only High anatomy correction, independent of policy outcome Replay."""
import collections
import gzip
import json
from pathlib import Path

from scripts import phase57_profit_target_diagnostic as d
from scripts.phase57_profit_target_precommit import OUT, ARM, TARGETS, canonical, digest, jst, check


def bands(v):
    if v is None:return 'UNKNOWN'
    for n,hi in enumerate(TARGETS):
        if v<hi:return ['<1','1-2','2-3','3-4','4-5','5-7','7-10'][n]
    return '>=10'


def run():
    check(not (OUT/'TARGET_REACH_SUMMARY_CORRECTED.json').exists(), 'CORRECTION_EXISTS')
    _,entries,ledgers,controls,raw,_=d.load_verified()
    riskset={(r['arm'],r['entryId']):r['sameTimestampRiskset'] for r in
             d.read_gz(OUT/'FUNDING_UNIVERSE_ROWS.jsonl.gz')}
    rows=[]; mismatches=collections.Counter()
    for a in ARM:
        for eid,e in sorted(entries[a].items()):
            path,bad=d.valid_bars(raw[e['opportunityId']],e['session'],e['entryMinute'])
            active=[m for m in d.execution.continuous_minutes(e['session']) if m>=e['entryMinute']]
            inclusive=active+[930]
            strict=[m for m in inclusive if m>e['entryMinute']]
            owned=[path[m][2] for m in inclusive if m in path]
            later=[path[m][2] for m in strict if m in path]
            p=e['entryPrice']
            own=100*(max(owned)/p-1) if owned else None
            legacy=100*(max(later)/p-1) if later else None
            old=e['futureUpsidePctEvaluatorOnly']
            if old is not None and legacy is not None and abs(old-legacy)>1e-6:
                mismatches[a]+=1
            missing=sum(m not in path for m in inclusive)
            item={'arm':a,'entryId':eid,'session':e['session'],'symbol':e['symbol'],
                  'funded':eid in ledgers[a]['funded'],
                  'sameTimestampRiskset':riskset[a,eid],
                  'entryBarIncludedObservedHighPct':own,
                  'legacyStrictLaterObservedHighPct':legacy,
                  'legacySavedHighPct':old,
                  'continuousExpected':len(active),'continuousObserved':sum(m in path for m in active),
                  'auctionReferencePresent':930 in path,
                  'completeEndpointPath':missing==0,
                  'missingOwnedObservationSlots':missing,
                  'invalidObservedMinutes':bad,
                  'signedHighPct':own,'zeroFloorMfePct':max(0,own) if own is not None else None,
                  'exclusiveBand':bands(own)}
            for x in TARGETS:
                status=('CONFIRMED_REACH' if own is not None and own>=x else
                        'CERTIFIED_NONREACH' if missing==0 else 'UNKNOWN')
                item[f'ge{x}']=status
            rows.append(item)
    with (OUT/'TARGET_REACH_ROWS_CORRECTED.jsonl.gz').open('xb') as f:
        with gzip.GzipFile(fileobj=f,mode='wb',mtime=0) as z:
            for row in rows:z.write(canonical(row))
    summary={}; capital={}
    for a in ARM:
        group=[r for r in rows if r['arm']==a]
        for x in TARGETS:
            k=f'{a}:{x}';summary[k]={}
            for scope, subset in {'ALL_ENTRY_100':group,
                 'R50_FUNDED_ACTUAL':[r for r in group if r['funded']],
                 'R50_FUNDED_100':[r for r in group if r['funded']],
                 'R50_NOT_FUNDED_100':[r for r in group if not r['funded']],
                 'SAME_TIMESTAMP_ELIGIBLE_RISKSET':[r for r in group
                                                     if r['sameTimestampRiskset']]}.items():
                n=len(subset);c=collections.Counter(r[f'ge{x}'] for r in subset)
                hit=c['CONFIRMED_REACH'];unknown=c['UNKNOWN']
                summary[k][scope]={'totalN':n,'confirmedReachN':hit,
                   'certifiedNonreachN':c['CERTIFIED_NONREACH'],'unknownReachN':unknown,
                   'lowerPct':100*hit/n if n else None,
                   'upperPct':100*(hit+unknown)/n if n else None,
                   'knownSubsetPct':100*hit/(n-unknown) if n>unknown else None,
                   'completePathN':sum(r['completeEndpointPath'] for r in subset),
                   'endpoint':'continuous through 15:24 plus exact 15:30 auction'}
            capital[k]={scope:summary[k][scope] for scope in
                  ('R50_FUNDED_ACTUAL','R50_NOT_FUNDED_100',
                   'SAME_TIMESTAMP_ELIGIBLE_RISKSET')}
    (OUT/'TARGET_REACH_SUMMARY_CORRECTED.json').write_bytes(canonical(summary))
    (OUT/'CAPITAL_ENRICHMENT_CORRECTED.json').write_bytes(canonical(capital))
    rec={'status':'APPEND_ONLY_HIGH_ENDPOINT_CORRECTION',
         'atJst':jst(),'policyArmEvaluationsAdded':0,
         'sourcePricePathSha256':json.loads((OUT/'SOURCE_MANIFEST.json').read_text())
                              ['pins']['rawPath']['sha256'],
         'savedPolicyRowsSha256':digest(OUT/'FIXED_TARGET_OUTCOME_ROWS.jsonl.gz'),
         'oldProvisionalFiles':['TARGET_REACH_SUMMARY.json','TARGET_REACH_ROWS.jsonl.gz',
                                'CAPITAL_ENRICHMENT.json','HIGH_DEFINITION_RECONCILIATION.json'],
         'oldValuesRetainedForAudit':True,
         'strictLaterHighVsSavedLabelMismatchN':dict(mismatches),
         'definition':'High uses post-Entry continuous observations plus 15:30 auction when present; owned includes Entry OPEN bar; no High is used for target trigger or fill',
         'missingAuctionCannotCertifyNonreach':True,
         'remainingOldReportedHighCrosscheck':'R50 saved evaluator high may use a different observation contract in isolated rows; mismatch count explicitly reported'}
    (OUT/'HIGH_CORRECTION_RECEIPT.json').write_bytes(canonical(rec))
    print(json.dumps(rec,ensure_ascii=False))


if __name__=='__main__':run()
