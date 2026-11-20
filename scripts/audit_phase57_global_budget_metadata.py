#!/usr/bin/env python3
"""Metadata-only budget attempt; no release, models, market clients or calendar inference."""
import collections
import hashlib
import json
from pathlib import Path

BASE = Path('docs/evidence/phase57-long-only-fresh-allocation-audit')
OUT = Path('docs/evidence/phase57-long-only-global-data-budget')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read(path):
    return json.loads(Path(path).read_text())

def save(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    previous = read(BASE / 'audit.json')
    base_rows = read(BASE / 'master-ledger.json')['sessions']
    extracts = read(BASE / 'source-metadata-extracts.json')
    rows = []
    transitions = collections.Counter()
    for old in base_rows:
        flags = {'protected': old['protected'], 'sealed': old['sealed'],
                 'reserved': bool(old['currentAllocation']),
                 'exposed': old['classification'] == 'EXPOSED',
                 'excluded': any('SOURCE_VALIDATION' in x for x in old['currentAllocation']),
                 'purged': any('PURGE' in x for x in old['currentAllocation'])}
        primary = old['classification']
        if primary not in ['EXPOSED', 'UNKNOWN']:
            if flags['excluded']:
                primary = 'EXCLUDED'
            elif flags['purged']:
                primary = 'PURGED'
            elif old['parentReserveOrdinal'] is not None and old['parentReserveOrdinal'] >= 180:
                primary = 'PROTECTED'
        r = dict(sessionId=old['sessionId'], sessionDate=old['sessionDate'],
                 parentReserveOrdinal=old['parentReserveOrdinal'],
                 primaryClassification=primary, previousClassification=old['classification'],
                 secondaryFlags=flags, allocations=old['currentAllocation'],
                 priorOutcomeExposure=old['priorOutcomeExposure'],
                 exposureEvidence=old['exposureReason'],
                 reallocationAllowed=False, freshPromotionEvidence=None,
                 sourceLedgerSessionId=old['sessionId'])
        rows.append(r)
        transitions[(old['classification'], primary)] += 1
    counts = {k: 0 for k in ['EXPOSED','RESERVED','SEALED','PROTECTED','FRESH_AVAILABLE','PURGED','EXCLUDED','UNKNOWN']}
    counts.update(collections.Counter(r['primaryClassification'] for r in rows))
    assert len(rows) == 513 and sum(counts.values()) == 513
    assert counts == dict(EXPOSED=375, RESERVED=4, SEALED=25, PROTECTED=1,
                          FRESH_AVAILABLE=0, PURGED=3, EXCLUDED=4, UNKNOWN=101)
    assert sum(r['sessionDate'] is not None for r in rows) == 412
    assert {r['parentReserveOrdinal'] for r in rows if r['primaryClassification']=='UNKNOWN'} == set(range(181,282))
    assert all(r['secondaryFlags']['protected'] for r in rows if r['primaryClassification']=='UNKNOWN')
    assert all(r['allocations']==old['currentAllocation'] and r['sessionDate']==old['sessionDate'] for r,old in zip(rows,base_rows))
    checked = {}
    for p, check in previous['protectedVerification'].items():
        if p == 'selectorPayloadSha256':
            payload = read('predict/research/phase57-long-only-frozen-selector-v1.json')['freezePayload']
            actual = hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
        else:
            actual = sha(p)
        assert actual == check['expected'], p
        checked[p] = dict(expected=check['expected'], actual=actual, passed=True)

    future = extracts['capitalFuture']
    assert future['window']['targetEligibleMarketSessions'] == 20
    assert future['window']['notBeforeSessionDate'] == '2026-10-22'
    future_block = dict(blockId='LEGACY_CAPITAL_INTEGRATED_OOS_FUTURE20',
        primaryClassification='RESERVED', sealed=True, exactSessionList=None,
        sessionSelectionRule=future['eligibilityRule'], window=future['window'],
        owner='LEGACY_CAPITAL_ALLOCATION_INTEGRATED_CANDIDATE',
        purpose=['INTEGRATION','CAPITAL_PORTFOLIO','EXISTING_ARK_COMPARISON_IN_LEGACY_CONTRACT_SCOPE'],
        longOnlyCandidateTransferAllowed=False, entryValidationUseAllowed=False,
        source=previous['sources']['capitalFuture'],
        accounting='ONE_EXISTING_RULE_ONLY_BLOCK; not20 additional dated identities or20 per purpose')
    save('resolved-master-ledger.json', dict(schemaVersion=1,
        previousLedgerPath=str(BASE/'master-ledger.json'),previousLedgerSha256=sha(BASE/'master-ledger.json'),
        classificationRule='EXPOSED and UNKNOWN preserved; non-exposed explicit exclusion/purge/Protected purpose made primary; secondary seals and all allocations unchanged.',
        sessions=rows,futureBlocks=[future_block]))
    save('classification-audit.json', dict(previousCounts=previous['classificationCounts'],
        currentCounts=counts,totalKnownIdentifiers=513,dateResolved=412,
        dateResolutionAdded=0,unknown101Resolved=0,unknownRemaining=101,
        unknownOrdinals=list(range(181,282)),
        transitions=[dict(previous=a,current=b,count=n) for (a,b),n in sorted(transitions.items())],
        previousSealed32=[r for r in rows if r['previousClassification']=='SEALED'],
        previousReserved5=[r for r in rows if r['previousClassification']=='RESERVED'],
        sealed32PurposeCounts={'LEGACY_ENTRY_VALIDATION':15,'LEGACY_ENTRY_OOS':10,'PROTECTED':1,'PERMANENT_SOURCE_EXCLUSION':4,'PURGE':2},
        reserved5PurposeCounts={'EXIT_DEV_A_AND_LONG_DEVELOPMENT_A':4,'LEGACY_ENTRY_PURGE_EMBARGO':1},
        allocationChanges=0,protectedOrSealedAllocationChanges=0,
        freshPromotions=0,existingUsableFreshSessionList=[],
        coverage='Previous513 identity domain only; exposed375 remains a mapped lower bound, not a global non-exposure attestation.'))
    safety = previous['safety']
    assert all(v is False for v in safety.values())
    save('budget-attempt.json',dict(schemaVersion=1,dateJst='2026-09-16',
        repository='Iam-2squared/ark-terminal',branch='research/phase57-long-only-cash-equity',pr=587,
        auditedHead='825da2af3256f554f4586be0db6d5ba36cc23309',
        latestMain='6b6c4d522cd1863132185463a0aed74bc819be01',
        verdict='PHASE57_LONG_ONLY_GLOBAL_DATA_BUDGET_BLOCKED',
        blockers=['UNKNOWN_IDENTITY_UNRESOLVED','ENTRY_BUDGET_UNRESOLVED','EXIT_BUDGET_UNRESOLVED',
                  'INTEGRATION_BUDGET_UNRESOLVED','PORTFOLIO_BUDGET_UNRESOLVED',
                  'PROTECTED_DATA_CONFLICT','INSUFFICIENT_METADATA'],
        frozenContractIssued=False,globalDataBudgetContractSha256=None,
        artifactHashIsNotFrozenContractHash=True,
        protectedVerification=checked,priorAuditManifestSha256=sha(BASE/'manifest.json'),
        allocationChanges=0,protectedOrSealedAllocationChanges=0,
        totalNewFreshSessionsRequired=None,minimumConfirmedEntryValidationShortage=30,
        minimumConfirmedEntryValidationShortageIsNotAcquisitionAuthorization=True,
        jquantsNewAcquisitionRequired='UNRESOLVED',
        priorCandidate30Status='NOT_FRESH_25_EXPOSED_4_PERMANENTLY_EXCLUDED_1_PURGE; never reallocate for Fresh Entry Validation',
        safety=safety,
        counts={'outcomeAccess':0,'candidatePrediction':0,'validationPrediction':0,'oosMarketOrOutcomeAccess':0,
                'exitOutcomeAccess':0,'projectModelFit':0,'scalerFit':0,'shortEvaluation':0,
                'yahooPriceRequests':0,'jquantsPriceRequests':0,'otherMarketDataPriceRequests':0,
                'providerMetadataRequests':0},
        counterScope='This task only; Git metadata operations excluded from market-data requests; no claim about independent autonomous jobs.',
        nextAction='Separate outcome-blind LONG-specific stage-budget and evaluation-reuse contract. Resolve Entry OOS, EXIT Dev/Validation/OOS, Integration/Portfolio/Comparison roles and counts; preserve all existing reservations. No price acquisition or Validation release.'))
    print(json.dumps({'counts':counts,'dateResolved':412,'unknownResolved':0,'frozenHashes':'PASS'}))

if __name__ == '__main__':
    main()
