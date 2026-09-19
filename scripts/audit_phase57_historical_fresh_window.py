"""Outcome-free upper bound on consecutive available historical sessions.

Weekdays are a superset of JPX sessions, not a synthesized trading calendar.
No missing ledger identity is promoted to fresh. A bound below30 proves that
no admissible30-session block exists under the supplied protection rules.
"""
from datetime import date, timedelta
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = 'docs/evidence/phase57-long-only-global-data-budget/resolved-master-ledger.json'
EVIDENCE = 'docs/evidence/phase57-msh-entry-long-v1-historical-fresh-fast-track'
BLOCKED = {'EXPOSED','RESERVED','SEALED','PROTECTED','PURGED','EXCLUDED','UNKNOWN'}


def upper_bound(rows, start, end, protected):
    start, end = date.fromisoformat(start), date.fromisoformat(end)
    if end < start:
        raise ValueError('INVALID_RANGE')
    dated = {}
    for row in rows:
        day = row['sessionDate']
        if day is None:
            continue  # UNKNOWN ordinal identity stays unresolved; never allocated.
        date.fromisoformat(day)
        if day in dated:
            raise ValueError('DUPLICATE_LEDGER_DATE')
        classification = row['primaryClassification']
        if classification not in BLOCKED | {'FRESH_AVAILABLE'}:
            raise ValueError('INVALID_CLASSIFICATION')
        dated[day] = classification
    periods = [(date.fromisoformat(x['first']), date.fromisoformat(x['last'])) for x in protected]
    runs, current, reasons = [], [], Counter()
    for offset in range((end-start).days+1):
        day = start+timedelta(days=offset)
        if day.weekday() >= 5:
            continue
        label = dated.get(str(day))
        why = 'PROTECTED_DATE_ENVELOPE' if any(a<=day<=b for a,b in periods) else label if label in BLOCKED else None
        if why:
            reasons[why] += 1
            if current:
                runs.append(current)
                current = []
        else:
            current.append(str(day))
    if current:
        runs.append(current)
    return {'start':str(start),'end':str(end),'weekdaySupersetCount':sum(reasons.values())+sum(map(len,runs)),
            'blockedWeekdayCounts':dict(reasons),'unblockedWeekdayUpperBound':sum(map(len,runs)),
            'longestUnblockedWeekdayRun':max(map(len,runs),default=0),'unblockedRuns':runs,
            'freshSessionsCertified':0,'classificationChanges':0,
            'qualifier':'Weekdays include holidays. Unregistered dates are not certified fresh. No UNKNOWN ordinal-to-date mapping.'}


def audit():
    raw=(ROOT/LEDGER).read_bytes()
    ledger=json.loads(raw)
    projection=json.loads((ROOT/EVIDENCE/'source-metadata-projection.json').read_text())
    protected=[projection['protectedExternal']]
    conservative=upper_bound(ledger['sessions'],'2024-09-16','2026-09-15',protected)
    sensitivity=upper_bound(ledger['sessions'],'2024-09-01','2026-09-16',protected)
    assert conservative['longestUnblockedWeekdayRun']<30
    assert sensitivity['longestUnblockedWeekdayRun']<30
    return {'verdict':'NO_ADMISSIBLE_CONSECUTIVE_30_IN_AUDITED_PROVIDER_WINDOW',
            'ledgerPath':LEDGER,'ledgerSha256':hashlib.sha256(raw).hexdigest(),
            'providerWindowRule':'Official minute API rolling past2 years; nominal bounds at2026-09-16. Actual account cutoff not probed.',
            'primary':conservative,'widenedBoundarySensitivity':sensitivity,
            'requiredSessions':30,'global195ExactDatesRequired':False,
            'futureGDateUsedAsBlocker':False,'unknownResolutionAttempted':False,
            'priceInputs':0,'candidateInputs':0,'providerRequests':0}


if __name__=='__main__':
    print(json.dumps(audit(),ensure_ascii=False,indent=2))
