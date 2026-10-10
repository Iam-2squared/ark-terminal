import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import phase57_exit_finite_r36 as frozen
from scripts.phase57_exit_gen2_runtime_r41 import load_protocol, PROTOCOL_SHA256
from scripts.phase57_exit_gen2_scoring_r41 import select_from_gates, score_audited_artifact


def results():
    return [{'candidateId': c['candidateId'], 'gate': {'pass': False,
        'capabilityMargins': {'winner': 0., 'retention': 0., 'loss': 0.}}}
        for c in load_protocol()['candidates']]


def synthetic_runner_artifact(root):
    """Use the real runner's flat ledger layout, with no market observations."""
    hashes = {}
    for run in ('run-a', 'run-b'):
        for cid in [c['candidateId'] for c in load_protocol()['candidates']] + ['HOLD_TO_TERMINAL_DIAGNOSTIC']:
            path = root / run / (cid + '.jsonl.gz')
            frozen.write_jsonl_gz(path, [
                {'candidateId': cid, 'entryArm': arm, 'opportunity': 'synthetic|only',
                 'syntheticToken': 'same-frozen-input-for-both-runs'}
                for arm in load_protocol()['entryArms']])
            hashes[str(path.relative_to(root))] = frozen.sha(path)
    return {'status': 'GEN2_ARTIFACT_AUDIT_PASS', 'protocolSha256': PROTOCOL_SHA256,
            'inputLedgerHashes': hashes}


class SelectionTests(unittest.TestCase):
    def test_cannot_select_before_every_policy_is_evaluated(self):
        with self.assertRaisesRegex(ValueError, 'ALL_16_REQUIRED'):
            select_from_gates(results()[:-1])

    def test_no_pass_remains_negative_result(self):
        self.assertEqual(select_from_gates(results())['outcome'], 'NO_SELECTION_STOP')

    def test_unique_pass_selected_only_after_all_gates(self):
        r = results(); r[5]['gate']['pass'] = True
        self.assertEqual(select_from_gates(r)['selectedCandidateId'], r[5]['candidateId'])

    def test_different_margins_with_equal_best_ranks_do_not_use_tertiary_tie_break(self):
        r = results()
        r[0]['gate'] = {'pass': True, 'capabilityMargins': {'winner': 2., 'retention': 1., 'loss': 1.}}
        r[1]['gate'] = {'pass': True, 'capabilityMargins': {'winner': 1., 'retention': 2., 'loss': 1.}}
        a = select_from_gates(r); b = select_from_gates(list(reversed(r)))
        self.assertEqual(a, b)
        self.assertEqual(a['reason'], 'BEST_WORST_RANK_AND_RANK_SUM_TIE')

    def test_passing_nonfinite_margin_fails_closed(self):
        r = results(); r[0]['gate']['pass'] = True
        r[0]['gate']['capabilityMargins']['winner'] = float('nan')
        with self.assertRaisesRegex(ValueError, 'NONFINITE_PASS_MARGIN'): select_from_gates(r)

    def test_scorecard_requires_post_run_artifact_audit_before_reading_any_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / 'out'
            with self.assertRaisesRegex(ValueError, 'INDEPENDENT_AUDIT_REQUIRED'):
                score_audited_artifact(Path(d), {}, None, out)
            self.assertFalse(out.exists())

    def test_runner_layout_all_ledgers_reach_score_and_gate_with_identical_ab_outputs(self):
        protocol = load_protocol()
        configs = {c['candidateId']: c for c in protocol['candidates']}
        seen_cards, seen_gates = [], []
        data = object()

        def score(rows, actual_data):
            self.assertIs(actual_data, data)
            self.assertEqual({r['entryArm'] for r in rows}, set(protocol['entryArms']))
            cid = rows[0]['candidateId']
            self.assertTrue(all(r['candidateId'] == cid for r in rows))
            seen_cards.append(cid)
            return {'syntheticScorecard': True, 'candidateId': cid, 'N': len(rows)}

        def gate(rows, neutral, config):
            cid = rows[0]['candidateId']
            self.assertEqual(config, configs[cid])
            self.assertEqual(len(neutral), len(protocol['entryArms']))
            self.assertTrue(all(r['candidateId'] == 'HOLD_TO_TERMINAL_DIAGNOSTIC' for r in neutral))
            seen_gates.append(cid)
            return {'pass': False, 'capabilityMargins': {'winner': 0., 'retention': 0., 'loss': 0.}}

        with tempfile.TemporaryDirectory() as d:
            root, out = Path(d) / 'artifact', Path(d) / 'score'
            audit = synthetic_runner_artifact(root)
            self.assertEqual(len(audit['inputLedgerHashes']), 34)
            with patch.object(frozen, 'full_scorecard', side_effect=score), \
                 patch.object(frozen, 'gate_candidate', side_effect=gate):
                receipt = score_audited_artifact(root, audit, data, out)
            expected = [c['candidateId'] for c in protocol['candidates']] * 2
            self.assertEqual(seen_cards, expected)
            self.assertEqual(seen_gates, expected)
            self.assertEqual(receipt['candidateCount'], 16)
            self.assertEqual(receipt['selection']['outcome'], 'NO_SELECTION_STOP')
            self.assertEqual(receipt['modelFitsPerformed'], 0)
            self.assertEqual(receipt['policyReplaysPerformed'], 0)
            self.assertTrue(receipt['scorecardRunABByteIdentical'])
            self.assertEqual(len(receipt['scoreHashes']), 17)
            self.assertEqual(frozen.tree_hashes(out / 'run-a'), frozen.tree_hashes(out / 'run-b'))

    def test_flat_runner_ledger_changed_after_audit_blocks_before_scoring(self):
        with tempfile.TemporaryDirectory() as d:
            root, out = Path(d) / 'artifact', Path(d) / 'score'
            audit = synthetic_runner_artifact(root)
            changed = root / 'run-b' / 'HOLD_TO_TERMINAL_DIAGNOSTIC.jsonl.gz'
            changed.write_bytes(changed.read_bytes() + b'tampered')
            with patch.object(frozen, 'full_scorecard') as score, \
                 patch.object(frozen, 'gate_candidate') as gate:
                with self.assertRaisesRegex(ValueError, 'AUDITED_LEDGER_IDENTITY'):
                    score_audited_artifact(root, audit, None, out)
                score.assert_not_called()
                gate.assert_not_called()
            self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
