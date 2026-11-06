"""The frozen new EXIT teacher. Future source is confined to this evaluator."""
import collections
from exit_common import *

def run():
    assert not (HERE/'TEACHER_LABELS.jsonl.gz').exists(), 'NO_LABEL_REGENERATION'
    contract=read(HERE/'EXIT_TEACHER_CONTRACT.json'); assert contract['before_teacher_computation']
    grid=list(lines(ENTRY/'PERSISTENT_GRID.jsonl.gz')); source=read(SOURCE)
    ranges=np.load(ENTRY/'PRIVATE_INPUTS/watch_row_ranges.npy')
    y=np.full(len(grid),np.nan); records=[None]*len(grid); status=collections.Counter()
    for lo,hi in ranges:
        lo,hi=int(lo),int(hi); r0=grid[lo]; day=r0['session']; a=clean(source[r0['watch_key']]['today'])
        eligible=a[np.isin(a[:,0],sell_starts(day))]; terminal=a[a[:,0]==close_minute(day)]
        op_minutes=eligible[:,0]; op_prices=eligible[:,1]*.9995
        if len(terminal):
            op_minutes=np.append(op_minutes,close_minute(day));op_prices=np.append(op_prices,terminal[-1,4]*.9995)
        suffix_sum=np.cumsum(op_prices[::-1])[::-1]
        for i in range(lo,hi):
            r=grid[i];t=r['intent_minute']; k=int(np.searchsorted(op_minutes,t,'left'))
            rec={'row_index':i,'row_id':r['row_id'],'watch_key':r['watch_key'],'session':day,'decision_minute':t,'target_raw_pct':None,'target':None,'status':None,'future_target_used_by_decision':False}
            if not len(terminal):rec['status']='TERMINAL_SOURCE_UNAVAILABLE'
            elif k>=len(op_minutes)-1:rec['status']='NO_LATER_EXECUTABLE_OPPORTUNITY'
            else:
                mean=float(suffix_sum[k+1]/(len(op_prices)-k-1)); raw=100*(mean/op_prices[k]-1);y[i]=np.clip(raw,-10,10)
                scheduled=int(sum(m>op_minutes[k] for m in sell_starts(day))+1)
                rec.update(status='KNOWN_OBSERVED_OPPORTUNITY_MEAN',target_raw_pct=raw,target=float(y[i]),exit_now_fill_minute=int(op_minutes[k]),exit_now_sell_price=float(op_prices[k]),later_opportunity_N=len(op_prices)-k-1,later_scheduled_opportunity_N=scheduled,later_observed_coverage=(len(op_prices)-k-1)/scheduled)
            status[rec['status']]+=1;records[i]=rec
    np.save(HERE/'PRIVATE_INPUTS/targets.npy',y);write_lines(HERE/'TEACHER_LABELS.jsonl.gz',records)
    write(HERE/'TEACHER_RECEIPT.json',{'saved_at_jst':now(),'teacher_contract_sha256':sha(HERE/'EXIT_TEACHER_CONTRACT.json'),'raw_source_sha256':sha(SOURCE),'labels_sha256':sha(HERE/'TEACHER_LABELS.jsonl.gz'),'targets_sha256':sha(HERE/'PRIVATE_INPUTS/targets.npy'),'grid_rows':len(grid),'status_counts':dict(status),'label_definition_changes':0,'future_isolation':'targets are separate file; OOF decision predictions contain no future evaluator fields','safety':SAFETY})
    print(json.dumps({'teacher_rows':len(grid),'status_counts':dict(status),'fits':0}),flush=True)
if __name__=='__main__':run()
