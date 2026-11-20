"""Deterministic two-worker transport for the unchanged canonical Pattern187."""
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
from scripts.phase57_exit_gen2_data_r41 import pattern_vector
from scripts.phase57_exit_gen3_runtime_r45 import require

_CONTEXT = None


def _initialize(day, raw, origins, names):
    global _CONTEXT
    _CONTEXT = (day, raw, origins, names)


def _vector(key):
    day, raw, origins, names = _CONTEXT
    oid, now = key
    values = pattern_vector(day, now, raw[oid], origins[oid], names)
    require(len(values) == 187, 'R45_PARALLEL_PATTERN_WIDTH')
    return key, values


def parallel_patterns(day, keys, raw, origins, names, workers):
    require(workers == 2 and len(names) == 187, 'R45_PATTERN_WORKER_CONTRACT')
    keys = sorted(set(keys))
    required_oids = {oid for oid, _ in keys}
    subset_raw = {oid: raw[oid] for oid in required_oids}
    subset_origins = {oid: origins[oid] for oid in required_oids}
    with ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context('fork'),
            initializer=_initialize, initargs=(day, subset_raw, subset_origins, names)) as pool:
        result = dict(pool.map(_vector, keys, chunksize=128))
    require(list(result) == keys, 'R45_PATTERN_IDENTITY_ORDER')
    return result
