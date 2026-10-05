"""Reuse parent day engine byte-for-byte; substitute only allocation weights."""
from control import *
import importlib.util
SPEC=importlib.util.spec_from_file_location('v10_frozen_v9_portfolio_engine',ROOT/'research/capital-v9-quality-aware-max3-integration-20261005-v1/replay.py')
ENGINE=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(ENGINE)
def run(arm,stream,books,tables):
    assert arm in ARMS
    rr=[dict(r,sizing_weight=1 if arm==ARMS[0] else r['consensus_weight']) for r in stream]
    return ENGINE.run(arm,rr,books,tables)
