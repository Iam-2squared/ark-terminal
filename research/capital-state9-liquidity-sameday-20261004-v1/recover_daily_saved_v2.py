"""Existing encrypted raw archive recovery only. No provider or estimator calls.

The key stays in its existing configured Actions env and is used only by openssl.
Only prior-date daily Va/Vo columns are exported as a PRIVATE Actions artifact.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile

def sha(b):return hashlib.sha256(b).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--archives',required=True);ap.add_argument('--grid',required=True)
    ap.add_argument('--out',required=True)
    args=ap.parse_args();root=Path(__file__).resolve().parents[2];here=Path(__file__).resolve().parent
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    scope=json.loads((here/'DAILY_RECOVERY_SCOPE_SAFE_V2.json').read_text())
    all_required=set(scope['required_prior_dates']);wanted_dates=set(scope['source_dates_authorized']);target_dates=set(scope['entry_cohort_dates'])
    split=json.loads((root/'docs/evidence/phase57-behavior-expansion-v1/04_session_split_manifest.json').read_text())
    assert not wanted_dates&set(split['commonHoldout']), 'PROTECTED_DATE'
    assert wanted_dates <= set(split['intradayDevelopment'])|set(split['dailyDevelopment']), 'NON_DEVELOPMENT_DATE'
    gridbytes=Path(args.grid).read_bytes()
    assert sha(gridbytes)=='54f7dbb8bd0c9f8974ccccb7a949c0b7ebf0bbe46581be7778f1607f9d9d8cb6'
    # This manifest is existing exposed Development; identity fields only, no model/label replay.
    symbols={r['opportunity'].split('|')[1] for r in json.loads(gridbytes) if r['session'] in target_dates}
    ledger=json.loads((root/'docs/evidence/phase57-entry-pattern-v2/ci-result/substrate/source-ledger.json').read_text())
    pins={(r['session'],r['kind']):r['sha256'] for r in ledger}
    if not os.environ.get('JQUANTS_API_KEY'):raise RuntimeError('CONFIGURED_ARCHIVE_KEY_UNAVAILABLE')
    archives=sorted(Path(args.archives).rglob('*.tar.gz.enc'))
    assert archives,'NO_EXISTING_ARCHIVES'
    def one(archive):
        text=archive.with_name(archive.name+'.sha256').read_text().strip()
        expected=(json.loads(text) if text.startswith(chr(34)) else text).split()[0]
        assert sha(archive.read_bytes())==expected,'ENCRYPTED_HASH'
        rows=[];receipts=[]
        proc=subprocess.Popen(['openssl','enc','-d','-aes-256-cbc','-pbkdf2','-iter','200000',
                               '-pass','env:JQUANTS_API_KEY','-in',str(archive)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            with tarfile.open(fileobj=proc.stdout,mode='r|gz') as tar:
                for member in tar:
                    if not member.isfile() or Path(member.name).name!='daily-pages.json':continue
                    day=next((x for x in Path(member.name).parts if len(x)==10 and x[4:5]=='-' and x[7:8]=='-'),None)
                    # Unapproved member bodies are not opened, even if headers exist in the archive.
                    if day not in wanted_dates:continue
                    b=tar.extractfile(member).read();digest=sha(b)
                    assert digest==pins[day,'daily'],'PINNED_DAILY_WRAPPER_HASH'
                    n=0
                    for page in json.loads(b):
                        response=page['responseText'];assert sha(response.encode())==page['responseSha256'],'RESPONSE_HASH'
                        for i,r in enumerate(json.loads(response,parse_float=str,parse_int=str)['data']):
                            assert r['Date']==day,'WRONG_DATE'
                            if r['Code'] not in symbols:continue
                            rows.append({'Date':day,'Code':r['Code'],'Va':r.get('Va'),'Vo':r.get('Vo'),
                                         'known_session':day,'assumed_available_at':day+'T16:30:00+09:00',
                                         'historical_actual_arrival':'UNKNOWN','source_provider':'EXISTING_JQUANTS_DAILY_CACHE',
                                         '_source':{'wrapper_SHA256':digest,'response_SHA256':page['responseSha256'],'row_ordinal':i}})
                            n+=1
                    receipts.append({'date':day,'wrapper_sha256':digest,'selected_Va_Vo_rows':n})
            assert proc.wait()==0,'EXISTING_ARCHIVE_DECRYPT_FAILED'
        finally:
            if proc.poll() is None:proc.terminate()
            proc.stdout.close()
        return rows,{'archive_sha256':expected,'opened_daily_members':receipts}
    indexed={};receipts=[];conflicts=0
    with ThreadPoolExecutor(max_workers=4) as pool:
        for rows,receipt in pool.map(one,archives):
            receipts.append(receipt)
            for r in rows:
                key=(r['Date'],r['Code'])
                if key in indexed:
                    assert indexed[key]==r,'SAVED_SOURCE_CONTRADICTION'
                indexed[key]=r
    missing=sorted(all_required-{r['Date'] for r in indexed.values()})
    payload=gzip.compress((json.dumps(list(indexed.values()),sort_keys=True,separators=(',',':'))+'\n').encode(),mtime=0)
    (out/'PRIOR_DAILY_VA_VO_PRIVATE.json.gz').write_bytes(payload)
    receipt={'status':'EXISTING_DAILY_SOURCE_RECOVERY_COMPLETE' if not missing else 'EXISTING_DAILY_SOURCE_RECOVERY_PARTIAL',
             'archives':len(archives),'prior_dates_required':len(all_required),'source_dates_recovered':len({r['Date'] for r in indexed.values()}),
             'prior_dates_missing':missing,'source_symbol_superset_N':len(symbols),'source_rows_exported':len(indexed),
             'scope':'Existing exposed frozen-watch symbol superset, daily prior dates only; local adapter must restrict to exact current1600 symbols/pairs.',
             'exported_fields':['Date','Code','Va','Vo','source lineage','known-at assumption'],
             'no_current_entry_day_volume_input':True,'provider_requests':0,'new_market_downloads':0,
             'protected_member_bodies_opened':0,'new_fits':0,'entry_exit_replays':0,'orders':0,
             'private_sha256':sha(payload),'private_bytes':len(payload),'archive_receipts':receipts}
    (out/'DAILY_SOURCE_RECOVERY_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k not in ['archive_receipts','prior_dates_missing']}))

if __name__=='__main__':main()
