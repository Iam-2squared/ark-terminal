"""Reuse H5 bytes exactly and freeze one shared score/rank stream; fit0."""
from checkpoint import *
from io_data import rows,gzwrite
from quality import materialize
from collections import Counter
h5=rows(V2/'CORE_P5_SCORE_STREAM.jsonl.gz');h={r['entry_id']:r for r in h5}
assert sha(V2/'CORE_P5_SCORE_STREAM.jsonl.gz')=='a34f2c4a090a589d4e80858b65f01f3dc95a7849a57aece7e815213d20429731'
new=rows(PRIVATE/'NEW_HEAD_OOF_PREDICTIONS.jsonl.gz');stream=[]
for r in new:
 old=h[r['entry_id']];assert old['block']==r['block']
 row={k:v for k,v in r.items() if k not in ('H3','HF1','HL0')}
 a,b,c=[r[x] for x in ('H3','HF1','HL0')]
 q=materialize(row,old['pP'],old['baseP'],a['p'],a['base_rate'],b['p'],b['base_rate'],c['p'],c['base_rate'])
 q['head_model_hashes']={'H5':old['P_model_sha256'],'H3':a['model_hash'],'HF1':b['model_hash'],'HL0':c['model_hash']};assert q['L5']==old['capital_score']
 stream.append(q)
gzwrite(PRIVATE/'QUALITY_V3_SCORE_STREAM.jsonl.gz',stream)
save(OUT/'QUALITY_SCORE_RANK_STREAM_FREEZE.json',{'jst':now(),'N':len(stream),'shared_profiles':4,'quality_score_hash':sha(PRIVATE/'QUALITY_V3_SCORE_STREAM.jsonl.gz'),'H5_hash':sha(V2/'CORE_P5_SCORE_STREAM.jsonl.gz'),'H5_byte_identical_reuse':True,'H5_scalar_mismatch_N':0,'fits_added':0,'quality_gate_pass_N':sum(r['quality_gate_pass'] for r in stream),'admitted_rank_counts':dict(Counter(r['rank'] for r in stream if r['quality_gate_pass'])),'all_rank_counts':dict(Counter(r['rank'] for r in stream)),'gate_failures':dict(Counter(k for r in stream for k in r['gate_failures'])),'safety':SAFETY})
print('QUALITY_SCORE_STREAM_FROZEN',len(stream))
