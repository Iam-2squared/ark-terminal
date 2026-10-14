"""As-of optional context. Missing joins remain None in the fixed 95 profile."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime
from fractions import Fraction as F
from typing import Any
from .contracts import FeatureFrame, SourceEvidence, STATE_NAMES
from .exact_math import V2Error


@dataclass(frozen=True)
class Peer:
    symbol: str
    sector: str
    master_session: date
    return1: F | None
    return5: F | None
    evidence: SourceEvidence


def market_features(t: date, cutoff: datetime, sector: str,
                    expected_market: set[str], expected_sector: set[str], peers: list[Peer],
                    own_return5: F | None, topix: dict[int,F | None] | None = None,
                    topix_evidence: SourceEvidence | None = None) -> FeatureFrame:
    out=FeatureFrame()
    for n in (1,5,25):
        value=topix.get(n) if topix is not None and topix_evidence is not None else None
        if topix_evidence is not None:
            topix_evidence.validate(cutoff,basis="RAW")
            if topix_evidence.effective_session!=t:
                raise V2Error("CONTEXT_EFFECTIVE_SESSION_MISMATCH")
        out.put(f"v2_topix_return_{n}d",value,"SOURCE_NOT_JOINED")
    seen=set()
    for p in peers:
        p.evidence.validate(cutoff,basis="RAW")
        if p.master_session!=t or p.evidence.effective_session!=t or p.symbol not in expected_market:
            raise V2Error("DATED_PEER_UNIVERSE_MISMATCH")
        if p.symbol in seen:
            raise V2Error("DUPLICATE_CONTEXT_PEER")
        seen.add(p.symbol)
    if not expected_sector<=expected_market:
        raise V2Error("SECTOR_PEER_NOT_IN_MARKET_MASTER")
    sector_peers=[p for p in peers if p.symbol in expected_sector and p.sector==sector]
    def supported(values: list[F], expected: int) -> bool:
        return expected>0 and 10*len(values)>=9*expected
    s1=[p.return1 for p in sector_peers if p.return1 is not None]
    s5=[p.return5 for p in sector_peers if p.return5 is not None]
    m1=[p.return1 for p in peers if p.return1 is not None]
    r1=sum(s1,F())/len(s1) if supported(s1,len(expected_sector)) else None
    r5=sum(s5,F())/len(s5) if supported(s5,len(expected_sector)) else None
    out.put("v2_sector_return_1d",r1,"PEER_COVERAGE_BELOW_90_PERCENT")
    out.put("v2_sector_return_5d",r5,"PEER_COVERAGE_BELOW_90_PERCENT")
    out.put("v2_relative_sector_return5",own_return5-r5 if own_return5 is not None and r5 is not None else None,"UNKNOWN_SECTOR_OR_OWN_RETURN")
    out.put("v2_market_breadth",100*F(sum(v>0 for v in m1),len(m1)) if supported(m1,len(expected_market)) else None,"PEER_COVERAGE_BELOW_90_PERCENT")
    out.put("v2_sector_breadth",100*F(sum(v>0 for v in s1),len(s1)) if supported(s1,len(expected_sector)) else None,"PEER_COVERAGE_BELOW_90_PERCENT")
    times=[p.evidence.available_at for p in peers]
    if topix_evidence:
        times.append(topix_evidence.available_at)
    out.metadata["context_available_at"]=max(times).isoformat() if times else None
    out.metadata["peer_support"]={"market_expected":len(expected_market),"market_known1":len(m1),"sector_expected":len(expected_sector),"sector_known1":len(s1),"sector_known5":len(s5)}
    return out


@dataclass(frozen=True)
class Financial:
    document_id: str
    fiscal_period_kind: str
    consolidation: str
    currency: str
    amount_unit: str
    sales: F | None
    previous_sales: F | None
    operating_profit: F | None
    previous_operating_profit: F | None
    evidence: SourceEvidence
    matched_year_basis: bool


def financial_features(records: list[Financial], session: date, cutoff: datetime,
                       valuation: dict[str,F | None] | None = None,
                       valuation_evidence: SourceEvidence | None = None,
                       roe_is_ratio: bool | None = None,
                       next_earnings: date | None = None,
                       earnings_evidence: SourceEvidence | None = None) -> FeatureFrame:
    out=FeatureFrame()
    eligible=[r for r in records if r.evidence.available_at<=cutoff and r.evidence.published_at<=cutoff]
    latest=max((r.evidence.available_at for r in eligible),default=None)
    last=[r for r in eligible if r.evidence.available_at==latest]
    row=last[0] if len(last)==1 else None
    reason="AMBIGUOUS_FINANCIAL_DOCUMENTS" if len(last)>1 else "SOURCE_NOT_JOINED"
    if row:
        row.evidence.validate(cutoff)
        if not row.matched_year_basis or row.currency!="JPY" or row.amount_unit not in {"JPY","THOUSAND_JPY","MILLION_JPY"} or not row.fiscal_period_kind or not row.consolidation:
            row=None
            reason="FINANCIAL_PERIOD_OR_UNITS_MISMATCH"
    sales=row.sales if row else None
    ps=row.previous_sales if row else None
    op=row.operating_profit if row else None
    pop=row.previous_operating_profit if row else None
    out.put("v2_sales_yoy",100*(sales/ps-1) if sales is not None and ps is not None and ps>0 else None,reason if row is None else "NONPOSITIVE_PRIOR_SALES")
    out.put("v2_operating_profit_change",100*(op-pop)/abs(pop) if op is not None and pop is not None and pop!=0 else None,reason if row is None else "ZERO_PRIOR_OPERATING_PROFIT")
    out.put("v2_operating_margin",100*op/sales if op is not None and sales is not None and sales>0 else None,reason if row is None else "NONPOSITIVE_SALES")
    if valuation_evidence is not None:
        valuation_evidence.validate(cutoff)
    values=valuation if valuation_evidence is not None and valuation is not None else {}
    roe=values.get("roe")
    out.put("v2_valuation_roe",(100*roe if roe_is_ratio else roe) if roe is not None and roe_is_ratio is not None else None,"UNKNOWN_ROE_UNIT_OR_SOURCE")
    out.put("v2_valuation_per",values.get("per"),"SOURCE_NOT_JOINED")
    out.put("v2_valuation_pbr",values.get("pbr"),"SOURCE_NOT_JOINED")
    if earnings_evidence:
        earnings_evidence.validate(cutoff)
    out.put("v2_days_to_known_earnings",(next_earnings-session).days if next_earnings is not None and earnings_evidence is not None and next_earnings>=session else None,"NO_KNOWN_NEXT_EARNINGS")
    out.put("v2_financial_disclosure_age",(cutoff-row.evidence.available_at).total_seconds()/86400 if row else None,reason)
    out.metadata["financial_document_id"]=row.document_id if row else None
    times=[x.available_at for x in (row.evidence if row else None,valuation_evidence,earnings_evidence) if x is not None]
    out.metadata["financial_available_at"]=max(times).isoformat() if times else None
    return out


def state_features(primary: str | None, *, formal_observed: bool,
                   t: date, cutoff: datetime, evidence: SourceEvidence | None,
                   rules_hash: str | None, profile_hash: str | None,
                   normalizer_hash: str | None, upstream_fit_end: date | None = None,
                   expected_lineage: tuple[str,str,str] | None = None) -> FeatureFrame:
    out=FeatureFrame()
    known=formal_observed and evidence is not None
    if known:
        assert evidence is not None
        evidence.validate(cutoff)
        if evidence.effective_session!=t or primary not in STATE_NAMES:
            raise V2Error("FORMAL_STATE_SESSION_OR_IDENTITY_MISMATCH")
        if any(h is None or len(h)!=64 for h in (rules_hash,profile_hash,normalizer_hash)):
            raise V2Error("STATE_LINEAGE_NOT_HASH_LOCKED")
        if evidence.known_at_evidence_kind!="SYNTHETIC" and (expected_lineage is None or expected_lineage!=(rules_hash,profile_hash,normalizer_hash)):
            raise V2Error("STATE_FROZEN_LINEAGE_MISMATCH")
        if upstream_fit_end is not None and upstream_fit_end>=t:
            raise V2Error("STATE_UPSTREAM_FIT_NOT_PRIOR")
    for name in STATE_NAMES:
        out.put("v2_previous_state_"+name,int(primary==name) if known else None,"STATE_NOT_FORMALLY_OBSERVED")
    out.metadata["state_available_at"]=evidence.available_at.isoformat() if known and evidence else None
    out.metadata["state_rules_hash"]=rules_hash
    return out


def assemble_features(daily: FeatureFrame, minute: FeatureFrame | None = None,
                      market: FeatureFrame | None = None, financial: FeatureFrame | None = None,
                      tick: FeatureFrame | None = None, state: FeatureFrame | None = None) -> FeatureFrame:
    from .contracts import feature_names, validate_features
    out=FeatureFrame()
    for frame in (daily,minute,market,financial,tick,state):
        if frame is not None:
            out.merge(frame)
    names=feature_names()
    if set(out.values)-set(names):
        raise V2Error("UNREGISTERED_OPTIONAL_FEATURE")
    values=out.values
    out.values={}
    for name in names:
        out.put(name,values.get(name),out.missing.get(name,"SOURCE_NOT_JOINED"))
    validate_features(out.values)
    return out
