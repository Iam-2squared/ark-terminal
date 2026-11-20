"""Exactly one verification campaign with frozen inputs; no performance selection."""
from io_utils import *
from campaign import inputs,plans,run_path

def main():
    dest=PRI/'reproduction';assert not (dest/'CAMPAIGN_STARTED.json').exists(),'one reproduction campaign only'
    save(dest/'CAMPAIGN_STARTED.json',{'campaign_N':1,'purpose':'BYTE_HASH_REPRODUCTION_ONLY','new_policy_N':0,'code_hash':pin(ROOT/'portfolio.py'),'spec_hash':pin(PUB/'WORK_SPEC.json')})
    stream,books,table,split,cache=inputs();ep=plans(books,cache)
    windows={r['window_id']:r['sessions'] for r in json.loads((ROOT/'inputs/S6_COVERAGE_AND_WINDOWS.json').read_text())['windows'] if r['coverage_complete']};windows['CHAIN38']=split['OOF38']
    compared=[];errors=[]
    for w,ss in windows.items():
        for arm in ['C','E']:
            original=PRI/'runs'/w/arm
            if not (original/'RESULT.json').exists():continue
            run_path(w,arm,ss,stream,books,table,ep,outroot=dest/'paths',stage='reproduction')
            new=dest/'paths'/w/arm
            for name in ['DECISIONS.jsonl.gz','TRADES.jsonl.gz','CURVE.jsonl.gz','INTENTS.jsonl.gz']:
                a=pin(original/name);b=pin(new/name);same=(original/name).read_bytes()==(new/name).read_bytes();compared.append({'window_id':w,'arm':arm,'payload':name,'official':a,'reproduction':b,'byte_hash_exact':same})
                if not same:errors.append({'window_id':w,'arm':arm,'payload':name})
            a=json.loads((original/'RESULT.json').read_bytes());b=json.loads((new/'RESULT.json').read_bytes())
            # Stage is verification receipt metadata, not the deterministic portfolio payload.
            a.pop('stage');b.pop('stage');save(new/'DETERMINISTIC_RESULT.json',b)
            ab=(json.dumps(a,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n').encode();bb=(json.dumps(b,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n').encode();same=ab==bb
            compared.append({'window_id':w,'arm':arm,'payload':'RESULT deterministic excludes stage receipt only','official_sha256':hashlib.sha256(ab).hexdigest(),'reproduction_sha256':hashlib.sha256(bb).hexdigest(),'byte_hash_exact':same})
            if not same:errors.append({'window_id':w,'arm':arm,'payload':'RESULT'})
            print(json.dumps({'reproduction_window':w,'arm':arm,'byte_hash_exact':not any(e['window_id']==w and e['arm']==arm for e in errors)}),flush=True)
    out={'status':'PASS' if not errors else 'FAIL','campaign_N':1,'path_N':len(compared)//5,'deterministic_payload_N':len(compared),'all_bytes_hashes_match':not errors,'errors':errors,'payloads':compared,'metadata_excluded':['formal/reproduction stage label','creation/commit/GET receipts are separate files'],'code_hash':pin(ROOT/'portfolio.py'),'spec_hash':pin(PUB/'WORK_SPEC.json'),'input_hashes':{n:pin(ROOT/'inputs/v5'/n) for n in ['candidate_stream','books','arrival','split']},'market_State_cache_hash':pin(PRI/'immutable/STATE_PREFIX_CACHE.jsonl.gz'),'policy_search_N':0}
    save(PUB/'REPRODUCTION_RECEIPT.json',out);save(dest/'COMPLETE.json',out)
    assert not errors,errors
if __name__=='__main__':main()
