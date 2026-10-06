"""Recover one incomplete training cache without fitting or changing predictions."""
import os
import pickle
import zlib
from sign_io import *

def main():
    signature="bb9827c1f8ad3e4c9cef365c4b8005c35891a6ef554b69ace4c799e2ff5b4d06"
    path=PRIVATE/"training_payloads"/(signature+".jsonl.gz")
    record=next(r for r in read(OUT/"FIT_LEDGER.json")["attempts"] if r["training_signature"]==signature)
    assert record["trial"]=="DISCOVERY_RAW_E_BLOCK_04"
    with (PRIVATE/"models"/(signature+".pkl")).open("rb") as f:artifact=pickle.load(f)
    original_hash=sha(path)
    before_model=sha(PRIVATE/"models"/(signature+".pkl"))
    before_predictions=sha(PRIVATE/"predictions"/(record["trial"]+".jsonl.gz"))
    snapshots={r["entry_id"]:r for r in rows(PRIVATE/"SNAPSHOTS.jsonl.gz")}
    signs={r["entry_id"]:r for r in rows(PRIVATE/"SIGN_TARGETS.jsonl.gz")}
    nn=artifact["preprocessing"]["numeric"];cc=artifact["preprocessing"]["categorical"]
    payload=[{"entry_id":k,"numeric":[snapshots[k]["numeric"][v] for v in nn],
        "categorical":[snapshots[k]["categorical"][v] for v in cc],
        "y_plus":signs[k]["y_plus"],"label_maturity":signs[k]["label_maturity"]} for k in artifact["fit_entry_ids"]]
    mathematical={"numeric":nn,"categorical":cc,"family":record["family"],"parameters":artifact["all_parameters"],
        "preprocessing":artifact["preprocessing"]["transform_version"],"sample_weight":None,"class_weight":None,
        "fit_cutoff":record["fit_cutoff"],"rows":payload}
    assert digest(mathematical)==signature==artifact["training_signature"]
    broken=path.read_bytes()
    stream=zlib.decompressobj(31);decoded=stream.decompress(broken).decode()
    prefix=[json.loads(line) for line in decoded.splitlines()[:-1]] if not decoded.endswith("\n") else [json.loads(line) for line in decoded.splitlines()]
    assert prefix==payload[:len(prefix)] and not stream.eof
    preserved=PRIVATE/"repair"/("TRUNCATED_"+path.name)
    preserved.write_bytes(broken)
    temp=path.with_name(path.name+".verified_tmp")
    gzsave(temp,payload)
    assert rows(temp)==payload
    os.replace(temp,path)
    assert before_model==sha(PRIVATE/"models"/(signature+".pkl")) and before_predictions==sha(PRIVATE/"predictions"/(record["trial"]+".jsonl.gz"))
    save(OUT/"TRAINING_CACHE_REPAIR.json",{"exact_jst":now(),"status":"RECOVERED_EXACT_MATHEMATICAL_SIGNATURE",
        "trial":record["trial"],"observed_error":"gzip missing end-of-stream marker",
        "original_corrupt_sha256":original_hash,"reconstructed_sha256":sha(path),
        "complete_original_prefix_rows_verified":len(prefix),"FIT_rows_recovered":len(payload),
        "training_signature_matches_original_claim_and_model":signature,
        "sources":"prefit hash-frozen SNAPSHOTS and SIGN_TARGETS; immutable model FIT entry IDs and parameters",
        "new_fits":0,"technical_fit_retries":0,"model_rewrites":0,"prediction_rewrites":0,
        "selection_lock_or_late_result_changes":0,"original_corrupt_file_preserved_private":True,
        "root_cause":"incomplete saved cache; exact storage overwrite/transfer mechanism not established"})
    print(canonical({"cache_signature_verified":True,"rows":len(payload),"preserved_prefix":len(prefix),"new_fits":0}))

if __name__=="__main__":main()
