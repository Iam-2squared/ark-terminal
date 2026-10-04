"""One recovery of existing Development cache. No network/provider/model calls.

Only date-authorized wrapper bodies are opened. Archive key never leaves the
existing Actions secret environment. Private output contains actual source rows.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile

def sha(x):
    return hashlib.sha256(x if isinstance(x,bytes) else str(x).encode()).hexdigest()

def pages(raw, day, kind, expected):
    assert sha(raw)==expected, 'PINNED_WRAPPER_HASH'
    wrapper=json.loads(raw)
    assert isinstance(wrapper,list) and wrapper
    cursor=None
    rows=[]
    receipts=[]
    keys=set()
    for index,page in enumerate(wrapper,1):
        assert page['page']==index
        req=page['request']
        assert req['endpoint']==('/v2/equities/bars/minute' if kind=='minute' else '/v2/equities/bars/daily')
        assert set(req['params']) <= {'date','pagination_key'}
        assert req['params']['date']==day and req['params'].get('pagination_key')==cursor
        assert sha(page['responseText'])==page['responseSha256']
        body=json.loads(page['responseText'],parse_float=str,parse_int=str)
        for i,row in enumerate(body['data']):
            assert row['Date']==day
            key=(row['Code'],row.get('Time'))
            assert key not in keys,'DUPLICATE_RAW_IDENTITY'
            keys.add(key)
            rows.append((row,{'wrapper_sha256':expected,'response_sha256':page['responseSha256'],
                             'row_ordinal':i,'acquired_at':page['acquiredAt']}))
        cursor=body.get('pagination_key') or None
        assert (cursor is None)==(index==len(wrapper)), 'PAGINATION_INCOMPLETE'
        receipts.append({'page':index,'response_sha256':page['responseSha256'],'rows':len(body['data'])})
    return rows,receipts

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--archives',required=True)
    ap.add_argument('--out',required=True)
    args=ap.parse_args()
    here=Path(__file__).resolve().parent
    root=here.parents[1]
    scope=json.loads((here/'SOURCE_RECOVERY_SCOPE.json').read_text())
    allowed=set(scope['source_dates_authorized'])
    split=json.loads((root/'docs/evidence/phase57-behavior-expansion-v1/04_session_split_manifest.json').read_text())
    assert not allowed&set(split['commonHoldout'])
    assert allowed<=set(split['intradayDevelopment'])|set(split['dailyDevelopment'])
    symbols=set(scope['symbol_sha256'])
    identity={(day,scope['symbol_sha256'][i]) for day,indices in scope['entry_pair_symbol_indices'].items() for i in indices}
    ledger=json.loads((root/'docs/evidence/phase57-entry-pattern-v2/ci-result/substrate/source-ledger.json').read_text())
    pins={(r['session'],r['kind']):r['sha256'] for r in ledger}
    archives=sorted(Path(args.archives).rglob('*.tar.gz.enc'))
    assert archives and os.environ.get('JQUANTS_API_KEY')
    def one(archive):
        expected=archive.with_name(archive.name+'.sha256').read_text().strip()
        expected=(json.loads(expected) if expected.startswith('"') else expected).split()[0]
        assert sha(archive.read_bytes())==expected
        proc=subprocess.Popen(['openssl','enc','-d','-aes-256-cbc','-pbkdf2','-iter','200000',
            '-pass','env:JQUANTS_API_KEY','-in',str(archive)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        records={}
        digests={}
        opened=[]
        try:
            with tarfile.open(fileobj=proc.stdout,mode='r|gz') as tar:
                for member in tar:
                    kind={'minute-pages.json':'minute','daily-pages.json':'daily'}.get(Path(member.name).name)
                    day=next((s for s in Path(member.name).parts if len(s)==10 and s[4:5]=='-' and s[7:8]=='-'),None)
                    if not member.isfile() or not kind or day not in allowed:continue
                    raw=tar.extractfile(member).read()
                    rows,receipt=pages(raw,day,kind,pins[day,kind])
                    source={'wrapper_sha256':sha(raw),'terminal_pagination_proven':True,
                            'date_scope_complete':True,'provider':'JQUANTS_V2_EQUITIES_BARS_'+kind.upper(),
                            'historical_actual_arrival':'UNKNOWN','assumed_available_at':day+'T16:30:00+09:00'}
                    opened.append({'session':day,'kind':kind,'wrapper_sha256':sha(raw),'pages':receipt})
                    codehash={}
                    for row,lineage in rows:
                        code=row['Code']
                        h=codehash.setdefault(code,sha(code))
                        if h not in symbols:continue
                        rec=records.setdefault((day,code),{'session':day,'symbol':code,'daily':None,'active_windows':set(),'market':[]})
                        if kind=='daily':
                            rec['daily']={'Va':row.get('Va'),'Vo':row.get('Vo'),'lineage':lineage}
                        else:
                            h,m=map(int,row['Time'].split(':'))
                            minute=h*60+m
                            # TSE continuous trading: 09:00-11:30,12:30-15:25;65 five-minute windows.
                            regular=540<=minute<690 or 750<=minute<925
                            valid=all(row.get(k) is not None and Decimal(row[k]).is_finite() and Decimal(row[k])>0 for k in ('O','H','L','C','Vo'))
                            if regular and valid:rec['active_windows'].add(minute//5)
                            if (day,sha(code)) in identity and (regular or minute==930):
                                rec['market'].append({'minute':minute,**{k:row.get(k) for k in ('O','H','L','C','Vo','Va')},'lineage':lineage})
                        rec[kind+'_source']=source
                    # Daily-present symbols with no minute rows still have a proven zero active coverage.
                    digests[day,kind]=source
            assert proc.wait()==0,'DECRYPT_FAILED'
        finally:
            if proc.poll() is None:proc.terminate()
            proc.stdout.close()
        for rec in records.values():
            for kind in ('minute','daily'):
                if (rec['session'],kind) in digests:rec[kind+'_source']=digests[rec['session'],kind]
            rec['active_windows']=sorted(rec['active_windows'])
            rec['market'].sort(key=lambda r:r['minute'])
        return records,{'archive_sha256':expected,'opened_members':opened}
    all_records={}
    all_sources={}
    receipts=[]
    # Pool limits memory while original date caches are parsed; no estimator work.
    with ThreadPoolExecutor(max_workers=2) as pool:
        for records,receipt in pool.map(one,archives):
            receipts.append(receipt)
            for key,rec in records.items():
                if key in all_records:assert all_records[key]==rec,'CACHE_CONFLICT'
                all_records[key]=rec
                for k in ('minute_source','daily_source'):
                    if k in rec:all_sources[(rec['session'],k)]=rec[k]
    for rec in all_records.values():
        for k in ('minute_source','daily_source'):
            if (rec['session'],k) in all_sources:rec[k]=all_sources[rec['session'],k]
    out=Path(args.out)
    out.mkdir(parents=True,exist_ok=True)
    data=gzip.compress((json.dumps(list(all_records.values()),sort_keys=True,separators=(',',':'))+'\n').encode(),mtime=0)
    (out/'SAVED_SOURCE_PRIVATE.json.gz').write_bytes(data)
    report={'status':'EXISTING_DEVELOPMENT_SOURCE_RECOVERED','scope_sha256':sha((here/'SOURCE_RECOVERY_SCOPE.json').read_bytes()),
            'private_sha256':sha(data),'bytes':len(data),'records_N':len(all_records),
            'source_dates_N':len({r['session'] for r in all_records.values()}),'archives':receipts,
            'new_market_data':0,'provider_requests':0,'protected_member_bodies_opened':0,
            'other_member_bodies_opened':0,'fits':0,'orders':0,'executionAllowed':False,'productionReady':False}
    (out/'SAVED_SOURCE_RECEIPT.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='archives'}))

if __name__=='__main__':main()
