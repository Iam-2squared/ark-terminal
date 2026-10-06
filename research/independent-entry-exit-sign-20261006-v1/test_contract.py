"""Focused contract checks; no market replay and no model fitting."""
import copy
import unittest
import numpy as np
from sign_io import validate_sign
from sign_model import fit_preprocessing, transform, TRANSFORM_VERSION
from sign_policy import select_threshold, filter_action
from sign_metrics import cells_metrics, evaluate
from inference import predict_sign
from audit_source_adapter import sign_row

def cal_rows(inverted=False, constant=False):
    return [{"entry_id":str(i),"session":"2025-01-"+str(1+i%3).zfill(2),
             "y_plus":int(i<30),"p_plus":0.4 if constant else (0.2 if i<30 else 0.8) if inverted else (0.8 if i<30 else 0.2)}
            for i in range(60)]

class StubModel:
    classes_=np.array([0,1])
    def predict_proba(self,x):
        return np.tile([0.5,0.5],(len(x),1))

class ContractTests(unittest.TestCase):
    def test_exact_sign_direction_zero_unknown(self):
        base={"entry_id":"x","session":"2025-01-01","label_maturity":"2025-01-01T16:00:00+09:00",
              "known":True,"buy_debit":"100000000000000000000000.00"}
        for credit,status,y in [("100000000000000000000000.01","PLUS",1),
            ("99999999999999999999999.99","MINUS",0),("100000000000000000000000.00","EXACT_ZERO",None)]:
            r=sign_row({**base,"sell_credit":credit},"fixed")
            self.assertEqual((r["sign_status"],r["y_plus"]),(status,y))
        self.assertEqual(sign_row({**base,"sell_credit":None},"fixed")["sign_status"],"UNKNOWN")

    def test_sign_view_allowlist(self):
        r=sign_row({"entry_id":"x","session":"d","known":True,"buy_debit":"1","sell_credit":"2","label_maturity":"d"},"h")
        with self.assertRaises(AssertionError):
            validate_sign({**r,"return":1})

    def test_magnitude_invariance(self):
        base={"entry_id":"x","session":"d","known":True,"buy_debit":"100","label_maturity":"d"}
        self.assertEqual(sign_row({**base,"sell_credit":"100.01"},"h"),sign_row({**base,"sell_credit":"130"},"h"))

    def test_perfect_threshold_and_all_reject_invalid(self):
        t=select_threshold(cal_rows(),"0.8")
        self.assertEqual((t["status"],t["tau"],t["cal_BA"]),("ACTIVE",0.8,1.0))
        self.assertGreater(t["all_reject_sentinel"],1)

    def test_support_off(self):
        self.assertEqual(select_threshold(cal_rows()[:49],"0.8")["status"],"FILTER_OFF_SUPPORT")

    def test_constant_score_all_pass(self):
        self.assertEqual(select_threshold(cal_rows(constant=True),"0.8")["status"],"NULL_ALL_PASS")

    def test_inverse_score_not_flipped(self):
        self.assertEqual(select_threshold(cal_rows(inverted=True),"0.8")["status"],"NULL_ALL_PASS")

    def test_tau_ties_and_permutation(self):
        a=cal_rows()
        self.assertEqual(select_threshold(a,"0.8"),select_threshold(list(reversed(a)),"0.8"))
        t=select_threshold(a,"0.8")
        self.assertEqual(filter_action(0.8,t),"PASS_CANDIDATE")
        self.assertEqual(filter_action(0.79,t),"REJECT_CANDIDATE")

    def test_abstain_filter_pass(self):
        t=select_threshold(cal_rows(),"0.8")
        self.assertEqual(filter_action(None,t),"PASS_CANDIDATE")
        metadata={"x":{"execution_eligible":True}}
        signs={"x":{"y_plus":0,"sign_status":"MINUS"}}
        p=[{"entry_id":"x","session":"d","p_plus":None,"actions":{"0.8":"PASS_CANDIDATE"}}]
        self.assertEqual(evaluate(p,signs,metadata)["FP"],1)
        self.assertEqual(evaluate(p,signs,metadata,"binary")["known_scored_N"],0)

    def test_zero_denominators(self):
        m=cells_metrics(0,0,0,0)
        self.assertIsNone(m["balanced_accuracy"]);self.assertIsNone(m["pass_MINUS_rate"])
        self.assertEqual(m["MCC"],0.0)

    def test_preprocessor_missing_unknown_fit_only(self):
        fit=[{"entry_id":"a","numeric":{"v":None},"categorical":{"c":"A"}},
             {"entry_id":"b","numeric":{"v":2},"categorical":{"c":"A"}}]
        prep=fit_preprocessing(fit,["v"],["c"]);frozen=copy.deepcopy(prep)
        test=[{"entry_id":"x","numeric":{"v":1000},"categorical":{"c":"NEVER_IN_FIT"}}]
        z=transform(test,prep)
        self.assertEqual(prep,frozen);self.assertEqual(z[0,-1],1)
        self.assertEqual(prep["mean"],[1.0,0.5]);self.assertNotIn("NEVER_IN_FIT",prep["vocabulary"]["c"])

    def test_inference_half_tie_forbidden_and_late(self):
        prep=fit_preprocessing([{"entry_id":"a","numeric":{"v":1},"categorical":{}}],["v"],[])
        s={"entry_id":"x","decision_ts":"d2","numeric":{"v":1},"categorical":{},
           "availability_status":"HISTORICAL_ASSUMED_AVAILABILITY","feature_as_of":"d1","valid_from":"d1",
           "transform_version":TRANSFORM_VERSION,"max_source_available_at":"d1","feature_schema_hash":"schema"}
        a={"model":StubModel(),"preprocessing":prep,"feature_schema_hash":"schema","model_hash":"m","fit_cutoff":"d0"}
        t={"model_hash":"m","threshold_hash":"t","cal_cutoff":"d1","status":"ACTIVE","tau":0.5}
        p=predict_sign(s,a,t)
        self.assertEqual(p["predicted_sign"],"PRED_PLUS");self.assertEqual(p["filter_action"],"PASS_CANDIDATE")
        self.assertIsNone(predict_sign({**s,"max_source_available_at":"d3"},a,t)["p_plus"])
        with self.assertRaises(AssertionError):
            predict_sign({**s,"future_EXIT":1},a,t)

if __name__=="__main__":
    unittest.main(verbosity=2)
