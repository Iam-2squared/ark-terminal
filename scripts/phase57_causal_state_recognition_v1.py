import gzip,json,collections,math,hashlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CP=ROOT/'docs/evidence/phase57-causal-entry-state-v1/ci-result/measurement/checkpoints.json.gz'
AUD=ROOT/'docs/evidence/phase57-future-path-deep-audit-v1/ci-result/measurement/raw/audit-records.json.gz'
OUT=ROOT/'docs/evidence/phase57-causal-state-recognition-v1/result'

def read(p):
    op=gzip.open if str(p).endswith('.gz') else open
    with op(p,'rt',encoding='utf-8') as f:return json.load(f)

def metric(rows):
    tp=sum(t and r for t,r in rows);fp=sum(t and not r for t,r in rows)
    fn=sum((not t) and r for t,r in rows);tn=sum((not t) and (not r) for t,r in rows)
    pr=tp/(tp+fp) if tp+fp else None;rc=tp/(tp+fn) if tp+fn else None
    f1=2*pr*rc/(pr+rc) if pr is not None and rc is not None and pr+rc else None
    return {'n':len(rows),'tp':tp,'fp':fp,'fn':fn,'tn':tn,'precision':pr,'recall':rc,'f1':f1}

def main():
    cps=read(CP);aud=read(AUD)
    assert len(aud)==2155 and len({r['opportunity'] for r in aud})==2155
    A={r['opportunity']:r for r in aud}
    by=collections.defaultdict(list)
    for z in cps:by[(z['opportunity'],z['checkpoint'])].append(z)
    assert all(len(v)==1 for v in by.values())
    attrs={
      'CONTINUATION_UP':('DIRECT_CONTINUATION','SCORE/TREND'),
      'RECOVERY':('PULLBACK_RECOVERY',None),
      'CONSOLIDATION':('ATOM_CONSOLIDATION','SCORE/COMPRESSION'),
      'MULTI_SWING_CHOPPINESS':('MULTI_SWING_CHOP','SCORE/CHOP'),
      'WEAKNESS_DOWN':('PERSISTENT_WEAKNESS','SCORE/WEAKNESS')}
    out={'population':2155,'checkpoints':{},'notOperationalized':{
      'PULLBACK':'TARGET_NOT_IDENTIFIABLE_FROM_STEP1',
      'BREAKOUT_UP':'RECOGNIZER_NOT_OPERATIONALIZED_WITHOUT_NEW_CAUSAL_DEFINITION'},
      'dictionaryUsed':False,'signalsUsed':False,'entryTimingEvaluated':False,'training':False,'holdoutOpened':0,'providerRequests':0}
    for delay in [0,5,10,15,30]:
      zz=[by.get((oid,delay),[None])[0] for oid in A]
      avail=sum(z is not None and z.get('features') is not None for z in zz)
      one={'population':2155,'checkpointAvailable':avail,'checkpointUnavailable':2155-avail,'attributes':{},'unknownReasons':collections.Counter()}
      for name,(target,score) in attrs.items():
        pairs=[];targetpos=0;recognized=0;unavailable=0
        for oid,z in zip(A,zz):
          a=A[oid]
          if target=='DIRECT_CONTINUATION': truth=bool(a['original']['predicate'].get('DIRECT_CONTINUATION'))
          elif target=='PULLBACK_RECOVERY': truth=bool(a['original']['predicate'].get('PULLBACK_RECOVERY'))
          elif target=='ATOM_CONSOLIDATION': truth=bool(a['atoms'].get('CONSOLIDATION/compressed10'))
          elif target=='MULTI_SWING_CHOP': truth=bool(a['original']['predicate'].get('MULTI_SWING_CHOP'))
          else: truth=bool(a['original']['predicate'].get('PERSISTENT_WEAKNESS'))
          targetpos+=truth
          if z is None or z.get('features') is None:
            unavailable+=1;continue
          f=z['features']
          if name=='RECOVERY':
            vals=[f.get('drawdown'),f.get('ret5'),f.get('recovery')]
            pred=None if any(v is None for v in vals) else vals[0]>=.3 and vals[1]>0 and vals[2]>=.5
          else:
            v=f.get(score);pred=None if v is None else v>=.5
          if pred is None:
            unavailable+=1;continue
          recognized+=bool(pred);pairs.append((bool(pred),truth))
        one['attributes'][name]={'evaluatorPositive':targetpos,'recognizedPositive':recognized,'unavailable':unavailable,**metric(pairs)}
      for oid,z in zip(A,zz):
        if z is None or z.get('features') is None:one['unknownReasons']['CHECKPOINT_BAR_UNAVAILABLE']+=1
        else:
          f=z['features'];known=0
          for k in ('SCORE/TREND','SCORE/COMPRESSION','SCORE/CHOP','SCORE/WEAKNESS'):
            known+=f.get(k) is not None
          vals=[f.get('drawdown'),f.get('ret5'),f.get('recovery')]
          known+=not any(v is None for v in vals)
          if not known:one['unknownReasons']['OBSERVATION_INSUFFICIENT']+=1
      one['unknownReasons']=dict(one['unknownReasons'])
      out['checkpoints'][str(delay)]=one
    OUT.mkdir(parents=True,exist_ok=False)
    with open(OUT/'summary.json','w',encoding='utf-8') as f:json.dump(out,f,ensure_ascii=False,sort_keys=True,indent=2)
    lines=['# STEP 3 Causal State Recognition v1 — RESULT / STOP','','Development diagnostic only. No Holdout/Fresh/OOS. No Entry timing evaluation.','',
    '| T+ | Available | Unavailable |','|---:|---:|---:|']
    for d,z in out['checkpoints'].items():lines.append(f"| {d} | {z['checkpointAvailable']} | {z['checkpointUnavailable']} |")
    lines+=['','## Attribute recognition','','Precision/Recall are against STEP 1 evaluator anatomy and are not trading performance.','']
    for d,z in out['checkpoints'].items():
      lines += [f'### T+{d}','', '| Attribute | Eval + | Recognized + | Precision | Recall | F1 | Unavailable |','|---|---:|---:|---:|---:|---:|---:|']
      for n,m in z['attributes'].items():
        fmt=lambda x:'NA' if x is None else f'{100*x:.1f}%'
        lines.append(f"| {n} | {m['evaluatorPositive']} | {m['recognizedPositive']} | {fmt(m['precision'])} | {fmt(m['recall'])} | {fmt(m['f1'])} | {m['unavailable']} |")
    lines += ['','## Explicit gaps','', '- PULLBACK: TARGET_NOT_IDENTIFIABLE_FROM_STEP1. No label was manufactured.', '- BREAKOUT_UP: evaluator witness exists, but no new causal recognizer threshold was invented in STEP 3.', '',
    '## STOP','', 'This diagnostic reuses already-saved closed-prefix checkpoint features and STEP 1 evaluator anatomy. It does not fit a model, sweep thresholds, use Signals, evaluate Entry timing, open Holdout, or use Dictionary. STEP 4 is not started.']
    (OUT/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.iterdir()) if p.is_file()}
    (OUT/'manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
