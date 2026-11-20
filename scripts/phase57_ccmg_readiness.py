"""CCMG zero-fit readiness on the frozen R50-owned Development paths.

Only a fresh closed checkpoint price may certify a milestone or a breach.
This script emits a dry decision trace; it does not resolve fills or evaluate PnL.
"""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import math
import statistics
from pathlib import Path

from scripts import phase57_exit_checkpoints_v1 as checkpoints
from scripts import phase57_wpsd_phase0 as upstream

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/evidence/phase57-checkpoint-certified-guard-exit'
PRE_SHA = '679cbe81bdaf483c7c68dbd290a520cdb6289ea1573519816e421b4c563cd079'
LADDER = (1, 2, 3, 5, 10)
FLOORS = {1: 0, 2: 1, 3: 2, 5: 3, 10: 5}
NEXT = {0: 1, 1: 2, 2: 3, 3: 5, 5: 10, 10: None}


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=False, allow_nan=False) + '\n').encode()


def decision_step(highest, streak, fresh, current):
    """Outcome-blind policy transition on a scheduled checkpoint."""
    if not fresh:
        require(current is None, 'STALE_USED_AS_CURRENT')
        return highest, 0, 'DATA_GAP', None, 'DATA_GAP_RESET' if streak else None
    require(isinstance(current, (int, float)) and math.isfinite(current), 'FRESH_RETURN')
    promoted = max((m for m in LADDER if current >= m), default=0)
    if promoted > highest:
        highest, streak = promoted, 0
        promotion = True
    else:
        promotion = False
    if highest == 0:
        return highest, 0, 'BASELINE', None, None
    floor = FLOORS[highest]
    if current >= floor or promotion:
        return highest, 0, 'ACTIVE', floor, 'PROMOTION' if promotion else ('RECOVERY' if streak else None)
    streak += 1
    return highest, streak, 'SELL_INTENT' if streak == 2 else 'ALERT_1', floor, 'BREACH_2' if streak == 2 else 'BREACH_1'


def read_control():
    result = {}
    with gzip.open(upstream.R50_CALENDAR, 'rt') as f:
        for line in f:
            row = json.loads(line)
            key = (row['entryArm'], row['entryId'])
            require(key not in result, 'DUPLICATE_CONTROL')
            result[key] = {'decisionNow': row['decisionNow'], 'exitKind': row['exitKind'],
                           'exitMinute': row['exitMinute'], 'exitPrice': row['exitPrice']}
    return result


def trace_entry(key, entry, control, bars, primary, initial_or_replacement):
    day, eprice = entry['session'], float(entry['effectiveEntryPrice'])
    ceiling = control['decisionNow']
    grid = [now for now in checkpoints.checkpoint_grid(day, entry['entryMinute']) if now <= ceiling]
    require(grid and grid[-1] == ceiling, 'CONTROL_NOT_ON_CHECKPOINT_GRID')
    envelope = {'opportunity': entry['opportunity'], 'session': day,
                'symbol': entry['symbol'], 'entryId': entry['entryId'],
                'entryMinute': entry['entryMinute'], 'price': eprice}
    prefix = ()
    highest = streak = 0
    certified_at = {}
    first_alert = None
    first_sell = None
    control_same = False
    missing_run = max_missing_run = 0
    scheduled = fresh_count = missing_count = data_gap_reset = 0
    skipped_promotions = recovery = alert = 0
    checkpoints_out = []
    arm = upstream.ARMS[key[0]]
    for idx, now in enumerate(grid):
        # Only the just-closed slot is admitted; no future suffix is handed to
        # position_features, and an absent slot leaves the prior prefix stale.
        raw = bars.get(now - 1)
        if raw is not None:
            one = checkpoints.closed_prefix(day, now, (raw,))
            require(len(one) == 1 and one[0].start + 1 == now and
                    one[0].known_at <= now, 'FUTURE_OR_INVALID_CURRENT_BAR')
            prefix = prefix + one
        position = checkpoints.position_features(envelope, now, prefix)
        fresh = position['freshClosedPrice']
        current = position['currentReturnPct']
        require(fresh == (raw is not None) and ((current is None) == (not fresh)),
                'FRESHNESS_PARITY')
        prev_highest, prev_streak = highest, streak
        highest, streak, state, floor, event = decision_step(highest, streak, fresh, current)
        if fresh:
            fresh_count += 1
            missing_run = 0
        else:
            missing_count += 1
            missing_run += 1
            max_missing_run = max(max_missing_run, missing_run)
        scheduled += 1
        if event == 'DATA_GAP_RESET':
            data_gap_reset += 1
        if event == 'RECOVERY':
            recovery += 1
        if event == 'BREACH_1':
            alert += 1
            if first_alert is None:
                first_alert = now
        if event == 'BREACH_2':
            first_sell = now
        if highest > prev_highest:
            for m in LADDER:
                if prev_highest < m <= highest:
                    certified_at[m] = now
            if sum(prev_highest < m <= highest for m in LADDER) > 1:
                skipped_promotions += 1
        next_m = NEXT[highest]
        snapshot = {
            'arm': arm, 'entryId': key[1], 'session': day, 'now': now,
            'scheduledIndex': idx, 'freshClosedPrice': fresh,
            'scheduledGridLength': len(grid),
            'currentReturnPct': current, 'highestCertifiedMilestone': highest or None,
            'floorPct': floor, 'state': state, 'breachStreak': streak,
            'event': event, 'previousBreachStreak': prev_streak,
            'nextMilestone': next_m,
            'distanceToNextMilestonePp': None if current is None or next_m is None else next_m-current,
            'floorMarginPp': None if current is None or floor is None else current-floor,
            'controlTerminalAtThisCheckpoint': now == ceiling,
            'inputMaxBarEnd': None if not prefix else prefix[-1].start+1,
            'inputMaxKnownAt': max((x.known_at for x in prefix), default=None)
        }
        require(snapshot['inputMaxBarEnd'] is None or snapshot['inputMaxBarEnd'] <= now, 'FUTURE_BAR')
        require(snapshot['inputMaxKnownAt'] is None or snapshot['inputMaxKnownAt'] <= now, 'FUTURE_PUBLICATION')
        checkpoints_out.append(snapshot)
        if first_sell is not None:
            control_same = now == ceiling
            break
    if first_sell is not None:
        terminal = 'BOTH_TRIGGER_SAME_CHECKPOINT' if control_same else 'CANDIDATE_FIRST'
    elif control['exitPrice'] is None:
        terminal = 'UNRESOLVED_CANONICAL_CONTROL_FILL'
    elif control['exitKind'] == 'FORCED_TERMINAL':
        terminal = 'CONTROL_TERMINAL_WITHOUT_CANDIDATE'
    else:
        terminal = 'CONTROL_FIRST'
    require(terminal in ('BOTH_TRIGGER_SAME_CHECKPOINT', 'CANDIDATE_FIRST',
                         'CONTROL_TERMINAL_WITHOUT_CANDIDATE', 'CONTROL_FIRST',
                         'UNRESOLVED_CANONICAL_CONTROL_FILL'),
            'UNCLASSIFIED_TERMINAL')
    return checkpoints_out, {
        'arm': arm, 'entryId': key[1], 'session': day,
        'primary': primary, 'initialOrReplacement': initial_or_replacement,
        'controlNow': ceiling, 'controlExitKind': control['exitKind'],
        'controlFillKnown': control['exitPrice'] is not None,
        'terminal': terminal, 'scheduledEvaluated': scheduled, 'fresh': fresh_count,
        'missing': missing_count, 'entriesWithGap': int(missing_count > 0),
        'maxConsecutiveGap': max_missing_run, 'dataGapReset': data_gap_reset,
        'certifiedAt': {str(k): v for k,v in certified_at.items()},
        'firstCertification': certified_at.get(1) or (min(certified_at.values()) if certified_at else None),
        'activeMinutesToFirstCertification': None if not certified_at else
            checkpoints.active_elapsed(day, entry['entryMinute'], min(certified_at.values())),
        'skippedPromotions': skipped_promotions, 'alerts': alert,
        'recoveries': recovery, 'firstAlert': first_alert, 'firstSellIntent': first_sell,
        'highestCertifiedAtTerminal': highest or None}


def aggregate(rows):
    by_arm = {}
    for arm in ('IM', 'R1', 'combined'):
        selected = [x for x in rows if arm == 'combined' or x['arm'] == arm]
        by_arm[arm] = {
            'entries': len(selected), 'primary': sum(x['primary'] for x in selected),
            'scheduled': sum(x['scheduledEvaluated'] for x in selected),
            'fresh': sum(x['fresh'] for x in selected),
            'missing': sum(x['missing'] for x in selected),
            'freshCoverage': (sum(x['fresh'] for x in selected)/sum(x['scheduledEvaluated'] for x in selected)
                              if selected else None),
            'entriesWithGap': sum(x['entriesWithGap'] for x in selected),
            'maxConsecutiveGap': max((x['maxConsecutiveGap'] for x in selected), default=0),
            'certified': {str(m): sum(str(m) in x['certifiedAt'] for x in selected) for m in LADDER},
            'none': sum(not x['certifiedAt'] for x in selected),
            'alerts': sum(x['alerts'] for x in selected),
            'recoveries': sum(x['recoveries'] for x in selected),
            'twoCheckpointSellIntent': sum(x['firstSellIntent'] is not None for x in selected),
            'candidateFirst': sum(x['terminal'] == 'CANDIDATE_FIRST' for x in selected),
            'bothSame': sum(x['terminal'] == 'BOTH_TRIGGER_SAME_CHECKPOINT' for x in selected),
            'controlFirst': sum(x['terminal'] == 'CONTROL_FIRST' for x in selected),
            'controlTerminalWithoutCandidate': sum(x['terminal'] == 'CONTROL_TERMINAL_WITHOUT_CANDIDATE' for x in selected),
            'unresolvedControlFill': sum(x['terminal'] == 'UNRESOLVED_CANONICAL_CONTROL_FILL' for x in selected),
            'dataGapResets': sum(x['dataGapReset'] for x in selected),
            'skippedPromotions': sum(x['skippedPromotions'] for x in selected),
            'initial': sum(x['initialOrReplacement'] == 'Initial' for x in selected),
            'replacement': sum(x['initialOrReplacement'] == 'Replacement' for x in selected)
        }
    return by_arm


def run(args):
    raw_pre = (OUT/'CYCLE_PRECOMMIT.json').read_bytes()
    require(sha(raw_pre) == PRE_SHA and (OUT/'CYCLE_PRECOMMIT.sha256').read_text().split()[0] == PRE_SHA,
            'PRECOMMIT_CHANGED')
    pre = json.loads(raw_pre)
    require(pre['runtime']['ladderPct'] == list(LADDER) and
            pre['runtime']['floorByHighestPct'] == {'NONE': None, '1': 0, '2': 1, '3': 2, '5': 3, '10': 5} and
            not any(pre['safety'].values()), 'PRECOMMIT_RULE_OR_SAFETY_DRIFT')
    old_pre, receipt, ledgers, paired = upstream.load_fixed(args.r45, args.replay, args.audit)
    entries, calendar, funded, context, paths, sessions = upstream.control_universe(old_pre, ledgers)
    controls = read_control()
    require(set(entries) <= set(controls) and len(entries) == 1614 and len(funded) == 111 and
            all(calendar[k] == controls[k]['decisionNow'] for k in entries),
            'CONTROL_CENSUS_DRIFT')
    events, entries_out = [], []
    for key, entry in sorted(entries.items()):
        trace, summary = trace_entry(key, entry, controls[key], paths[entry['opportunity']],
                                     key in funded, context.get(key))
        events.extend(trace)
        entries_out.append(summary)
    require(len(entries_out) == 1614 and
            collections.Counter(x['arm'] for x in entries_out) == {'IM': 819, 'R1': 795} and
            sum(x['primary'] and x['arm'] == 'IM' for x in entries_out) == 79 and
            sum(x['primary'] and x['arm'] == 'R1' for x in entries_out) == 32,
            'ENTRY_AND_PRIMARY_CENSUS')
    require(all(x['fresh']+x['missing'] == x['scheduledEvaluated'] for x in entries_out),
            'R1_ACCOUNTING')
    raw_trace = b''.join(encoded(x) for x in events)
    zipped = gzip.compress(raw_trace, mtime=0)
    summary_rows = b''.join(encoded(x) for x in entries_out)
    summary_zip = gzip.compress(summary_rows, mtime=0)
    prior_trace = (OUT/'CHECKPOINT_DRY_TRACE.jsonl.gz')
    prior_summary = (OUT/'CHECKPOINT_ENTRY_SUMMARY.jsonl.gz')
    repeat = (prior_trace.is_file() and prior_summary.is_file() and
              prior_trace.read_bytes() == zipped and prior_summary.read_bytes() == summary_zip)
    require(not prior_trace.exists() or not prior_summary.exists() or repeat,
            'R5_DRY_TRACE_BYTE_DRIFT')
    prior_trace.write_bytes(zipped)
    prior_summary.write_bytes(summary_zip)
    all_agg = aggregate(entries_out)
    primary_agg = aggregate([x for x in entries_out if x['primary']])
    timing = {}
    for arm in ('IM', 'R1'):
        timing[arm] = {}
        for part in ('EARLY','MID','LATE'):
            selected = [x for x in events if x['arm'] == arm and
                ('EARLY' if x['scheduledIndex']/max(1, x['scheduledGridLength']-1) < 1/3 else
                 'MID' if x['scheduledIndex']/max(1, x['scheduledGridLength']-1) < 2/3 else
                 'LATE') == part]
            timing[arm][part] = {'scheduled': len(selected), 'fresh': sum(x['freshClosedPrice'] for x in selected),
                                 'missing': sum(not x['freshClosedPrice'] for x in selected)}
    by_session = {s: {arm: aggregate([x for x in entries_out if x['session'] == s and x['arm'] == arm])[arm]
                      for arm in ('IM','R1')} for s in sessions}
    gate = {'R1': 'PASS', 'R2': 'PASS', 'R3': 'PASS',
            'R4': 'PASS' if all(x['terminal'] in ('CANDIDATE_FIRST','CONTROL_FIRST',
                     'BOTH_TRIGGER_SAME_CHECKPOINT','CONTROL_TERMINAL_WITHOUT_CANDIDATE',
                     'UNRESOLVED_CANONICAL_CONTROL_FILL')
                     for x in entries_out if x['primary']) else 'FAIL',
            'R5': 'PASS' if repeat else 'PENDING_IDENTICAL_RERUN', 'R6': 'PASS'}
    result = {'schema': 'phase57-ccmg-checkpoint-readiness-v1',
              'precommitSha256': PRE_SHA, 'sourcePinsSha256': json.loads((OUT/'START_AUDIT.json').read_text())['sourcePinsSha256'],
              'traceSha256': sha(zipped), 'entrySummarySha256': sha(summary_zip),
              'traceRows': len(events), 'entryRows': len(entries_out), 'allEntry': all_agg,
              'primary': primary_agg, 'bySession': by_session, 'byTiming': timing,
              'gates': gate, 'newEstimatorFits': 0, 'integratedReplayInvocations': 0,
              'providerRequests': 0, 'restrictedPartitionsOpened': 0,
              'safety': pre['safety']}
    (OUT/'CHECKPOINT_READINESS.json').write_bytes(encoded(result))
    print(json.dumps({'all': all_agg, 'primary': primary_agg, 'gate': gate,
                      'traceSha256': sha(zipped)}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--r45', required=True, type=Path)
    parser.add_argument('--replay', required=True, type=Path)
    parser.add_argument('--audit', required=True, type=Path)
    run(parser.parse_args())
