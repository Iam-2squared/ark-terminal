"""Combined execution boundaries, bootstrap wiring, no live approval."""
from copy import deepcopy
from pathlib import Path
import json
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import no11_received_session_bootstrap as bootstrap
import no11_original_exit_shadow as exit_code
import no11_shadow_portfolio as ledger
import no11_h235_asof_forward_shadow as h
import test_no11_frozen_p1_execution_bundle as f
import test_no11_frozen_p1_h235_asof as model_fixture


class BundleBoundaries(unittest.TestCase):
    def test_first_sharp_after_fractional_fill_is_not_delayed_an_extra_bar(self):
        rows = [f.trace_row(33, context=-1, primary='DROP'),
                f.trace_row(34, context=-1, primary='SHARP_DROP')]
        result = exit_code.decide_received_exit(session=f.DAY,
            entry_at=f.at(573, 15), trace=rows, evaluated_at=f.at(574, 12))
        self.assertEqual(result['intent']['minute'], 574)
        self.assertEqual(result['intent']['reason'], 'SHARP_DROP_FIRST_OBSERVED')

    def test_bootstrap_forwards_optional_shadow_config_to_existing_service(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            file = root / 'placeholder.json'
            file.write_text('{}')
            config = {'schemaId': bootstrap.CONFIG, 'sessionDate': f.DAY,
                      'dailyRun': str(root), 'datedMaster': str(file),
                      'previousContext': str(file), 'runtimeRoot': str(root),
                      'h235ModelRoot': str(root), 'shadowAccountConfig': str(file),
                      'privateRoot': str(root), 'productionReady': False, 'orderTransmission': False}
            validated = bootstrap.validate_config(config)
            prepared = {'files': {k: str(file) for k in ('plan', 'mask', 'master', 'previous')}}
            argv = bootstrap.service_args(validated, prepared, root)
            self.assertEqual(argv[argv.index('--shadow-account-config') + 1], str(file))
            self.assertIn('--h235-model-root', argv)
            del config['h235ModelRoot']
            with self.assertRaisesRegex(ValueError, 'H235_REQUIRED_FOR_SHADOW_PORTFOLIO'):
                bootstrap.validate_config(config)

    def test_native_capital_cannot_reserve_more_than_three_symbols(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = model_fixture.synthetic_models(root, None)
            scorer = h.FrozenH235AsOf(root, f.DAY, manifest=manifest)
            row = scorer.score(model_fixture.valid_input())
            records = []
            for index, symbol in enumerate(('7203.T', '6501.T', '6758.T', '8306.T')):
                r = deepcopy(row)
                r.update(candidateId=h.digest([index]), symbol=symbol)
                records.append(r)
            records.sort(key=scorer.stair.candidate_order)
            batch = {'schemaId': 'ARK_NO11_H235_ASOF_PRIVATE_RANK_BATCH_V1',
                     'policy': scorer.policy, 'results': records, 'capitalV5Executed': False,
                     'brokerOrders': 0, 'productionReady': False, 'orderTransmission': False}
            portfolio = ledger.ShadowPortfolio(root / 'ledger.sqlite', f.config(root), f.arrival())
            try:
                result = portfolio.fund(batch, f.at(571, 12))
                self.assertGreater(result['buyIntents'], 0)
                self.assertLessEqual(result['buyIntents'], 3)
                state = portfolio.state()
                self.assertEqual(state['positions'], {})
                self.assertTrue(all(o['quantity'] % 100 == 0 for o in state['orders'].values()))
                self.assertEqual(state['cash'], '1000000')
                self.assertFalse(state['orderTransmission'])
            finally:
                portfolio.close()


if __name__ == '__main__':
    unittest.main()
