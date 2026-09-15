import unittest
from datetime import datetime, timezone, timedelta
from phase57_cash_only_unlock import build_cash_only_unlock_candidate

NOW=datetime(2026,9,15,5,0,0,tzinfo=timezone.utc)
RECON={"status":"RECONCILIATION_PASS","blockers":[],"snapshotAgeSeconds":5}
RUNTIME={"killSwitchLatched":False,"faults":[]}

def draft(**changes):
    intent={"symbol":"7203.T","direction":"LONG","side":"BUY","positionEffect":"OPEN","quantity":100,"orderType":"MARKET"}
    intent.update(changes)
    return {"function":"RssStockOrder","trigger":0,"transmitted":False,"excelWritePerformed":False,"rssCallPerformed":False,"intent":intent}

def run(d=None, **changes):
    args=dict(reconciliation=RECON,runtime_safety=RUNTIME,draft=d or draft(),buying_power=100000,estimated_notional=50000,daily_realized_pnl=0,human_approval_id="approve-1",approval_expires_at=(NOW+timedelta(minutes=2)).isoformat(),now=NOW)
    args.update(changes)
    return build_cash_only_unlock_candidate(**args)

class CashOnlyUnlockTests(unittest.TestCase):
    def test_clean_cash_long_is_candidate_only(self):
        out=run(); self.assertTrue(out["eligible"]); self.assertTrue(out["cashOnly"]); self.assertFalse(out["marginAllowed"]); self.assertFalse(out["shortSellingAllowed"]); self.assertFalse(out["safety"]["executionAllowed"]); self.assertFalse(out["safety"]["transmitted"])
    def test_short_is_blocked(self):
        self.assertIn("LONG_ONLY",run(draft(direction="SHORT",side="SELL"))["blockers"])
    def test_margin_function_is_blocked(self):
        d=draft(); d["function"]="RssMarginOpenOrder"; self.assertIn("CASH_ORDER_FUNCTION_REQUIRED",run(d)["blockers"])
    def test_insufficient_cash_blocks_without_margin_fallback(self):
        out=run(buying_power=1000); self.assertIn("INSUFFICIENT_CASH",out["blockers"]); self.assertFalse(out["marginAllowed"])
    def test_order_notional_cap(self):
        self.assertIn("ORDER_NOTIONAL_CAP_EXCEEDED",run(estimated_notional=100001)["blockers"])
    def test_daily_loss_cap(self):
        self.assertIn("DAILY_LOSS_LIMIT_REACHED",run(daily_realized_pnl=-10000)["blockers"])
    def test_kill_switch_blocks(self):
        self.assertIn("KILL_SWITCH_OR_FAULT_PRESENT",run(runtime_safety={"killSwitchLatched":True,"faults":["X"]})["blockers"])
    def test_stale_reconciliation_blocks(self):
        self.assertIn("RECONCILIATION_TOO_OLD",run(reconciliation={"status":"RECONCILIATION_PASS","blockers":[],"snapshotAgeSeconds":31})["blockers"])
    def test_approval_replay_blocks(self):
        self.assertIn("APPROVAL_REPLAYED",run(used_approval_ids=["approve-1"])["blockers"])
    def test_expired_approval_blocks(self):
        self.assertIn("APPROVAL_EXPIRED",run(approval_expires_at=(NOW-timedelta(seconds=1)).isoformat())["blockers"])
    def test_long_ttl_blocks(self):
        self.assertIn("APPROVAL_TTL_TOO_LONG",run(approval_expires_at=(NOW+timedelta(minutes=6)).isoformat())["blockers"])

if __name__=="__main__": unittest.main()
