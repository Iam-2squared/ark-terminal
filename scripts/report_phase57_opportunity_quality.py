"""Presentation and complete-path breadth supplement from immutable quality ledger."""
import argparse,collections,json
from pathlib import Path
from scripts import phase57_opportunity_quality as q

def fmt(v):return 'N/A' if v is None else f'{v:.3f}' if isinstance(v,float) else str(v)
def percent(x):return None if x is None else 100*x
def rr(x):return f"{x['n']}/{x['denominator']} ({fmt(percent(x['rate']))}%)"
def run(source,out):
 source=Path(source);out=Path(out)
 if out.exists():raise FileExistsError(out)
 s=q.read(source/'summary.json');rows=q.read(source/'ledger.json.gz');manifest=q.read(source/'manifest.json')
 for p,h in manifest['outputPins'].items():assert q.sha(source/p)==h,p
 groups=q.by_timestamp(rows);supplement={}
 for n in range(1,6):
  gs={t:rs for t,rs in groups.items() if len(rs)==n};supplement[str(n)]={}
  for h in ('30','SESSION'):
   complete={t:rs for t,rs in gs.items() if all(r['windows'][h]['complete'] for r in rs)}
   supplement[str(n)][h]={'allTimestampN':len(gs),'allPathsCompleteTimestampN':len(complete),'breadth':q.breadth(complete,h)}
 # Independent ledger reconciliation, without replay or decisions.
 assert len(rows)==3508 and sum(len(rs) for rs in groups.values())==3508
 for h in ('5','10','15','30','60','SESSION'):
  assert q.aggregate(rows,h)==s['cohorts']['TOTAL'][h]
  for r in rows:
   w=r['windows'][h]
   assert (w['returnPct'] is not None)==w['complete']
   for level in q.LEVELS:
    lab=w['reach'][str(level)]
    assert lab is not False or w['complete']
    assert lab is not True or (w['mfe'] is not None and w['mfe']>=level)
 lines=[]
 def para(t):lines.extend([t,''])
 def table(headers,rs):
  lines.extend(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |'])
  lines.extend('| '+' | '.join(fmt(v) for v in row)+' |' for row in rs);lines.append('')
 para('# ¥75 Frozen Selector × Frozen NEW Entry — Opportunity Quality')
 para('Historical Development / outcome-exposed / evaluator-only。Actual ENTER、約定、EXIT、Capital simulationではない。')
 para(f"Source HEAD `{s['sourceHead']}`。測定前protocol commit `{s['protocolCommit']}`。")
 para('Identity: FROZEN_LONG_SELECTOR_WITH_MIN_PRICE_75 → phase57-new-long-entry-two-opportunity-v1。候補発行のみ、Entryのmodel/threshold変更なし。')
 para('## 判定')
 para(f"`{s['verdict']['quality']}` / `{s['verdict']['closure']}`")
 para('判定は事前固定した記述基準による。4〜5候補timestampの全分母で、同日観測済み2銘柄以上の+3到達>=20%かつ+5到達>=10%、4block中3以上および固定頻出top3除外でも成立するかを検証。収益性・OOS検証・最適候補数の意味ではない。基準は既存aggregate Qualityが既にexposedなDevelopment上の記述ラベルであり、独立した性能合格基準ではない。')
 para('## 母集団・欠測')
 table(['sessions','TOTAL','INITIAL','DIP','timestamps','REFERENCE_OPEN','UNKNOWN_REFERENCE_OPEN','EXPIRED_BOUNDARY'],[[76,3508,2841,667,1181,*[s['population']['referenceStatus'][k] for k in ('REFERENCE_OPEN','UNKNOWN_REFERENCE_OPEN','EXPIRED_BOUNDARY')]]])
 para('各horizon returnとstrict30 MFE/MAEは、参照OPENあり・完成5m連続・昼休み/セッション境界を跨がない完全窓のみ。欠測を0で補完しない。正本の5m足はunderlying minuteの観測が5本未満の場合もacceptedであり、完全5本minute観測数をJSONに別記。価格やbarは追加取得しない。')
 para('同日観測pathは昼休みを除いた残りregular5mの既存データ。観測済み到達はtrue、全窓完備で未到達のみfalse、その他unknown。部分pathの観測MFEは真のMFEの下限、観測MAEは未観測区間でさらに悪化し得る。成否確定分母はpositiveが確定しやすい選択biasを持つため、全発行分母の下限/上限も必ず見る。')
 para('## +1/+2/+3/+5 Quality')
 table(['cohort','horizon','emitted','complete window','observed path','+1 complete','+2 complete','+3 complete','+5 complete'],[[co,h,x['emittedN'],x['completeN'],x['observedPathN'],*[rr(x['reach'][str(k)]['completeCase']) for k in q.LEVELS]] for co,pan in s['cohorts'].items() for h in ('30','SESSION') for x in [pan[h]]])
 table(['cohort','horizon','level','known +','known −','unknown','到達率下限 %','上限 %'],[[co,h,k,x['knownPositive'],x['knownNegative'],x['unknown'],percent(x['allEmittedLowerBound']['rate']),percent(x['allEmittedUpperBound']['rate'])] for co,pan in s['cohorts'].items() for h in ('30','SESSION') for k in q.LEVELS for x in [pan[h]['reach'][str(k)]]])
 para('## Horizon gross CLOSE return (%)')
 table(['cohort','min','n','mean','median','p25','p75','p05','positive %'],[[co,h,*[pan[str(h)]['return'][key] for key in ('n','mean','median','p25','p75','p05')],percent(pan[str(h)]['return']['positiveRate'])] for co,pan in s['cohorts'].items() for h in q.HORIZONS])
 para('コスト・スプレッド・約定保証を含まないfuture return。EXIT結果ではない。')
 para('## MFE / MAE (%)')
 table(['cohort','horizon/panel','n','MFE median','MFE p75','MFE p90','MAE median','MAE p10','MAE p05','worst MAE'],[[co,f'{h}/{kind}',x[kind+'MFE']['n'],*[x[kind+'MFE'][k] for k in ('median','p75','p90')],*[x[kind+'MAE'][k] for k in ('median','p10','p05','min')]] for co,pan in s['cohorts'].items() for h in ('30','SESSION') for kind in ('complete','observed') for x in [pan[h]]])
 table(['cohort','horizon complete','MAE<=-1','<=-3','<=-5','<=-10'],[[co,h,*[rr(pan[h]['completeMAETails'][str(k)]) for k in (1,3,5,10)]] for co,pan in s['cohorts'].items() for h in ('30','SESSION')])
 para('## Time-to-Opportunity')
 para('壁時計分。HIGH touchの正確な足内時刻は不明。下表の時間は「first hit barの終了時刻」分布で、通常その5分前〜終了時刻の区間を意味する。先行missing barがある場合はfirst-hit時刻確定対象から除外し、曖昧件数を明示。HIGH/LOW順序は仮定しない。')
 table(['cohort','horizon','level','observed hits','first-hit identified','earlier missing','end p25','end median','end p75','end p90'],[[co,h,k,x['observedHitN'],x['identifiedFirstHitN'],x['ambiguousEarlierMissingN'],*[x['identifiedIntervalEndMinutes'][v] for v in ('p25','median','p75','p90')]] for co,pan in s['cohorts'].items() for h in ('30','SESSION') for k in q.LEVELS for x in [pan[h]['timeToHit'][str(k)]]])
 para('## 同時候補数別Quality')
 table(['candidates','timestamps','opps','strict30 n','+1','+2','+3','+5','return mean','median','MFE median','MAE median'],[[n,x['timestamps'],x['opportunities'],a['completeN'],*[rr(a['reach'][str(k)]['completeCase']) for k in q.LEVELS],a['return']['mean'],a['return']['median'],a['completeMFE']['median'],a['completeMAE']['median']] for n,x in s['candidateCount'].items() for a in [x['quality']['30']]])
 para('4〜5候補はINITIALに偏るため、candidate-count間の単純差だけでEntry failureとしない。INITIAL/DIP別の高breadth−低breadth差はsummary.verdict.sourceDilutionに保存。')
 para('## Timestamp breadth: 全候補の成否確定分布')
 para('既知positiveは部分pathでも確定する。下表は全labelがtrue/false確定したtimestampのみであり、全path完備とは異なる。全path完備の分布は次表。両者とも全timestampの代表性は保証しない。')
 table(['candidates','horizon','level','all timestamps','成否確定 n','0','1','2','3','4+'],[[n,h,k,b['timestamps'],b['outcomeIdentifiedTimestamps'],*[rr(b['completeGroupedDistribution'][j]) for j in ('0','1','2','3','4+')]] for n,x in s['candidateCount'].items() if int(n)>=2 for h in ('30','SESSION') for k in ('3','5') for b in [x['breadth'][h][k]]])
 para('## Timestamp breadth: 全候補path完備分布')
 table(['candidates','horizon','level','全path完備 n','0','1','2','3','4+'],[[n,h,k,x['allPathsCompleteTimestampN'],*[rr(x['breadth'][k]['completeGroupedDistribution'][j]) for j in ('0','1','2','3','4+')]] for n,v in supplement.items() if int(n)>=2 for h,x in v.items() for k in ('3','5')])
 para('## 4〜5候補重点: 全475 timestamp分母')
 para(f"475 timestamps / {s['focus45']['opportunities']} Opportunities。下限は既知winnerのみ、上限はunknownを全てwinnerとした限界。未知を負けと確定しない。")
 table(['horizon','level','known winners','possible winners','mean winners LB','UB','>=1 LB','>=2 LB','>=3 LB','>=1 UB','>=2 UB','>=3 UB'],[[h,k,b['knownWinnerCount'],b['possibleWinnerCount'],b['meanWinnersLowerBound'],b['meanWinnersUpperBound'],*[rr(b['atLeast'][str(j)]['lower']) for j in (1,2,3)],*[rr(b['atLeast'][str(j)]['upper']) for j in (1,2,3)]] for h,x in s['focus45']['breadth'].items() for k,b in x.items() if k in ('3','5')])
 para('## INITIAL / DIP interaction')
 table(['type','timestamps','opps','candidate mean','strict30 n','+3','+5','MFE median','MAE median'],[[name,x['timestamps'],x['opportunities'],x['candidateCount']['mean'],a['completeN'],rr(a['reach']['3']['completeCase']),rr(a['reach']['5']['completeCase']),a['completeMFE']['median'],a['completeMAE']['median']] for name,x in s['interaction'].items() for a in [x['quality']['30']]])
 para('## Session / chronological stability')
 table(['block','horizon','complete n','+3 complete','+5 complete','return mean','MFE median','MAE median'],[[block,h,a['completeN'],rr(a['reach']['3']['completeCase']),rr(a['reach']['5']['completeCase']),a['return']['mean'],a['completeMFE']['median'],a['completeMAE']['median']] for block,x in s['chronological'].items() for h in ('30','SESSION') for a in [x['quality'][h]]])
 table(['block','4/5 timestamps','>=2 +3 session LB','>=2 +5 session LB'],[[block,x['SESSION']['3']['timestamps'],rr(x['SESSION']['3']['atLeast']['2']['lower']),rr(x['SESSION']['5']['atLeast']['2']['lower'])] for block,x in s['focus45']['chronological'].items()])
 table(['session','opps','strict30 n','+1','+2','+3','+5','session +3 LB','session +5 LB'],[[date,x['30']['emittedN'],x['30']['completeN'],*[rr(x['30']['reach'][str(k)]['completeCase']) for k in q.LEVELS],rr(x['SESSION']['reach']['3']['allEmittedLowerBound']),rr(x['SESSION']['reach']['5']['allEmittedLowerBound'])] for date,x in s['sessions'].items()])
 para('## Concentration / fixed top3 sensitivity')
 para(json.dumps(s['concentration'],ensure_ascii=False,sort_keys=True))
 para('固定top3='+json.dumps(s['top3Exclusion']['symbols'])+'。symbol blacklistではない。除外後breadthは元のcandidate-countおよび475 timestamps分母を維持し、除外銘柄によるwinnerを加算しない。')
 table(['panel','horizon','complete n','+3 complete','+5 complete','observed MFE median','observed MAE median'],[[name,h,a['completeN'],rr(a['reach']['3']['completeCase']),rr(a['reach']['5']['completeCase']),a['observedMFE']['median'],a['observedMAE']['median']] for name,pan in [('ALL',s['cohorts']['TOTAL']),('EX_TOP3',s['top3Exclusion']['quality'])] for h in ('30','SESSION') for a in [pan[h]]])
 table(['EX_TOP3 focus','>=2 +3 LB','>=2 +5 LB'],[[h,rr(x['3']['atLeast']['2']['lower']),rr(x['5']['atLeast']['2']['lower'])] for h,x in s['top3Exclusion']['focus45OriginalTimestampDenominator'].items()])
 para('## Frozen Selector anchor rank — 記述のみ')
 para('DIPでも元anchor選定時のrank/score。新しいEntry scoreやDIP時点の再rankではない。source/timestamp混在のため因果的な優劣ではない。')
 table(['anchor rank','n strict30','score median','+1','+2','+3','+5'],[[rank,x['quality']['30']['completeN'],x['score']['median'],*[rr(x['quality']['30']['reach'][str(k)]['completeCase']) for k in q.LEVELS]] for rank,x in s['selectorAnchorRankDescriptive'].items()])
 para('## Integrity / STOP')
 para(json.dumps(s['audit'],sort_keys=True));para('全9Safety false、Fresh/OOS未開封。機会のHIGH到達は売却利益や約定を保証しない。Candidate A、Entry、Selector、Capitalは不変。Entry closureはFreeze維持のみで、Fresh validation済み・完成品・実用利益を意味しない。EXIT/Capitalへの自動移行なし。STOP。')
 out.mkdir(parents=True);(out/'REPORT.md').write_text('\n'.join(lines))
 q.write(out/'complete-path-breadth.json',supplement)
 q.write(out/'manifest.json',{'sourcePins':{p:q.sha(source/p) for p in ('summary.json','ledger.json.gz','manifest.json')},'codePin':q.sha(__file__),'outputPins':{p:q.sha(out/p) for p in ('REPORT.md','complete-path-breadth.json')},'aggregationAudit':'PASS'})
 print(json.dumps({'verdict':s['verdict']['quality'],'closure':s['verdict']['closure'],'report':str(out/'REPORT.md')}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--out',required=True);a=p.parse_args();run(a.source,a.out)
