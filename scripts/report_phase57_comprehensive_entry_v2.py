"""Frozen-result interpretation and independently serialized policy audit, no fit."""
import argparse,collections,json,math
from pathlib import Path
import numpy as np
from scripts import phase57_comprehensive_entry_v2 as v
from scripts.verify_phase57_comprehensive_entry import equal
m=v.m

def head_predict(d,f):
 a=np.array([[f.get(k) if f.get(k) is not None else np.nan for k in d['features']]])
 z=np.concatenate([np.where(np.isnan(a),d['medians'],a),np.isnan(a).astype(float)],axis=1)
 z=(z-np.array(d['scalerMean']))/np.array(d['scalerScale'])
 if d['kind']=='LINEAR':return float((z@np.array(d['coefficients']).T+np.array(d['intercept'])).reshape(-1)[0]),z
 t=d['tree'];i=0
 while t['children_left'][i]!=-1:i=t['children_left'][i] if z[0,t['feature'][i]]<=t['threshold'][i] else t['children_right'][i]
 return float(np.array(t['value'][i]).reshape(-1)[0]),z
class SavedPolicy:
 def __init__(self,d):self.d=d
 def predict(self,f):
  wait,_=head_predict(self.d['waitHead'],f);skip,z=head_predict(self.d['skipHead'],f);g=self.d['guard'];prob=None
  if g:
   a=float((z@np.array(g['coefficients']).T+np.array(g['intercept'])).reshape(-1)[0]);prob=1/(1+math.exp(-a)) if a>=0 else math.exp(a)/(1+math.exp(a))
  return wait,skip,prob

def fmt(x):return '—' if x is None else f'{x:.4f}' if isinstance(x,float) else str(x)
def table(head,rows):return '\n'.join(['| '+' | '.join(head)+' |','| '+' | '.join(['---']*len(head))+' |']+['| '+' | '.join(fmt(x) for x in r)+' |' for r in rows])
def pc(x):return None if x is None else x*100

def run(source,outdir):
 source=Path(source);out=Path(outdir)
 if out.exists():raise FileExistsError(out)
 out.mkdir(parents=True);s=m.read(source/'summary.json');p,ops,paths,selectors,legacy=v.sources();opmap={x['id']:x for x in ops};teacher=m.read(source/'training-teacher-ledger.json.gz')
 audit={};calibration={};digests={};diff=[];valsets={}
 for kind in v.KINDS:
  md=m.read(source/(kind.lower()+'-model.json'));saved=SavedPolicy(md)
  digests[kind]={'modelSHA256':m.sha(source/(kind.lower()+'-model.json')),'waitScalerSHA256':__import__('hashlib').sha256(m.enc({k:md['waitHead'][k] for k in ('features','medians','scalerMean','scalerScale')})).hexdigest(),'skipScalerSHA256':__import__('hashlib').sha256(m.enc({k:md['skipHead'][k] for k in ('features','medians','scalerMean','scalerScale')})).hexdigest()}
  calibration[kind]={}
  for delay in range(0,31,5):
   rs=[r for r in teacher if r['delay']==delay];pred=[saved.predict(r['features']) for r in rs];wa=[(y[0],r['labels']['waitAdvantage']) for r,y in zip(rs,pred) if r['labels']['waitAdvantage'] is not None]
   calibration[kind][str(delay)]={'states':len(rs),'predictedActions':dict(collections.Counter(v.action(*y,delay<30) for y in pred)),'predictedWaitAdvantage':m.dist([y[0] for y in pred]),'waitMAE':sum(abs(a-b) for a,b in wa)/len(wa) if wa else None,'guardProbabilities':m.dist([y[2] for y in pred])}
  tested=0;identity=[];reusedSourcePairs=[]
  for split in ('train','validation'):
   path=source/(kind.lower()+'-'+split+'.json.gz')
   if not path.exists():continue
   rows=m.read(path);assert len(rows)==len({r['id'] for r in rows})
   if split=='validation':valsets[kind]=rows
   for r in rows:
    x=opmap[r['id']];aid=x['op']['anchorId'];decision=v.decide(x,paths[aid],selectors[aid],legacy.get(aid,{}),saved)
    equal(r['decision'],decision,'serializedDecision');tested+=1
    ts=r['timestamp'];terminal=False
    for t in decision['transitions']:
     assert not terminal and t['timestamp']>=ts and t['delay']<=30
     if t['action']=='WAIT_ONE_STEP':assert t['waitAllowed'];ts=v.c.stamp(r['session'],v.c.minute(t['timestamp'])+5)
     else:terminal=True
    assert sum(t['action']=='BUY_NOW' for t in decision['transitions'])<=1
   groups=collections.defaultdict(list)
   for r in rows:groups[(r['session'],r['symbol'])].append(r)
   reusedSourcePairs.append({'split':split,'symbolSessionsWithBothSourceEntries':sum(sum(r['decision']['status']=='COUNTERFACTUAL_ENTER' for r in rs)>1 for rs in groups.values())})
  audit[kind]={'serializedPolicyDecisionsVerified':tested,'identityUnique':True,'transitionChronology':True,'waitStepExactly5':True,'noTerminalResurrection':True,'singleEntryPerOpportunity':True,'independentSourceEpisodes':reusedSourcePairs}
 if 'S1_LINEAR' in valsets and 'S3_GUARDED_LINEAR' in valsets:
  for a,b in zip(valsets['S1_LINEAR'],valsets['S3_GUARDED_LINEAR']):
   assert a['id']==b['id']
   if (a['decision']['status'],a['decision']['delay'])!=(b['decision']['status'],b['decision']['delay']):diff.append({'id':a['id'],'linear':a['decision'],'guarded':b['decision'],'commonComplete':bool(a['baseline'] and a['baseline']['commonComplete'])})
 supplement={'serializedReplay':audit,'modelDigests':digests,'TRAIN_stateConditionalCalibrationNotOnPolicy':calibration,'guardDecisionDifferences':diff,'noEconomicRun':s['audit']['economicCohortEvaluations']==0,'developmentTestOpened':s['developmentTestOpened'],'knownLimitations':['Teacher is one-step delayed-purchase surrogate, not Bellman continuation value.','Policy evaluates all simulated TRAIN offsets for labels, but on-policy trajectories may never WAIT; this covariate gap is diagnosed, not rescued by post-hoc fitting.','Only633 TRAIN episodes and336 VALIDATION episodes have common60 coverage; 4431 correlated TRAIN states are not independent trades.','All prior76 Development sessions have general outcome exposure; internal DEV TEST not Fresh/OOS.','Sparse accepted5m bars may contain fewer than5 observed minute records; fullUnderlyingMinutes sensitivity retained.','Independent INITIAL/DIP episodes may share symbol-session; no funded portfolio or symbol-session no-reentry claim.'],'safety':p['safety'],'freshOOSOpened':False}
 m.write(out/'audit-appendix.json',supplement)
 top=s['baselines']['B0_IMMEDIATE']['concentration']['top3Train'];lines=['# Comprehensive LONG Entry Intelligence v2 — one-step sequential research','',f"**{s['status']} / {s['freeze']}**",'', '事前固定した3 architectureを終了。全候補KILL。既存Frozen Opportunity Generatorをfallback保持する。新Entryの完成・利益化・PIT情報全体の不可能性は主張しない。','',f"開始HEAD `{p['sourceHead']}`。Protocol commit `{v.PROTOCOL_COMMIT}`。最終exact HEAD・CI identityは final-ci-receipt.json。",'', '## Frozen lineage / exposure','', '`FROZEN_LONG_SELECTOR_WITH_MIN_PRICE_75` → `phase57-new-long-entry-two-opportunity-v1`。Selector、¥75 policy、Opportunity Generator、Candidate A `NEW_LONG_EXIT_PROTECT_3_TO_1_FIXED12_V1` は無変更。v1 Evidenceも無変更。','',table(['Partition','sessions','opportunities','dates'],[[k,len(p['split'][k]),s['population']['splitCounts'][k],p['split'][k][0]+' … '+p['split'][k][-1]] for k in ('TRAIN','VALIDATION','DEVELOPMENT_TEST')]),'', '全3,508 = INITIAL2,841 + DIP667。TRAIN complete common60=633 episodes / 4,431 states、WAIT head=3,798 one-step transitions。VALIDATION863中336 complete (INITIAL259 / DIP77)。内部DEV TEST19sessions/885件はv1/v2候補評価に未使用。以前の一般診断では76sessionsすべてexposedでありFresh扱いしない。','', '## v1 teacher → v2 objective','', 'v1はfuture-best-entryのmax価値をWAIT教師に使い、BUYより楽観的なWAIT→EXPIREに偏った。v2は現在OPENと厳密に5分後のOPENの差だけを教師にする。未来値はTRAIN label/evaluatorだけに使用。','', '- U(now) = common-end close return − 0.05pp cost + 0.25×MAE。', '- WAIT advantage = U(next OPEN) − U(now) − 0.05pp delay cost − lost-threshold penalty − 1pp fast-winner chase penalty。', '- SKIP advantage = −U(now) − missed-opportunity penalty − 1pp FAST_WINNER penalty。', '- +1/+2/+3/+5のpenaltyは0.25/0.5/2/3ppに事前固定。結果を見たweight調整なし。', '- BUY advantage=0。WAIT/SKIPと比較し、同点はBUY→WAIT→SKIP。上限30分・session境界ではWAITをmask。', '- FAST_WINNERはfirst5m HIGH>=1%かつcommon60 MFE>=3%のevaluator label。第三候補のguardはPIT特徴から予測した確率>=0.5のみでBUYを優先。future labelで直接guardしない。','', 'これはone-step delayed-purchase surrogateを毎5分再評価する設計であり、最適な多段階continuation valueを学習できたという主張ではない。','', '## Models / fixed gates','', '同じ43 PIT特徴（欠測indicator込み86入力）。TRAINだけでmedian/scaler/modelをfit。S1はWAIT/SKIPのRidge alpha10、S2はdepth3/min_leaf100の木2本、S3はS1固定＋LogisticRegression C1のguard。合計5 fits。feature追加、hyperparameter sweepなし。','', 'TRAIN catastrophic gate: ENTER/+3/+5各50%以上。Validation: ENTER70%、+1 80%、+2 85%、+3/+5 90%、Immediate/Fast winner90%、価格mean改善0.10pp、strict30 MAE median0.10pp/p05 0.25pp改善、deep5削減10%ほか。Contract全文にcohort/chronological/concentration条件を固定。','',table(['Candidate','status','TRAIN entry coverage %','Validation evaluated'],[[k,z['status'],pc(s['trainMonitoring'][k]['summary']['entryCoverage']),z['validationOpened']] for k,z in s['candidates'].items()]),'', '## Validation B0/B1/B2/v2','']
 comparison={k:z['overall'] for k,z in s['baselines'].items()}
 comparison.update({k:z['entry']['overall'] for k,z in s['candidates'].items() if z['entry'] is not None})
 lines += [table(['Policy','ENTER all863','ENTER complete336','coverage %','+1 %','+2 %','+3 %','+5 %','price improvement mean %'],[[k,z['enteredAll'],z['enteredCommon'],pc(z['entryCoverage']),*[pc(z['preservation'][str(l)]['rate']) for l in v.LEVELS],z['priceImprovement']['mean']] for k,z in comparison.items()]),'', 'B2は既存v1 ledgerのdecisionをそのまま再利用し、モデルを再学習していない。B1は診断のみで採用候補にしない。','', '## Main result / KEEP-KILL','', '**v1のほぼ全abstentionは線形系で緩和したが、v2の全候補はWAITを一度も選ばず、即BUYまたは即SKIPへ退化した。** S1 Validation291 ENTER、S3は292 ENTER。ただし完全paired336では両方197 ENTER。同一197件のEntry価格・MAEはB0と完全同じであり、timing/location改善はない。', '', 'Guardによる差はValidationのcommon60不完全な1件だけ。完全pairedでincremental valueなし。S2はTRAIN633中61 ENTER=9.64%でKILLし、Validationを評価していない。','', '- KEEP: 一歩先のteacherとoracle-maxの分離、WAIT期限でのaction mask、PIT projection、missing fail-closed、winner-preservation gate。', '- KILL: 3 policy architectures。threshold/weight/guard probabilityを調整して救済しない。', '- deep tail件数が減っても、単なるSKIPによる件数減と、同じtradeのEntry Location改善を区別。後者は線形系で0。','']
 for kind,z in s['candidates'].items():
  if z['entry'] is None:continue
  pn=z['entry'];a=pn['overall'];lines += [f'## {kind}','',table(['Source','complete n','ENTER','+3 preserved/base','+5 preserved/base'],[[k,w['commonComplete'],w['enteredCommon'],str(w['preservation']['3']['preserved'])+'/'+str(w['preservation']['3']['baseline']),str(w['preservation']['5']['preserved'])+'/'+str(w['preservation']['5']['baseline'])] for k,w in pn['cohorts'].items()]),'',table(['Class','n','ENTER','remaining+3','remaining+3 %','price mean','baseline strict30 MAE median','entry strict30 MAE median'],[[k,w['n'],w['entered'],w['preserved3'],pc(w['rate3']),w['priceImprovement']['mean'],w['baselineStrict30MAE']['median'],w['entryStrict30MAE']['median']] for k,w in a['classes'].items()]),'', 'CONTINUED_FAILUREのremaining+3欄は定義上0であり、quality preservation指標として解釈しない。failureへのENTER38/70、SKIP32/70。代わりにImmediate winner5/14、FAST winner9/41、Pullback winner14/57を喪失。','',table(['Action outcome','count','all-emitted %'],[[k,n,100*n/a['emitted']] for k,n in a['decisions'].items()]), '',table(['Delay minutes / no entry','n'],list(a['delayDistribution'].items())), '',f"WAIT transitions={a['waitTransitions']}。Entry delay mean/median={fmt(a['delay']['mean'])}/{fmt(a['delay']['median'])}min。価格改善 mean/median/p25/p75={fmt(a['priceImprovement']['mean'])}/{fmt(a['priceImprovement']['median'])}/{fmt(a['priceImprovement']['p25'])}/{fmt(a['priceImprovement']['p75'])}%。favorable/worse rate={fmt(a['favorableRate'])}/{fmt(a['worseRate'])}。",'',table(['Risk/Upside','n','mean','median','p10','p05','worst(min)'],[[k,a[k]['n'],a[k]['mean'],a[k]['median'],a[k]['p10'],a[k]['p05'],a[k]['min']] for k in ('baselineCommonMAE','baselinePairedMAE','entryPairedMAE','baselineStrict30MAE','entryStrict30MAE','baselinePairedMFE','entryPairedMFE')]),'',table(['tail','baseline all','baseline entered pair','entry pair','strict30 baseline pair','strict30 entry pair'],[[k,*[w[j] for j in ('baselineAll','baselineEnteredPair','entryPair','strict30BaselinePair','strict30EntryPair')]] for k,w in a['tails'].items()]),'',table(['Gate','PASS'],list(pn['gates'].items())), '',table(['Chronological block','complete n','coverage %','+3 %','+5 %','price mean'],[[k,w['commonComplete'],pc(w['entryCoverage']),pc(w['preservation']['3']['rate']),pc(w['preservation']['5']['rate']),w['priceImprovement']['mean']] for k,w in pn['blocks'].items()]),'',f"TRAIN頻度top3固定除外={top}。symbol HHI={fmt(pn['concentration']['symbolHHI'])}、session HHI={fmt(pn['concentration']['sessionHHI'])}。除外後gateもFAIL。",'',table(['Breadth','complete n','coverage %','+3 %','+5 %'],[[k,w['commonComplete'],pc(w['entryCoverage']),pc(w['preservation']['3']['rate']),pc(w['preservation']['5']['rate'])] for k,w in pn['breadth'].items()]),'', 'session別・anchor context欠測別・全minute観測別はsummaryに保存。subgroupでのrule追加なし。','']
 lines += ['## Economics / DEV TEST','', '**Entry gate通過候補0。Candidate Aの新規economic pairingは実行0回、DEV TEST候補評価0回。** n/mean/PF/p05/Win/HOLDのv2経済結果はNOT_RUN_ENTRY_GATE_FAILED。ゼロ利益やPASSと置き換えない。v1経済比較は旧Evidenceとして保持し、v2成績へ転用しない。', '', '## Model/source/deterministic audit','', table(['Candidate','model SHA256','wait scaler SHA256','skip scaler SHA256'],[[k,d['modelSHA256'],d['waitScalerSHA256'],d['skipScalerSHA256']] for k,d in digests.items()]),'', table(['Policy','saved-model replay episodes','identity / causal / terminal audit'],[[k,d['serializedPolicyDecisionsVerified'],'PASS'] for k,d in audit.items()]),'', '保存modelの係数/木/scalerから別実装でdecisionを再現。PIT特徴はcompleted prefixのみ。execution OPEN参照は未来HIGH/LOW/CLOSEを使用しない。one-step teacherはnow/next購入だけで、後続の最良Entry検索なし。未来outcomeはteacher/evaluatorに隔離。TRAIN-only fitting、同一inputのcanonical数値再生成。単一Opportunity内の重複ENTERとterminal後resurrectionなし。INITIAL/DIPの独立episode間で同じsymbol-sessionを再利用し得るため、実保有や再エントリー許可とはしない。','', '全9 safety flags=false、LONG-only cash equity。Frozen artifacts不変、既存Evidence上書きなし。Fresh/OOS未開封。Capital/Portfolio/main merge/Paper/Live/注文接続なし。tests・regression・CI artifact hashはfinal-ci-receiptに固定。CI greenはperformance PASSではない。','', '## Limitation and next information','', '3つの事前固定architectureと今回のone-step teacherでは、Immediateを安定改善できなかった。これは、同じ5m保存substrateからのEntry Timing全体が不可能という証明ではない。今回のモデルは初回時点でWAIT価値を発見できず、遅延stateを学習してもon-policyでそこへ到達しなかった。TRAINのoffset別教師/予測/action分布をaudit-appendixへ保存した。','', '次に進むなら、このone-step surrogateとon-policy到達stateの不一致、shared terminalのrisk/skip trade-off、PIT snapshot coverageを別研究契約で検討する必要がある。今回Validationに合わせてteacherやthresholdを作り直さない。','', '**COMPREHENSIVE_LONG_ENTRY_V2_DEVELOPMENT_LIMIT_REACHED。DO_NOT_FREEZE。既存Opportunity Generatorを保持しSTOP。**','']
 (out/'REPORT.md').write_text('\n'.join(lines))
 m.write(out/'manifest.json',{'sourceManifestSHA256':m.sha(source/'manifest.json'),'codeSHA256':m.sha(__file__),'outputPins':{f.name:m.sha(f) for f in sorted(out.iterdir())},'safety':p['safety']})
 print(json.dumps({'audit':audit,'guardDecisionDifferenceN':len(diff),'economicCalls':s['audit']['economicCohortEvaluations'],'verdict':s['status']}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--out',required=True);a=p.parse_args();run(a.source,a.out)
