"""Unchanged v5 execution authority; no model, teacher or policy evaluation."""
from control import ROOT
import importlib.util
spec=importlib.util.spec_from_file_location('v11r1_frozen_v5_execution',ROOT/'research/capital-v5-max3-slot-intelligence-20261004-v1/execution.py')
FROZEN=importlib.util.module_from_spec(spec);spec.loader.exec_module(FROZEN)
BUY=FROZEN.BUY
