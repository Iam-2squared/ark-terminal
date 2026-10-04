"""Verify the funded empty window in saved raw and original provider tokens."""
from pathlib import Path
from datetime import datetime,timedelta,timezone
import gzip,hashlib,json,sys

def main():
    root=Path(sys.argv[1]);out=root/'long_mtm_private'
    blocks=json.loads((out/'FUNDED_BLOCKERS_PRIVATE.json').read_text())
    read=lambda p:json.loads(gzip.open(root/p,'rt').read())
    primary=read('eod_private/primary/raw_paths.json.gz')
    independent=read('eod_private/independent/raw_paths.json.gz')
    tokens=read('eod_private/primary/source_tokens.json.gz')
    unique={b['blocker']['entry_id']:b['blocker'] for b in blocks if b['blocker']}
    audits=[]
    for key,block in unique.items():
        clock=datetime.fromisoformat(block['timestamp']);grid=60*clock.hour+clock.minute
        a=[r for r in primary[key]['today'] if grid-5<=int(r[0])<grid]
        b=[r for r in independent[key]['today'] if grid-5<=int(r[0])<grid]
        original=tokens[key]['current_prefix']
        minutes=[int(r['Time'][:2])*60+int(r['Time'][3:5]) for r in original]
        selected=[r for r,m in zip(original,minutes) if grid-5<=m<grid]
        covered=bool(minutes and min(minutes)<=grid-5 and max(minutes)>=grid-1)
        audits.append({'affected_arms_N':sum(x['blocker'] and x['blocker']['entry_id']==key for x in blocks),
          'primary_window_rows_N':len(a),'independent_window_rows_N':len(b),
          'original_provider_token_window_rows_N':len(selected),
          'primary_independent_window_mismatch_N':int(a!=b),
          'window_within_saved_original_prefix_time_range':covered,
          'original_prefix_rows_N':len(original),
          'original_prefix_canonical_sha256':hashlib.sha256(json.dumps(original,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
          'classification':'SOURCE_WINDOW_EMPTY_UNKNOWN_NO_TRADE_OR_CAPTURE_GAP',
          'true_market_no_trade_certified':False,'new_source_rows_recovered_N':0})
    status='PASS' if all(x['primary_window_rows_N']==x['independent_window_rows_N']==x['original_provider_token_window_rows_N']==0 and x['window_within_saved_original_prefix_time_range'] for x in audits) else 'FAIL'
    result={'jst':datetime.now(timezone(timedelta(hours=9))).isoformat(),'status':status,
            'distinct_funded_blockers_N':len(unique),'audits':audits,
            'provider_requests':0,'new_market_data':0,'price_imputation_N':0,
            'candidate_exclusions_N':0,'empty_window_contract_relaxed':False}
    (out/'BLOCKED_SOURCE_AUDIT.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    if status!='PASS':raise SystemExit(2)

if __name__=='__main__':main()
