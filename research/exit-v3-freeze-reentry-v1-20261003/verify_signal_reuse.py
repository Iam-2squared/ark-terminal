"""Exact saved P1/Q70 + causal grid projection. No predict/fit/feature generation."""
from work_io import *
from collections import Counter
import gzip,math

def lines(p):
    with gzip.open(p,'rt') as f:
        for l in f:yield json.loads(l)
def write_lines(p,records):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('wb') as out,gzip.GzipFile(fileobj=out,mode='wb',mtime=0) as z:
        for x in records:z.write((json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode())
def need(ok,label):
    if not ok:raise RuntimeError('BLOCKED_REENTRY_LINEAGE_MISMATCH: '+label)

def run():
    p=INPUT/'frozen_signal'
    receipt=read(INPUT/'first_entry_public/PRIVATE_FREEZE_PACKAGE_RECEIPT.json')
    archive=INPUT/'frozen_signal_archive'/receipt['filename']
    need(sha(archive)==receipt['sha256'],'official freeze archive')
    dependency=INPUT/'frozen_signal_archive'/receipt['base_package_dependency']['filename']
    need(sha(dependency)==receipt['base_package_dependency']['sha256'],'base grid dependency archive')
    for f in ['UPTREND_SCORE_ROWS.jsonl.gz','WATCH_RECORDS.jsonl.gz','P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz']:
        need(sha(p/f)==receipt['selected_private_files'][f]['sha256'],f)
    need(sha(p/'P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz')==sha(TRACE/'FROZEN_ENTRY/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz'),'FIRST Entry bytes parity')
    grid_receipt=read(INPUT/'first_entry_public/PERSISTENT_GRID_RECEIPT.json')
    need(sha(p/'PERSISTENT_GRID.jsonl.gz')==grid_receipt['grid_sha256'],'exact grid')
    grid=list(lines(p/'PERSISTENT_GRID.jsonl.gz'))
    need(len(grid)==grid_receipt['grid_rows'],'grid row count')
    entries=[e for e in lines(p/'P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz') if e['entry_status']=='FIRST_ENTRY']
    watches={e['watch_key'] for e in entries}; need(len(watches)==1600,'1600 watches')
    calibration={}
    for fold in range(1,6):
        name=f'P1_F{fold}_calibration.json';meta=receipt['selected_private_files']['PRIVATE_MODELS/'+name]
        need(sha(p/name)==meta['sha256'],name);v=read(p/name)
        need(v['family']=='P1' and v['fold']==fold and v['corrected_Q_D'] and v['UPSIDE_unchanged_reuse'],'calibration lineage')
        calibration[fold]=v['thresholds']['Q70']
    need(read(INPUT/'first_entry_public/CORRECTED_OOF_LINEAGE_RECEIPT.json')['status']=='CORRECTED_OOF_COMPLETE','corrected OOF complete')
    output=[];source_P1_N=0;lookup={};previous={};folds=Counter()
    for s in lines(p/'UPTREND_SCORE_ROWS.jsonl.gz'):
        if s['family']!='P1':continue
        source_P1_N+=1;g=grid[s['row_index']]
        for key in ['watch_key','row_id','session','intent_minute']:need(s[key]==g[key],'grid identity '+key)
        need(g['canonical'] and g['feature_max_timestamp']<=g['intent_timestamp'],'past-only cutoff')
        need(g['closed_raw_start']+1==g['intent_minute'],'closed source/bar-end availability')
        need(s['Q_D_lineage']=='CORRECTED_CALENDAR_Q_D_REFIT' and s['thresholds']['Q70']==calibration[s['fold']],'P1 corrected threshold')
        need(math.isfinite(s['UPTREND_SCORE']),'finite score')
        prev=previous.get(s['watch_key']);need(prev is None or prev<s['intent_minute'],'strict watch chronology');previous[s['watch_key']]=s['intent_minute']
        if s['watch_key'] not in watches:continue
        q={'watch_key':s['watch_key'],'session':s['session'],'minute':s['intent_minute'],'timestamp':g['intent_timestamp'],'closed_raw_start':g['closed_raw_start'],'feature_max_timestamp':g['feature_max_timestamp'],'actual_known_at':'UNKNOWN','availability_assumption':'bar_end','row_id':s['row_id'],'row_index':s['row_index'],'fold':s['fold'],'score':s['UPTREND_SCORE'],'threshold':s['thresholds']['Q70'],'Q_D_lineage':s['Q_D_lineage']}
        output.append(q);lookup[s['row_id']]=q;folds[s['fold']]+=1
    need(source_P1_N==223940,'complete saved P1 rows')
    # Identity parity only: no first-entry threshold decision replay or performance calculation.
    for e in entries:
        s=lookup[e['first_intent']['row_id']]
        for k in ['row_index','fold','score','threshold']:need(s[k]==e['first_intent'][k],'Frozen FIRST intent '+k)
        need(s['minute']==e['first_intent']['intent_minute'],'Frozen FIRST intent minute')
    target=PRIVATE/'FROZEN_P1_Q70_SIGNAL_ROWS.jsonl.gz';write_lines(target,output)
    result={'saved_at_jst':now(),'status':'FROZEN_P1_Q70_POST_EXIT_SIGNAL_EXACT_REUSE_AVAILABLE','FIRST_ENTRY_HEAD':ENTRY_HEAD,'Entry_N':1600,'source_P1_rows_N':source_P1_N,'selected_1600_watch_signal_rows_N':len(output),'selected_watch_N':len({s['watch_key'] for s in output}),'fold_rows_N':dict(folds),'Frozen_Q70_thresholds':calibration,'official_freeze_archive_sha256':sha(archive),'base_grid_archive_sha256':sha(dependency),'saved_score_rows_sha256':sha(p/'UPTREND_SCORE_ROWS.jsonl.gz'),'saved_grid_sha256':sha(p/'PERSISTENT_GRID.jsonl.gz'),'signal_projection_sha256':sha(target),'projection_fields':'exact saved P1 score, Q70 threshold and causal grid metadata only; future buckets/economics absent','first_intent_identity_parity_N':1600,'feature_or_score_recalculation_N':0,'fit_teacher_threshold_search_N':0,'provider_new_data_N':0,'State9_Path_reconstruction_N':0,'historical_actual_known_at':'UNKNOWN','availability_assumption':'bar_end; not actual timestamp evidence','safety':SAFETY}
    write(ROOT/'FROZEN_SIGNAL_REUSE_RECEIPT.json',result)
    print(json.dumps(result))

if __name__=='__main__':run()
