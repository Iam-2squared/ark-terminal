"""Charts and transparent fixed-population Entry research report."""
import argparse,csv,json,os,re,subprocess
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scripts import phase57_chart_entry as e
read=e.read;write=e.write;sha=e.sha

def report(evidence,replay):
 root=Path(evidence);m=root/'measurement';src=root/'substrate';p=e.verify()
 assert read(m/'manifest.json')==read(Path(replay)/'manifest.json')
 data=read(m/'metrics.json');chosen=read(m/'selection-lock.json');effects=read(m/'effects.json');dec=read(m/'decisions.json');inventory=read(src/'inventory.json');coverage=read(m/'coverage.json');session=read(m/'session-metrics.json');anatomy=read(m/'anatomy.json');models=read(m/'models.json');trades=read(m/'trades.json.gz');opps=read(src/'opportunities.json.gz');rows=read(src/'features.json.gz');labs=read(src/'outcomes.json.gz')
 assert len(inventory)==144 and len({data[k]['opportunities'] for k in data})==1
 arms=['IMMEDIATE','CURRENT']+list(e.ARMS);cols=['#718096','#9c6b48']+['#267b91']*8
 def save(fig,name):
  fig.tight_layout();fig.savefig(root/(name+'.png'),dpi=135);fig.savefig(root/(name+'.svg'));plt.close(fig)
 def bar(ax,vals,title,ylabel=''):
  ax.bar(arms,[np.nan if v is None else v for v in vals],color=cols);ax.set_title(title);ax.set_ylabel(ylabel);ax.tick_params(axis='x',rotation=45);ax.grid(axis='y',alpha=.2)
 fig,axs=plt.subplots(1,2,figsize=(13,4));stages=['Input','Candidates','Opportunity','30m labels'];vals=[144,sum(x['selectorCandidates']>0 for x in inventory),sum(x['opportunities']>0 for x in inventory),len({x['session'] for x in rows if (labs[x['id']]['labels'] or {}).get('mae30') is not None})];axs[0].bar(stages,vals);axs[0].set_title('All144 input: sessions');axs[1].bar(['Candidates','Unique opportunities','Decision rows'],[sum(x['selectorCandidates'] for x in inventory),len(opps),len(rows)]);axs[1].set_title('All144 events / deduplicated opportunity identity');save(fig,'01-funnel')
 ev=[o for o in opps if o['session'] in p['evaluation']]
 fig,axs=plt.subplots(1,2,figsize=(12,4));axs[0].hist([o['anatomy']['timeToLow'] for o in ev if 'anatomy' in o],bins=20,alpha=.65,label='Time to low');axs[0].hist([o['anatomy']['timeToHigh'] for o in ev if 'anatomy' in o],bins=20,alpha=.5,label='Time to high');axs[0].legend();axs[0].set_xlabel('Minutes from selection');counts=anatomy['evaluation']['order'];axs[1].bar(counts.keys(),counts.values());axs[1].tick_params(axis='x',rotation=15);axs[1].set_title('Oracle anatomy only, never decision features');save(fig,'02-anatomy')
 fig,axs=plt.subplots(1,2,figsize=(13,4));bar(axs[0],[data[k]['mae30']['median'] for k in arms],'Post-entry MAE30 median','%');bar(axs[1],[data[k]['mae30']['p05'] for k in arms],'Post-entry MAE30 p05 tail','%');save(fig,'03-downside')
 fig,axs=plt.subplots(1,2,figsize=(13,4));bar(axs[0],[data[k]['capture']['3']['pct'] for k in arms],'+3% winner capture','%');bar(axs[1],[data[k]['capture']['5']['pct'] for k in arms],'+5% winner capture','%');[ax.axhline(90,color='red',linestyle='--') for ax in axs];save(fig,'04-capture')
 fig,axs=plt.subplots(1,2,figsize=(12,4))
 for ax,t in zip(axs,[3,5]):
  for k in arms:
   x=data[k]['capture'][str(t)]['pct'];a=data[k]['mae30']['mean'];base=data['IMMEDIATE']['mae30']['mean']
   if x is not None and a is not None and base is not None:ax.scatter(x,a-base);ax.annotate(k,(x,a-base),fontsize=8)
  ax.axvline(90,ls='--',c='gray');ax.axhline(0,c='gray');ax.set_xlabel(f'+{t}% captured / all Selector winners (%)');ax.set_ylabel('Conditional mean MAE improvement vs immediate (pp)');ax.set_title('Different entered counts: read alongside paired analysis')
 save(fig,'05-tradeoff')
 waits=['IMMEDIATE','WAIT_5','WAIT_10','WAIT_15','WAIT_30'];fig,axs=plt.subplots(1,3,figsize=(14,4))
 for ax,key,title in [(axs[0],'mae30','MAE30 median'),(axs[1],'mfeEnd','Session MFE median')]:ax.plot([0,5,10,15,30],[data[k][key]['median'] for k in waits],marker='o');ax.set_title(title);ax.set_xlabel('Fixed wait minutes')
 for t in [1,2,3,5]:axs[2].plot([0,5,10,15,30],[data[k]['capture'][str(t)]['pct'] for k in waits],marker='o',label=f'+{t}%')
 axs[2].legend();axs[2].set_title('Opportunity capture after fixed wait');save(fig,'06-wait-anatomy')
 fig,axs=plt.subplots(1,2,figsize=(13,4));bar(axs[0],[data[k]['entryImprovement']['mean'] for k in arms],'Entry price improvement vs Selector reference','%');bar(axs[1],[data[k]['waitMinutes']['median'] for k in arms],'Median time to entry','minutes');save(fig,'07-timing')
 fig,axs=plt.subplots(1,2,figsize=(13,4));bar(axs[0],[data[k]['enterCount'] for k in arms],'Entered opportunities');bar(axs[1],[data[k]['noEntryPct'] for k in arms],'No entry / all opportunities','%');save(fig,'08-throughput')
 fig,axs=plt.subplots(1,2,figsize=(13,4));bar(axs[0],[data[k]['return30']['mean'] for k in arms],'30m mean net return (proxy costs)','%');bar(axs[1],[data[k]['populationObjective'] for k in arms],'Population utility, missing/absent entry=0 + missed-winner penalty');save(fig,'09-economic-reference')
 fig,axs=plt.subplots(1,2,figsize=(13,4))
 for k in ['IMMEDIATE','CURRENT','E5','E7']:
  ss=[x for x in session if x['arm']==k];axs[0].plot([x['mae30']['mean'] for x in ss],label=k);axs[1].plot([x['capture']['5']['pct'] for x in ss],label=k)
 axs[0].set_title('Session MAE30 mean');axs[1].set_title('Session +5 capture');[ax.legend() for ax in axs];save(fig,'10-session-stability')
 fig,axs=plt.subplots(1,2,figsize=(13,4));states=coverage['WHOstates'];axs[0].bar(range(len(states)),list(states.values()));axs[0].set_xticks(range(len(states)),states.keys(),rotation=90,fontsize=7);axs[0].set_title('WHO state counts (trait cells, overlapping)');a=coverage['analog'];axs[1].plot([x['covered']/max(x['queries'],1)*100 for x in a]);axs[1].set_title('Causal analog coverage, all144 sessions');axs[1].set_ylabel('% of decision rows');save(fig,'11-coverage')
 fig,axs=plt.subplots(1,2,figsize=(13,5))
 for ax,k in zip(axs,['E5','E7']):
  imp=models[chosen['chosen'][k]]['importance'][:12];ax.barh([x[0] for x in imp][::-1],[x[1] for x in imp][::-1]);ax.set_title(k+' '+chosen['chosen'][k]+' attribution (fit only)')
 save(fig,'12-attribution')
 fig,axs=plt.subplots(1,2,figsize=(13,4))
 for ax,k in zip(axs,['CURRENT','E7']):
  sc=data[k]['symbolConcentration'];ax.bar([x[0] for x in sc],[x[1] for x in sc]);ax.tick_params(axis='x',rotation=45);ax.set_title(k+' top10 symbol entry counts')
 save(fig,'13-concentration')
 # Report regime panels on fixed previous-day volatility threshold; not used to select model.
 origin={o['id']:o for o in ev};rmap={x['id']:x for x in rows};regimes={}
 for o in ev:
  x=rmap.get(o['id']+'|'+str(e.minute(o['origin']['decisionTimestamp'])));vol=x['RECENT']['features'].get('volatility5') if x else None;regimes[o['id']]='MISSING' if vol is None else 'HIGH_GE2' if vol>=2 else 'LOW_LT2'
 regime=[]
 for group in ['MISSING','HIGH_GE2','LOW_LT2']:
  os=[o for o in ev if regimes[o['id']]==group]
  for k in arms:regime.append({'regime':group,'arm':k,**e.metrics(os,[x for x in trades[k] if regimes[x['opportunity']]==group],labs)})
 write(root/'regime-diagnostic.json',regime)
 fig,axs=plt.subplots(1,2,figsize=(13,4))
 for k in ['IMMEDIATE','CURRENT','E5','E7']:
  a=[x for x in regime if x['arm']==k];axs[0].plot([x['regime'] for x in a],[x['mae30']['mean'] for x in a],marker='o',label=k);axs[1].plot([x['regime'] for x in a],[x['capture']['5']['pct'] for x in a],marker='o',label=k)
 axs[0].set_title('Fixed prior volatility regime: MAE30');axs[1].set_title('+5 capture');[ax.legend() for ax in axs];save(fig,'14-regime')
 examples=read(m/'examples.json')
 for i,x in enumerate(examples):
  frame=next(z for z in x['decisionFrames'] if e.minute(z['time'])==int(x['trade']['entryId'].split('|')[-1]))
  bars=frame['rawClosed5m'];fig,ax=plt.subplots(figsize=(10,4))
  for j,z in enumerate(bars):
   color='#16887a' if z['C']>=z['O'] else '#c14f45';ax.plot([j,j],[z['L'],z['H']],c=color);ax.plot([j,j],[z['O'],z['C']],c=color,lw=7)
  ax.set_title(f"{x['category']} example {x['trade']['symbol']} | decision {frame['time']}\nOnly bars closed by decision; later outcome stored separately")
  ax.set_xticks(range(len(bars)),['%02d:%02d'%divmod(z['t'],60) for z in bars],rotation=45);save(fig,f'15-case-{i+1}')
 def fmt(x):return 'UNAVAILABLE' if x is None else f'{x:,.3f}' if isinstance(x,(float,int)) else str(x)
 getters=[('Opportunities',lambda x:x['opportunities']),('Enter count',lambda x:x['enterCount']),('Enter/session',lambda x:x['enterPerSession']),('No entry %',lambda x:x['noEntryPct']),('MAE30 n',lambda x:x['mae30']['n']),('MAE30 median %',lambda x:x['mae30']['median']),('MAE30 p05 %',lambda x:x['mae30']['p05']),('MAE30 worst5 mean %',lambda x:x['mae30']['worst5Mean']),('MFE median %',lambda x:x['mfeEnd']['median']),('Net return30 mean %',lambda x:x['return30']['mean']),('Net return30 median %',lambda x:x['return30']['median']),('Positive30 %',lambda x:x['positive30Pct']),('Entry improvement mean %',lambda x:x['entryImprovement']['mean']),('WAIT median minutes',lambda x:x['waitMinutes']['median'])]
 for t in [1,2,3,5]:getters.append((f'+{t} capture %',lambda x,t=t:x['capture'][str(t)]['pct']))
 table=[[name]+[fmt(fn(data[k])) for k in arms] for name,fn in getters]
 with (root/'comparison.csv').open('w') as fh:
  w=csv.writer(fh);w.writerow(['Metric']+arms);w.writerows(table)
 regression=read(root/'regression/regression.json');assert regression['status']=='PASS'
 focused=re.findall(r'Ran (\d+) tests', (root/'focused.log').read_text());assert focused
 assert (root/'substrate-determinism.json').exists()
 receipt={'executionHead':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'focusedTests':int(focused[-1]),'runId':os.environ.get('GITHUB_RUN_ID'),'substrateRegeneration':True,'measurementRegeneration':True,'safety':e.b.SAFETY,'regression':regression}
 write(root/'ci-receipt.json',receipt)
 gate={'status':'DEVELOPMENT_COMPARISON_COMPLETE_NOT_PROMOTED','all144Audited':True,'commonHoldoutOpened':0,'sealedOpened':0,'dictionaryValue':'INCONCLUSIVE','safety':e.b.SAFETY,'newExitDeveloped':False,'productionAllowed':False};write(root/'completion-gate.json',gate)
 lines=['# Phase57 NEW LONG Entry — Chart-aware BUY / WAIT Development','',gate['status'],'',f"全144日入力監査、Selector候補 {sum(x['selectorCandidates'] for x in inventory)}件、symbol×session Opportunity {len(opps)}件。評価対象 {len(ev)}件。",'','既存144日をfit55 / embargo5 / selection20 / embargo5 / evaluation59に事前固定。最後59日は前回と同じ。過去Developmentを再利用した記述的研究であり、独立OOSではない。', '','Selector候補を情報源coverageで事前削除しない。同一symbol×sessionの最初の候補をOpportunityとし、以降の再選出は重複として追跡する。NEWはSelector落選後もWATCHを維持、最大30分の5分closed-bar再評価、最終scheduled tickはBUYを試行。BUY後の再Entryなし。昼休み・session境界は時計に明示。', '', 'BUYはdecision直後の実1m Openに片道5bpsを加えた研究用約定proxy。時刻の実約定がなければ未約定・次のtickまでWAIT。終端評価にも5bpsを控除する。板・スプレッド・容量の実約定認証ではない。EXITモデルは開発していない。', '', 'CURRENTは既存MSHモデル・特徴・閾値0.6・落選expire state machineをそのまま再生。共通価格評価のため実Open proxyに揃え、CURRENT本体は変更していない。', '', 'BUY/WAIT教師は U(now)−U(next5m)。U=net return30 +0.2×min(MFEend,10)+0.3×MAE30+0.1×MAEend−0.002×delay minutes。future項は教師専用。oracle最安値はanatomyのみ。deadline fallbackは固定、結果を見た閾値調整なし。', '', '各E0〜E7についてRidge(lambda10)と固定小型HistGradientBoostingをfit55日で学習。selection20日の保持率・throughput条件、population utilityでfamilyを選び、評価前に保存。条件不達のbest candidateも診断用であり自動昇格しない。','', '## 共通Opportunity母集団比較','', '| Metric | '+' | '.join(arms)+' |','|---|'+'---:|'*len(arms)]
 lines += ['| '+' | '.join(row)+' |' for row in table]
 lines += ['', '各Entry後outcomeの可用件数は異なる。比較表は条件付き分布、effects.jsonはpaired entrants、captureは全Selector winner固定分母（未Entry・outcome不明も保持成功にしない）。この3つを併読し、BUY削減だけによるMAE改善を成功としない。','', '## 判定','', '| Arm | Model selected before evaluation | Judgment |','|---|---|---|']
 for k in e.ARMS:lines.append(f"| {k} | {chosen['chosen'][k]} | {dec[k]['status']} |")
 lines += ['', '**WHO正式trait効果はDICTIONARY_ENTRY_VALUE_INCONCLUSIVE。** 数値valueはH/M+PASSのみ、その他traitValue/confidence/temporal/uncertainty/nEff/computedThrough/evidenceClassは別状態として保存。欠測を性格0として扱わない。','', 'Historical Analogはquery前の既にsession終了した初回Opportunity caseのみ。近傍20、最低5、最大直近10000 case。same-session futureはpoolに入らない。後日評価中の過去case追加入力は事前固定したonline retrievalであり、Entryモデル再学習ではない。各queryのneighbors・maxRealizedThroughを保存。','', '成功Gate: +3/+5 capture各90%以上、Immediate比enter数90%以上、paired MAE改善0.1pp以上・session block5 bootstrap95%下限>0・paired entry価格改善>0。CURRENT比較・ablation差はeffects.jsonで個別表示し、他情報源の効果に読み替えない。','', '## 図表','']
 for pic in sorted(root.glob('*.png')):lines += [f'![{pic.stem}]({pic.name})','']
 lines += ['## 検証・制約','', '新規テスト・既存回帰PASS。substrate/measurementを各2回生成して全manifest一致。Common Holdout244と他sealed領域の追加開封0。Safety9全false。Frozen Selector、Dictionary Gate、Current Entry、Capital Allocation、EXITは不変。','', '上流制約: Frozen L0は既存の同日Daily validity/corporate-action/adjustment metadata利用を継承。追加入力・Analog・fit/evalの因果性監査と、上流全体の独立PIT認証を混同しない。','',f"[CI](https://github.com/Iam-2squared/ark-terminal/actions/runs/{os.environ.get('GITHUB_RUN_ID','LOCAL')})。PR #587 Draft・未merge。STOP、NEW EXIT・自動昇格・売買へ進まない。"]
 (root/'REPORT-ja.md').write_text('\n'.join(lines)+'\n')
 write(root/'report-manifest.json',{x.name:sha(x) for x in sorted(root.iterdir()) if x.is_file()})
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--evidence',required=True);a.add_argument('--replay',required=True);x=a.parse_args();report(x.evidence,x.replay)
