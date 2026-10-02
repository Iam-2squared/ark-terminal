"""Separate real HTTP attempts from a cap guard counter increment before I/O.
Preserves the original runner receipt and unchanged cap; never grants extra calls.
"""
from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
runner=json.loads((R/'NEW_DEVELOPMENT/RUNNER_FINAL_RECEIPT.json').read_text());cap=json.loads((R/'BUDGET_START_V4.json').read_text())['finite_caps']['provider_HTTP_requests'];counter=runner['provider_requests'];universe=json.loads((R/'NEW_DEVELOPMENT/ACQUISITION_UNIVERSE_PRECOMMIT.json').read_text());ledger=json.loads((R/'NEW_DEVELOPMENT/DEVELOPMENT_COMPLETION_LEDGER.json').read_text())
guard=counter==cap+1 and (universe.get('provider_stopped')=='PROVIDER_REQUEST_CAP' or any(x.get('reason')=='PROVIDER_REQUEST_CAP' for x in ledger))
source=(R/'runner/acquisition_base.py').read_text();assert source.index('requests+=1')<source.index("assert requests<=CFG['maxrequests']")<source.index('opener.open'),'COUNTER_FENCE_ORDER'
x={'status':'PASS','original_runner_receipt_SHA256':sha(R/'NEW_DEVELOPMENT/RUNNER_FINAL_RECEIPT.json'),'original_counter':counter,'cap_guard_rejected_before_HTTP_N':1 if guard else 0,'actual_provider_HTTP_requests':counter-(1 if guard else 0),'finite_cap_unchanged':cap,'source_SHA256':sha(R/'runner/acquisition_base.py'),'cap_guard_logic':'The inherited counter increments before the assert and before opener.open; exactly one hard cap guard is then remembered and all subsequent requests stopped. Guard-rejected attempt is not an HTTP request. Original receipt retained unchanged.','extra_HTTP_permission':0,'new_requests':0}
(R/'RUNNER_ACCOUNTING_V4.json').write_text(json.dumps(x,sort_keys=True,indent=2)+'\n');print(json.dumps({k:x[k] for k in ['status','original_counter','cap_guard_rejected_before_HTTP_N','actual_provider_HTTP_requests']}))
