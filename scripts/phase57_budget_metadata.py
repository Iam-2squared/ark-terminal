"""Strict outcome-free budget input boundary and independent arithmetic.

Only planning metadata is accepted. This module does not load models, datasets,
candidate contracts, provider clients or outcome records.
"""
from decimal import Decimal, ROUND_CEILING
import hashlib
import json

SOURCE_KEYS = {
    'validationBlockSessions', 'outerOosBlockSessions', 'replicationBlockSessions',
    'prospectiveBlockSessions', 'exitCheckpointATarget', 'planningUniverseSymbols',
    'referenceMinutePages', 'referenceSessionCount',
}
ASSUMPTION_KEYS = {
    'zDecimal', 'worstCaseRateDecimal', 'halfWidthDecimal', 'bufferSessions',
    'minutesPerSession', 'minutesPerBar', 'rowBytesMin', 'rowBytesMax',
    'warmupDailyQueries',
}
IDENTITY_KEYS = {'sessionCount', 'sessionListSha256', 'trainingSessions'}


def _keys(value, expected, location):
    # Never include rejected values or source dictionaries in exception text.
    if type(value) is not dict or set(value) != expected:
        raise ValueError('METADATA_SCHEMA_REJECTED:' + location)


def project_identity(source):
    """Copy only explicit identity fields; never enumerate or render siblings."""
    result = {k: source[k] for k in sorted(IDENTITY_KEYS)}
    validate_identity(result)
    return result


def validate_identity(value):
    _keys(value, IDENTITY_KEYS, 'identity')
    if type(value['sessionCount']) is not int or value['sessionCount'] <= 0:
        raise ValueError('INVALID_SESSION_COUNT')
    dates = value['trainingSessions']
    if type(dates) is not list or any(type(d) is not str for d in dates):
        raise ValueError('INVALID_SESSION_LIST')
    if len(dates) != value['sessionCount'] or len(set(dates)) != len(dates) or dates != sorted(dates):
        raise ValueError('SESSION_IDENTITY_MISMATCH')
    digest = hashlib.sha256(json.dumps(dates, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
    if value['sessionListSha256'] != digest:
        raise ValueError('SESSION_IDENTITY_HASH_MISMATCH')


def validate_input(value):
    _keys(value, {'schemaVersion', 'sourceMetadata', 'designAssumptions', 'developmentIdentity'}, 'root')
    if type(value['schemaVersion']) is not int or value['schemaVersion'] != 1:
        raise ValueError('INVALID_SCHEMA_VERSION')
    source, assumptions = value['sourceMetadata'], value['designAssumptions']
    _keys(source, SOURCE_KEYS, 'sourceMetadata')
    _keys(assumptions, ASSUMPTION_KEYS, 'designAssumptions')
    validate_identity(value['developmentIdentity'])
    if any(type(v) is not int or v <= 0 for v in source.values()):
        raise ValueError('INVALID_PLANNING_INTEGER')
    for key in ASSUMPTION_KEYS - {'zDecimal', 'worstCaseRateDecimal', 'halfWidthDecimal'}:
        if type(assumptions[key]) is not int or assumptions[key] < 0:
            raise ValueError('INVALID_DESIGN_INTEGER')
    # These are the predeclared design assumptions, not a tunable interface.
    if tuple(assumptions[k] for k in ['zDecimal', 'worstCaseRateDecimal', 'halfWidthDecimal']) != ('1.96', '0.5', '0.10'):
        raise ValueError('FIXED_UNCERTAINTY_ASSUMPTIONS_CHANGED')
    if assumptions['minutesPerBar'] <= 0 or assumptions['minutesPerSession'] % assumptions['minutesPerBar']:
        raise ValueError('INVALID_PLANNING_CADENCE')
    return value


def derive(value):
    validate_input(value)
    s, a, identity = value['sourceMetadata'], value['designAssumptions'], value['developmentIdentity']
    z, rate, half = (Decimal(a[k]) for k in ['zDecimal', 'worstCaseRateDecimal', 'halfWidthDecimal'])
    minimum = int((z*z*rate*(1-rate)/(half*half)).to_integral_value(rounding=ROUND_CEILING))
    sizes = {'DEV': identity['sessionCount'], 'A': s['validationBlockSessions'],
             'B': s['outerOosBlockSessions'], 'C': s['validationBlockSessions'],
             'D': s['outerOosBlockSessions'], 'E': s['replicationBlockSessions'],
             'F': s['outerOosBlockSessions'], 'G': s['prospectiveBlockSessions']}
    uses = {'ENTRY_VALIDATION': ['A'], 'ENTRY_OOS': ['B'], 'EXIT_DEVELOPMENT': ['DEV'],
            'EXIT_VALIDATION': ['C'], 'EXIT_OOS': ['D'], 'INTEGRATION_VALIDATION': ['E'],
            'CAPITAL_ALLOCATION': ['DEV', 'E'], 'PORTFOLIO': ['DEV', 'E'],
            'FINAL_COMPARISON': ['F'], 'FINAL_PROSPECTIVE_OOS': ['G']}
    event_floors = {'DEV': s['exitCheckpointATarget'], 'A': None, 'B': None,
                    'C': minimum, 'D': minimum, 'E': minimum, 'F': None, 'G': None}
    gross = sum(sizes[b] for row in uses.values() for b in row)
    unique = sum(sizes.values())
    fresh = unique - sizes['DEV']
    minute_rows = fresh*s['planningUniverseSymbols']*a['minutesPerSession']
    minute_pages = (fresh*s['referenceMinutePages'] + s['referenceSessionCount'] - 1)//s['referenceSessionCount']
    return {'blockSessions': sizes, 'stageBlocks': uses, 'eventFloors': event_floors,
            'grossSessions': gross, 'netUniqueSessions': unique, 'newFreshSessions': fresh,
            'grossEventFloors': s['exitCheckpointATarget'] + 5*minimum,
            'netEventFloors': s['exitCheckpointATarget'] + 3*minimum,
            'newFreshEventFloors': 3*minimum, 'bufferSessions': a['bufferSessions'],
            'planning5mBars': minute_rows//a['minutesPerBar'], 'planningMinuteRows': minute_rows,
            'planningStorageBytes': [minute_rows*a['rowBytesMin'], minute_rows*a['rowBytesMax']],
            'planningRequests': minute_pages + 2*fresh + a['warmupDailyQueries']}


def compare_previous(result, previous):
    """Fail closed if independent arithmetic would silently change any budget."""
    expected_sizes = {b['blockId']: b['sessions'] for b in previous['acquisitionBlocks']}
    expected_events = {b['blockId']: b['minimumDistinctFirstEntryEvents'] for b in previous['acquisitionBlocks']}
    expected_uses = {r['stage']: r['blocks'] for r in previous['responsibilityMatrix']}
    if (result['blockSessions'], result['eventFloors'], result['stageBlocks']) != (expected_sizes, expected_events, expected_uses):
        raise ValueError('BUDGET_RESPONSIBILITY_CHANGED')
    b, a = previous['globalBudget'], previous['newJQuantsRequirement']
    comparisons = {'grossSessions': b['grossSessionRoleCount'], 'netUniqueSessions': b['netUniqueAllSessions'],
                   'newFreshSessions': b['netUniqueFreshSessions'], 'grossEventFloors': b['grossApplicableDistinctEventFloors'],
                   'netEventFloors': b['netApplicableDistinctEventFloors'], 'newFreshEventFloors': b['newFreshApplicableDistinctEventFloors'],
                   'bufferSessions': a['bufferSessions'], 'planning5mBars': a['estimated5mBars'],
                   'planningMinuteRows': a['estimatedMinuteRowsDenseUpper'], 'planningStorageBytes': a['estimatedStorageBytesMinuteAt100To200BytesPerRow'],
                   'planningRequests': a['estimatedRequestsPoint']}
    if any(result[k] != v for k, v in comparisons.items()):
        raise ValueError('BUDGET_ARITHMETIC_CHANGED')
    return True
