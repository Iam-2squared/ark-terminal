import copy, unittest
from scripts import phase57_exit_winner_lifecycle_r50 as r

def env(now=700, fresh=True, **kw):
    v={k:0.0 for k in r.FACTS}; v.update(certifiedMfePct=4.0, certifiedGivebackPp=0.5,
        timeSincePeak=5.0, barsHeld=60.0, momentum5Pct=0.2, signalTrueN=1.0)
    v.update(kw); return {"now":now,"maxKnownAt":now,"maxBarEnd":now,"fresh":fresh,"values":v}

class R50RuntimeTests(unittest.TestCase):
    def call(self,e,s=None,c=r.CANDIDATES[0],terminal=False): return r.intent(e,s or r.initial_state(),c,terminal=terminal)
    def test_protocol(self): self.assertEqual(r.load_protocol()["candidateCount"],2)
    def test_safety9(self): self.assertTrue(all(v is False for v in r.load_protocol()["safety"].values()))
    def test_exact_candidates(self): self.assertEqual(len(r.CANDIDATES),2)
    def test_no_fifth(self):
        with self.assertRaisesRegex(ValueError,"UNKNOWN_CANDIDATE"): self.call(env(),c="R50_C")
    def test_known_at(self):
        e=env(); e["maxKnownAt"]=701
        with self.assertRaisesRegex(ValueError,"FUTURE_FACT"): self.call(e)
    def test_bar_end(self):
        e=env(); e["maxBarEnd"]=701
        with self.assertRaisesRegex(ValueError,"FUTURE_FACT"): self.call(e)
    def test_deny_extra_fact(self):
        e=env(); e["values"]["futureHigh"]=99
        with self.assertRaisesRegex(ValueError,"ALLOWLIST"): self.call(e)
    def test_missing_holds(self): self.assertEqual(self.call(env(fresh=False))["authority"],"MISSING_HOLD")
    def test_incomplete_giveback_holds(self): self.assertEqual(self.call(env(certifiedGivebackPp=None))["authority"],"UNCERTIFIED_HOLD")
    def test_incomplete_mfe_holds(self): self.assertEqual(self.call(env(certifiedMfePct=None))["authority"],"UNCERTIFIED_HOLD")
    def test_unarmed_holds(self): self.assertEqual(self.call(env(certifiedMfePct=2.99))["authority"],"UNARMED_HOLD")
    def test_new_peak_holds(self): self.assertEqual(self.call(env(newPeak=1))["authority"],"NEW_PEAK_CONTINUATION")
    def test_continuation_holds(self): self.assertEqual(self.call(env())["authority"],"CONTINUATION")
    def test_recovery_attempt_holds(self): self.assertEqual(self.call(env(stateRecovery=1,momentum5Pct=-1,signalTrueN=0))["authority"],"RECOVERY_ATTEMPT")
    def test_recovery_confirmed_two(self):
        a=self.call(env(stateRecovery=1)); b=self.call(env(now=701,stateRecovery=1),a["state"])
        self.assertEqual(b["authority"],"RECOVERY_CONFIRMED")
    def test_drop_alone_cannot_exit(self): self.assertEqual(self.call(env(momentum5Pct=-1,signalTrueN=0))["action"],"HOLD")
    def test_negative_pnl_alone_cannot_exit(self): self.assertEqual(self.call(env(currentReturnPct=-20))["action"],"HOLD")
    def test_one_signal_loss_cannot_exit(self): self.assertEqual(self.call(env(signalLossN=1))["action"],"HOLD")
    def test_unknown_not_false(self):
        e=env(momentum5Pct=-1,signalTrueN=0,signalFalseN=0); self.assertEqual(self.call(e)["authority"],"ORDINARY_PULLBACK")
    def mature(self,now=700,**kw):
        x=dict(certifiedMfePct=6,certifiedGivebackPp=3,timeSincePeak=12,barsHeld=50,momentum5Pct=0,signalTrueN=0,signalFalseN=3)
        x.update(kw); return env(now=now,**x)
    def test_mature_needs_persistence(self): self.assertEqual(self.call(self.mature())["action"],"HOLD")
    def test_a_harvests_second(self):
        a=self.call(self.mature()); b=self.call(self.mature(701),a["state"]); self.assertEqual(b["action"],"EXIT_INTENT")
    def test_b_requires_failed_recovery(self):
        a=self.call(self.mature(),c=r.CANDIDATES[1]); b=self.call(self.mature(701),a["state"],r.CANDIDATES[1]); self.assertEqual(b["action"],"HOLD")
    def test_b_harvests_failed_recovery(self):
        a=self.call(self.mature(failedRecovery=1,weakRun=4),c=r.CANDIDATES[1]); b=self.call(self.mature(701,failedRecovery=1,weakRun=4),a["state"],r.CANDIDATES[1]); self.assertEqual(b["action"],"EXIT_INTENT")
    def test_recovery_resets_deterioration(self):
        a=self.call(self.mature()); b=self.call(env(now=701,stateRecovery=1,momentum5Pct=-1,signalTrueN=0),a["state"]); self.assertEqual(b["state"]["deteriorationCount"],0)
    def test_new_peak_resets(self):
        a=self.call(self.mature()); b=self.call(env(now=701,newPeak=1),a["state"]); self.assertEqual(b["state"]["deteriorationCount"],0)
    def test_threshold_geometry(self): self.assertEqual(self.call(self.mature(certifiedGivebackPp=2.99))["authority"],"ORDINARY_PULLBACK")
    def test_fractional_geometry(self): self.assertEqual(self.call(self.mature(certifiedMfePct=8,certifiedGivebackPp=3.9))["authority"],"ORDINARY_PULLBACK")
    def test_age(self): self.assertEqual(self.call(self.mature(timeSincePeak=11))["authority"],"ORDINARY_PULLBACK")
    def test_hold_time(self): self.assertEqual(self.call(self.mature(barsHeld=49))["authority"],"ORDINARY_PULLBACK")
    def test_signal_count(self): self.assertEqual(self.call(self.mature(signalFalseN=2))["authority"],"ORDINARY_PULLBACK")
    def test_terminal(self): self.assertEqual(self.call(env(),terminal=True)["action"],"FORCE_TERMINAL")
    def test_nonmonotone(self):
        a=self.call(env())
        with self.assertRaisesRegex(ValueError,"NONMONOTONE"): self.call(env(),a["state"])
    def test_input_not_mutated(self):
        s=r.initial_state(); before=copy.deepcopy(s); self.call(env(),s); self.assertEqual(s,before)
    def test_future_denylist_primary(self): self.assertIn("POST_ENTRY_UPSIDE_GE5",r.load_protocol()["futureDenylist"])
    def test_pattern_blocked(self): self.assertEqual(r.load_protocol()["lifecycle"]["roles"]["pattern187"],"not admitted for R50 decisions")
    def test_diagnostic_scores(self): self.assertIn("diagnostic",r.load_protocol()["lifecycle"]["roles"]["gen3DeteriorationScore"])
    def test_entry_identity_includes_arm(self):
        self.assertNotEqual(r.identity_key(r.load_protocol()["entryArms"][0],"same"),r.identity_key(r.load_protocol()["entryArms"][1],"same"))

if __name__ == "__main__": unittest.main()
