"""Single selected LONG EXIT Development Final research interface; no execution."""
import importlib.util
from pathlib import Path

_spec=importlib.util.spec_from_file_location('long_exit_continuation',Path(__file__).with_name('phase57_long_exit_continuation_v1.py'))
_runtime=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_runtime)
POLICY_ID='LONG_EXIT_BAR5_TWO_LOWER_CLOSES_V1'
STATUS='LONG_EXIT_DEVELOPMENT_FINAL_SELECTED_NOT_VALIDATED'
MODE='BAR5_TWO_LOWER_CLOSES'

def new_position(remaining_regular_slots,*,direction='LONG',cash_equity_only=True):
 if cash_equity_only is not True:raise ValueError('CASH_EQUITY_ONLY')
 if remaining_regular_slots==0:raise ValueError('NO_REMAINING_REGULAR_BAR')
 return _runtime.new_state(MODE,remaining_regular_slots,direction)

def on_completed_bar(state,bar):
 if state.get('mode')!=MODE:raise ValueError('FINAL_POLICY_MISMATCH')
 return _runtime.on_completed_bar(state,bar)
