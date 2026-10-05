"""Hash-frozen v11 M1/M2 implementation, instantiated in this new cycle."""
from control import ROOT,ARMS
import importlib.util
spec=importlib.util.spec_from_file_location('v11r1_frozen_v11_caps',ROOT/'research/capital-v11-realized-monetization-signal-20261005-v1/runtime.py')
FROZEN=importlib.util.module_from_spec(spec);spec.loader.exec_module(FROZEN)
order=FROZEN.order;predicted_release=FROZEN.predicted_release
CAP=FROZEN.CAP;BASE=FROZEN.BASE;percentile=FROZEN.percentile
gate=FROZEN.gate;effective_cap=FROZEN.effective_cap;allocation=FROZEN.allocation
