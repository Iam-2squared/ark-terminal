"""R45 immutable R35 projection plus isolated sampled-utility targets.

Support-only mode never creates a model or a policy replay and does not
regenerate the inherited Pattern187 matrix. Full preparation uses exactly the
same facts/labels plus the hash-pinned canonical closed-prefix Pattern producer.
"""
from __future__ import annotations
import collections
import gzip
from pathlib import Path
import numpy as np
from scripts import phase57_exit_finite_r36 as r36
from scripts import phase57_exit_gen2_data_r41 as r41
from scripts import phase57_exit_gen3_runtime_r45 as runtime
from scripts.phase57_exit_gen3_facts_r45 import FactEncoder, calendar_features, schedule
from scripts.phase57_exit_gen3_labels_r45 import HEADS, REASONS, index_rows, utility_labels


def build_data(core_root: Path, out: Path, *, support_only: bool):
    p = runtime.load_protocol()
    r36.require(not out.exists(), 'R45_APPEND_ONLY_DATA')
    manifest = r41.verify_r35(core_root, p)
    columns = r36.read_json(core_root / 'core-a/columns.json')
    r36.require(columns['numeric'] == p['features']['baseNumeric'] and
                columns['categorical'] == p['features']['categorical'], 'R45_CORE_SCHEMA_DRIFT')
    for path, h in ((r36.RAW_PATHS, r36.RAW_PATHS_SHA256),
                    (r36.PATTERN_OPPORTUNITIES, r36.PATTERN_OPPORTUNITIES_SHA256),
                    (r36.OPPORTUNITY_RECORDS, r36.OPPORTUNITY_RECORDS_SHA256)):
        r36.require(r36.sha(path) == h, 'R45_PINNED_SOURCE:' + str(path))
    days = r36.r25.development_sessions()
    envelopes = r36.read_json(core_root / 'core-a/entry-envelopes.json.gz')
    entry_rows = {}; populations = []
    for arm in p['entryArms']:
        rows = envelopes[arm]
        ids = {r['opportunity'] for r in rows}
        r36.require(len(rows) == len(ids) == 2155, 'R45_POPULATION')
        populations.append(ids)
        for row in rows:
            if row['entryId'] is None:
                continue
            key = arm + '::' + row['entryId']
            r36.require(key not in entry_rows and row['session'] in days, 'R45_ENTRY_IDENTITY')
            entry_rows[key] = {**row, 'entryArm': arm}
    r36.require(populations[0] == populations[1], 'R45_COMMON_POPULATION')
    r36.require(collections.Counter(r['entryArm'] for r in entry_rows.values()) ==
                dict(zip(p['entryArms'], (1963, 1885))), 'R45_FROZEN_FILLS')
    allowed = populations[0]
    raw_all = r36.read_json(r36.RAW_PATHS)
    raw = {oid: raw_all[oid] for oid in sorted(allowed)}; del raw_all
    origins = {r['id']: r['origin'] for r in r36.read_json(r36.PATTERN_OPPORTUNITIES) if r['id'] in allowed}
    records = {r['opportunity']: r for r in r36.read_json(r36.OPPORTUNITY_RECORDS)}
    r36.require(set(raw) == set(origins) == set(records) == allowed, 'R45_RAW_COHORT')
    entry_ids = sorted(entry_rows); entry_code = {e: i for i, e in enumerate(entry_ids)}
    maps = [set() for _ in columns['categorical']]; n = 0
    for day in days:
        for row in r41._core_rows(core_root, day):
            n += 1
            for j, value in enumerate(row['categorical']): maps[j].add(value)
    r36.require(n == 656247, 'R45_CHECKPOINT_COUNT')
    maps = [{s: i for i, s in enumerate(sorted(values))} for values in maps]
    names = columns['numeric'] + p['features']['calendarFields'] + ['facts.' + f for f in p['features']['decisionFactFields']]
    r36.require(len(names) == 106, 'R45_NUMERIC_WIDTH')
    sessions = np.empty(n, np.int16); arms = np.empty(n, np.int8); entries = np.empty(n, np.int32)
    now_values = np.empty(n, np.int16); fresh = np.empty(n, np.bool_)
    cats = np.empty((n, 21), np.int16); nums = np.full((n, 106), np.nan, np.float32)
    patterns = np.full((n, 0 if support_only else 187), np.nan, np.float32)
    targets = np.full((n, 3), np.nan, np.float32); known = np.full((n, 3), -1, np.int16)
    horizons = np.zeros(n, np.int16); reasons = np.zeros((n, 3), np.uint8)
    out.mkdir(parents=True, exist_ok=False)
    cursor = 0; unique_patterns = 0
    with (out / 'row-identities.jsonl.gz').open('xb') as bf, gzip.GzipFile(fileobj=bf, mode='wb', filename='', mtime=0) as ids_out:
        for day_code, day in enumerate(days):
            rows = sorted(r41._core_rows(core_root, day), key=lambda r: (
                p['entryArms'].index(r['identity'][0]), r['identity'][1], r['identity'][2]))
            current = None; encoder = None; raw_index = {}; pattern_cache = {}; seen = set()
            day_schedule = schedule(day)
            for row in rows:
                arm, eid, now = row['identity']; key = arm + '::' + eid
                ident = (arm, eid, now)
                r36.require(ident not in seen, 'R45_DUPLICATE_CHECKPOINT'); seen.add(ident)
                entry = entry_rows[key]
                r36.require(entry['session'] == day and now in r36.execution.decision_endpoints(day, entry['entryMinute']),
                            'R45_CHECKPOINT_ENTRY_JOIN')
                if key != current:
                    current = key; encoder = FactEncoder(day, (arm, eid))
                oid = entry['opportunity']
                if oid not in raw_index: raw_index[oid] = index_rows(raw[oid]['today'])
                index = raw_index[oid]
                # Only the five exact past scheduled bars are transported into facts.
                pos = np.searchsorted(day_schedule, now)
                closed = [index[t] for t in day_schedule[max(0, pos - 5):pos] if t in index]
                fact = encoder.encode(row, closed)
                sessions[cursor] = day_code; arms[cursor] = p['entryArms'].index(arm)
                entries[cursor] = entry_code[key]; now_values[cursor] = now; fresh[cursor] = row['fresh']
                cats[cursor] = [maps[j][v] for j, v in enumerate(row['categorical'])]
                vals = row['numeric'] + calendar_features(day, now) + [fact['values'][k] for k in p['features']['decisionFactFields']]
                nums[cursor] = [float(v) if v is not None else np.nan for v in vals]
                if not support_only:
                    pattern_key = (oid, now)
                    if pattern_key not in pattern_cache:
                        pattern_cache[pattern_key] = r41.pattern_vector(day, now, raw[oid], origins[oid], p['features']['patternNames'])
                        unique_patterns += 1
                    patterns[cursor] = pattern_cache[pattern_key]
                # Future reference reads happen only inside the training-label module.
                label = utility_labels(now, day_schedule, index, float(entry['price']), row['fresh'],
                                       fact['values']['certifiedMfePct'], p['labels'])
                targets[cursor] = [np.nan if label['targets'][h] is None else label['targets'][h] for h in HEADS]
                known[cursor] = [v if v is not None else -1 for v in label['knownAt']]
                horizons[cursor] = label['horizonBars']
                reasons[cursor] = [REASONS.index(v) for v in label['reasonCodes']]
                ids_out.write(r36.canonical({'index': cursor, 'session': day, 'arm': arm, 'entryId': eid, 'now': now}))
                cursor += 1
            print(r36.canonical({'phase': 'SUPPORT_ONLY' if support_only else 'PREPARE', 'session': day,
                                 'rowsCompleted': cursor, 'modelFits': 0}).decode().strip(), flush=True)
    r36.require(cursor == n, 'R45_ASSEMBLY_COUNT')
    available = np.isfinite(targets)
    r36.require(np.array_equal(available, reasons == 0), 'R45_REASON_MASK')
    r36.require(np.all(known[available] > np.broadcast_to(now_values[:, None], known.shape)[available]) and
                np.all(known[available] <= 930), 'R45_LABEL_MATURITY')
    r36.require(np.all(np.isnan(targets[~fresh])) and np.all(np.isnan(targets[now_values == 925])), 'R45_LABEL_FRESHNESS')
    r36.require(not np.any((targets[:, 0] == 1) & (targets[:, 2] == 1)), 'R45_CD_EXCLUSIVITY')
    if not support_only: r36.require(unique_patterns == 345893, 'R45_PATTERN_KEYS')
    with (out / 'training-labels.npz').open('xb') as f:
        np.savez_compressed(f, targets=targets, available=available, knownAt=known,
                            horizonBars=horizons, reasonCode=reasons)
    with (out / 'decision-features.npz').open('xb') as f:
        np.savez_compressed(f, categorical=cats, numeric=nums, pattern=patterns, fresh=fresh)
    r36.write_json(out / 'categorical-representation.json', {'maps': dict(zip(columns['categorical'], maps)),
        'ordinalFeatures': False, 'preprocessingFitted': False})
    counts = {arm: {head: {'available': int(np.sum(available[arms == a, h])),
                          'positive': int(np.sum(targets[arms == a, h] == 1)),
                          'negative': int(np.sum(targets[arms == a, h] == 0))}
                    for h, head in enumerate(HEADS)} for a, arm in enumerate(p['entryArms'])}
    r36.write_json(out / 'data-receipt.json', {'schema': 'phase57-gen3-data-r45-v1', 'rows': n,
        'protocolSha256': runtime.PROTOCOL_SHA256, 'supportOnly': support_only,
        'patternRegenerated': not support_only, 'patternColumns': p['features']['patternNames'],
        'numericColumns': names, 'categoricalColumns': columns['categorical'], 'labelCounts': counts,
        'r35ProjectionSha256': manifest['projectionSha256'], 'labelAvailabilityUsedAsFeature': False,
        'outputHashes': {name: r36.sha(out / name) for name in ('training-labels.npz', 'decision-features.npz',
                        'row-identities.jsonl.gz', 'categorical-representation.json')},
        'modelFits': 0, 'policyReplays': 0, 'performanceInspected': False,
        'providerRequests': 0, 'protectedPartitionsOpened': 0, 'safety': p['safety']})
    data = r36.Data(days, columns['categorical'], names, [] if support_only else p['features']['patternNames'],
                    sessions, arms, entries, now_values, fresh, cats, nums, patterns, targets,
                    entry_ids, entry_rows, raw, records)
    return data


def support_slices(data, p):
    r36.require(data.targets.shape == (len(data.now), 3), 'R45_TARGET_SHAPE')
    r36.require(np.all(np.isnan(data.targets[~data.fresh])) and
                np.all(np.isnan(data.targets[data.now == 925])), 'R45_UNTRAINABLE_ROWS')
    code = {s: i for i, s in enumerate(data.session_names)}; gate = p['supportGate']; slices = []; reports = []
    scored = set()
    for fold in p['split']['folds']:
        train_days, purge, score_days = map(set, (fold['train'], fold['purge'], fold['score']))
        r36.require(not (train_days & (purge | score_days) or purge & score_days or scored & score_days),
                    'R45_FOLD_OVERLAP')
        r36.require(max(train_days) < min(purge) <= max(purge) < min(score_days) and len(purge) == 2, 'R45_TIME_SPLIT')
        scored.update(score_days)
        for a, arm in enumerate(p['entryArms']):
            train_mask = (data.arms == a) & np.isin(data.sessions, [code[s] for s in train_days]) & data.fresh
            score = np.flatnonzero((data.arms == a) & np.isin(data.sessions, [code[s] for s in score_days]) & (data.now != 925))
            r36.require(len(score) > 0, 'R45_EMPTY_SCORE')
            for h, head in enumerate(HEADS):
                train = np.flatnonzero(train_mask & np.isfinite(data.targets[:, h]))
                classes, counts = np.unique(data.targets[train, h], return_counts=True)
                opps = len(np.unique(data.entries[train])); sessions = len(np.unique(data.sessions[train]))
                r36.require(classes.tolist() == [0., 1.], 'R45_TWO_CLASS_SUPPORT')
                r36.require(len(train) >= gate['minimumRowsPerFoldArmHead'] and counts.min() >= gate['minimumClassRows']
                            and opps >= gate['minimumOpportunities'] and sessions >= gate['minimumSessions'], 'R45_SUPPORT_GATE')
                slices.append((fold, arm, h, train, score))
                reports.append({'fold': fold['fold'], 'arm': arm, 'head': head, 'trainRows': len(train),
                    'negative': int(counts[0]), 'positive': int(counts[1]), 'opportunities': opps, 'sessions': sessions,
                    'scoreRows': len(score)})
    r36.require(len(slices) == 24 and len(scored) == 34, 'R45_SUPPORT_COUNT')
    return slices, reports
