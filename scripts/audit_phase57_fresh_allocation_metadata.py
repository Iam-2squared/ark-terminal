#!/usr/bin/env python3
"""Outcome-blind allocation reconciliation. Reads explicit governance JSON only.

No model imports, market payloads, network clients, calendar invention, or allocation
mutations. Git object reads are metadata sources; only whitelisted fields persist.
Run from repository root. This produces audit evidence, never a release contract.
"""
import collections
import hashlib
import json
from pathlib import Path
import subprocess

OUT = Path('docs/evidence/phase57-long-only-fresh-allocation-audit')
SOURCES = {}

def digest(b):
    return hashlib.sha256(b).hexdigest()

def git(*args):
    return subprocess.check_output(['git', *args])

def source(name, ref, filename):
    path = filename if '/' in filename else 'predict/research/' + filename
    commit = git('rev-parse', ref).decode().strip()
    b = git('show', commit + ':' + path)
    SOURCES[name] = {'ref': ref, 'commit': commit, 'path': path,
                     'blobSha': git('rev-parse', commit + ':' + path).decode().strip(),
                     'sha256': digest(b)}
    return json.loads(b)

def save(name, obj):
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')

def run():
    OUT.mkdir(parents=True, exist_ok=True)
    er = 'origin/research/phase57-exit-v4-hybrid-msh-large-scale'
    cr = 'origin/research/phase57-capital-allocation-v3-phase-b-integrated'
    sr = 'origin/research/phase57-selector-capacity-v2'
    br = 'origin/research/phase57-hybrid-p21-entry-baseline'
    inv = source('exitInventory', er, 'phase57-exit-v4-stage2-session-metadata-inventory-v1.json')
    em = source('exitManifest', er, 'phase57-exit-v4-stage2-allocation-manifest-v1.json')
    ec = source('exitContract', er, 'phase57-exit-v4-stage2-data-allocation-contract-v1.json')
    close = source('selectorCloseout', sr, 'phase57-selector-closeout-data-use-manifest.json')
    old = source('oldEntryInventory', br, 'phase57-entry-historical-inventory-2026-09-08.json')
    oldalloc = source('oldEntryAllocation', br, 'phase57-entry-allocation-freeze-2026-09-08.json')
    dev = source('oldEntryDevelopment', er, 'phase57-entry-development-allocation-v1.json')
    hold = source('oldEntryHoldout', er, 'phase57-entry-historical-holdout29-source-parity-precommit.json')
    fresh = source('oldEntryFresh', er, 'phase57-minimal-stateful-entry-fresh-allocation.json')
    cap = source('capitalInventory', cr, 'phase57-capital-allocation-historical-oos-inventory-v1.json')
    future = source('capitalFuture', cr, 'phase57-capital-allocation-future-integrated-oos-precommit.json')
    capval = source('capitalValidation', cr, 'phase57-capital-allocation-validation-contract.json')
    base = '649ff89fa8542819d14fa3c5a7337f6dd4fab4a8'
    allocation = source('longAllocation', base, 'predict/long-only/phase57-long-only-session-allocation-v3.json')
    plan = source('longPlan', base, 'predict/long-only/phase57-long-only-data-plan.json')
    scope = source('finalTrainingScope', base, 'phase57-msh-entry-long-v1-final-model-scope-v1.json')
    prior = json.loads(Path('docs/evidence/phase57-msh-entry-long-v1-validation-dataset-preregistration/audit.json').read_text())
    checked = {}
    for p, expected in prior['protectedHashes'].items():
        if p == 'selectorPayloadSha256':
            selector = json.loads(Path('predict/research/phase57-long-only-frozen-selector-v1.json').read_text())
            actual = digest(json.dumps(selector['freezePayload'], sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode())
        else:
            actual = digest(Path(p).read_bytes())
        assert actual == expected, (p, actual, expected)
        checked[p] = {'expected': expected, 'actual': actual, 'pass': True}

    rows = {}
    def row(date=None, ordinal=None):
        key = 'JPX:' + date if date else f'RESERVE282:{ordinal:03}'
        if key not in rows:
            rows[key] = dict(sessionId=key, sessionDate=date, parentReserveOrdinal=ordinal,
                source=[], availableMetadata=[], currentAllocation=[], allocationPurpose=[],
                allocationStatus=[], priorOutcomeExposure='UNKNOWN', exposureReason=[],
                sealed=False, protected=False, usedBySelectorDevelopment=None,
                usedByEntryDevelopment=None, usedByEntryDiagnostics=None, usedByExitResearch=None,
                reservedForExit=False, reservedForValidation=False, reservedForOOS=False,
                reservedForIntegration=False, reallocationAllowed=False,
                localData='UNKNOWN_NOT_PRICE_PAYLOAD_INSPECTED', notes=[])
        if ordinal is not None:
            rows[key]['parentReserveOrdinal'] = ordinal
        return rows[key]

    def claim(r, owner, purpose, sealed=True):
        value = owner + ':' + purpose
        if value not in r['currentAllocation']:
            r['currentAllocation'].append(value)
            r['allocationPurpose'].append(purpose)
        r['sealed'] |= sealed
        r['protected'] |= any(x in purpose.upper() for x in ['OOS', 'RESERVE', 'PROTECTED', 'PURGE', 'EXCLUSION'])
        r['reservedForExit'] |= owner == 'EXIT_STAGE2'
        r['reservedForValidation'] |= 'VALIDATION' in purpose
        r['reservedForOOS'] |= 'OOS' in purpose.upper()
        r['allocationStatus'].append('EXISTING_RECORD_NOT_CHANGED')

    def exposed(r, reason, who=None):
        r['priorOutcomeExposure'] = 'EXPOSED_CONFIRMED_BY_METADATA'
        if reason not in r['exposureReason']:
            r['exposureReason'].append(reason)
        if who:
            r[who] = True

    # The 179 dated diagnostic sessions form the first 179 positions of the
    # chronological parent reserve. Verify every available explicit ordinal/date
    # anchor before using this metadata join. No synthesized business dates.
    reserve179 = sorted(x['sessionDate'] for x in inv['sessions'] if x['allocationClass'] == 'DIAGNOSTIC_ONLY')
    assert len(reserve179) == 179 and reserve179[0] == '2025-04-15' and reserve179[-1] == '2026-01-07'
    ordinal_dates = {i + 1: d for i, d in enumerate(reserve179)}
    for x in dev['sessions']:
        assert ordinal_dates[x['reserveOrdinal']] == x['sessionDate']
    assert [ordinal_dates[i] for i in range(92, 121)] == hold['sessions']
    # Only explicitly attested boundary dates for remaining103; interior unknown.
    ordinal_dates[180] = inv['protectedExternal']['first']
    ordinal_dates[282] = inv['protectedExternal']['last']

    for x in inv['sessions']:
        r = row(x['sessionDate'])
        r['source'].append('J_QUANTS:exitInventory')
        r['availableMetadata'].append({'source': 'exitInventory', 'asOf': inv['asOfJst'],
            'status': x['status'], 'scopeExposure': x['exposureStatus'],
            'rawPersistedAtInventory': x.get('source', {}).get('rawPersisted')})
        claim(r, 'EXIT_STAGE2', x['allocationClass'], any(k in x['allocationClass'] for k in ['VALIDATION', 'HOLDOUT', 'SEALED']))
        if x['exposureStatus'] == 'PRIOR_RESEARCH_EXPOSED':
            exposed(r, 'exitInventory:PRIOR_RESEARCH_EXPOSED')
    for i in range(1, 283):
        r = row(ordinal_dates.get(i), i)
        if i >= 180:
            claim(r, 'ARK_WIDE', 'PROTECTED_103')
            r['source'].append('J_QUANTS:protected-parent-ordinal')
            r['notes'].append('Protected identifier metadata only; no market/event/label data accessed.')
    for x in old['sessions']:
        d = x.get('sessionDate') or ordinal_dates.get(x.get('parentOrdinal'))
        r = row(d, x.get('parentOrdinal'))
        p = old['governanceProfiles'][x['governanceProfile']]
        claim(r, 'LEGACY_SELECTOR_ENTRY', x['governanceProfile'], p.get('SEALED') is True)
        r['source'].append('oldEntryInventory')
        if p.get('outcomeViewed') is True:
            exposed(r, 'oldEntryInventory:' + x['governanceProfile'], 'usedBySelectorDevelopment')
        if x['governanceProfile'] == 'SOURCE_VALIDATION':
            r['protected'] = True
            r['notes'].append('SOURCE_VALIDATION_ONLY_PERMANENT_EXCLUSION; not fresh research data.')
        if x['governanceProfile'] == 'PURGE':
            r['protected'] = True
            r['notes'].append('PURGE_EXCLUDED_NOT_FRESH_EVALUATION')
    for purpose, ds in allocation['partitions'].items():
        for d in ds:
            claim(row(d), 'LONG_INTEGRATED_V3', purpose, not purpose.startswith('DEVELOPMENT'))
    for d in scope['trainingIdentity']['trainingSessions']:
        r = row(d)
        exposed(r, 'finalTrainingScope:LONG_ONLY_DEVELOPMENT', 'usedByEntryDevelopment')
        r['usedBySelectorDevelopment'] = True
        r['usedByEntryDiagnostics'] = True
        r['localData'] = 'SAVED_DEVELOPMENT_ARTIFACTS_IDENTIFIED_NO_PAYLOAD_OPENED'
    for kind in ['FRESH_ENTRY_VALIDATION', 'PURGE_EMBARGO', 'RESERVED_ENTRY_OOS']:
        for d in fresh[kind]:
            r = row(d)
            claim(r, 'LEGACY_ENTRY_FRESH', kind, kind != 'PURGE_EMBARGO')
            r['source'].append('oldEntryFresh:calendar-identity-only')
            r['notes'].append('Reservation does not attest global non-exposure or current price availability.')

    # Capital inventory contains exposure attestations, not outcome measurements.
    # Range-based claims annotate known dates only; never invent sessions in range.
    classifications = cap['classification']
    exposed_ids = {'ENTRY_HOLDOUT_EXPOSED', 'ENTRY_DEVELOPMENT_USED', 'EXIT_BLOCK_C',
                   'EXIT_BLOCK_A', 'EXIT_BLOCK_B', 'EXIT_DIAGNOSTIC_20'}
    for c in classifications:
        if c['id'] not in exposed_ids:
            continue
        for r in rows.values():
            d = r['sessionDate']
            if d and c['window'][0] <= d <= c['window'][1]:
                who = 'usedByExitResearch' if c['id'].startswith('EXIT_') else ('usedByEntryDevelopment' if c['id'] == 'ENTRY_DEVELOPMENT_USED' else 'usedByEntryDiagnostics')
                exposed(r, 'capitalInventory:' + c['id'], who)

    for r in rows.values():
        # Distinguish missing calendar identity from actual unreserved freshness.
        if r['priorOutcomeExposure'].startswith('EXPOSED'):
            r['classification'] = 'EXPOSED'
        elif r['sessionDate'] is None:
            r['classification'] = 'UNKNOWN'
            r['notes'].append('Exact date not mapped; cross-research exposure may overlap EXIT_BLOCK_C. Never certify fresh.')
        elif r['sealed']:
            r['classification'] = 'SEALED'
        elif r['currentAllocation']:
            r['classification'] = 'RESERVED'
        else:
            r['classification'] = 'UNKNOWN'
        for k in ['source', 'allocationStatus', 'notes']:
            r[k] = sorted(set(r[k]))
        if r['classification'] == 'EXPOSED' and any(m.get('scopeExposure') == 'METADATA_ONLY_OUTCOME_UNTOUCHED' for m in r['availableMetadata']):
            r['notes'].append('CONFLICT: scope-level untouched metadata cannot override cross-research positive exposure attestation.')
    values = sorted(rows.values(), key=lambda r: r['sessionId'])
    counts = dict(collections.Counter(r['classification'] for r in values))
    for k in ['EXPOSED', 'RESERVED', 'SEALED', 'FRESH_AVAILABLE', 'UNKNOWN']:
        counts.setdefault(k, 0)
    assert len(values) == len({r['sessionId'] for r in values})
    assert sum(counts.values()) == len(values) and counts['FRESH_AVAILABLE'] == 0
    assert len({r['parentReserveOrdinal'] for r in values if r['parentReserveOrdinal']}) == 282
    conflict_dates = allocation['partitions']['VALIDATION']
    conflict = [rows['JPX:' + d] for d in conflict_dates]
    assert len(conflict) == 30
    assert sum(r['classification'] == 'EXPOSED' for r in conflict) == 25

    def group(ds):
        rs = [rows['JPX:' + d] for d in ds]
        return {'sessions': len(rs), 'first': min(ds), 'last': max(ds),
                'classificationCounts': dict(collections.Counter(r['classification'] for r in rs)),
                'globallyFreshCertified': 0}
    matrix = {k: group(v) for k, v in allocation['partitions'].items()}
    exit_matrix = {k: group([x['sessionDate'] for x in em['sessions'] if x['allocationClass'] == k]) for k in sorted({x['allocationClass'] for x in em['sessions']})}
    safety = {k: False for k in ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed',
        'rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed',
        'productionUpdateAllowed','transmitted','shortAllowed','marginAllowed','leverageAllowed']}
    summary = dict(schemaVersion=1, dateJst='2026-09-16',
        verdict='PHASE57_LONG_ONLY_DATA_ALLOCATION_AUDIT_COMPLETE',
        recommendation='D.INSUFFICIENT_INFORMATION',
        meaning='Inventory and plan complete within explicit metadata domain; global data sufficiency and Validation release remain unresolved.',
        sourceHead='649ff89fa8542819d14fa3c5a7337f6dd4fab4a8',
        latestMain='6b6c4d522cd1863132185463a0aed74bc819be01',
        totalKnownIdentities=len(values), datedIdentities=sum(r['sessionDate'] is not None for r in values),
        unmappedParentIdentities=sum(r['sessionDate'] is None for r in values), classificationCounts=counts,
        totalRepositoryUniqueSessions='UNKNOWN_OUTSIDE_ENUMERATED_METADATA_DOMAIN',
        historicalIdentities=487, separatelyEnumeratedFreshReservations=26,
        futureRuleOnlyBudgetsNotAddedToIdentityTotal={'longIntegratedProspective':25,'capitalIntegratedOos':20},
        classificationRule='EXPOSED positive evidence first; unmapped dates UNKNOWN; otherwise SEALED, RESERVED, UNKNOWN. Operational seals/reservations retained as orthogonal flags.',
        exposureCountLimitation='Exact mapped exposure lower bound. EXIT_BLOCK_C metadata covers protected June dates without full ordinal/date mapping; UNKNOWN preserves this uncertainty. No invented calendar.',
        negativeAttestation='No globally fresh unreserved sessions certified; absence of an exposure record is not proof of freshness.',
        protectedVerification=checked, longAllocationMatrix=matrix, exitAllocationMatrix=exit_matrix,
        conflict30={'count':30,'exitDevB':10,'exitValidation':20,'confirmedPriorSelectorExposure':25,'permanentSourceExclusion':4,'purge':1,'reallocationAuthorization':'NONE_FOUND_OR_ISSUED','source':'exitContract + selectorCloseout + oldEntryInventory'},
        sources=SOURCES,
        requests={'Yahoo':0,'JQuants':0,'otherMarketData':0,'confidence':'CONFIRMED_FOR_THIS_AUDIT_TOOL_CALLS_ONLY_NO_AUTONOMOUS_JOB_CLAIM'},
        actions={'allocationChanges':0,'candidatePrediction':0,'validationOutcomeAccess':0,'oosOutcomeAccess':0,'exitOutcomeAccess':0,'modelFit':0,'scalerFit':0,'thresholdComparison':0,'shortEvaluation':0},
        safety=safety,
        unresolved=['GLOBAL_CROSS_RESEARCH_OWNERSHIP_AND_EXPOSURE_RECONCILIATION','PROTECTED_103_FULL_CALENDAR_MAPPING','CURRENT_PRIVATE_PRICE_CACHE_EXISTENCE','LONG_EXIT_SPECIFIC_SAMPLE_BUDGET','INDEPENDENT_INTEGRATION_AND_PORTFOLIO_STAGE_BUDGET','CURRENT_ENTITLEMENT_FOR_FUTURE_WINDOW'],
        nextAction='Separate metadata-only architecture/allocation decision: reconcile supersession and exposure, retain all seals, define joint later-stage independent budgets and acquisition feasibility. Do not unlock the conflicting30 or select Validation dates.')
    save('master-ledger.json', {'schemaVersion':1,'classificationRule':summary['classificationRule'],'sessions':values})
    save('conflict-30.json', {'sources':{k:SOURCES[k] for k in ['exitContract','exitManifest','selectorCloseout','oldEntryInventory']},'sessions':conflict})
    save('audit.json', summary)
    save('source-metadata-extracts.json', {
        'exit':{k:ec[k] for k in ['contractId','contractVersion','asOfJst','status','allocation','protection','stage3']},
        'capital':{k:cap[k] for k in ['status','decision','classification','nextCleanOpportunity']},
        'capitalFuture':{k:future[k] for k in ['status','window','eligibilityRule','reservedBoundary']},
        'capitalValidation':{k:capval[k] for k in ['status','futureWindow','executionGate']},
        'longPlan':{k:plan[k] for k in ['datasetSplit','researchObjective','humanOverfittingControls','integratedResearchDataset','integratedComparisonContract','currentEntitlementEvidence','storageManifest']},
        'legacyFresh':{k:fresh[k] for k in ['status','FRESH_ENTRY_VALIDATION','PURGE_EMBARGO','RESERVED_ENTRY_OOS','PROSPECTIVE','unknownExposureDefault']},
        'legacyUnresolved':old['unresolvedDatasets'],
        'legacyEntryProtection':oldalloc['protectedReserve']})
    print(json.dumps({k:summary[k] for k in ['totalKnownIdentities','datedIdentities','unmappedParentIdentities','classificationCounts','longAllocationMatrix','exitAllocationMatrix']},indent=2))

if __name__ == '__main__':
    run()
