import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from preopen_model import HEADS,probability_diagnostics


class FixedProbabilityDiagnostics(unittest.TestCase):
    def test_exact_endpoint_probabilities_and_fixed_ece_bins(self):
        labels=[{h:y for h in HEADS} for y in (0,1)]
        result=probability_diagnostics({h:[0,1] for h in HEADS},labels)
        for head in result['heads'].values():
            self.assertEqual(head['brier'],0)
            self.assertEqual(head['ece10'],0)
            self.assertEqual([b['N'] for b in head['bins']],[1]+[0]*8+[1])
            self.assertEqual(sum(b['N'] for b in head['bins']),2)

    def test_empty_labels_are_unmeasured(self):
        self.assertEqual(probability_diagnostics({},[])['status'],'NOT_MEASURED')


if __name__=='__main__':unittest.main()
