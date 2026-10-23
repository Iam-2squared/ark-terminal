import unittest
from run_phase57_historical_remeasurement import causal_decisions, preservation

class CausalReplayTests(unittest.TestCase):
    def rows(self):
        return [dict(selectorEventId=str(i),symbolSessionId='s',decisionTimestamp=f'2024-12-02T10:{i*5:02d}:00+09:00',label={'labelable':i>0}) for i in range(3)]
    def test_unlabelable_first_entry_blocks_reentry(self):
        actual=causal_decisions(self.rows(),[2.1,2.3,2.4])
        self.assertEqual([r['state'] for r in actual],['ENTER','SKIP_THIS_DECISION','SKIP_THIS_DECISION'])
    def test_future_labels_do_not_gate_any_decision(self):
        rows=self.rows();before=causal_decisions(rows,[1.9,2,3]);rows[1]['label']={'labelable':False,'ordinalClass':4}
        self.assertEqual(before,causal_decisions(rows,[1.9,2,3]))
    def test_threshold_equality_and_independent_symbol(self):
        rows=self.rows();rows[1]['symbolSessionId']='t'
        self.assertEqual([r['state'] for r in causal_decisions(rows,[2,2,2])],['ENTER','ENTER','SKIP_THIS_DECISION'])
    def test_transfer_is_not_remaining_opportunity(self):
        first={'s':self.rows()[0]};entry={**self.rows()[1],'decisionTimestamp':'2024-12-02T11:00:00+09:00'}
        paths={'0':{'labelable':True,'highReturnPct':5},'1':{'labelable':True,'highReturnPct':0}}
        p=preservation(first,{'s':entry},paths,1)['1']
        self.assertEqual(p['preservationPct'],100);self.assertEqual(p['timelyPreservationPct'],0);self.assertEqual(p['winnerAndRemainingHit'],0)
    def test_score_count_identity(self):
        with self.assertRaises(ValueError):causal_decisions(self.rows(),[2])
class FrozenArtifactTests(unittest.TestCase):
    def test_saved_sources_and_predictions_integrity(self):
        import json,gzip,math
        from run_phase57_historical_remeasurement import inputs,OUT,sha
        c,rows=inputs()
        receipt=json.loads((OUT/'prediction-receipt.json').read_text())
        raw=(OUT/'frozen-predictions.ndjson.gz').read_bytes()
        self.assertEqual(sha(raw),receipt['predictionArtifactSHA'])
        preds=[json.loads(s) for s in gzip.decompress(raw).decode().splitlines()]
        self.assertEqual([r['selectorEventId'] for r in rows],[p['selectorEventId'] for p in preds])
        for p in preds:
            self.assertEqual(len(p['probabilities']),5)
            self.assertTrue(all(math.isfinite(x) and 0<=x<=1 for x in p['probabilities']))
            self.assertAlmostEqual(sum(p['probabilities']),1,places=12)
            self.assertAlmostEqual(sum(i*x for i,x in enumerate(p['probabilities'])),p['expectedClass'],places=12)
        expected=causal_decisions(rows,[p['expectedClass'] for p in preds])
        self.assertEqual(expected,[{k:p[k] for k in ['state','reason']} for p in preds])
        self.assertEqual(receipt['modelPredictionCalls'],1)
        self.assertFalse(any(receipt['safety'].values()))

    def test_report_uses_actual_entry_outcomes_and_preserves_receipts(self):
        import json,gzip,statistics
        from run_phase57_historical_remeasurement import OUT,sha
        measurement=json.loads((OUT/'measurement.json').read_text())
        receipt=json.loads((OUT/'path-recovery-receipt.json').read_text())
        raw=(OUT/'path-diagnostics.json.gz').read_bytes()
        self.assertEqual(sha(raw),receipt['compressedPathDiagnosticsSHA'])
        decoded=gzip.decompress(raw)
        self.assertEqual(sha(decoded),receipt['rawPathDiagnosticsSHA'])
        paths={p['selectorEventId']:p for p in json.loads(decoded)['events']}
        preds=[json.loads(s) for s in gzip.decompress((OUT/'frozen-predictions.ndjson.gz').read_bytes()).decode().splitlines()]
        enters=[p for p in preds if p['state']=='ENTER']
        self.assertEqual(len(enters),measurement['enter'])
        self.assertEqual(len({p['symbolSessionId'] for p in enters}),len(enters))
        evaluated=[paths[p['selectorEventId']] for p in enters if paths[p['selectorEventId']]['labelable']]
        for k in [1,2,3,5]:
            hits=sum(p['highReturnPct']>=k for p in evaluated)
            self.assertEqual(hits,measurement['candidateActualEntry']['high'][str(k)]['hits'])
            self.assertAlmostEqual(100*hits/len(evaluated),measurement['candidateActualEntry']['high'][str(k)]['precisionPct'])
        self.assertAlmostEqual(statistics.mean(p['trueMaePct'] for p in evaluated),measurement['candidateActualEntry']['trueMaePct']['mean'])
        assessment=json.loads((OUT/'assessment.json').read_text())
        self.assertEqual(assessment['measurementSHA'],sha((OUT/'measurement.json').read_bytes()))
        self.assertFalse(measurement['freshClaim']);self.assertFalse(measurement['oosClaim'])
        self.assertFalse(any(measurement['safety'].values()))
        self.assertTrue(all(v==0 for v in measurement['counts'].values()))
        from run_phase57_historical_remeasurement import ROOT
        manifest=json.loads((OUT/'manifest.json').read_text())
        self.assertEqual(sha((OUT/'manifest.json').read_bytes()),(OUT/'manifest.sha256').read_text().strip())
        for file,expected in {**manifest['fileSHAs'],**manifest['implementationSHAs']}.items():
            self.assertEqual(sha((ROOT/file).read_bytes()),expected,file)

if __name__=='__main__':unittest.main()
