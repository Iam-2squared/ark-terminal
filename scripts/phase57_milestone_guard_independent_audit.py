"""Independent raw-path audit of the frozen milestone Phase 0 NO-GO.

This script deliberately does not import the Phase 0 implementation.
"""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import math
import zipfile
from pathlib import Path

from scripts import phase57_development_integrated_v0 as v0
from scripts import phase57_exit_continuation_r52 as r52
from scripts import phase57_exit_execution_contract_v1 as clock

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/evidence/phase57-milestone-guard-exit"
LADDER = (1,2,3,5,10)
FLOOR = {1:0,2:1,3:2,5:3,10:5}
NEXT = {1:2,2:3,3:5,5:10,10:None}


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()


def check(ok, label):
    if not ok:raise AssertionError(label)


def bars(day, entry_minute, control_now, path):
    result=[]
    for minute in clock.continuous_minutes(day):
        if minute<entry_minute or minute+1>control_now:continue
        row=path.get(minute)
        if row is None or len(row)!=7 or any(not isinstance(row[i],(int,float)) or
                not math.isfinite(row[i]) or row[i]<=0 for i in (1,2,3,4)):
            result.append(None)
        elif row[2]<max(row[1],row[4]) or row[3]>min(row[1],row[4]):
            result.append(None)
        else:result.append((row[2],row[3],row[4]))
    return result


def first_reach(series, price, threshold):
    gap=False
    for i,bar in enumerate(series):
        if bar is None:gap=True
        elif bar[0]>=price*(1+threshold/100):
            return ('MISSING_PRIOR' if gap else 'REACHED',i)
    return ('MISSING' if gap else 'CONTROL_TERMINAL_FIRST',None)


def first_passage(series,price,reach,start,stop):
    status,j=reach
    if status!='REACHED':return status
    for k in range(j,len(series)):
        bar=series[k]
        if bar is None:return 'MISSING'
        high,low,_=bar
        upper=stop is not None and high>=price*(1+stop/100)
        lower=low<price*(1+FLOOR[start]/100)
        if upper and lower or lower and k==j:return 'AMBIGUOUS_SAME_BAR'
        if upper:return 'UPPER_FIRST'
        if lower:return 'FLOOR_FIRST'
    return 'CONTROL_TERMINAL_FIRST'


def alert_labels(series,day,entry_minute,price,path):
    highs=0;breach=0;labels=[]
    grid=clock.continuous_minutes(day)
    loc={m:i for i,m in enumerate(grid)}
    for offset,bar in enumerate(series):
        if bar is None:
            breach=0
            continue
        for m in LADDER:
            if bar[0]>=price*(1+m/100):highs=max(highs,m)
        if not highs:continue
        if bar[2]>=price*(1+FLOOR[highs]/100):
            breach=0
            continue
        breach+=1
        if breach>=2:break
        minute=grid[loc[entry_minute]+offset]
        endpoint_index=loc[minute]+30
        endpoint=None if endpoint_index>=len(grid) else path.get(grid[endpoint_index])
        valid=(endpoint is not None and len(endpoint)==7 and
               all(isinstance(endpoint[i],(int,float)) and math.isfinite(endpoint[i])
                   and endpoint[i]>0 for i in (1,2,3,4)) and
               endpoint[2]>=max(endpoint[1],endpoint[4]) and
               endpoint[3]<=min(endpoint[1],endpoint[4]))
        labels.append(None if not valid else int(endpoint[4]>=price*(1+FLOOR[highs]/100)))
    return labels


def run(args):
    a=json.loads((BASE/'PHASE0_A.json').read_text())
    b=json.loads((BASE/'PHASE0_B.json').read_text())
    pre=json.loads((BASE/'CYCLE_PRECOMMIT.json').read_text())
    check(digest(BASE/'CYCLE_PRECOMMIT.json')==(BASE/'CYCLE_PRECOMMIT.sha256').read_text().strip(),'PRECOMMIT_SHA')
    check(digest(args.r45)==pre['sourcePins']['r45ArtifactZipSha256'],'R45_SHA')
    check(digest(args.replay)==pre['sourcePins']['r54ReplayZipSha256'],'R54_SHA')
    check(digest(args.audit)==pre['sourcePins']['r34AuditZipSha256'],'R34_SHA')
    check(digest(r52.RAW)==pre['sourcePins']['rawPathSha256'],'RAW_SHA')
    frozen={key:entry for key,entry in r52.all_frozen_entries().items()
            if entry['session'] in json.loads((ROOT/'docs/evidence/phase57-exit-mh-r54/CYCLE2_PRECOMMIT.json').read_text())['sessions']}
    check(len(frozen)==1614,'FROZEN_ENTRIES')
    calendar={}
    with gzip.open(ROOT/'docs/evidence/phase57-capital-exit-integrated/INPUTS/R50_A_LIFECYCLE-run-a.jsonl.gz','rt') as f:
        for line in f:
            rec=json.loads(line);key=(rec['entryArm'],rec['entryId'])
            if key in frozen:
                check(key not in calendar,'CALENDAR_DUPLICATE')
                calendar[key]=rec['decisionNow']
    check(set(calendar)==set(frozen),'CALENDAR_COMPLETE')
    allowed={e['opportunity'] for e in frozen.values()}
    raw,ignored=v0.allowlisted_raw_paths(r52.RAW,allowed)
    check(set(raw)==allowed and ignored==5375-len(raw),'RAW_SCOPE')
    with gzip.open(BASE/'PHASE0_B_ENTRY_ROWS.jsonl.gz','rt') as f:
        saved=[json.loads(line) for line in f]
    check(len(saved)==b['entryRowsN']==1614 and digest(BASE/'PHASE0_B_ENTRY_ROWS.jsonl.gz')==b['entryRowsSha256'],'ENTRY_ROWS_PIN')
    checked_reach=checked_passage=checked_alert=0
    means=collections.Counter()
    alerts=collections.Counter()
    winners={5:[],10:[]}
    for rec in saved:
        arm=v0.IM if rec['arm']=='IM' else v0.R1
        key=(arm,rec['entryId']);entry=frozen[key]
        check(rec['session']==entry['session'],'ENTRY_SESSION')
        day=entry['session'];price=entry['effectiveEntryPrice']
        path=raw[entry['opportunity']]
        series=bars(day,entry['entryMinute'],calendar[key],path)
        reach={m:first_reach(series,price,m) for m in LADDER}
        for m in LADDER:
            check(list(reach[m])==rec['reach'][str(m)],'REACH_MISMATCH')
            checked_reach+=1
            means[(rec['arm'],m,reach[m][0])]+=1
        for m in LADDER:
            name=f'{m}->{NEXT[m]}' if NEXT[m] is not None else '10->floor5'
            predicted=first_passage(series,price,reach[m],m,NEXT[m])
            check(predicted==rec['transitions'][name]['status'],'PASSAGE_MISMATCH')
            checked_passage+=1
        lab=alert_labels(series,day,entry['entryMinute'],price,path)
        check(len(lab)==rec['alertsN'],'ALERT_COUNT')
        alerts.update('UNKNOWN' if y is None else 'POS' if y else 'NEG' for y in lab)
        checked_alert+=len(lab)
        for cutoff in (5,10):
            if rec['upsidePct'] is not None and rec['upsidePct']>=cutoff:
                steps=[m for m in LADDER if NEXT[m] is not None and NEXT[m]<=cutoff]
                states=[first_passage(series,price,reach[m],m,NEXT[m]) for m in steps]
                verdict=('FLOOR_FIRST' if 'FLOOR_FIRST' in states else
                         'UPPER_FIRST_ALL' if all(s=='UPPER_FIRST' for s in states) else
                         'UNKNOWN_OR_CONTROL_TERMINAL')
                winners[cutoff].append((day,verdict))
    check(checked_reach==8070 and checked_passage==8070,'AUDIT_CENSUS')
    check(checked_alert==a['survival']['combined']['alerts'],'ALERT_TOTAL')
    check(alerts=={k:a['survival']['combined'][v] for k,v in
                   (('UNKNOWN','unknown'),('POS','positive'),('NEG','negative'))},'ALERT_CLASSES')
    calculated={}
    for cutoff,cohort in winners.items():
        known=[(day,s) for day,s in cohort if s!='UNKNOWN_OR_CONTROL_TERMINAL']
        changed=sum(s=='FLOOR_FIRST' for _,s in known)
        saved_gate=b['winnerFeasibility'][str(cutoff)]
        check((len(cohort),len(known),changed)==
              (saved_gate['totalWinnerEntries'],saved_gate['exactKnownEntries'],saved_gate['floorFirstEntries']),'WINNER_GATE_RECOMPUTE')
        calculated[str(cutoff)]={'total':len(cohort),'known':len(known),'floorFirst':changed,
                                 'coverage':len(known)/len(cohort)}
    check(b['guardGate']=='GUARD_FEASIBILITY_UNMEASURABLE','GATE_STATUS')
    check(not any(pre['safety'].values()) and not any(a['safety'].values()) and
          not any(b['safety'].values()),'SAFETY9')
    out={'schema':'phase57-mg-independent-audit-v1','status':'PASS_AS_AUDIT_OF_GUARD_FEASIBILITY_UNMEASURABLE',
         'phase0ASha256':digest(BASE/'PHASE0_A.json'),
         'phase0BSha256':digest(BASE/'PHASE0_B.json'),
         'entryRowsSha256':digest(BASE/'PHASE0_B_ENTRY_ROWS.jsonl.gz'),
         'checks':{'reached':checked_reach,'passages':checked_passage,'alerts':checked_alert,
                   'labelCounts':dict(alerts),'winner':calculated,
                   'sourceArtifactAndRawPins':'PASS','safety9':'ALL_FALSE'},
         'budget':{'newEstimatorFits':0,'integratedReplayInvocations':0,'providerRequests':0,
                   'protectedOpened':0,'orders':0,'mainMerges':0}}
    (BASE/'INDEPENDENT_AUDIT.json').write_text(json.dumps(out,sort_keys=True,indent=2)+'\n')
    print(json.dumps(out['checks'],sort_keys=True))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--r45',required=True,type=Path)
    parser.add_argument('--replay',required=True,type=Path)
    parser.add_argument('--audit',required=True,type=Path)
    run(parser.parse_args())
