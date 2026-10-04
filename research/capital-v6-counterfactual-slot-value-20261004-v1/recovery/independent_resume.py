"""Supply only the missing report-writer Path symbol to the unchanged engine."""
from pathlib import Path
import importlib.util

path=Path(__file__).with_name('independent_audit.py')
spec=importlib.util.spec_from_file_location('v6_frozen_independent_engine',path)
audit=importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
audit.Path=Path
audit.main()
