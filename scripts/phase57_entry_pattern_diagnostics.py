"""Read-only post-measurement report checks. No fitting, selection or policy changes."""
import argparse,collections,gzip,json
from pathlib import Path
import numpy as np
from scripts import phase57_entry_pattern_v2 as e

def run(root,out):
 root=Path(root);out=Path(out);out.mkdir(parents=True,exist_ok=False);m=root/'measurement';src=root/'substrate'
 for folder in [m,src]:
  for name,h in e.read(folder/'manifest.json').items():assert e.sha(folder/name)==h
 gate=e.read(m/'decisions.json');selected=gate['selected'];family=selected.rsplit('_',2)[0];mode=selected.rsplit('_',2)[1];metrics=e.read(m/'metrics.json');models=e.read(m/'models.json.gz');names=e.read(src/'names.json');rows=e.read(src/'rows.json.gz');labs=e.read(src/'outcomes.json.gz');tr=e.read(m/'trades.json.gz');rowidx={r['id']:i for i,r in enumerate(rows)}
 cov={side:dict(collections.Counter(r[side+'Coverage'] for r in rows)) for side in ['previous','today']}
 with gzip.open(m/'predictions.npy.gz','rb') as fh:pred=np.load(fh,allow_pickle=False)[e.read(m/'prediction-order.json').index(family)]
 chosenmodel=models[family];importance=[]
 if chosenmodel['family']=='TREE':
  gains=collections.Counter()
  for head,w in zip(chosenmodel['heads'][:4],[1,.15,.3,.2]):
   for tree in head['nodes']:
    for node in tree:
     if not node['is_leaf']:gains[int(node['feature_idx'])]+=max(0,node['gain'])*w
  for i,val in gains.items():
   n=len(chosenmodel['columns']);orig=chosenmodel['columns'][i%n];importance.append({'feature':('MISSING/' if i>=n else '')+names[orig],'weightedTrainingSplitGain':val})
  importance=sorted(importance,key=lambda x:-x['weightedTrainingSplitGain'])[:30]
 else:importance=e.read(m/'attribution.json')[family]
 # Descriptive noise and fresh-turning outcome proxy; never a selection criterion.
 turnAvailable=all(n in names for n in ['STRUCT/turningUp','STRUCT/swingAge']);turncols=[names.index(n) for n in ['STRUCT/turningUp','STRUCT/swingAge'] if n in names];turn=[]
 for d in e.read(src/'inventory.json'):
  with gzip.open(src/(d['session']+'.npy.gz'),'rb') as fh:a=np.load(fh,allow_pickle=False)
  if a.shape[1]:turn.append(a[:,turncols])
 turn=np.vstack(turn);byopp=collections.defaultdict(list)
 for i,r in enumerate(rows):byopp[r['opportunity']].append(i)
 noise=[]
 for step in [1,5]:
  arm=selected[:-2]+str(step)+'m';flips=pairs=freshBuy=negativeFresh=unknownFresh=0
  for trade in tr[arm]:
   stop=int(trade['entryId'].split('|')[-1]) if trade['entryId'] else 2000;previous=None
   for i in byopp[trade['opportunity']]:
    r=rows[i]
    if not r['eligible1'] or (step==5 and not r['eligible5']) or not r['quoteAvailable'] or r['minute']>stop:continue
    q=float(pred[i,:4]@np.array([1,.15,.3,.2])-.002*r['delay']);proposal=q>=0 and (mode=='QUALITY' or q>=max(0,pred[i,4]))
    if previous is not None:pairs+=1;flips+=proposal!=previous
    previous=proposal
   if trade['entryId']:
    i=rowidx[trade['entryId']]
    if turnAvailable and turn[i,0]==1 and turn[i,1]==0:
     freshBuy+=1;value=labs[trade['entryId']]['labels']['return30'];unknownFresh+=value is None;negativeFresh+=value is not None and value<=0
  noise.append({'cadence':step,'turnFeaturesAvailable':turnAvailable,'proposalAdjacentPairsUntilEntryOrExpiry':pairs,'proposalFlips':flips,'flipPct':100*flips/pairs if pairs else None,'BUYAtFreshConfirmedSwingLow':freshBuy,'nonpositiveReturn30AfterFreshSwingLowBUY':negativeFresh,'unknownReturn30AfterFreshSwingLowBUY':unknownFresh})
 # Fit/selection/evaluation sample anatomy and cadence-specific baseline comparisons.
 anatomy=e.read(m/'anatomy.json');cadence=[]
 for step in [1,5]:
  model=selected[:-2]+str(step)+'m';baseline='B0_RETRY_'+str(step)+'m';a=metrics[model];b=metrics[baseline]
  cadence.append({'cadence':step,'model':model,'BUY':a['BUY'],'baselineBUY':b['BUY'],'capture3':a['capture']['3']['rate'],'baselineCapture3':b['capture']['3']['rate'],'capture3DeltaPp':a['capture']['3']['rate']-b['capture']['3']['rate'],'capture5DeltaPp':a['capture']['5']['rate']-b['capture']['5']['rate'],'decisionEvaluations':a['decisionEvaluations']})
 e.write(out/'supplement.json',{'selected':selected,'anatomy':anatomy,'noiseAndFreshTurningProxy':noise,'coverage':cov,'selectedAttribution':importance,'cadenceMatchedBaseline':cadence,'definitions':{'attribution':'Training-only split gains or standardized linear coefficient weight; not causal contribution','falseTurning':'Not inferred from gross return alone; source turning state may persist and is not a fresh-signal event'},'noFit':True,'noSelection':True})
 lines=['# Entry Pattern v2 — report supplement','',f'Selection-fixed primary: `{selected}`. No refit or evaluation winner selection.','', '## Pattern sample / good-bad anatomy','', '| Split | Samples | Complete30 | Good | Bad |','|---|---:|---:|---:|---:|']
 for split,z in anatomy.items():lines.append(f'| {split} | {z["sampleRows"]} | {z["complete30"]} | {z["good"]} | {z["bad"]} |')
 lines+=['','Good: complete30, return>0, MFE>=2%, MAE>−1%. Bad: observed return<0 or MAE<=−2%. Fixed before training; labels are anatomy only, not decision features.','', '## Full1m coverage','']
 for side,z in cov.items():lines.append(f'- {side}: {z}')
 lines+=['','FULL_SLOTS means every expected continuous-minute slot is present; PARTIAL_OBSERVED is preserved without interpolation. Source record absence is not proof of no trade.','', '## Cadence-matched retry comparison','', '| Cadence | BUY model / baseline | +3 Capture model / baseline | +3 delta pp | +5 delta pp | Model decision evaluations |','|---|---:|---:|---:|---:|---:|']
 for z in cadence:lines.append(f'| {z["cadence"]}m | {z["BUY"]} / {z["baselineBUY"]} | {z["capture3"]:.3f} / {z["baselineCapture3"]:.3f} | {z["capture3DeltaPp"]:.3f} | {z["capture5DeltaPp"]:.3f} | {z["decisionEvaluations"]} |')
 lines+=['','## Proposal noise / fresh-turning outcome proxy','','Adjacent model BUY/WAIT proposal flips are measured only until actual BUY or expiry, on available quotes. Fresh turning = STRUCT/turningUp=1 and swingAge=0. Nonpositive return30 after that BUY is a descriptive adverse-outcome proxy, not an objective false-pattern label.','']
 lines += ['- '+str(x) for x in noise]
 lines+=['','## Selected-model attribution','', 'Training-only coefficients/gains. Correlated features and availability masks prevent a causal interpretation.','']
 lines += ['- '+str(x) for x in importance[:15]]
 lines+=['','No formal event-level false-turning precision is claimed: turning state persists, so a negative-return BUY is a bad-BUY diagnostic, not proof that a newly detected turning signal was false.','']
 (out/'REPORT-ja.md').write_text('\n'.join(lines))
 e.write(out/'manifest.json',{x.name:e.sha(x) for x in out.iterdir()})
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--evidence',required=True);a.add_argument('--output',required=True);x=a.parse_args();run(x.evidence,x.output)
