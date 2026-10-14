"""Typed contracts, strict identities, provenance and non-execution invariants."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, date
from fractions import Fraction
from pathlib import Path
from typing import Any
import hashlib
import json
import re
from .exact_math import V2Error, rational

ROOT = Path(__file__).resolve().parents[2]
DESIGN_ID = "ARK_PREOPEN_V2_TREND_CONTINUATION_CASCADE"
LABEL_ID = "JPX_RAW_OPEN_FULL_SESSION_UP_RISK_JOINT_V2"
FLAGS = ("executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed",
         "rssOrderFunctionAllowed", "liveTradingAllowed", "paperTradingAllowed",
         "automaticPromotionAllowed", "productionUpdateAllowed", "transmitted",
         "productionReady", "entryAllowed")
STATE_NAMES = ("RISE_STOP", "RISE", "SHARP_RISE", "PULLBACK", "RANGE", "REBOUND",
               "SHARP_DROP", "DROP", "DROP_STOP")


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                   separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def code_hash() -> str:
    h = hashlib.sha256()
    for p in sorted((ROOT / "src").rglob("*.py")) + sorted((ROOT / "tools").glob("*.py")):
        h.update(str(p.relative_to(ROOT)).encode() + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest()


def configuration_hash() -> str:
    return digest({name:json.loads((ROOT/name).read_text(encoding="utf8"))
                   for name in ("V2_PARAM_PROPOSAL.json","LABEL_CONTRACT.json","QUALITY_TARGETS.json")})


def utc_aware(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise V2Error("TIMEZONE_REQUIRED")
    return value


def safe_flags(obj: dict[str, Any]) -> None:
    if any(obj.get(k) is not False for k in FLAGS):
        raise V2Error("SAFETY_FLAG_TRUE_OR_MISSING")


def forbid_outcomes(value: Any) -> None:
    if isinstance(value, dict):
        for k, v in value.items():
            token = str(k).lower()
            if token == "conditionalonoutcomeknown" and v is True:
                continue
            if any(x in token for x in ("label", "outcome", "future", "current_day", "today_ohlc", "today_state")):
                raise V2Error("OUTCOME_IN_FORECAST_INPUT")
            forbid_outcomes(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            forbid_outcomes(v)


@dataclass(frozen=True)
class Identity:
    canonical_symbol: str
    rss_symbol: str
    market: str
    effective_session: date
    security_kind: str
    lot: int
    rule_version: str
    domestic: bool = True
    cash: bool = True

    def eligible(self, session: date) -> bool:
        if not re.fullmatch(r"[0-9A-Z]{4}", self.canonical_symbol):
            raise V2Error("INVALID_CANONICAL_SYMBOL")
        if self.effective_session != session or not self.rule_version or not self.rss_symbol:
            raise V2Error("DATED_MASTER_IDENTITY_MISMATCH")
        return (self.market in {"PRIME", "STANDARD", "GROWTH"}
                and self.security_kind == "COMMON_STOCK" and self.lot == 100
                and self.domestic and self.cash)


@dataclass(frozen=True)
class SourceEvidence:
    source_id: str
    source_sha256: str
    source_version: str
    source_record_id: str
    event_at: datetime
    published_at: datetime
    available_at: datetime
    captured_at: datetime
    effective_session: date
    units: str
    raw_or_adjusted: str
    transformation_version: str
    original_ordinal: int
    lookback_sessions: int
    source_contract_hash: str
    known_at_evidence_kind: str
    missing_reason: str | None
    historical_live_parity_status: str

    def validate(self, cutoff: datetime, *, basis: str | None = None) -> None:
        for t in (self.event_at, self.published_at, self.available_at, self.captured_at, cutoff):
            utc_aware(t)
        if self.available_at > cutoff or self.published_at > self.available_at:
            raise V2Error("SOURCE_NOT_KNOWN_AT_CUTOFF")
        if self.event_at > self.available_at:
            raise V2Error("SOURCE_EVENT_IN_FUTURE")
        if basis and self.raw_or_adjusted != basis:
            raise V2Error("PRICE_BASIS_MISMATCH")
        if not all((self.source_id, self.source_version, self.source_record_id,
                    self.transformation_version, self.historical_live_parity_status)):
            raise V2Error("INCOMPLETE_SOURCE_PROVENANCE")
        for h in (self.source_sha256, self.source_contract_hash):
            if not re.fullmatch(r"[0-9a-f]{64}", h):
                raise V2Error("INVALID_SOURCE_HASH")
        if self.original_ordinal < 0 or self.lookback_sessions < 0:
            raise V2Error("INVALID_SOURCE_ORDINAL_OR_LOOKBACK")
        if self.known_at_evidence_kind not in {"OBSERVED_RECEIPT", "SCHEDULE_ASSUMED", "SYNTHETIC"}:
            raise V2Error("UNKNOWN_KNOWN_AT_EVIDENCE")

    def public_metadata(self) -> dict[str, Any]:
        return {"source_id": self.source_id, "source_sha256": self.source_sha256,
                "available_at": self.available_at.isoformat(),
                "captured_at": self.captured_at.isoformat(),
                "known_at_evidence_kind": self.known_at_evidence_kind}


@dataclass(frozen=True)
class Candle:
    session: date
    open: Fraction | None
    high: Fraction | None
    low: Fraction | None
    close: Fraction | None
    volume: Fraction | None = None
    turnover: Fraction | None = None
    basis: str = "RAW"
    comparable_suffix: str = "SYNTHETIC_RAW"
    status: str = "TRADED"
    units: tuple[str, str, str] = ("JPY", "SHARES", "JPY")

    @classmethod
    def from_values(cls, session: date, o: object, h: object, l: object, c: object,
                    vo: object = None, va: object = None, **kwargs: Any) -> Candle:
        v = [None if x is None else rational(x) for x in (o, h, l, c, vo, va)]
        row = cls(session, v[0], v[1], v[2], v[3], v[4], v[5], **kwargs)
        row.validate()
        return row

    def validate(self) -> None:
        xs = (self.open, self.high, self.low, self.close)
        if all(x is None for x in xs):
            if self.status not in {"NO_TRADE", "NO_VERIFIED_OPEN", "INCOMPLETE_SOURCE"}:
                raise V2Error("UNVERIFIED_NULL_OHLC")
            return
        if any(x is None for x in xs):
            raise V2Error("DATA_INTEGRITY_ERROR_PARTIAL_OHLC")
        if any(not isinstance(x, Fraction) or x <= 0 for x in xs):
            raise V2Error("DATA_INTEGRITY_ERROR_PRICE")
        o, h, l, c = xs
        assert o is not None and h is not None and l is not None and c is not None
        if h < max(o, c) or l > min(o, c) or h < l:
            raise V2Error("DATA_INTEGRITY_ERROR_OHLC_RANGE")
        for x in (self.volume, self.turnover):
            if x is not None and (not isinstance(x, Fraction) or x < 0):
                raise V2Error("DATA_INTEGRITY_ERROR_ACTIVITY")
        if self.status != "TRADED":
            raise V2Error("DATA_INTEGRITY_ERROR_STATUS")


@dataclass
class FeatureFrame:
    values: dict[str, float | None] = field(default_factory=dict)
    missing: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def put(self, name: str, value: Any, reason: str = "UNKNOWN_REQUIRED_HISTORY") -> None:
        import math
        if value is None:
            self.values[name] = None
            self.missing[name] = reason
        else:
            n = float(value)
            if not math.isfinite(n):
                raise V2Error("NONFINITE_FEATURE")
            self.values[name] = n
            self.missing.pop(name, None)

    def merge(self, other: FeatureFrame) -> None:
        if set(self.values) & set(other.values):
            raise V2Error("DUPLICATE_FEATURE")
        self.values.update(other.values)
        self.missing.update(other.missing)
        self.metadata.update(other.metadata)


def registry() -> dict[str, Any]:
    return json.loads((ROOT / "FEATURE_REGISTRY.json").read_text(encoding="utf-8"))


def feature_names() -> tuple[str, ...]:
    return tuple(r["name"] for r in registry()["columns"])


def validate_features(values: dict[str, Any]) -> None:
    import math
    if tuple(values) != feature_names():
        raise V2Error("FEATURE_SCHEMA_ORDER_OR_COLUMNS_DRIFT")
    for x in values.values():
        if x is not None and (isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x)):
            raise V2Error("INVALID_FEATURE_VALUE")


def bind_provenance(frame: FeatureFrame, sources: dict[str,tuple[SourceEvidence,...]],
                    cutoff: datetime) -> FeatureFrame:
    """Require dependency evidence for every known value before store/forecast."""
    if set(sources)!=set(frame.values):
        raise V2Error("FEATURE_DEPENDENCY_PROVENANCE_INCOMPLETE")
    metadata={}
    for name,value in frame.values.items():
        dependencies=sources[name]
        if value is not None and not dependencies:
            raise V2Error("KNOWN_FEATURE_WITHOUT_SOURCE_EVIDENCE")
        for source in dependencies:source.validate(cutoff)
        metadata[name]={"available_at":max(s.available_at for s in dependencies).isoformat() if dependencies else None,
                        "sources":[{k:(v.isoformat() if isinstance(v,(datetime,date)) else v)
                                    for k,v in vars(s).items()} for s in dependencies],
                        "missing_reason":frame.missing.get(name)}
    frame.metadata["column_provenance"]=metadata
    return frame
