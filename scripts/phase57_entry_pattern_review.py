"""Read-only, post-measurement presentation and feature coverage audit.

No inference, model selection, fitting, price repair or policy replay is performed.
"""
import argparse, collections, gzip
from pathlib import Path
import numpy as np
from scripts import phase57_entry_pattern_v2 as e


def review(source, output):
 root=Path(source);out=Path(output);out.mkdir(parents=True,exist_ok=False)
 src=root/'substrate';m=root/'measurement'
 for folder in [src,m]:
  for name,h in e.read(folder/'manifest.json').items():assert e.sha(folder/name)==h
 gate=e.read(m/'decisions.json');metrics=e.read(m/'metrics.json');selected=gate['selected']
 rows=e.read(src/'rows.json.gz');names=e.read(src/'names.json');opps=e.read(src/'opportunities.json.gz')
 trades=e.read(m/'trades.json.gz');labels=e.read(src/'outcomes.json.gz');inv=e.read(src/'inventory.json')
 protocol=e.read(e.BASE/'protocol.json');ev=set(protocol['evaluation'])
 byday=collections.defaultdict(list)
 for r in rows:byday[r['session']].append(r)
 probes=['AVAIL/quote','AVAIL/age','AVAIL/prevRows','TODAY/vwapDistance','PREV/vwapDistance','STRUCT/turningUp','STRUCT/swingAge','STRUCT/complete5Count','STRUCT/partial5Count','RECENT/position_close']
 probes += [f'LOCAL{w}/return' for w in [1,5,15,30,60]]
 probes += [f'AVAIL/fullWindow{w}' for w in [1,5,15,30,60]]
 probes += ['SEQ_PREV/0','SEQ_TODAY/0','SEQ_MICRO/0/C','SEQ_MICRO/14/C']
 probes=[n for n in probes if n in names];ii=[names.index(n) for n in probes]
 groups={}
 for day in protocol['sessions']:
  with gzip.open(src/(day+'.npy.gz'),'rb') as fh:a=np.load(fh,allow_pickle=False)
  assert len(a)==len(byday[day])
  if day not in ev:continue
  for j,r in enumerate(byday[day]):
   if not r['eligible1']:continue
   minute=r['minute'];age=minute-(540 if minute<690 else 750)
   agebin='00-14' if age<15 else '15-29' if age<30 else '30-59' if age<60 else '60+'
   key=('AM' if minute<690 else 'PM')+'/'+agebin
   if key not in groups:groups[key]={'n':0,'finite':np.zeros(len(ii),int),'positive':np.zeros(len(ii),int)}
   z=groups[key];values=a[j,ii];z['n']+=1;z['finite']+=np.isfinite(values);z['positive']+=np.isfinite(values)&(values>0)
 availability={k:{'rows':z['n'],'features':{n:{'finite':int(z['finite'][j]),'finitePct':100*int(z['finite'][j])/z['n'],'positive':int(z['positive'][j])} for j,n in enumerate(probes)}} for k,z in sorted(groups.items())}
 # Exact opportunity population, independent of which method eventually enters.
 evalopps=[o for o in opps if o['session'] in ev];ids={o['id'] for o in evalopps}
 assert len(ids)==len(evalopps)==2155
 for arm,ts in trades.items():assert len(ts)==len(ids) and {t['opportunity'] for t in ts}==ids,arm
 funnel={'inputSessions':len(inv),'candidateSessions':sum(x['opportunities']>0 for x in inv),'evaluationManifestSessions':len(ev),'evaluationCandidateSessions':len({o['session'] for o in evalopps}),'opportunitiesAll':len(opps),'evaluationOpportunities':len(ids),'patternRows':len(rows),'v1EmptyAll':sum(x['emptyV1'] for x in inv),'v2EmptyAll':sum(x['emptyV2'] for x in inv),'evaluation1130':sum(e.old.minute(o['origin']['decisionTimestamp'])==690 for o in evalopps),'evaluation1130EmptyV2':sum(e.old.minute(o['origin']['decisionTimestamp'])==690 and not o['v2grid'] for o in evalopps)}
 funnel['frozenSelectorEvents']=sum(o['current']['selectionCount'] for o in opps)
 primary=['B0_RETRY_1m','B1_WAIT5_1m','B1_WAIT15_1m','B2_E5_V1_PRESERVED',selected]
 table={};price={};reasons={}
 for arm,z in metrics.items():
  table[arm]={'BUY':z['BUY'],'NoEntry':z['noEntry'],'capture':z['capture'],'horizons':{h:z[h] for h in ['30','60']},'returnEnd':z['returnEnd'],'delay':z['delay'],'entryPriceImprovement':z['entryPriceImprovement']}
  reasons[arm]={'states':z['reasons'],'expireReason':dict(collections.Counter(t.get('expireReason') or next((a.get('reason') for a in reversed(t['attempts']) if a['state']=='EXPIRED'),'V1_OR_UNSPECIFIED') for t in trades[arm] if not t['entryId']))}
  byid={t['opportunity']:t for t in trades[arm]}
  base={t['opportunity']:t for t in trades['B0_RETRY_1m']}
  paired=[]
  for oid in sorted(ids):
   a=byid[oid];b=base[oid]
   if a['entryId'] and b['entryId']:
    paired.append(100*(1-labels[a['entryId']]['price']/labels[b['entryId']]['price']))
  price[arm]={'vsSelectorReference':z['entryPriceImprovement'],'vsRetryPairedEntrants':e.ext.distribution(paired),'pairedWarning':'Secondary conditional comparison, not the primary fixed-opportunity estimand.'}
 e.write(out/'review.json',{'selected':selected,'funnel':funnel,'availabilityByPhaseElapsed':availability,'metrics':table,'price':price,'reasons':reasons,'noFitOrPolicyCalls':True,'sourceMeasurementManifestSHA256':e.sha(m/'manifest.json'),'sourceSubstrateManifestSHA256':e.sha(src/'manifest.json')})
 fmt=lambda x:'UNAVAILABLE' if x is None else f'{x:.2f}' if isinstance(x,(float,np.floating)) else str(x)
 lines=['# Entry v2 — fixed-population comparison and coverage review','',f'Primary fixed by selection dates: **{selected}**. {gate["performanceJudgment"]}.','',
 'All methods retain the same 2,155 evaluation Opportunities. No refit, inference, policy change or evaluation-based model selection occurs in this review. B2 preserves v1 timing/fill mechanics and is historical context; B0 is the fair mechanics-matched timing baseline.','',
 '## Data funnel','', '| Item | Count |','|---|---:|']
 for k,v in funnel.items():lines.append(f'| {k} | {v} |')
 lines+=['','## Main methods','', '| Entry | BUY | No entry | +1 Capture | +2 Capture | +3 Capture | +4 Capture | +5 Capture | Median delay | Price improvement vs Selector |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
 for arm in primary:
  z=metrics[arm];vals=[arm,z['BUY'],z['noEntry']]+[z['capture'][str(t)]['rate'] for t in range(1,6)]+[z['delay']['median'],z['entryPriceImprovement']['median']]
  lines.append('| '+' | '.join(map(fmt,vals))+' |')
 lines+=['','Capture uses the original fixed Selector session-end winner denominator; no-entry and unknown outcomes are not successes. Delay is session-active minutes. Price improvement is relative to the Selector reference, not automatically model alpha.','']
 for h in ['30','60']:
  lines += [f'## {h} active-minute path / return / Hit','', '| Entry | BUY | Complete | Censored | Unavailable | MFE med | MAE med | MAE p5 | MaxDD med | MaxDD p5 | Net mean | Net med | Positive % | +1 Hit | +2 Hit | +3 Hit | +4 Hit | +5 Hit |','|'+'---|'*18]
  for arm,z in metrics.items():
   hh=z[h];co=hh['coverage'];vals=[arm,z['BUY'],co.get('COMPLETE',0),co.get('CENSORED',0),co.get('UNAVAILABLE',0),hh['MFE']['median'],hh['MAE']['median'],hh['MAE']['p5'],hh['MaxDD']['median'],hh['MaxDD']['p5'],hh['returnNet']['mean'],hh['returnNet']['median'],hh['returnNet']['positiveRate']]+[hh['hit'][str(t)]['rate'] for t in range(1,6)]
   lines.append('| '+' | '.join(map(fmt,vals))+' |')
  lines+=['','Path and returns condition on complete observed source-slot coverage. Hit denominator is all BUY; rates are observed lower bounds, with unknown counts and upper bounds in review.json. A missing source minute is not certified as no trade. MaxDD is the confirmed chronological OHLC bound; intra-bar ordering remains unknown.','']
 lines+=['## Availability by AM/PM elapsed minutes','', 'Each row is an evaluation decision opportunity before model actions. Window warmup masks are shown separately from finite observed summaries: a partial observed local window is usable information, not a certified full window.','', '| Phase / age | N | Quote true % | Local15 finite % | Local30 finite % | Local60 finite % | Full15 age % | Full30 age % | Full60 age % | Previous sequence finite % | Swing finite % | VWAP finite % |','|'+'---|'*12]
 for key,z in availability.items():
  def value(n,positive=False):
   q=z['features'].get(n);return None if q is None else 100*q['positive']/z['rows'] if positive else q['finitePct']
  vals=[key,z['rows'],value('AVAIL/quote',True)]+[value(f'LOCAL{w}/return') for w in [15,30,60]]+[value(f'AVAIL/fullWindow{w}',True) for w in [15,30,60]]+[value('SEQ_PREV/0'),value('STRUCT/turningUp'),value('TODAY/vwapDistance')]
  lines.append('| '+' | '.join(map(fmt,vals))+' |')
 lines+=['','## Interpretation boundaries','','- Metrics use active-minute horizons; do not silently compare them with v1 wall-clock 30m/60m values. The original v1 report is preserved.','- The continuation target is realized-best future quality supervision, an optimistic proxy; this is not a solved Bellman optimal stopping policy.','- The recorded timeToRecovery is first observed high reaching Entry price, which can be zero in the entry minute. It is not post-drawdown recovery duration.','- Lower MAE among fewer entrants does not by itself establish Entry value. Read fixed-denominator Capture, BUY throughput, unknown outcomes and session stability together.','- Feature availability and attribution are descriptive. Partial bars, fixed projection, and inherited upstream metadata limit claims about chart understanding and independent prospective PIT.','- Common Holdout244 and other sealed partitions remain outside this study. No Entry promotion, EXIT development, allocation change or trading is performed.','']
 (out/'REPORT.md').write_text('\n'.join(lines)+'\n')
 a=metrics[selected];b=metrics['B0_RETRY_1m'];receipt=e.read(root/'completion-gate.json')
 ja=['# NEW LONG Entry v2 — 最終結果','',
 '研究比較は完了しました。**v2の採用基準は未達、昇格しません。** 判定は `ENTRY_DEVELOPMENT_INCONCLUSIVE`。条件付きMAE・Returnの一部改善はありますが、OpportunityとBUY throughputを失いすぎています。','',
 f'144日を監査し、候補が存在する142日・Selectorイベント{funnel["frozenSelectorEvents"]:,}件・{len(opps):,} Opportunityから{len(rows):,} pattern sampleを構成。内部評価は59日manifestのうち58日・2,155 Opportunityです。候補なしの2025-04-15 / 2025-07-14もinventoryに保持しています。','',
 f'選択期間20日で固定したPrimaryは `{selected}`。評価結果を見たモデルの入れ替えや再学習はしていません。','',
 '| 方法 | BUY | +3 Capture | +5 Capture | 30m完全観測 | 30m MFE中央値 | 30m MAE中央値 | 30m MaxDD中央値 | 30m net平均 |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
 for arm in ['B0_RETRY_1m','B1_WAIT5_1m','B2_E5_V1_PRESERVED',selected]:
  z=metrics[arm];h=z['30'];vals=[arm,z['BUY'],z['capture']['3']['rate'],z['capture']['5']['rate'],h['MFE']['count'],h['MFE']['median'],h['MAE']['median'],h['MaxDD']['median'],h['returnNet']['mean']]
  ja.append('| '+' | '.join(map(fmt,vals))+' |')
 ja+=['','価格指標・Captureは%。30m/60mは昼休みを除くsession-active時間。Path/Returnは完全観測ケースに条件付けた値で、BUY母集団が異なります。v1旧wall-clock数値は上書きしていません。','',
 f'- 公平なB0に対し、BUY throughputは{100*a["BUY"]/b["BUY"]:.1f}%。+3 Capture差は{a["capture"]["3"]["rate"]-b["capture"]["3"]["rate"]:.2f}ポイント、+5差は{a["capture"]["5"]["rate"]-b["capture"]["5"]["rate"]:.2f}ポイント。',
 f'- +3 capturedは{a["capture"]["3"]["captured"]}/{a["capture"]["3"]["selectorWinnerDenominator"]}、+5は{a["capture"]["5"]["captured"]}/{a["capture"]["5"]["selectorWinnerDenominator"]}。+3 missedのうち{a["capture"]["3"]["noEntry"]}件、+5 missedのうち{a["capture"]["5"]["noEntry"]}件は未Entryです。',
 f'- LOW_THEN_HIGH保持率も、+3はB0 {b["capture"]["3"]["lowThenHigh"]["pct"]:.1f}% → v2 {a["capture"]["3"]["lowThenHigh"]["pct"]:.1f}%、+5は{b["capture"]["5"]["lowThenHigh"]["pct"]:.1f}% → {a["capture"]["5"]["lowThenHigh"]["pct"]:.1f}%でした。',
 '- B0自体もCapture90%には届いていません。ただし、それを基準緩和の理由にはせず、v2はB0にも大幅に劣るという結果をそのまま保存します。','',
 '## P0と計測基盤','',
 f'- 評価期間の11:30 selection {funnel["evaluation1130"]}件は、v2では空grid {funnel["evaluation1130EmptyV2"]}件。全144日では空grid {funnel["v1EmptyAll"]}→{funnel["v2EmptyAll"]}件。残る90件は取引時間延長前の15:00 selectionで、残り取引時間がないsession境界です。',
 '- B0/モデルは同じ1m・5m grid、参照価格freshness、実1m Open＋5bps、未約定retry契約を共有。MODEL_WAITと価格欠測・未約定・EXPIREを分離しました。',
 '- 前日full observed1m・当日closed prefix、476個の固定numeric/sequence/context特徴を構成。欠測とpartialを保持し、価格補間はしていません。full observedは全minute存在の保証ではありません。',
 '- 1mは選択モデルの5mよりCaptureを保ちましたが、公平baselineとの差は依然大きく、成功とは判定しません。全モデル・固定wait・ablationは詳細表に保存しました。','',
 '## 検証と制約','',
 f'- focused tests {receipt["tests"]} PASS、既存regression {receipt["regressionCount"]} PASS。基盤・測定・REPORT/グラフは2回生成一致。このread-only reviewも2回生成一致。',
 '- v1 BUY時刻・価格・Captureは一致確認済み。Frozen Selector / Dictionary Gateは変更なし。Common Holdout244未開封、9 Safetyすべてfalse。NEW EXIT、Capital Allocation、merge、売買、昇格は行っていません。',
 '- 本研究は再利用Development内の診断です。独立OOSではありません。Frozen upstreamの同日Daily metadata制約は継承し、そのprospective PITを独立認証したとは主張しません。',
 '- 継続価値は実現した将来最大品質を教師にした楽観的proxyで、Bellman最適停止の解ではありません。Dictionary/Pattern Memoryの追加評価は今回のPrimaryから分離しています。',
 '- 既存の別研究CIに失敗が残るため、v2専用CIの成功をPR全体のgreenとは扱いません。','',
 f'測定HEAD: `{receipt["head"]}`。専用CI: https://github.com/Iam-2squared/ark-terminal/actions/runs/{receipt["runId"]}。','',
 '[全方式の30m/60m比較・可用性層別](REPORT.md) / [グラフ付き本体REPORT](../ci-result/REPORT-ja.md) / [raw review](review.json)','']
 (out/'RESULT-ja.md').write_text('\n'.join(ja)+'\n')
 e.write(out/'manifest.json',{x.name:e.sha(x) for x in sorted(out.iterdir())})


if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--source',required=True);parser.add_argument('--output',required=True)
 args=parser.parse_args();review(args.source,args.output)
