"""Transparent descriptive v2 report. Oracle targets are never displayed as strategy performance."""
import argparse,collections,csv,gzip,os,re,subprocess
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scripts import phase57_entry_pattern_v2 as e
plt.rcParams['svg.hashsalt']='entry-pattern-v2'

def report(root,replay):
 root=Path(root);src=root/'substrate';m=root/'measurement';p=e.verify()
 assert e.read(m/'manifest.json')==e.read(Path(replay)/'manifest.json')
 assert e.read(src/'manifest.json')==e.read(root/'substrate-determinism.json')
 data=e.read(m/'metrics.json');gate=e.read(m/'decisions.json');inv=e.read(src/'inventory.json');p0=e.read(src/'p0-audit.json');rows=e.read(src/'rows.json.gz');tr=e.read(m/'trades.json.gz');paths=e.read(src/'raw-paths-evaluator-only.json.gz');labs=e.read(src/'outcomes.json.gz');names=e.read(src/'names.json');selected=gate['selected']
 arms=['B0_RETRY_1m','B0_RETRY_5m','B1_WAIT5_1m','B1_WAIT15_1m','B2_E5_V1_PRESERVED',selected];arms=list(dict.fromkeys(arms));pics=[]
 def save(fig,n):fig.tight_layout();fig.savefig(root/(n+'.png'),dpi=130);fig.savefig(root/(n+'.svg'),metadata={'Date':None});plt.close(fig);pics.append(n)
 def bars(ax,values,title,labels=arms):ax.bar(range(len(labels)),[np.nan if x is None else x for x in values]);ax.set_xticks(range(len(labels)),labels,rotation=60,fontsize=7);ax.set_title(title);ax.grid(axis='y',alpha=.2)
 fig,axs=plt.subplots(1,2,figsize=(12,4));bars(axs[0],[144,sum(x['opportunities']>0 for x in inv),len(p['evaluation'])],'Session funnel',['Input','With opportunity','Evaluation manifest']);bars(axs[1],[sum(x['opportunities'] for x in inv),len(rows),data[selected]['opportunities']],'Pattern funnel',['All opportunity','All pattern rows','Eval opportunity']);save(fig,'01-funnel')
 fig,axs=plt.subplots(1,2,figsize=(12,4));bars(axs[0],[sum(x['emptyV1'] for x in inv),sum(x['emptyV2'] for x in inv)],'Empty monitor grid',['v1 wall clock','v2 active clock']);cov=collections.Counter(r['previousCoverage'] for r in rows);bars(axs[1],list(cov.values()),'Previous full1m observed-slot coverage',list(cov));save(fig,'02-clock-full1m')
 rootcauses=p0['rootCauses'];fig,ax=plt.subplots(figsize=(12,5));ax.barh(list(rootcauses),list(rootcauses.values()));ax.set_title('v1 sequence unavailable: raw-prefix diagnosis');save(fig,'03-feature-causes')
 fig,axs=plt.subplots(1,2,figsize=(13,4))
 for ax,h in zip(axs,['30','60']):
  for a in arms:ax.plot([1,2,3,4,5],[data[a][h]['hit'][str(t)]['rate'] for t in range(1,6)],marker='o',label=a)
  ax.set_title(h+' active-minute Hit / all BUY (observed lower bound)');ax.set_ylabel('%');ax.legend(fontsize=6)
 save(fig,'04-hit')
 fig,ax=plt.subplots(figsize=(12,5))
 for a in arms:ax.plot([1,2,3,4,5],[data[a]['capture'][str(t)]['rate'] for t in range(1,6)],marker='o',label=a)
 ax.axhline(90,ls='--',c='gray');ax.set_title('Session-end Capture / fixed Selector winners');ax.legend(fontsize=7);save(fig,'05-capture')
 fig,axs=plt.subplots(2,3,figsize=(15,9))
 for row,h in zip(axs,['30','60']):
  for ax,k in zip(row,['MFE','MAE','MaxDD']):bars(ax,[data[a][h][k]['median'] for a in arms],h+'m '+k+' median (%)')
 save(fig,'06-path')
 fig,axs=plt.subplots(1,3,figsize=(15,5))
 for ax,k in zip(axs,['30','60','end']):bars(ax,[data[a][k]['returnNet']['mean'] if k!='end' else data[a]['returnEnd']['mean'] for a in arms],k+' net return mean (%)')
 save(fig,'07-return')
 fig,axs=plt.subplots(1,3,figsize=(15,5));bars(axs[0],[data[a]['BUY'] for a in arms],'BUY');bars(axs[1],[data[a]['noEntry'] for a in arms],'EXPIRE / no entry');bars(axs[2],[data[a]['delay']['median'] for a in arms],'Median active-minute delay');save(fig,'08-throughput-timing')
 fig,ax=plt.subplots(figsize=(12,6));states=['MODEL_WAIT','STALE_OR_MISSING_REFERENCE','BUY_ATTEMPT_UNFILLED','EXPIRED'];bottom=np.zeros(len(arms))
 for st in states:
  vals=[data[a]['reasons'].get(st,0) for a in arms];ax.bar(arms,vals,bottom=bottom,label=st);bottom+=vals
 ax.tick_params(axis='x',rotation=60);ax.legend(fontsize=7);ax.set_title('AI WAIT versus source/quote/fill state counts');save(fig,'09-state-reasons')
 fig,axs=plt.subplots(1,2,figsize=(12,5));pair=[selected,selected[:-2]+'5m']
 bars(axs[0],[data[a]['capture']['3']['rate'] for a in pair],'+3 Capture: same selected model',pair);bars(axs[1],[data[a]['decisionEvaluations'] for a in pair],'Decision compute count',pair);save(fig,'10-1m-vs-5m')
 ab=['RIDGE_FULL_STOP_1m','RIDGE_NO_SEQUENCE_STOP_1m','RIDGE_NO_PREVIOUS_STOP_1m','RIDGE_NO_RECENT_STOP_1m'];fig,axs=plt.subplots(1,2,figsize=(13,5));bars(axs[0],[data[a]['capture']['3']['rate'] for a in ab],'Ablation +3 capture',ab);bars(axs[1],[data[a]['30']['returnNet']['mean'] for a in ab],'Ablation conditional return30',ab);save(fig,'11-ablation')
 sessions=e.read(m/'session-metrics.json');fig,axs=plt.subplots(1,2,figsize=(13,4))
 for a in ['B0_RETRY_1m',selected]:
  ss=[x for x in sessions if x['arm']==a];axs[0].plot([x['capture']['3']['rate'] for x in ss],label=a);axs[1].plot([x['populationQuality'] for x in ss],label=a)
 axs[0].set_title('Session capture');axs[1].set_title('Fixed-population quality');[ax.legend(fontsize=7) for ax in axs];save(fig,'12-stability')
 fig,axs=plt.subplots(1,2,figsize=(13,5))
 for ax,t in zip(axs,[3,5]):bars(ax,[data[a]['capture'][str(t)]['lowThenHigh']['pct'] for a in arms],f'+{t} LOW_THEN_HIGH capture')
 save(fig,'13-low-then-high')
 att=e.read(m/'attribution.json')['RIDGE_FULL'][:20];fig,ax=plt.subplots(figsize=(10,6));ax.barh([x['feature'] for x in att][::-1],[x['absoluteBuyUtilityWeight'] for x in att][::-1]);ax.set_title('Ridge entry-quality absolute standardized coefficient weights');save(fig,'14-attribution')
 fig,axs=plt.subplots(1,2,figsize=(13,5));bars(axs[0],[data[a]['badBuy']['negativeReturn30'] for a in arms],'BUY with observed negative return30');bars(axs[1],[data[a]['capture']['3']['missed'] for a in arms],'Missed +3 winners');save(fig,'15-bad-buy-missed-winners')
 by={r['id']:r for r in rows};examples=[]
 for good in [True,False]:
  candidates=[t for t in tr[selected] if t['entryId'] and labs[t['entryId']]['labels']['return30'] is not None and (labs[t['entryId']]['labels']['return30']>0)==good]
  if not candidates:continue
  trade=sorted(candidates,key=lambda t:e.f.digest(t['opportunity']))[0];r=by[trade['entryId']];pa=paths[r['opportunity']];today=[x for x in pa['today'] if x[0]<r['minute']];assert all(x[0]<r['minute'] for x in today)
  fig,axs=plt.subplots(1,2,figsize=(13,4))
  for ax,path,title in [(axs[0],pa['previous'],'Previous session full observed1m'),(axs[1],today,'Today CLOSED prefix only')]:
   if path:ax.plot([x[0] for x in path],[x[4] for x in path]);ax.set_title(title)
  save(fig,'16-case-'+('positive' if good else 'negative'));examples.append({'trade':trade,'decisionPrefix':today,'previous':pa['previous'],'futureOutcomeSeparate':labs[trade['entryId']]['labels']})
 e.write(root/'examples.json',examples)
 header=['Entry','BUY','NoEntry','MFE30 med','MAE30 med','MaxDD30 med','Return30 mean','Return60 mean','End mean','+1 Capture','+2 Capture','+3 Capture','+4 Capture','+5 Capture']
 vals=[]
 for a,z in data.items():vals.append([a,z['BUY'],z['noEntry'],z['30']['MFE']['median'],z['30']['MAE']['median'],z['30']['MaxDD']['median'],z['30']['returnNet']['mean'],z['60']['returnNet']['mean'],z['returnEnd']['mean']]+[z['capture'][str(t)]['rate'] for t in range(1,6)])
 with (root/'comparison.csv').open('w') as fh:w=csv.writer(fh);w.writerow(header);w.writerows(vals)
 fmt=lambda x:'UNAVAILABLE' if x is None else f'{x:.3f}' if isinstance(x,float) else str(x)
 lines=['# NEW LONG Entry Pattern v2 — Development','',gate['status'],'',f'Primary chosen on selection dates before evaluation: **{selected}**. Judgment: **{gate["performanceJudgment"]}**.','',
 '144日を入力監査。既存fit55 / embargo5 / selection20 / embargo5 / evaluation59を再利用。Independent OOSではない。Frozen Selector、Dictionary、v1 decision/model/threshold/clockは不変。Dictionaryはv2入力から除外、廃棄・FAIL認定ではない。','',
 '新契約: 同一symbol×session Opportunityを30 session-active minutes監視。11:30選出は12:31以降のclosed1mで再開、昼休みは時計停止。前場11:00選出は既に30分使うため後場への監視時間は残らない。15:25以降のpre-closeへ新規注文しない。1m主評価、同一modelの5m比較。最終tickは強制BUYせずEXPIRE=0。','',
 'B0は同じquote freshness<=5m、同じgrid、同じ実1m Open+5bps、同じunfilled retry。モデルはWHOやfeature availabilityで候補を事前削除しない。MODEL_WAIT / STALE_OR_MISSING_REFERENCE / BUY_ATTEMPT_UNFILLED(reason=NO_SOURCE_TRADE) / EXPIRED(reason=SESSION_BOUNDARY or MONITOR_BUDGET)を分離。','',
 '前日full observed1mと当日open→closed-prefixを保持。fullとは保存source内の実record全体で、全minute約定存在を意味しない。欠測はmask、価格補間なし。5m observed OHLCVは実recordだけを集約し、partial5とstrict complete5を別状態にする。v1 Reader/Gateは変更せずv2 adapterで部分情報を表現。VWAPはobserved prefix値でsource completeness認証とは別。','',
 'Raw numeric入力: 前日/当日全1m OHLC・Volume・Trading Valueの固定seed24次元線形projection、直近15分のraw-normalized6channel、全日/AM/PM/late/local1/2/3/5/10/15/30/60統計、1/3/5/10/15/30分signal前path、Swing確認・価格構造・RVOL/Value変化。完全raw pathはevaluator-only archiveに置き、decision/modelへは前日全体と当日prefixだけを渡す。画像modelなし。','',
 '学習: Ridge(lambda10)と固定小型Tree(60 iterations,7 leaves,min_leaf100,l2=10)。return30/MFE30/MAE30/MaxDD30を別head、買い品質U=return30+.15*min(MFE30,10)+.3*MAE30+.2*MaxDD30−.002*active delay。全て30 active-minute horizonへ統一。別headで将来実行可能tickの実現最大UとEXPIRE=0のmaxを教師とする。これはoptimistic continuation proxyであり、Bellman最適policyを解いたと主張しない。futureは教師専用、evaluation labelsは学習・選択に使用しない。未知のfuture rewardはcontinuation教師をcensor。','',
 'Quality-onlyは予測U>=0でBUY。STOPは予測U>=max(0,予測continuation)でBUY。それ以外WAIT、期限でEXPIRE。4候補をselection20日で事前定義目的により選択し、その後evaluationを一度比較。NO_SEQUENCE/NO_PREVIOUS/NO_RECENTは固定Ridge STOP ablation。Pattern MemoryとWHO追加はPrimaryの後の別ablationへ延期し、今回のPrimaryに混ぜていない。','',
 '結果表の30/60はsession-active minutesで、v1 wall-clock値を上書きしない。B2はv1のBUY timestamp/price/Captureを完全保存し、同じ新horizonで補助比較。MFE/MAE/MaxDD/returnはcomplete source-slot caseのみ、Hitは全BUY分母の観測下限、Captureは従来session-end Selector winner固定分母。MaxDDは確認できるOHLC順序の下落で、同一足内順序のadverse boundもlabelに保存。','',
 '## Comparison','', '| '+' | '.join(header)+' |','|'+'---|'*len(header)]
 lines+=['| '+' | '.join(map(fmt,row))+' |' for row in vals]
 lines+=['','## Limitations / safety','','Sparse/partial minute data cannot distinguish no trade from source acquisition gap without external completeness metadata. Exact prior session outside authorized144 remains unavailable, never backfilled. Fixed projection is a numeric representation, not proof of human-like chart understanding. Frozen upstream same-day Daily metadata limitation inherited; this study does not independently certify upstream prospective PIT. Prior Development reused and prior outcomes known; no independent OOS claim.','',
 'Weights are precommitted. weight-sensitivity.json changes the upside coefficient 0/.15/.3 only for descriptive scoring of the same selected decisions; no result-based retune. Conditional means do not establish success by themselves; read fixed-population capture, throughput, unknown outcomes and session plots. Models/targets/scores/selection lock/ablation saved.','',
 'Completion verification: focused tests, regression, dual substrate manifests and dual measurement manifests in ci-receipt.json. Holdout244 untouched, all9 Safety false, no EXIT/capital/trading/merge/promotion.','']
 for pic in pics:lines += [f'![{pic}]({pic}.png)','']
 (root/'REPORT-ja.md').write_text('\n'.join(lines)+'\n')
 reg=e.read(root/'regression/regression.json');assert reg['status']=='PASS';focused=re.findall(r'Ran (\d+) tests',(root/'focused.log').read_text());assert focused
 final={'status':gate['status'],'head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'runId':os.environ.get('GITHUB_RUN_ID'),'tests':int(focused[-1]),'regression':reg['status'],'regressionCount':sum(x['counts']['pass'] for x in reg['suites']),'substrateDeterminism':True,'measurementDeterminism':True,'v1CaptureAndFillsPreserved':True,'holdoutOpened':0,'safety':p['safety'],'limitations':['Descriptive reused Development','Inherited frozen upstream Daily metadata','Optimistic continuation proxy','Pattern memory and WHO deferred']}
 e.write(root/'completion-gate.json',final);e.write(root/'ci-receipt.json',final);e.write(root/'report-manifest.json',{x.name:e.sha(x) for x in sorted(root.iterdir()) if x.is_file()})
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--evidence',required=True);a.add_argument('--replay',required=True);x=a.parse_args();report(x.evidence,x.replay)
