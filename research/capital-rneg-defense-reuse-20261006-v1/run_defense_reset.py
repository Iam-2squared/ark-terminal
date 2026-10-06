"""One authorized candidate batch; original21 windows and saved Control reused."""
import sys
from collections import defaultdict
from decimal import Decimal as D
from rneg_io import *
sys.path.insert(0,str(REPO/'research/capital-v51-reset20-r5r10-20261006-v1'))
from reset20 import run_window, summarize
from defense_engine import make_engine, native

def main():
    assert read(OUT/'OOF_POLICY_ASOF_AUDIT.json')['status']=='PASS'
    assert read(OUT/'CAPITAL_CONNECTION_QUALIFICATION.json')['action_support']
    receipt=read(OUT/'POLICY_READBACK.json');assert receipt['verified']
    for name,h in receipt['snapshot_sha256'].items():assert sha(OUT/'policy_snapshots'/name)==h
    root=PRIVATE/'runs/V5_RNEG_DEFENSE_V1';root.mkdir(parents=True,exist_ok=True)
    assert not (root/'STARTED.json').exists(),'Formal batch already claimed; no result rescue or implicit repeat'
    stream=rows(SPECTRUM/'source/candidate_stream.jsonl.gz')
    books_path=DATA/'hl0/bigwinner_private/MARKET_EXECUTION_BOOK_V2.jsonl.gz'
    assert sha(books_path)=='ee7c88e19832439f615da54dc9df7e4a0307fdb1b2b5a18d3e1f60f71566736a'
    books={r['entry_id']:r for r in rows(books_path)}
    tables_path=REPO/'docs/evidence/capital-v5-max3-slot-intelligence-20261004-v1/ARRIVAL_TABLE.json'
    tables=read(tables_path);manifest=read(REPO/'docs/evidence/capital-v51-reset20-r5r10-20261006-v1/COVERAGE_AND_WINDOWS.json')
    control=read(REPO/'docs/evidence/capital-v51-reset20-r5r10-20261006-v1/V5_RESET20_RESULT.json')
    actions={r['entry_id']:r for r in rows(PRIVATE/'DEFENSE_ACTIONS.jsonl.gz')}
    def defense(r):
        assert r['entry_id'] in actions,'RNEG_INPUT_SCHEMA_MISSING'
        a=actions[r['entry_id']]
        assert a['session']==r['session'] and a['symbol']==r['symbol'] and a['block']==r['block']
        return a['action']
    engine=make_engine(defense);by_day=defaultdict(list)
    for r in stream:by_day[r['session']].append(r)
    first=min(by_day)
    compat=make_engine(lambda r:'PASS_TO_V5')(3,first,by_day[first],books,D('1000000'),True,native.PROFILE,tables=tables)
    for d in compat[1]:d.pop('defense_action',None)
    comparisons=[]
    for name,i in [('native_decisions',1),('native_trades',2),('native_curve',3)]:
        old=[r for r in rows(SPECTRUM/'source'/f'{name}.jsonl.gz') if r['session']==first]
        assert compat[i]==old,(name,'OFF_FIRST_DAY_INCOMPATIBLE')
        comparisons.append({'saved':name,'rows':len(old),'matches':True})
    save(OUT/'OFF_NATIVE_COMPATIBILITY.json',{'exact_jst':now(),'synthetic_tests':12,'saved_first_market_day':first,'market_diagnostic_days':1,'control_full_replays':0,'comparisons':comparisons,'status':'PASS'})
    save(OUT/'REPLAY_SOURCE_BINDING.json',{'books_hash':sha(books_path),'arrival_table_hash':sha(tables_path),
        'window_calendar_hash':sha(REPO/'docs/evidence/capital-v51-reset20-r5r10-20261006-v1/COVERAGE_AND_WINDOWS.json'),
        'native_V5_code_hashes':{p.name:sha(p) for p in V5.glob('*.py')},'wrapper_hash':sha(REPO/'research/capital-v51-reset20-r5r10-20261006-v1/reset20.py'),
        'control_saved_result_hash':sha(REPO/'docs/evidence/capital-v51-reset20-r5r10-20261006-v1/V5_RESET20_RESULT.json'),
        'candidate_code_hashes':{n:sha(CODE/n) for n in ['run_defense_reset.py','defense_engine.py']},'unchanged_runtime_fields':True})
    save(root/'STARTED.json',{'exact_jst':now(),'formal_batch':1,'candidate':'V5_RNEG_DEFENSE_V1','policy_snapshots_fixed_before_replay':True,'planned_window_N':21,'control_full_replays':0},exclusive=True)
    results=[]
    for w in manifest['windows']:
        result,ds,ts,cs,it=run_window(w,by_day,books,tables,engine,'V5_RNEG_DEFENSE_V1')
        dest=root/w['window_id']
        for name,data in [('DECISIONS',ds),('TRADES',ts),('CURVE',cs),('INTENTS',it)]:
            for row in data:row['window_id']=w['window_id']
            gzsave(dest/(name+'.jsonl.gz'),data,exclusive=True)
        save(dest/'COMPLETE.json',result,exclusive=True);results.append(result)
        print(w['window_id'],result['status'],result['final_cash_for_primary'],flush=True)
    save(OUT/'DEFENSE_RESET20_RESULT.json',{'exact_jst':now(),'profile':'V5_RNEG_DEFENSE_V1','formal_batches':1,
        'window_attempt_N':len(results),'day_attempt_N':sum(w['attempted_day_N'] for w in results),
        'control_full_replays':0,'summary':summarize(results),'windows':results,'source_exposure':'ITERATIVE_DEVELOPMENT_EVIDENCE','productionReady':False})

if __name__=='__main__':main()
