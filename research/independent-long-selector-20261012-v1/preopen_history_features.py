"""Explicit previous-session windows and native corporate/flow feature schema."""
from __future__ import annotations

from datetime import timedelta

from preopen_selector import PreopenError, number, stamp
from preopen_native_source import cash_clock
from tick_feature_library import tick_registry, compute_tick_features

FIN_COLUMNS = tuple("""Sales OP OdP NP EPS DEPS TA Eq EqAR BPS CFO CFI CFF CashEq
Div1Q Div2Q Div3Q DivFY DivAnn DivTotalAnn PayoutRatioAnn FDiv1Q FDiv2Q
FDiv3Q FDivFY FDivAnn FDivTotalAnn FPayoutRatioAnn NxFDiv1Q NxFDiv2Q NxFDiv3Q
NxFDivFY NxFDivAnn NxFDivTotalAnn NxFPayoutRatioAnn FSales2Q FOP2Q FOdP2Q FNP2Q
FEPS2Q NxFSales2Q NxFOP2Q NxFOdP2Q NxFNp2Q NxFEPS2Q FSales FOP FOdP FNP FEPS
NxFSales NxFOP NxFOdP NxFNp NxFEPS ShOutFY TrShFY AvgSh NCSales NCOP NCOdP
NCNP NCEPS NCTA NCEq NCEqAR NCBPS FNCSales2Q FNCOP2Q FNCOdP2Q FNCNP2Q
FNCEPS2Q NxFNCSales2Q NxFNCOP2Q NxFNCOdP2Q NxFNCNP2Q NxFNCEPS2Q FNCSales
FNCOP FNCOdP FNCNP FNCEPS NxFNCSales NxFNCOP NxFNCOdP NxFNCNP NxFNCEPS
ShEq NCShEq ROE NCROE""".split())
FLOW_COLUMNS = tuple(a+b for a in ("Prop","Brk","Tot","Ind","Frgn","SecCo",
                                  "InvTr","BusCo","OthCo","InsCo","Bank","TrstBnk","OthFin")
                     for b in ("Sell","Buy","Tot","Bal"))
VALUATION_COLUMNS = ("EPS","FwdEPS","BPS","ROE","FwdROE","PER","FwdPER","PBR","MktCap")
SUMMARY_NAMES = ("vwap_distance_pct","afternoon_return_pct","last30_turnover_share",
                 "last60_turnover_share","observed_minute_count",
                 "observed_minute_turnover","auction_turnover_share")


def native_feature_names():
    return tuple(sorted(
        [f"preopen_native_fin_{c}" for c in FIN_COLUMNS] +
        [f"preopen_native_flow_{c}_jpy" for c in FLOW_COLUMNS] +
        [f"preopen_native_valuation_{c}" for c in VALUATION_COLUMNS] +
        [f"preopen_previous_tick_{c}" for c in tick_registry()] +
        [f"preopen_previous_session_{c}" for c in SUMMARY_NAMES]))


def prior_tick_features(events, *, previous_session, cutoff, reference_price,
                        complete_source_verified):
    result = {f"preopen_previous_tick_{k}":None for k in tick_registry()}
    if events is None or not complete_source_verified:
        return result
    closing = stamp(previous_session+"T"+cash_clock(previous_session)["auction_close"]+":00+09:00")
    carried = []
    for event in events:
        occurred, known = stamp(event["tradeAt"]), stamp(event["availableAt"])
        if (occurred.date().isoformat() != previous_session or occurred > closing
                or known < occurred or known > stamp(cutoff)):
            raise PreopenError("PREVIOUS_TICK_SESSION_WINDOW_OR_CARRY_AVAILABILITY")
        # The generic calculation is anchored to previous exchange event time.
        # It does not assert that the delayed native file arrived at tradeAt.
        carried.append({**event,"availableAt":event["tradeAt"]})
    values = compute_tick_features(carried, decision_at=(closing+timedelta(microseconds=1)).isoformat(),
        decision_price=number(reference_price,positive=True),complete_stream_verified=True,
        side_semantics_verified=False)
    return {f"preopen_previous_tick_{k}":v for k,v in values.items()}


def minute_session_summary(bars, *, previous_session, reference_price):
    result = {f"preopen_previous_session_{k}":None for k in SUMMARY_NAMES}
    if bars is None:
        return result
    continuous, auctions = [], []
    for b in bars:
        if stamp(b["start"]).date().isoformat() != previous_session:
            raise PreopenError("CURRENT_MINUTE_IN_PRIOR_SESSION_SUMMARY")
        (continuous if b["kind"] == "CONTINUOUS_1M" else auctions).append(b)
    all_bars = continuous + auctions
    volume = sum(number(b["volume"]) for b in all_bars)
    turnover = sum(number(b["turnover"]) for b in all_bars)
    result["preopen_previous_session_observed_minute_count"] = float(len(continuous))
    result["preopen_previous_session_observed_minute_turnover"] = turnover
    if volume and turnover:
        vwap = turnover/volume
        result["preopen_previous_session_vwap_distance_pct"] = 100*(number(reference_price)/vwap-1)
        closing = stamp(previous_session+"T"+cash_clock(previous_session)["auction_close"]+":00+09:00")
        for minutes in (30,60):
            result[f"preopen_previous_session_last{minutes}_turnover_share"] = (
                sum(number(b["turnover"]) for b in all_bars
                    if stamp(b["start"]) >= closing-timedelta(minutes=minutes))/turnover)
        result["preopen_previous_session_auction_turnover_share"] = (
            sum(number(b["turnover"]) for b in auctions)/turnover)
    afternoon = sorted([b for b in all_bars if stamp(b["start"]).hour >= 12],
                       key=lambda b: b["start"])
    if afternoon:
        result["preopen_previous_session_afternoon_return_pct"] = (
            100*(number(afternoon[-1]["close"])/number(afternoon[0]["open"])-1))
    return result
