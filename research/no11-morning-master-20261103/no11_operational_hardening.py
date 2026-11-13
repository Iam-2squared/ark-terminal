"""Reviewed source transformations; apply only to a staging checkout, not LIVE.

Original numerical models, native admission/expiry, actions, account data and
frozen artifacts remain unchanged. Unknown source spans are rejected. CLI is
explicit staging only; it is not a PC installer or a restart command.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
from pathlib import Path

from no11_oneclick_display_transform import replace_regions

OLD_FUND = '''    def fund(self, batch, quotes, at):
        need(type(batch) is dict and type(batch.get('results')) is list, 'H235_BATCH')
        consumed = self.book.source_checkpoint('capital.consumed') or {}
        changed, fresh = dict(consumed), []
        for row in batch['results']:
            key, sha = row.get('candidateId'), h.digest(row)
            need(type(key) is str and bool(key), 'CANDIDATE_ID')
            need(key not in consumed or consumed[key] == sha, 'CANDIDATE_CHANGED')
            if key not in consumed:
                decision = h.timestamp(row.get('decisionAtJst'), self.session)
                now = h.timestamp(at, self.session)
                need(decision <= now, 'CANDIDATE_FROM_FUTURE')
                if h.minute(decision) == h.minute(now) and (now - decision).total_seconds() <= 90:
                    fresh.append(row)
                changed[key] = sha
        if not fresh:
            if changed != consumed:
                self.book.checkpoint_source('capital.consumed', changed, at)
            return None
        # Validate the complete fresh batch before consuming a candidate or
        # reserving funds. Already evaluated rows may never return as new BUY.
        result = decisions.calculate_capital(dict(batch, results=fresh), self._capital_input(quotes, at), self.arrival)
        self.book.checkpoint_source('capital.consumed', changed, at)
        self.last_decision = result
        self.submit_intents(result['intents'], self.clock())
        return result
'''
NEW_FUND = '''    def fund(self, batch, quotes, at):
        # ARK_NO11_CAPITAL_DURABLE_DECISION_AUDIT_V1
        from no11_capital_decision_audit import fund_with_audit
        return fund_with_audit(self, batch, quotes, at,
                               time_api=h, decisions=decisions, require=need)
'''
OLD_NODE_FAILURE = '''    if result.returncode != 0:
        message = result.stderr.strip()
        if message == 'NO11_PIPELINE_CAPTURE_WRITE_IN_PROGRESS':
            return None
        raise ValueError(message if re.fullmatch(r'NO11_[A-Z0-9_]+', message)
                         else 'NO11_SERVICE_NODE_TICK_FAILED')
'''
NEW_NODE_FAILURE = '''    if result.returncode != 0:
        message = result.stderr.strip()
        if message == 'NO11_PIPELINE_CAPTURE_WRITE_IN_PROGRESS':
            return None
        # ARK_NO11_NODE_TICK_FAILURE_EVIDENCE_V1: no raw stderr, paths, or account data.
        # Preserve the native fail-closed result and all retry/dispatch boundaries.
        stderr_bytes = result.stderr.encode('utf-8', errors='replace')
        stdout_bytes = result.stdout.encode('utf-8', errors='replace')
        valid_code = bool(re.fullmatch(r'NO11_[A-Z0-9_]+', message))
        safe_lines = sorted(set(line for line in result.stderr.splitlines()
                                if re.fullmatch(r'NO11_[A-Z0-9_]+', line)))[:8]
        evidence_file = Path(root) / ('node-tick-failure-' + os.urandom(16).hex() + '.json')
        need(not evidence_file.exists(), 'NODE_FAILURE_EVIDENCE_COLLISION')
        atomic_private(evidence_file, {
            'schemaId': 'ARK_NO11_NODE_TICK_FAILURE_EVIDENCE_V1',
            'observedAtJst': now_jst(), 'returnCode': result.returncode,
            'stderrBytes': len(stderr_bytes), 'stderrSha256': hashlib.sha256(stderr_bytes).hexdigest(),
            'stdoutBytes': len(stdout_bytes), 'stdoutSha256': hashlib.sha256(stdout_bytes).hexdigest(),
            'stderrLineCount': len(result.stderr.splitlines()),
            'stderrShape': ('EMPTY' if not message else 'SINGLE_SAFE_CODE' if valid_code else 'OTHER'),
            'safeCodeLines': safe_lines, 'rawErrorStored': False,
            'orderTransmission': False, 'brokerStateChanged': False
        })
        raise ValueError(message if valid_code else 'NO11_SERVICE_NODE_TICK_FAILED')
'''


# For unknown Node exceptions the old native process printed only a generic
# NO11_PIPELINE_PRIVATE_SOURCE_OR_RUNTIME_FAILURE. Preserve a finite stage
# code without ever logging an account path, original thrown message or stack.
NODE_STAGE_EDITS = (
    ("export function runPipelineTick(args){",
     "export function runPipelineTick(args){\n  let failureStage='ARGUMENTS';\n  try{"),
    ("  const req=readPrivate(args[1],1_000_000);",
     "  failureStage='REQUEST_LOAD';\n  const req=readPrivate(args[1],1_000_000);"),
    ("  const chart=readPrivate(req.plan,250_000);",
     "  failureStage='SOURCE_READ';\n  const chart=readPrivate(req.plan,250_000);"),
    ("  const folder=safePath(req.captureFolder,true),incoming=[];",
     "  failureStage='CAPTURE_SCAN';\n  const folder=safePath(req.captureFolder,true),incoming=[];"),
    ("  const result=advanceReceivedPipeline({sessionDate:req.sessionDate,chartPlan:chart.chartPlan,",
     "  failureStage='PIPELINE_ADVANCE';\n  const result=advanceReceivedPipeline({sessionDate:req.sessionDate,chartPlan:chart.chartPlan,"),
    ("  const outDir=safePath(req.privateRoot,true);",
     "  failureStage='OUTPUT_PERSIST';\n  const outDir=safePath(req.privateRoot,true);"),
    ("  return result;\n}\nif(process.argv[1]",
     """  return result;
  }catch(error){
    // ARK_NO11_NODE_FAILURE_STAGE_V1: retain exact approved existing NO11 codes.
    if(error instanceof Error&&/^NO11_[A-Z0-9_]+$/.test(error.message))throw error;
    throw new Error('NO11_PIPELINE_PRIVATE_'+failureStage+'_FAILURE');
  }
}
if(process.argv[1]"""),
)


def pipeline_node_stage(raw):
    """Fail-closed classification only; no success route, timeout or order change."""
    return transform(raw, NODE_STAGE_EDITS, python=False)


def pipeline_node(raw):
    """Only nonzero Node child failure evidence; no trading or retry changes."""
    return transform(raw, [(OLD_NODE_FAILURE, NEW_NODE_FAILURE)])


OLD_OVERLAY = '''  if($trading -match 'ENTRY HALTED'){
       $disabledTradeOverlay.Text='TRADING PAUSED  /  RECOVERY REVIEW REQUIRED'
   }
   elseif($s.mode -ceq 'AFTER_CLOSE'){
       $disabledTradeOverlay.Text='TRADING CLOSED FOR TODAY'
   }
   elseif($s.reason -ceq 'NEW_ENTRY_WINDOW_CLOSED'){
       $disabledTradeOverlay.Text='NEW ENTRIES CLOSED'
   }
   else{
       $disabledTradeOverlay.Text='TRADING UNAVAILABLE  /  CHECK STATUS'
   }
'''
NEW_OVERLAY = '''  # ARK_NO11_PREOPEN_OVERLAY_PRESENTATION_ONLY_V1
  if($view.phase -ceq 'PREOPEN'){
       $disabledTradeOverlay.Text=[string]$view.trading
   }
   elseif($trading -match 'ENTRY HALTED'){
       $disabledTradeOverlay.Text='TRADING PAUSED  /  RECOVERY REVIEW REQUIRED'
   }
   elseif($s.mode -ceq 'AFTER_CLOSE'){
       $disabledTradeOverlay.Text='TRADING CLOSED FOR TODAY'
   }
   elseif($s.reason -ceq 'NEW_ENTRY_WINDOW_CLOSED'){
       $disabledTradeOverlay.Text='NEW ENTRIES CLOSED'
   }
   else{
       $disabledTradeOverlay.Text='TRADING UNAVAILABLE  /  CHECK STATUS'
   }
'''


def transform(raw, edits, *, python=True):
    bom = b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b''
    text = raw.decode('utf-8-sig')
    new = replace_regions(text, edits)
    if replace_regions(new, [(after, before) for before, after in edits]) != text:
        raise ValueError('NO11_HARDENING_NONREVERSIBLE')
    if python:
        ast.parse(new)
    return bom + new.encode('utf-8')


def service(raw):
    before = "            'capital': self.last_decision, 'exit': self.last_exit, 'drafts': self.drafts,"
    after = "            'capitalAudit': self.book.source_checkpoint('capital.decision.latest'),\n" + before
    return transform(raw, [(OLD_FUND, NEW_FUND), (before, after)])


def display(raw):
    before = "            if result['collector'] == 'CLOSED' or last_time is None or failure.stat().st_mtime_ns >= last_time:\n                result['state'] = 'FAILURE_RECORDED'\n            else:\n                result['previousFailure'] = True"
    after = """            if last_time is None or failure.stat().st_mtime_ns >= last_time:
                result['state'] = 'FAILURE_RECORDED'
            elif result['collector'] == 'CLOSED':
                # A rewritten CLOSED attempt is not proof that this older
                # failure belongs to it. Preserve uncertainty, not success.
                result['state'] = 'FAILURE_SCOPE_UNVERIFIED'
                result['failureAttribution'] = 'UNVERIFIED'
                result['previousFailure'] = True
            else:
                result['previousFailure'] = True"""
    branch = "    elif rs == 'UNVERIFIED' or reserved.get('state') == 'UNVERIFIED':"
    new_branch = "    elif rs == 'FAILURE_SCOPE_UNVERIFIED':\n        trading = 'CLOSED / 停止理由要確認'\n" + branch
    return transform(raw, [(before, after), (branch, new_branch)])


def base_installer(raw):
    before = "def verify(store, record, *, frozen=True):\n    home, launcher, legacy, engine, external = context(store)"
    after = """def verify(store, record, *, frozen=True):
    # Recognize only a fully proven subsequent overlay; no permissive hash bypass.
    if record.get('phase') == 'COMPLETE' and (Path(store) / 'oneclick-display-v2-overlay-compat-install.json').exists():
        from no11_display_install_chain import verify_complete_chain
        return verify_complete_chain(store, record)
    home, launcher, legacy, engine, external = context(store)"""
    return transform(raw, [(before, after)])


def overlay_installer(raw):
    before = '    original_record = journal_io.checkpoint(original_journal)'
    after = before + "\n    from no11_display_install_chain import validate_v2_dependencies\n    validate_v2_dependencies(store)"
    return transform(raw, [(before, after)])


def launcher_preopen(raw):
    """A separately journaled final display delta, not an authorization patch.

    Keep old V2/overlay recipes frozen so existing receipts remain provable.
    This delta belongs in the next consolidated PC installer; never edit an
    installed launcher in place without its own verified migration receipt.
    """
    return transform(raw, [(OLD_OVERLAY, NEW_OVERLAY)], python=False)


ENGINE = 'research/no12-prebuy-causal-runtime-20261011/tools/'
MORNING = 'research/no11-morning-master-20261103/'
TARGETS = {
    ENGINE + 'no11_broker_execution_service.py': service,
    MORNING + 'no11_oneclick_display_v2.py': display,
    MORNING + 'install_no11_oneclick_display_v2.py': base_installer,
    MORNING + 'install_no11_oneclick_display_overlay_compat.py': overlay_installer,
    ENGINE + 'no11_received_pipeline_service.py': pipeline_node,
    ENGINE + 'no11_received_pipeline_tick.mjs': pipeline_node_stage,
}


def stage(root):
    root = Path(root).resolve()
    if not (root / '.git').exists():
        raise ValueError('NO11_HARDENING_STAGING_CHECKOUT_REQUIRED')
    prepared = [(root / name, change((root / name).read_bytes())) for name, change in TARGETS.items()]
    for path, data in prepared:
        path.write_bytes(data)
        print('STAGED_SOURCE|' + str(path.relative_to(root)) + '=' + hashlib.sha256(data).hexdigest())
    print('PC_INSTALL_PERFORMED=False')
    print('TRADE_STARTED=False')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--staging-checkout', type=Path, required=True)
    args = parser.parse_args()
    stage(args.staging_checkout)
