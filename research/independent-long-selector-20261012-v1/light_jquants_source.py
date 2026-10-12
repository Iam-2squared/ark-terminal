"""Read-only J-Quants E source adapters: daily/master/valuation/finance/index.

Historical future-restated fields are never treated as contemporaneously known.
No implicit claim that a GitHub upload timestamp is historical market knownAt.
"""
from __future__ import annotations

import csv
import gzip
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

JST=timezone(timedelta(hours=9))
REQUIRED_RAW_DAILY=("Date","Code","O","H","L","C","Vo","Va")
DAILY_SOURCE_BASIS="HISTORICAL_PREVIOUS_SESSION_CONFIRMED_CLOSE_NOT_RECEIVE_TIME"
NONDAILY_SOURCE_BASIS="PROVIDER_PUBLICATION_KNOWN_AT_REQUIRED"
MISSING="UNAVAILABLE"

class LightSourceError(ValueError):
    pass


def _number(value: Any, *, strictly_positive: bool) -> float:
    if value is None or value == "":
        raise LightSourceError("MISSING_NUMERIC_SOURCE_FIELD")
    try:
        result=float(value)
    except (TypeError,ValueError) as exc:
        raise LightSourceError("BAD_NUMERIC_SOURCE_FIELD") from exc
    if not math.isfinite(result) or (
        strictly_positive and result <= 0
    ) or (not strictly_positive and result < 0):
        raise LightSourceError("NONFINITE_OR_ILLEGAL_SOURCE_VALUE")
    return result


def iter_unadjusted_daily_native(path: str | Path) -> Iterator[dict[str,Any]]:
    """Consume exact E DAILY original, subject to calling SHA-256 verification.

    Ignore Adj* columns: retroactive adjustment could encode future splits.
    Availability tag means earlier-session market close, not verified receipt.
    """
    prev:tuple[str,str]|None=None
    with gzip.open(path,"rt",newline="",encoding="utf-8") as f:
        reader=csv.DictReader(f)
        if not reader.fieldnames or not set(REQUIRED_RAW_DAILY).issubset(reader.fieldnames):
            raise LightSourceError("JQUANTS_E_DAILY_SCHEMA_NOT_VERIFIED")
        for row in reader:
            date,code=row["Date"],row["Code"]
            key=date,code
            if prev is not None and key<=prev:
                raise LightSourceError("NONCANONICAL_NATIVE_DAILY_ORDER")
            prev=key
            try:
                d=datetime.strptime(date,"%Y-%m-%d").replace(tzinfo=JST)
            except ValueError as exc:
                raise LightSourceError("INVALID_DAILY_DATE") from exc
            o,h,l,c=(_number(row[f],strictly_positive=True)
                       for f in ("O","H","L","C"))
            if not l<=min(o,c)<=max(o,c)<=h:
                raise LightSourceError("INVALID_DAILY_OHLC")
            volume=_number(row["Vo"],strictly_positive=False)
            turnover=_number(row["Va"],strictly_positive=False)
            # Must not enter current session decision. End of previous session
            # close is known after close but vendor arrival is not certified.
            known_next_day=(d+timedelta(days=1)).isoformat()
            yield {
                "session":date,"symbol":str(code),
                "availableAt":known_next_day,
                "sourceAvailabilityBasis":DAILY_SOURCE_BASIS,
                "historicalActualReceiveTimeVerified":False,
                "open":o,"high":h,"low":l,"close":c,
                "volume":volume,"turnover":turnover,
                "priceBasis":"RAW_UNADJUSTED",
                "futureAdjustedFieldsIgnored":True,
            }


def exact_asof_numeric_fields(
    row:dict[str,Any], *,
    fieldmap:dict[str,str],
    publication_at:str|None,
    decision_at:str,
    provenance:dict[str,Any],
) -> tuple[dict[str,dict],dict[str,str]]:
    """Admission for valuation, earnings, financial, investor, market extras.

    Source file Date alone isn't historical publish time. Fins summary must use
    its actual disclosed timestamp or equivalent verified publication evidence.
    Uncertified availability yields UNKNOWN for every requested feature.
    """
    features={}
    missing={}
    if publication_at is None or provenance.get("pitPublicationVerified") is not True:
        return ({}, {target:"UNKNOWN_PUBLICATION_TIME" for target in fieldmap})
    try:
        pub=datetime.fromisoformat(publication_at)
        now=datetime.fromisoformat(decision_at)
    except ValueError as exc:
        raise LightSourceError("INVALID_PUBLICATION_TIMESTAMP") from exc
    if not pub.tzinfo or not now.tzinfo or pub.utcoffset()!=timedelta(hours=9):
        raise LightSourceError("JST_PUBLICATION_REQUIRED")
    if pub>now:
        return ({}, {target:"NOT_YET_PUBLIC_AT_DECISION" for target in fieldmap})
    for name,source_col in fieldmap.items():
        value=row.get(source_col)
        if value in ("",None):
            missing[name]="SOURCE_FIELD_MISSING"
            continue
        try:
            v=float(value)
        except (TypeError,ValueError):
            missing[name]="NONNUMERIC_SOURCE_FIELD"
            continue
        if not math.isfinite(v):
            missing[name]="NONFINITE_SOURCE_FIELD"
            continue
        features[name]={"value":v,
                        "availableAt":publication_at,
                        "pitVerified":True,
                        "dataset":provenance.get("dataset"),
                        "sourceKey":provenance.get("sourceObjectKey")}
    return features,missing
