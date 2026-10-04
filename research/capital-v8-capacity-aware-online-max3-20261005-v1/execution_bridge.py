"""Immutable frozen v5 execution adapter, not a runtime selection policy."""
from control import ROOT,sha
import importlib.util
PATH=ROOT/'research/capital-v5-max3-slot-intelligence-20261004-v1/execution.py'
SPEC=importlib.util.spec_from_file_location('frozen_v5_execution_contract',PATH)
FROZEN=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(FROZEN)
BUY=FROZEN.BUY
def exit_source(book):
 source=FROZEN.frozen_execution(book)
 return source if source is not None else FROZEN.eod_source(book['market'],book['session'])
def execution_ok(row,book):
 if not book['capture_complete'] or not book.get('entry_actual_source'):return False
 src=exit_source(book)
 return bool(src and not src.get('blocked') and src['release_minute']>row['entry_minute'])
