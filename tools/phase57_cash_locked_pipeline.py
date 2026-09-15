"""Compose the cash-only G6-G10 pipeline without any Excel/RSS write capability."""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from phase57_account_reconciliation import reconcile_account_snapshot
from phase57_execution_dryrun_gate import build_locked_cash_order_draft
from phase57_cash_only_unlock import build_cash_only_unlock_candidate
from phase57_cash_micro_live_gate import build_micro_live_preflight
from phase57_locked_excel_adapter import build_locked_excel_interface


def run_locked_pipeline(
    snapshot,
    *,
    external_positions,
    intent,
    estimated_notional,
    ark_managed_positions=None,
    daily_realized_pnl=0,
    max_order_notional=500000,
    max_daily_loss=10000,
    now=None,
):
    current=now or datetime.now(timezone.utc)
    managed=list(ark_managed_positions or [])
    recon=reconcile_account_snapshot(
        snapshot,
        ark_positions=managed,
        external_positions=external_positions,
        now=current,
        max_age_seconds=30,
    )
    if recon["status"] != "RECONCILIATION_PASS":
        return {"status":"BLOCKED","stage":"G6","reconciliation":recon}
    draft=build_locked_cash_order_draft(recon,intent,order_id=1,account_type=0,sor=0)
    candidate=build_cash_only_unlock_candidate(
        reconciliation=recon,
        runtime_safety={"killSwitchLatched":False,"faults":[]},
        draft=draft,
        buying_power=snapshot.get("buyingPower"),
        estimated_notional=estimated_notional,
        daily_realized_pnl=daily_realized_pnl,
        human_approval_id="LOCKED-PREFLIGHT",
        approval_expires_at=(current+timedelta(minutes=2)).isoformat(),
        now=current,
        used_approval_ids=[],
        max_order_notional=max_order_notional,
        max_daily_loss=max_daily_loss,
    )
    if not candidate["eligible"]:
        return {"status":"BLOCKED","stage":"G9","reconciliation":recon,"draft":draft,"candidate":candidate}
    preflight=build_micro_live_preflight(
        unlock_candidate=candidate,
        draft=draft,
        ark_managed_positions=managed,
        open_order_count=len(snapshot.get("orders") or []),
    )
    if not preflight["readyForPhysicalUnlock"]:
        return {"status":"BLOCKED","stage":"G10","reconciliation":recon,"draft":draft,"candidate":candidate,"preflight":preflight}
    interface=build_locked_excel_interface(preflight=preflight,draft=draft,buying_power=snapshot.get("buyingPower"))
    return {"status":"LOCKED_READY","stage":"EXCEL_ADAPTER","reconciliation":recon,"draft":draft,"candidate":candidate,"preflight":preflight,"interface":interface}
