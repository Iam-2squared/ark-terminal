"""Audit completed research without remeasuring or overwriting pinned evidence.

The historical checkout is essential: older manifests pin the producing workflow
itself. We verify those bytes in their original checkout, and independently reject
changes to existing scientific code, protocols or evidence in the current tree.
No historical manifest or research qualification gate is relaxed.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

SOURCE_HEAD = 'e11f8af571a03c7e73f79a77c3964752fd109a08'
ROOT = Path(__file__).resolve().parents[1]
SCIENTIFIC_ROOTS = ['scripts', 'predict', 'docs/evidence', 'package.json', 'package-lock.json']
STUDIES = {
 'causal': ('phase57-causal-entry-exit-recoverability-v1', ['-m','scripts.phase57_causal_entry_exit','audit','--directory'], ['scripts.test_phase57_causal_entry_exit']),
 'low-high': ('phase57-selector-low-high-anatomy-v1', ['-m','scripts.phase57_selector_low_high_anatomy','audit','--directory'], ['scripts.test_phase57_selector_low_high_anatomy']),
 'dictionary': ('phase57-behavior-dictionary-v1', ['-m','scripts.phase57_behavior_dictionary','audit','--directory'], ['scripts.test_phase57_behavior_dictionary']),
 'economic': ('phase57-selector-economic-alpha-v1', ['scripts/audit_phase57_selector_economic_alpha.py','--measurement'], ['scripts.test_phase57_selector_economic_alpha']),
 'path': ('phase57-selector-full-day-path-anatomy-v1', ['-m','scripts.phase57_selector_path_anatomy','audit','--measurement'], ['scripts.test_phase57_selector_path_anatomy']),
 'pairability': ('phase57-selector-pairability-repair-v2', ['-m','scripts.phase57_selector_pairability_v2','audit','--measurement'], ['scripts.test_phase57_selector_pairability_v2']),
}


def git(root, *args):
 return subprocess.check_output(['git', '-C', str(root), *args])


def tree(root):
 result = {}
 for row in git(root, 'ls-tree', '-rz', 'HEAD', '--', *SCIENTIFIC_ROOTS).split(b'\0'):
  if row:
   meta, name = row.split(b'\t', 1)
   result[name.decode()] = meta.decode()
 return result


def unchanged(current, historical):
 differences = [name for name, old in historical.items() if current.get(name) != old]
 if differences:
  raise ValueError('SAVED_RESEARCH_CHANGED_REUSE_BLOCKED: ' + ', '.join(differences[:12]))
 # Added files are not executed in the historical audit. Existing files must match.
 return len(historical)


def audit_saved(study, history, output):
 history = Path(history).resolve()
 if history == ROOT or git(history, 'rev-parse', 'HEAD').decode().strip() != SOURCE_HEAD:
  raise ValueError('EXACT_HISTORICAL_CHECKOUT_REQUIRED')
 for root in [ROOT, history]:
  subprocess.run(['git', '-C', str(root), 'diff', '--exit-code', 'HEAD', '--', *SCIENTIFIC_ROOTS], check=True)
 count = unchanged(tree(ROOT), tree(history))
 folder, command, tests = STUDIES[study]
 relative = Path('docs/evidence') / folder / 'measurement'
 manifest = relative / ('source-manifest.json' if study in ['path','pairability'] else 'manifest.json')
 current_bytes = (ROOT / manifest).read_bytes()
 if current_bytes != (history / manifest).read_bytes():
  raise ValueError('SAVED_MANIFEST_CHANGED')
 output = Path(output).resolve()
 if output == history or history in output.parents or output == ROOT / relative or ROOT / relative in output.parents:
  raise ValueError('RECEIPT_MUST_NOT_OVERWRITE_HISTORICAL_EVIDENCE')
 output.mkdir(parents=True, exist_ok=False)
 commands = [['-m', 'unittest', '-v', *tests], command + [str(relative)]]
 for name, args in zip(['focused-tests.log', 'saved-audit.log'], commands):
  with (output / name).open('w') as log:
   subprocess.run([sys.executable, 'scripts/offline/kernel_exec.py', sys.executable, *args], cwd=history, stdout=log, stderr=subprocess.STDOUT, check=True)
 for root in [ROOT, history]:
  subprocess.run(['git', '-C', str(root), 'diff', '--exit-code', 'HEAD', '--', *SCIENTIFIC_ROOTS], check=True)
 receipt = {'status':'SAVED_EVIDENCE_REUSE_AUDIT_PASS', 'study':study,
  'currentHead':git(ROOT,'rev-parse','HEAD').decode().strip(), 'historicalHead':SOURCE_HEAD,
  'scientificFilesUnchanged':count, 'historicalWorkflowPinsVerifiedInOriginalCheckout':True,
  'measurementManifestSHA256':hashlib.sha256(current_bytes).hexdigest(),
  'measurementDirectory':str(relative), 'researchVerdictsUnchanged':True,
  'fitCalls':0, 'remeasurementCalls':0, 'rawCacheRestores':0, 'providerRequests':0,
  'historicalEvidenceWrites':0, 'promotionAllowed':False,
  'logs':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir())}}
 (output/'receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
 print(json.dumps(receipt,sort_keys=True))


if __name__ == '__main__':
 p=argparse.ArgumentParser();p.add_argument('--study',required=True,choices=STUDIES);p.add_argument('--history',required=True);p.add_argument('--output',required=True)
 a=p.parse_args();audit_saved(a.study,a.history,a.output)
