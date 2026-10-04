# EOD1520 audit source

Research-only downstream overlay; no broker/RSS/Excel/network execution path.
Frozen source is read-only. Historical reference fill and live full-order receipt are separate.
Policy was precommitted before coverage at d4322d6c27eb6ae29c3e21fa4d71adfd809a5eb1.
Current status: CAPITAL_C2_EOD1520_SOURCE_BLOCKED. No allocator/performance run.

Run against private original components in fresh output directories:

```bash
python audit_eod1520_primary.py --inputs INPUTS_PRIMARY --output RESULTS_NEW --precommit EOD1520_PRECOMMIT.json --basis-head PRECOMMIT_HEAD
python audit_eod1520_independent.py --inputs INPUTS_ORIGINAL_V2_V3 --primary-inputs INPUTS_PRIMARY --primary-rows RESULTS_NEW/EOD1520_ADAPTER_ROWS.jsonl.gz --output INDEPENDENT_NEW
python audit_eod1520_canaries.py --inputs INPUTS_PRIMARY --rows RESULTS_NEW/EOD1520_ADAPTER_ROWS.jsonl.gz --output CANARIES_NEW.json
python render_eod1520_charts.py --coverage RESULTS_NEW/SOURCE_COVERAGE.json --output CHARTS_NEW
```

Independent uses Fraction and original manifests, never imports Primary.
Do not publish row inputs/output or private18-target request plan.
Late Entry >=15:20 is a precommitted contract gap, never silently excluded.
Source absence is UNKNOWN unless positive no-trade/halt/completeness evidence exists.
Cash reference assumes completed-bar minute+1m; no runtime certificate/backdate.
