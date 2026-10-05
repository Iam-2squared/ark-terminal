"""Unchanged v9 day engine, with the frozen v11 effective-cap allocator."""
from control import *
import importlib.util
spec=importlib.util.spec_from_file_location('v11r1_frozen_v9_day_engine',ROOT/'research/capital-v9-quality-aware-max3-integration-20261005-v1/replay.py')
ENGINE=importlib.util.module_from_spec(spec);spec.loader.exec_module(ENGINE)
def run(arm,stream,books,tables):
    assert arm in ARMS
    return ENGINE.run(arm,[dict(r,cap_policy=arm) for r in stream],books,tables)
