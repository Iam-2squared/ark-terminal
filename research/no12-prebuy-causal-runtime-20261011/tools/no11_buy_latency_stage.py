"""Source-pinned offline staging for BUY latency; never writes installed sources.
Original source pins used by existing ownership and other transforms stay intact.
Do not deploy this independently of the ownership and evidence patches.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EDITS = json.loads("{\"no11_broker_execution_service.py\":{\"blob\":\"9fe2be9835c06605f9c15177eecc49bdf6a931f3\",\"replacements\":[[\"                if h.minute(decision) == h.minute(now) and (now - decision).total_seconds() <= 90:\",\"                if decisions.candidate_current_for_funding(row, at, self.session):\"],[\"    def _command(self, intent, at, *, kind='ORDER', assigned=()):\",\"    def _command(self, intent, at, *, kind='ORDER', assigned=(), validate_config=False):\"],[\"        return self.bridge({'action': 'compile', 'input': original})\",\"        if validate_config:\\n            if self.config['transport']['mode'] == 'LIVE':\\n                need(self.source is not None and self.source['excelSession']['processId'] == self.config['transport']['expectedExcelPid'],\\n                     'EXCEL_PROCESS_CHANGED')\\n            return self.bridge({'action': 'compile-and-validate-config', 'input': original,\\n                                'config': self.config['transport'], 'now': at})\\n        return self.bridge({'action': 'compile', 'input': original})\"],[\"            command = self._command(intent, at, assigned=assigned)\\n            self._validate_physical_config(command, at)\",\"            # Same two pure checks, one Node startup on the native bridge.\\n            # Custom/offline injected bridges keep their established interface.\\n            if self.bridge is node_bridge and intent['side'] == 'BUY':\\n                command = self._command(intent, at, assigned=assigned, validate_config=True)\\n            else:\\n                command = self._command(intent, at, assigned=assigned)\\n                self._validate_physical_config(command, at)\"]]},\"no11_broker_decision_bridge.py\":{\"blob\":\"31c5d13da94d2c894f21bd9fe9775d50e4f49044\",\"replacements\":[[\"def calculate_capital(batch, account, arrival):\\n    \\\"\\\"\\\"Run the original gate and allocator on a bounded, current account view.\\\"\\\"\\\"\\n    need(type(account) is dict and account.get('schemaId') == 'ARK_NO11_BROKER_CAPITAL_INPUT_V1', 'ACCOUNT')\\n    session, at = account['sessionDate'], account['decisionAtJst']\\n    instant(at, session)\\n    # No real account values enter a SYNTHETIC scenario. Reuse its exact source\\n    # and causal checks as a zero-cash validation pass, with no funding call.\\n    validation = {'schemaId': hcap.SCENARIO, 'evidenceMode': 'SYNTHETIC_OFFLINE_ONLY',\\n        'sessionDate': session, 'decisionAtJst': at,\",\"def candidate_current_for_funding(row, at, session):\\n    \\\"\\\"\\\"Keep existing 90s freshness, not wall-clock minute equality.\\n\\n    A decision cannot travel across a market recess, session, cutoff, or\\n    backwards in time. This is pre-BUY admission, not an order permit.\\n    \\\"\\\"\\\"\\n    decision = h.timestamp(row['decisionAtJst'], session)\\n    current = h.timestamp(at, session)\\n    elapsed = instant(at, session) - instant(row['decisionAtJst'], session)\\n    return (0 <= elapsed <= 90_000_000_000\\n            and any(lo <= h.minute(decision) <= h.minute(current) < hi\\n                    for lo, hi in ((540, 690), (750, 920))))\\n\\n\\ndef capital_strategy_time(batch, at, session):\\n    \\\"\\\"\\\"Preserve the original decision minute for the frozen slot policy.\\n\\n    Never rewrite source receipts or the actual account/intent clock.\\n    The existing R0 same-minute validator still rejects mixed-minute batches.\\n    \\\"\\\"\\\"\\n    rows = batch['results']\\n    if not rows:\\n        return at\\n    need(all(candidate_current_for_funding(row, at, session) for row in rows),\\n         'R0_CANDIDATE_NOT_CURRENT')\\n    return max((row['decisionAtJst'] for row in rows),\\n               key=lambda value: instant(value, session))\\n\\n\\ndef calculate_capital(batch, account, arrival):\\n    \\\"\\\"\\\"Run the original gate and allocator on a bounded, current account view.\\\"\\\"\\\"\\n    need(type(account) is dict and account.get('schemaId') == 'ARK_NO11_BROKER_CAPITAL_INPUT_V1', 'ACCOUNT')\\n    session, at = account['sessionDate'], account['decisionAtJst']\\n    instant(at, session)\\n    strategy_at = capital_strategy_time(batch, at, session)\\n    # No real account values enter a SYNTHETIC scenario. Reuse its exact source\\n    # and causal checks as a zero-cash validation pass, with no funding call.\\n    validation = {'schemaId': hcap.SCENARIO, 'evidenceMode': 'SYNTHETIC_OFFLINE_ONLY',\\n        'sessionDate': session, 'decisionAtJst': strategy_at,\"]]},\"no11_broker_bridge.mjs\":{\"blob\":\"e5b2289f95389dd763589395f29e2cbfbeb4408b\",\"replacements\":[[\" if(request.action==='compile')return compileTransportCommand(request.input);\",\" if(request.action==='compile')return compileTransportCommand(request.input);\\n if(request.action==='compile-and-validate-config'){\\n  const command=compileTransportCommand(request.input);\\n  validateTransportConfiguration(request.config,command,request.now);\\n  return command;\\n }\"]]}}")

def blob(source):
    data = source.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()

def staged_source(name, source=None):
    rule = EDITS[name]
    if source is None:
        source = (HERE / name).read_text(encoding="utf-8")
    source = source.replace("\r\n", "\n")
    if blob(source) != rule["blob"]:
        raise ValueError("NO11_BUY_LATENCY_ORIGINAL_PIN_MISMATCH: " + name)
    for old, new in rule["replacements"]:
        if source.count(old) != 1:
            raise ValueError("NO11_BUY_LATENCY_ANCHOR_MISMATCH: " + name)
        source = source.replace(old, new)
    if name.endswith(".py"):
        ast.parse(source)
    return source

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.output_dir
    if not out.is_absolute() or not out.parent.is_dir() or out.exists() or any(p.is_symlink() for p in out.parents):
        raise ValueError("NO11_BUY_LATENCY_NEW_ISOLATED_DIRECTORY_REQUIRED")
    results = {name: staged_source(name) for name in EDITS}
    out.mkdir()
    for name, source in results.items():
        with (out / name).open("xb") as f:
            f.write(source.encode("utf-8"))
        print(name, blob(source))
    print("ORDER_TRANSMISSION=False")

if __name__ == "__main__":
    main()
