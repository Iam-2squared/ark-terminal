"""Deterministic outcome-only tables and figures. No model ranking or selection."""
import csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scripts import phase57_entry_extended as e
plt.rcParams['svg.hashsalt']='phase57-entry-extended-v1'

def report(root):
 root=Path(root);s=e.read(root/'summary.json');arms=e.ARMS;main=['IMMEDIATE','CURRENT','E5'];figures=[]
 colors=['#375b8c' if a=='IMMEDIATE' else '#bb7939' if a=='CURRENT' else '#14816e' if a=='E5' else '#a6b0ba' for a in arms]
 def save(fig,name):
  fig.tight_layout();fig.savefig(root/(name+'.png'),dpi=140,metadata={'Software':'Ark outcome evaluation'});fig.savefig(root/(name+'.svg'),metadata={'Date':None});plt.close(fig);figures.append(name)
 def bar(ax,vals,title,subset=arms):
  cs=[colors[arms.index(a)] for a in subset];ax.bar(subset,[np.nan if v is None else v for v in vals],color=cs);ax.set_title(title);ax.set_ylabel('%');ax.tick_params(axis='x',rotation=45);ax.grid(axis='y',alpha=.2)
 for n,key in [(1,'MFE'),(2,'MAE'),(3,'MaxDD')]:
  fig,ax=plt.subplots(figsize=(10,4));bar(ax,[s[a]['30'][key]['median'] for a in arms],f'30m {key} median | complete-source cases only');save(fig,f'{n:02d}-30m-{key}')
 for n,h in [(4,'30'),(5,'60')]:
  fig,ax=plt.subplots(figsize=(11,5))
  for t in e.LEVELS:ax.plot(arms,[s[a][h]['hit'][str(t)]['rate'] for a in arms],marker='o',label=f'+{t}%')
  ax.set_title(f'{h}m observed Hit / all BUY (%) | unknown != miss; lower bounds');ax.set_ylim(0,100);ax.legend();ax.grid(alpha=.2);save(fig,f'{n:02d}-{h}m-hit')
 fig,ax=plt.subplots(figsize=(11,5))
 for t in e.LEVELS:ax.plot(arms,[s[a]['capture'][str(t)]['rate'] for a in arms],marker='o',label=f'+{t}%')
 ax.set_title('Session-end Opportunity Capture / frozen Selector winners (%)');ax.set_ylim(0,100);ax.legend();ax.grid(alpha=.2);save(fig,'06-opportunity-capture')
 for n,key in [(7,'MAE'),(8,'MaxDD')]:
  fig,axs=plt.subplots(1,2,figsize=(12,5))
  for ax,h in zip(axs,['30','60']):
   for a in arms:
    x=s[a][h][key]['median'];y=s[a][h]['MFE']['median']
    if x is not None and y is not None:ax.scatter(x,y,color=colors[arms.index(a)]);ax.annotate(a,(x,y),fontsize=8)
   ax.set_xlabel(key+' median %');ax.set_ylabel('MFE median %');ax.set_title(h+'m | conditional complete-source cohort');ax.grid(alpha=.2)
  save(fig,f'{n:02d}-MFE-vs-{key}')
 fig,axs=plt.subplots(2,3,figsize=(13,8))
 for row,h in zip(axs,['30','60']):
  for ax,key in zip(row,['MFE','MAE','MaxDD']):bar(ax,[s[a][h][key]['median'] for a in main],h+'m '+key+' median',main)
 save(fig,'09-main-comparison')
 fig,axs=plt.subplots(1,2,figsize=(13,5))
 for h in ['30','60']:
  axs[0].plot(arms,[s[a][h]['returnNet']['mean'] for a in arms],marker='o',label=h+'m')
  axs[1].plot(arms,[s[a]['pairedCompleteReturn'][h]['mean'] for a in arms],marker='o',label=h+'m')
 axs[0].set_title('Net return means | separate complete cohorts');axs[1].set_title('Net return means | same BUY complete at both horizons')
 for ax in axs:ax.set_ylabel('%');ax.legend();ax.tick_params(axis='x',rotation=45);ax.grid(alpha=.2)
 save(fig,'10-horizon-return')
 fig,axs=plt.subplots(1,2,figsize=(13,5))
 for ax,h in zip(axs,['30','60']):
  bottom=np.zeros(len(arms))
  for k in ['complete','censored','unavailable']:
   vals=[s[a][h]['coverage'][k] for a in arms];ax.bar(arms,vals,bottom=bottom,label=k);bottom+=vals
  ax.set_title(h+'m BUY outcome coverage');ax.legend();ax.tick_params(axis='x',rotation=45)
 save(fig,'11-coverage')
 fig,axs=plt.subplots(1,2,figsize=(13,5))
 for ax,h in zip(axs,['30','60']):
  ax.plot(arms,[s[a][h]['MaxDD']['median'] for a in arms],marker='o',label='Confirmed chronology')
  ax.plot(arms,[s[a][h]['MaxDDAdverseBound']['median'] for a in arms],marker='o',label='Adverse intrabar order bound')
  ax.set_title(h+'m MaxDD bounds (1m OHLC order unknown)');ax.legend();ax.tick_params(axis='x',rotation=45);ax.set_ylabel('%')
 save(fig,'12-MaxDD-bounds')
 def fmt(x):return 'UNAVAILABLE' if x is None else f'{x:.3f}' if isinstance(x,float) else str(x)
 def table(name,header,rows):
  with (root/(name+'.csv')).open('w',newline='') as fh:w=csv.writer(fh);w.writerow(header);w.writerows(rows)
  return ['| '+' | '.join(header)+' |','|'+'---|'*len(header)]+['| '+' | '.join(fmt(x) for x in row)+' |' for row in rows]
 lines=['# NEW LONG Entry — Extended Outcome / Capture Measurement','','既存decision固定の追加評価。モデル学習・推論・BUY/WAIT再実行は0。Immediate / Current / E5を図09で強調。全10方式を同じ評価Opportunity 2,155件から比較。','',
 'Hit Rate = 各方式の全BUYを分母、horizon内に実データで到達確認できた件数を分子。censored/unavailableで未確認のcaseはunknownで、未到達と断定しない。表示率は観測下限、上限・complete-only率・分子分母をdenominators.jsonに保存。部分観測で確認できたhitは含める。','',
 'Capture = 既存と完全に同じsession-end Selector winner固定分母。Entry後session-end MFEで捕捉判定。30m/60m Captureへ定義を変更していないため両表のCapture列は同じ。未Entry・不明は捕捉成功にしない。','',
 '30m/60mは壁時計時間。昼休みをまたがず、前場/日中session末尾で打切り。完全観測は既存のstrict 5m source slot＋endpoint契約を継承し、毎1分の約定存在を意味しない。無約定分足は補間しない。終端11:30/15:00/15:30の実auctionは既存契約どおり。','',
 'Entry priceは保存値（実1m Open＋5bps）。MFE/MAEはEntryを0とし上昇/下落がなければ0。Returnは終端の実Closeにexit-reference 5bpsを控除。給付戻しgivebackはMFE−net return（percentage points）。価格・時間proxyの研究値で、実約定認証ではない。','',
 '**MaxDDはMAEと別**。Entry価格から開始するrunning peakに対し、前の足のpeak→今のLow、今のOpen→Low、High→Closeという順序が確認できる下落を主表に表示。同じ1m内のHigh→Lowの順序は不明なので、その順序を仮定した最大下落幅を別列MaxDDAdverseBoundに保存。真のtick MaxDDは両者の間。主表を正確なtick MaxDDと解釈しない。','',
 '分布はcomplete caseのみ。Hitの全BUY分母やCaptureのSelector winner分母とは異なる。CurrentはBUY60件と少なく条件付き分布だけで優劣を断定しない。これは再利用Development内の記述的評価で独立OOSではない。','']
 for h in ['30','60']:
  header=['Entry','BUY','MFE med','MAE med','MaxDD med']+[f'+{t} Hit' for t in e.LEVELS]+[f'+{t} Capture' for t in e.LEVELS]
  rows=[[a,s[a]['buyTotal']]+[s[a][h][k]['median'] for k in ['MFE','MAE','MaxDD']]+[s[a][h]['hit'][str(t)]['rate'] for t in e.LEVELS]+[s[a]['capture'][str(t)]['rate'] for t in e.LEVELS] for a in arms]
  lines+=['## '+h+'m（件数以外は%）','']+table(h+'m-comparison',header,rows)+['']
 header=['Entry','30m Mean','30m Median','30m Positive','60m Mean','60m Median','60m Positive']
 rows=[[a]+[s[a][h]['returnNet'][k] for h in ['30','60'] for k in ['mean','median','positiveRate']] for a in arms]
 lines+=['## Horizon Return (%)','']+table('returns',header,rows)+['']
 header=['Entry','Horizon','BUY','Path available','Complete','Censored','Unavailable','Reasons']
 rows=[[a,h]+[s[a][h]['coverage'][k] for k in ['buyTotal','pathAvailable','complete','censored','unavailable']]+[str(s[a][h]['coverage']['reasons'])] for a in arms for h in ['30','60']]
 lines+=['## Coverage / 母集団差','']+table('coverage',header,rows)+['','30mと60m Return主表は母集団が異なる。図10右は両horizonでcompleteの同一BUYへ揃えた補助診断。summary.jsonに各nを保存。','']
 # Flat numerator/denominator table for every requested threshold.
 headers=['Entry','Metric','Horizon','Threshold','Numerator','Denominator','Unknown','Rate']
 rows=[]
 for a in arms:
  for t in e.LEVELS:
   c=s[a]['capture'][str(t)];rows.append([a,'CAPTURE','SESSION_END',t,c['captured'],c['selectorWinnerDenominator'],c['unknownEntered'],c['rate']])
   for h in ['30','60']:
    x=s[a][h]['hit'][str(t)];rows.append([a,'HIT',h,t,x['observedHits'],x['buyDenominator'],x['unknown'],x['rate']])
 table('denominator-table',headers,rows)
 lines+=['## Reproduction / Safety','','reproduction-audit.json: PASS。保存decision/model/score/feature/outcome manifestを入力時検証。BUY件数、全方式MAE30 count/median/mean/p05、既存+1/+2/+3/+5 Capture分子分母・率を再現。+4は同じ式の追加threshold。各BUYのraw sourceに対する30/60mとsession-end extremaの再現も監査。','',
 '計測データと全図を2回生成してmanifest照合。CIの最終tests/regression/determinismはcompletion-gate.jsonとci-receipt.jsonを参照。','',
 'Common Holdout244・他sealed開封0、Safety9全false、Frozen Selector/Entry/Dictionary/EXIT/Capital Allocation変更なし。STOP、昇格なし。','']
 for name in figures:lines += [f'![{name}]({name}.png)','']
 (root/'REPORT-ja.md').write_text('\n'.join(lines)+'\n')
