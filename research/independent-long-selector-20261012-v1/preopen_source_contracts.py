"""Reviewed native field semantics. No data acquisition or entitlement inference."""
from __future__ import annotations

import re
from datetime import timedelta

from preopen_selector import PreopenError, day, stamp, rational

MASTER_SPEC = "https://jpx-jquants.com/ja/spec/eq-master"
TYPE_SPEC = "https://jpx-jquants.com/ja/help/data#普通株式と優先株式を判別する方法はありますか"
PRODUCT_SPEC = "https://jpx-jquants.com/ja/spec/eq-master/product-category"
LOT_SPEC = "https://www.jpx.co.jp/equities/improvements/unit/"
CLASS_VERSION = "DATED_JQUANTS_PRODUCT_MARKET_SECURITY_TYPE_V1"


def official_security_class(row, *, session):
    """Combine the dated product, market and documented security-type code.

    A suffix alone is never sufficient: ETFs, foreign issues, REITs and
    contribution certificates cannot enter via a superficially matching code.
    The dates are original master applicability dates, not today's universe.
    """
    if row.get("Date") != session:
        raise PreopenError("SECURITY_CLASS_WRONG_DATED_MASTER")
    code = row.get("Code", "")
    if not re.fullmatch(r"[0-9A-Z]{5}", code):
        raise PreopenError("SECURITY_CLASS_UNKNOWN_CANONICAL_CODE")
    if not row.get("ProdCat") or not row.get("Mkt"):
        raise PreopenError("SECURITY_CLASS_MISSING_PRODUCT_OR_MARKET")
    if session < "2018-10-01":
        raise PreopenError("HISTORICAL_LOT_BEFORE_UNIFICATION_UNVERIFIED")
    common = (row["ProdCat"] == "011" and row["Mkt"] in ("0111", "0112", "0113")
              and code[-1] == "0" and code not in ("83010", "84210"))
    return {"commonStock":common,"lotSize":100 if common else None,
            "classificationVersion":CLASS_VERSION,"basisFields":["Date","ProdCat","Mkt","Code"],
            "typeEvidence":TYPE_SPEC,"productEvidence":PRODUCT_SPEC,"lotEvidence":LOT_SPEC,
            "actualHistoricalReceiptVerified":False}


def native_available_at(row, source, *, calendar=None):
    """Conservative schedule assumptions remain distinct from actual receipts."""
    c = source.get("availabilityContract", {})
    if not c.get("evidenceReference") or not c.get("publicationTime"):
        raise PreopenError("NATIVE_PUBLICATION_TIME_EVIDENCE_REQUIRED:"+source["dataset"])
    event = row[source.get("dateField", "Date")]
    rule = c.get("dateRule", "CALENDAR_DAY_LAG")
    if rule == "NEXT_EXCHANGE_SESSION":
        if not calendar:
            raise PreopenError("AVAILABILITY_REQUIRES_EXCHANGE_CALENDAR")
        later = [d for d in calendar if d > event]
        if not later:
            raise PreopenError("NO_NEXT_EXCHANGE_SESSION_FOR_AVAILABILITY")
        event = later[0]
    elif rule == "CALENDAR_DAY_LAG":
        event = (day(event)+timedelta(days=c.get("dayLag", 0))).isoformat()
    else:
        raise PreopenError("UNKNOWN_NATIVE_AVAILABILITY_DATE_RULE")
    at = stamp(event+"T"+c["publicationTime"]+"+09:00")
    if source["dataset"] == "FIN_SUMMARY":
        at = max(at, stamp(row["DiscDate"]+"T"+row["DiscTime"]+"+09:00"))
    return at.isoformat()


def converted_native_value(value, units, *, output_unit=None):
    v = rational(value)
    conversions = {("MILLION_JPY","JPY"):1000000, ("THOUSAND_JPY","JPY"):1000,
                   ("RATIO","PERCENT"):100}
    if output_unit is None or output_unit == units:
        return float(v), units
    key = (units, output_unit)
    if key not in conversions:
        raise PreopenError("NATIVE_UNIT_CONVERSION_UNVERIFIED")
    return float(v*conversions[key]), output_unit
