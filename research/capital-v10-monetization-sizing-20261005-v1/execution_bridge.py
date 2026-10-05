"""Frozen execution adapter, not sizing/selection or evaluation."""
from control import ROOT
import importlib.util
SPEC=importlib.util.spec_from_file_location('v10_frozen_v5_execution',ROOT/'research/capital-v5-max3-slot-intelligence-20261004-v1/execution.py')
FROZEN=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(FROZEN)
BUY=FROZEN.BUY
