#!/usr/bin/env python3
"""Counterfactual replay of the preserved prior builder, with allowlisted inputs.

All outputs stay in memory. The original budget expressions are unchanged.
No candidate JSON is decoded: only its raw SHA is checked by the prior builder.
"""
import ast
import hashlib
import json
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / 'docs/evidence/phase57-long-only-global-budget-integrity-review'
PRIOR = ROOT / 'docs/evidence/phase57-long-only-e2e-data-responsibility'
SOURCE_SHA = '1f287bf621d7842030134f330082f38c0ee8231866302a41f4789e69e4e01702'


def replay():
    raw = (REVIEW / 'prior_builder_source.txt').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == SOURCE_SHA
    tree = ast.parse(raw.decode())
    fixture = json.loads((REVIEW / 'outcome-free-input.json').read_text())
    source_records = json.loads((PRIOR / 'source-recovery.json').read_text())['contracts']
    accesses, outputs = [], {}

    class GuardedIdentity(dict):
        def __getitem__(self, key):
            accesses.append('trainingIdentity.' + key)
            if key not in {'sessionCount', 'sessionListSha256', 'trainingSessions'}:
                raise AssertionError('FORBIDDEN_CANDIDATE_FIELD_ACCESS')
            return super().__getitem__(key)

    def safe_read(path):
        if path == 'predict/research/phase57-msh-entry-long-v1-validation-candidate-v1.json':
            return {'trainingIdentity': GuardedIdentity(fixture['developmentIdentity'])}
        allowed = {
            'docs/evidence/phase57-long-only-global-data-budget/budget-attempt.json',
            'docs/evidence/phase57-long-only-fresh-allocation-audit/audit.json',
            'docs/evidence/phase57-long-only-fresh-allocation-audit/source-metadata-extracts.json',
            'predict/research/phase57-long-only-frozen-selector-v1.json',
        }
        if path not in allowed:
            raise AssertionError('UNAPPROVED_METADATA_PATH')
        return json.loads((ROOT / path).read_text())

    def safe_save(path, data):
        if not path.startswith('docs/evidence/phase57-long-only-e2e-data-responsibility/'):
            raise AssertionError('UNAPPROVED_OUTPUT')
        outputs[path] = (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode()

    def exact_sha(path):
        return hashlib.sha256(outputs[path] if path in outputs else (ROOT / path).read_bytes()).hexdigest()

    def archived_source_record(ref, path, role):
        # Metadata already pinned in the previous report; no git/network dependency
        # during offline replay or shallow-checkout CI.
        matches = [r for r in source_records if r['path'] == path and r.get('role') == role]
        if len(matches) != 1:
            raise AssertionError('PINNED_SOURCE_METADATA_NOT_UNIQUE')
        return matches[0]

    # Replace I/O adapters only; no numeric, responsibility, reuse or formula node.
    tree.body = [n for n in tree.body if not (isinstance(n, ast.FunctionDef) and n.name in {'read', 'save', 'sha', 'source_record'})]

    class PathsOnly(ast.NodeTransformer):
        def visit_Constant(self, node):
            if node.value == '/workspace/scratch/4972db587728/ark-terminal-phase57-ordinal':
                return ast.copy_location(ast.Constant(str(ROOT)), node)
            if node.value == '/tmp/phase57-responsibility-catalog.json':
                return ast.copy_location(ast.Constant(str(REVIEW / 'prior_contract_path_catalog.json')), node)
            return node

    tree = PathsOnly().visit(tree)
    with tempfile.TemporaryDirectory(prefix='phase57-budget-replay-') as temporary:
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'OUT' for t in node.targets):
                node.value = ast.Call(func=ast.Name(id='Path', ctx=ast.Load()), args=[ast.Constant(temporary)], keywords=[])
        ast.fix_missing_locations(tree)
        namespace = {'read': safe_read, 'save': safe_save, 'sha': exact_sha,
                     'source_record': archived_source_record, 'print': lambda *args, **kwargs: None}
        exec(compile(tree, str(REVIEW / 'prior_builder_source.txt'), 'exec'), namespace)
    key = 'docs/evidence/phase57-long-only-e2e-data-responsibility/responsibility-budget-contract.json'
    expected = (PRIOR / 'responsibility-budget-contract.json').read_bytes()
    if outputs[key] != expected:
        raise AssertionError('OUTCOME_FREE_REPLAY_CHANGED_PRIOR_CONTRACT')
    return {'sourceSha256': SOURCE_SHA, 'candidateOutcomeFieldsSupplied': 0,
            'candidateFieldAccesses': accesses, 'priorContractSha256': hashlib.sha256(expected).hexdigest(),
            'replayedContractSha256': hashlib.sha256(outputs[key]).hexdigest(),
            'priorContractByteIdentical': True, 'budgetExpressionsModified': 0,
            'researchExecution': False, 'outputWritesToRepository': 0,
            'scope': 'Deterministic computational counterfactual; not a claim of a separate human reviewer or proof of unobservable cognition.'}


if __name__ == '__main__':
    print(json.dumps(replay(), indent=2))
