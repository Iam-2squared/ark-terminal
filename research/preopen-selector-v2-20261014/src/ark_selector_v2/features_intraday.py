"""Dated continuous phases, completeness-aware records and causal references."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from fractions import Fraction as F
import math
import statistics
from .calendar_phase import JST, phase_times, tick_in_window
from .contracts import Candle, FeatureFrame
from .exact_math import V2Error


@dataclass(frozen=True)
class Tick:
    event: datetime
    price: F
    size: F
    ordinal: int
    transaction_id: str
    phase: str

    def validate(self) -> None:
        if (self.event.tzinfo is None or not isinstance(self.price,F) or self.price<=0
                or not isinstance(self.size,F) or self.size<0 or self.ordinal<0
                or not self.transaction_id or self.phase not in {"CONTINUOUS","AUCTION","UNKNOWN"}):
            raise V2Error("INVALID_TICK_CONTRACT")


@dataclass(frozen=True)
class Bar:
    start: datetime
    end: datetime
    candle: Candle
    phase: str
    ordinal: int

    def validate(self) -> None:
        self.candle.validate()
        if self.start.tzinfo is None or self.end.tzinfo is None or self.end-self.start!=timedelta(minutes=1):
            raise V2Error("INVALID_1M_START_END_CONTRACT")
        if self.start.astimezone(JST).date()!=self.candle.session or self.end.astimezone(JST).date()!=self.candle.session:
            raise V2Error("BAR_SESSION_MISMATCH")
        if self.phase not in {"CONTINUOUS","AUCTION","UNKNOWN"}:
            raise V2Error("INVALID_BAR_PHASE")


@dataclass(frozen=True)
class Coverage:
    full_continuous: bool
    last30: bool
    preceding30: bool
    all_phases: bool
    evidence_hash: str
    status: str

    def validate(self) -> None:
        if not all(type(v) is bool for v in (self.full_continuous,self.last30,self.preceding30,self.all_phases)):
            raise V2Error("INVALID_COVERAGE_BOOLEAN")
        if len(self.evidence_hash)!=64 or self.status not in {"COMPLETE","PARTIAL","SOURCE_NOT_JOINED"}:
            raise V2Error("UNVERIFIED_WINDOW_COVERAGE")
        if self.status!="COMPLETE" and any((self.full_continuous,self.last30,self.preceding30,self.all_phases)):
            raise V2Error("FALSE_COMPLETE_WINDOW_CLAIM")


def ordered_ticks(records: list[Tick]) -> list[Tick]:
    ids=set()
    ordinals=set()
    for r in records:
        r.validate()
        if r.transaction_id in ids or r.ordinal in ordinals:
            raise V2Error("DUPLICATE_TICK_ID_OR_SOURCE_ORDINAL")
        ids.add(r.transaction_id)
        ordinals.add(r.ordinal)
    return sorted(records,key=lambda r:(r.event,r.ordinal))


def tick_features(records: list[Tick], session: date, coverage: Coverage,
                  continuous_last: F | None = None) -> FeatureFrame:
    coverage.validate()
    rows=ordered_ticks(records)
    end,_=phase_times(session)
    if any(r.event.astimezone(JST).date()!=session for r in rows):
        raise V2Error("TICK_SESSION_MISMATCH")
    last=[r for r in rows if tick_in_window(r.event,session,30,r.phase)]
    prior=[r for r in rows if tick_in_window(r.event,session,60,r.phase) and r.event<end-timedelta(minutes=30)]
    all_cont=[r for r in rows if r.phase=="CONTINUOUS" and r.event<end]
    out=FeatureFrame()
    missing="SOURCE_NOT_JOINED" if coverage.status=="SOURCE_NOT_JOINED" else "INCOMPLETE_WINDOW"
    count=len(last) if coverage.last30 else None
    volume=sum((r.size for r in last),F()) if coverage.last30 else None
    out.put("v2_tick_count30",count,missing)
    out.put("v2_tick_volume30",volume,missing)
    vwap=sum((r.price*r.size for r in last),F())/volume if volume else None
    p=continuous_last
    if p is None and all_cont and coverage.full_continuous:
        p=all_cont[-1].price
    out.put("v2_tick_vwap_distance30",100*(p/vwap-1) if p is not None and vwap is not None else None,
            "NO_TRADES_IN_COMPLETE_WINDOW" if coverage.last30 and not last else missing)
    changes=[math.log(float(b.price/a.price)) for a,b in zip(last[:-1],last[1:])]
    out.put("v2_tick_up_ratio30",F(sum(b.price>a.price for a,b in zip(last[:-1],last[1:])),len(last)-1) if coverage.last30 and len(last)>1 else None,"INSUFFICIENT_PRICE_CHANGES" if coverage.last30 else missing)
    out.put("v2_tick_realized_vol30",100*statistics.pstdev(changes) if changes and coverage.last30 else None,"INSUFFICIENT_PRICE_CHANGES" if coverage.last30 else missing)
    out.put("v2_tick_last_trade_age",(end-all_cont[-1].event).total_seconds() if coverage.full_continuous and all_cont else None,missing)
    out.put("v2_tick_burst30",F(len(last),len(prior)) if coverage.last30 and coverage.preceding30 and prior else None,"ZERO_PRECEDING_WINDOW" if coverage.preceding30 and not prior else missing)
    out.metadata["tick_identity_kind"]="AGGREGATED_RECORD_NOT_INDIVIDUAL_ORDER"
    out.metadata["tick_window"]={"start":(end-timedelta(minutes=30)).isoformat(),"end_exclusive":end.isoformat(),"coverage_hash":coverage.evidence_hash}
    return out


def reference_price(bars: list[Bar], when: datetime) -> tuple[F | None, dict[str, object]]:
    valid=[b for b in bars if b.phase=="CONTINUOUS" and b.end<=when and b.candle.close is not None]
    if not valid:
        return None,{"reason":"NO_CAUSAL_REFERENCE"}
    b=max(valid,key=lambda b:(b.end,b.ordinal))
    # Close's actual event lies inside [start,end]; use the oldest endpoint for
    # the five-minute gate, without inventing an exact last execution time.
    old=(when-b.start).total_seconds()
    young=(when-b.end).total_seconds()
    meta={"bar_start":b.start.isoformat(),"bar_end":b.end.isoformat(),"age_seconds_interval":[young,old],"individual_trade_time_known":False}
    if old>300:
        return None,{**meta,"reason":"STALE_REFERENCE_OLDEST_ENDPOINT"}
    return b.candle.close,meta


def minute_features(bars: list[Bar], session: date, coverage: Coverage) -> FeatureFrame:
    coverage.validate()
    for b in bars:
        b.validate()
        if b.candle.session!=session:
            raise V2Error("BAR_SESSION_MISMATCH")
    identities=[(b.start,b.end,b.phase,b.ordinal) for b in bars]
    if len(set(identities))!=len(identities):
        raise V2Error("DUPLICATE_BAR_IDENTITY")
    end,auction_end=phase_times(session)
    if any(b.phase=="UNKNOWN" for b in bars):
        raise V2Error("BOUNDARY_PHASE_UNKNOWN")
    cont=sorted([b for b in bars if b.phase=="CONTINUOUS" and b.end<=end],key=lambda b:(b.end,b.ordinal))
    pm_start=datetime.combine(session,time(12,30),JST)
    pm=[b for b in cont if b.start>=pm_start]
    valid=[b for b in cont if b.candle.close is not None]
    last=valid[-1] if valid else None
    price=last.candle.close if last else None
    allva=[b.candle.turnover for b in cont]
    allvo=[b.candle.volume for b in cont]
    full=coverage.full_continuous and all(v is not None for v in allva+allvo)
    vat=sum((v for v in allva if v is not None),F()) if full else None
    vot=sum((v for v in allvo if v is not None),F()) if full else None
    vwap=vat/vot if vat is not None and vot else None
    out=FeatureFrame()
    why="SOURCE_NOT_JOINED" if coverage.status=="SOURCE_NOT_JOINED" else "INCOMPLETE_WINDOW"
    out.put("v2_continuous_vwap_distance",100*(price/vwap-1) if price is not None and vwap is not None else None,why)
    first=next((b for b in pm if b.candle.open is not None),None)
    out.put("v2_pm_return",100*(price/first.candle.open-1) if coverage.full_continuous and price is not None and first and first.candle.open is not None else None,why)
    for w in (30,60):
        ref,meta=reference_price(cont,end-timedelta(minutes=w))
        out.metadata[f"last{w}_reference"]=meta
        out.put(f"v2_last{w}_return",100*(price/ref-1) if price is not None and ref is not None else None, str(meta.get("reason","UNKNOWN_CONTINUOUS_LAST")))
        window=[b for b in cont if b.start>=end-timedelta(minutes=w) and b.end<=end]
        window_ok=coverage.last30 if w==30 else coverage.last30 and coverage.preceding30
        wva=[b.candle.turnover for b in window]
        out.put(f"v2_last{w}_turnover_share",sum((v for v in wva if v is not None),F())/vat if window_ok and vat and all(v is not None for v in wva) else None,why)
    segment=[]
    if pm and pm[-1].end==end and pm[-1].candle.close is not None:
        segment=[pm[-1]]
        for b in reversed(pm[:-1]):
            if b.end!=segment[0].start or b.candle.close is None:
                break
            segment.insert(0,b)
    efficiency=None
    if len(segment)>=2:
        prices=[b.candle.close for b in segment if b.candle.close is not None]
        denom=sum((abs(b-a) for a,b in zip(prices[:-1],prices[1:])),F())
        efficiency=abs(prices[-1]-prices[0])/denom if denom else F(0)
    out.put("v2_pm_path_efficiency",efficiency,"INSUFFICIENT_CONSECUTIVE_BARS")
    locations=[]
    for b in cont:
        h,l,c=b.candle.high,b.candle.low,b.candle.close
        if b.start>=end-timedelta(minutes=60) and h is not None and l is not None and c is not None and h>l:
            locations.append((c-l)/(h-l))
    out.put("v2_last60_close_location_mean",sum(locations,F())/len(locations) if locations else None,"NO_VALID_NONFLAT_BARS")
    out.metadata["last60_close_location_validN"]=len(locations)
    out.metadata["pm_last_segmentN"]=len(segment)
    scheduled=int((end-pm_start).total_seconds()/60)
    out.put("v2_pm_observed_minute_fraction",F(sum(b.candle.close is not None for b in pm),scheduled) if coverage.status!="SOURCE_NOT_JOINED" else None,why)
    out.metadata["pm_confirmed_no_trade_minutes"]=sum(b.candle.status=="NO_TRADE" for b in pm)
    out.metadata["pm_scheduled_minutes"]=scheduled
    out.put("v2_last_continuous_bar_age_seconds",(end-last.end).total_seconds() if last else None,why)
    av=[b.candle.turnover for b in bars if b.phase=="AUCTION"]
    allphase=[b.candle.turnover for b in bars]
    total=sum((v for v in allphase if v is not None),F()) if coverage.all_phases and all(v is not None for v in allphase) else None
    out.put("v2_auction_turnover_share",sum((v for v in av if v is not None),F())/total if total and all(v is not None for v in av) else None,why)
    closing=[b for b in bars if b.phase=="AUCTION" and b.end==auction_end and b.candle.close is not None]
    if len(closing)>1:
        raise V2Error("AMBIGUOUS_CLOSING_AUCTION")
    close=closing[0].candle.close if closing else None
    out.put("v2_closing_auction_gap",100*(close/price-1) if close is not None and price is not None else None,"UNKNOWN_CLOSING_AUCTION_OR_CONTINUOUS_LAST")
    return out


def path_first_hit(bars: list[Bar], open_price: F, up_pct: int, down_pct: int) -> str:
    for b in sorted(bars,key=lambda b:b.end):
        h,l=b.candle.high,b.candle.low
        if h is None or l is None:
            return "UNKNOWN"
        up=100*h>=(100+up_pct)*open_price
        down=100*l<=(100-down_pct)*open_price
        if up and down:
            return "AMBIGUOUS"
        if up:
            return "UP_FIRST"
        if down:
            return "DOWN_FIRST"
    return "NO_OBSERVED_HIT"


def remaining_high(bars: list[Bar], reference: datetime) -> F | None:
    highs=[b.candle.high for b in bars if b.start>=reference and b.candle.high is not None]
    return max(highs) if highs else None
