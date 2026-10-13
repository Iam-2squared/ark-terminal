#!/usr/bin/env python3
"""Offline-only H2/H3/H5 BUY_INTENT *research* score from a private model file.

Never calls a broker, Excel, the network or a frozen strategy runtime.
Refuses any model claiming production eligibility or any input with labels,
fills, P&L, future prices or other post-decision information.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True

ALLOWED_MODE = "OFFLINE_RESEARCH_ONLY"
MODEL_SCHEMA = "ARK_NO11_BUY_INTENT_CAUSAL_CANDIDATE_DEV_MODEL_V1"
FEATURE_SCHEMA = "ARK_NO11_ASOF_RESEARCH_FEATURE_ROW_V1"
LABEL_BLOCKLIST = (
    "potential_return", "realized_net_return", "future_high", "future_low",
    "teacher", "label", "exit", "fill_price", "fill_minute", "sell_price",
    "actual_buy", "actual_sell", "broker_order",
)
RECEIPT_SCHEMA = "ARK_NO11_ASOF_RESEARCH_OFFLINE_SCORE_V1"


def check(ok, code):
    if not ok:
        raise ValueError(code)


def read_json(p):
    check(p.is_file() and not p.is_symlink(), "NO11_RESEARCH_SCORE_FILE_MISSING_OR_SYMLINK")
    b = p.read_bytes()
    check(0 < len(b) <= 1_000_000, "NO11_RESEARCH_SCORE_FILE_TOO_LARGE")
    obj = json.loads(b)
    check(isinstance(obj, dict), "NO11_RESEARCH_SCORE_JSON_NOT_OBJECT")
    return b, obj


def score(model, row):
    check(model.get("schemaId") == MODEL_SCHEMA and
          model.get("head") in ("H2","H3","H5") and
          model.get("feature_input_asof") == "BUY_INTENT_WITH_ASSUMED_BAR_AVAILABILITY" and
          model.get("training_label") == "LEGACY_POST_FILL_POTENTIAL_2025" and
          model.get("trained_on_2026_rss_rows") == 0 and
          model.get("historical_actual_known_at") == "UNKNOWN" and
          model.get("frozen_no11_model_modified") is False and
          model.get("model_production_eligible") is False and
          model.get("productionReady") is False and
          model.get("orderTransmission") is False,
          "NO11_RESEARCH_MODEL_UNAPPROVED_OR_UNEXPECTED")
    check(row.get("schemaId") == FEATURE_SCHEMA and
          row.get("mode") == ALLOWED_MODE and
          row.get("featureTime") == "BUY_INTENT" and
          row.get("pointInTimeCertified") is False and
          row.get("productionReady") is False and
          row.get("orderTransmission") is False,
          "NO11_RESEARCH_FEATURES_NOT_OFFLINE")
    # Do not accept arbitrary extra fields. In particular, refuse future labels.
    check(set(row)=={
        "schemaId","mode","featureTime","pointInTimeCertified",
        "numeric","categorical","productionReady","orderTransmission"
    }, "NO11_RESEARCH_INPUT_ENVELOPE_NOT_ALLOWLIST")
    payload=json.dumps(row,sort_keys=True)
    check(not any(p in payload.lower() for p in LABEL_BLOCKLIST),
          "NO11_RESEARCH_FUTURE_FIELD_FORBIDDEN")
    pp=model.get("preprocessing")
    check(isinstance(pp,dict) and isinstance(row["numeric"],dict)
          and isinstance(row["categorical"],dict),
          "NO11_RESEARCH_PREPROCESS_MISSING")
    num=pp.get("numeric_fields")
    cat=pp.get("categorical_fields")
    check(isinstance(num,list) and len(num)>0 and len(num)<=128 and
          isinstance(cat,list) and len(cat)<=128 and
          set(row["numeric"])==set(num) and
          set(row["categorical"])==set(cat),
          "NO11_RESEARCH_FEATURE_CONTRACT_MISMATCH")
    mean=pp.get("numeric_mean")
    scale=pp.get("numeric_scale")
    vocab=pp.get("categorical_train_vocab")
    check(isinstance(mean,list) and isinstance(scale,list) and
          len(mean)==len(scale)==2*len(num) and
          isinstance(vocab,dict) and set(vocab)==set(cat),
          "NO11_RESEARCH_PREPROCESS_DIMENSION_MISMATCH")
    nums=[]
    misses=[]
    for k in num:
        value=row["numeric"][k]
        check(value is None or
              (type(value) in (int,float) and math.isfinite(value)),
              "NO11_RESEARCH_FEATURE_NONFINITE")
        nums.append(float(value) if value is not None else 0.0)
        misses.append(float(value is None))
    vals=nums+misses
    x=[]
    for value,mn,std in zip(vals,mean,scale):
        check(type(mn) in (int,float) and math.isfinite(mn) and
              type(std) in (int,float) and math.isfinite(std) and std>0,
              "NO11_RESEARCH_PREPROCESS_NONFINITE")
        x.append((value-float(mn))/float(std))
    for k in cat:
        vc=vocab[k]
        check(isinstance(vc,list) and vc and "__UNKNOWN__" in vc and
              len(vc)==len(set(vc)) and all(type(v) is str for v in vc),
              "NO11_RESEARCH_CATEGORY_VOCAB_INVALID")
        value=row["categorical"][k]
        check(value is None or type(value) is str,
              "NO11_RESEARCH_CATEGORY_TYPE_INVALID")
        value=value if value in vc else "__UNKNOWN__"
        x.extend(float(value==v) for v in vc)
    coef=model.get("coef")
    intercept=model.get("intercept")
    check(isinstance(coef,list) and len(coef)==len(x) and
          type(intercept) in (int,float) and math.isfinite(intercept) and
          all(type(w) in (int,float) and math.isfinite(w) for w in coef),
          "NO11_RESEARCH_MODEL_DIMENSION_INVALID")
    logit=float(intercept) + math.fsum(float(w)*v for w,v in zip(coef,x))
    if logit >= 0:
        proba=1/(1+math.exp(-logit))
    else:
        a=math.exp(logit);proba=a/(1+a)
    check(math.isfinite(proba) and 0<=proba<=1,
          "NO11_RESEARCH_SCORE_NONFINITE")
    return proba


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode",required=True)
    p.add_argument("--model",type=Path,required=True)
    p.add_argument("--features",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    check(a.mode==ALLOWED_MODE, "NO11_RESEARCH_SCORE_MODE_NOT_ALLOWED")
    model_bytes,model=read_json(a.model)
    feature_bytes,feature=read_json(a.features)
    probability=score(model,feature)
    payload={
      "schemaId":RECEIPT_SCHEMA,
      "mode":ALLOWED_MODE,
      "head":model["head"],
      "research_probability":probability,
      "modelSha256":hashlib.sha256(model_bytes).hexdigest(),
      "featureSha256":hashlib.sha256(feature_bytes).hexdigest(),
      "2026NativeSelectorEntryRebuilt":False,
      "2026SupervisedTrainingRows":0,
      "brokerActualKnownAtCertified":False,
      "newModelAutomaticallyPromoted":False,
      "productionReady":False,
      "orderTransmission":False,
    }
    check(a.output.parent.is_dir() and not a.output.exists() and
          not a.output.is_symlink(), "NO11_RESEARCH_SCORE_OUTPUT_NOT_NEW")
    with a.output.open("x",encoding="utf8") as f:
        json.dump(payload,f,ensure_ascii=False,sort_keys=True,allow_nan=False)
        f.write("\n")
    print("NO11_ASOF_RESEARCH_OFFLINE_SCORE=PASS")
    print("NO11_ASOF_RESEARCH_HEAD="+model["head"])
    print("NO11_ASOF_RESEARCH_PROBABILITY="+format(probability,".12f"))
    print("NO11_ASOF_RESEARCH_NATIVE_PRODUCTION_READY=False")
    print("ORDER_TRANSMISSION=False")


if __name__=="__main__":
    try:
        main()
    except Exception as exc:
        print("NO11_ASOF_RESEARCH_OFFLINE_SCORE=BLOCKED:"+str(exc),file=sys.stderr)
        print("ORDER_TRANSMISSION=False",file=sys.stderr)
        sys.exit(2)
