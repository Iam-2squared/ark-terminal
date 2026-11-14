"""Saved-only tables and review handoff; no new policies, fits, or runtime changes."""
import collections
import csv
import hashlib
import json
import statistics
from scripts import phase57_entry_location_study as s


def run():
    r=s.read(s.BASE/'result.json.gz');ledger=s.read(s.BASE/'ledger.json.gz');c=s.read(s.BASE/'protocol.json')
    audit=s.read(s.BASE/'denominator-and-window-audit.json.gz')
    panel=[x for x in ledger if x['primary60']]; dates=sorted({x['sessionDate'] for x in ledger})
    sub={}
    for i in range(4):
        for flag in [True,False]:
            sub[f'period{i+1}_'+('DIP' if flag else 'NO_DIP')]=s.summarize([x for x in panel if x['sessionDate'] in dates[i*19:(i+1)*19] and x['firstClosedDip']==flag])
    coverage={}
    for field in ['timeOfDay','segment']:
        coverage[field]={}
        for value in sorted({x[field] for x in ledger}):
            a=[x for x in ledger if x[field]==value];n=sum(x['primary60'] for x in a)
            coverage[field][value]={'full':len(a),'primary':n,'excluded':len(a)-n,'primaryFraction':n/len(a)}
    directions={}
    for name,rows in [('ALL',panel),('DIP',[x for x in panel if x['firstClosedDip']]),('NO_DIP',[x for x in panel if not x['firstClosedDip']])]:
        by=collections.defaultdict(list)
        for x in rows:by[x['symbol']].append(x)
        changes=[statistics.mean(x['policies']['WAIT5']['windows']['30']['downside']-x['policies']['IMMEDIATE']['windows']['30']['downside'] for x in xs) for xs in by.values()]
        directions[name]={'symbols':len(by),'symbolMeanD30Delta':s.distribution(changes),'betterSymbols':sum(v<0 for v in changes),'worseSymbols':sum(v>0 for v in changes),'flatSymbols':sum(v==0 for v in changes),'minimumCount':1,'inference':'descriptive macro direction; many symbols singletons, not significance'}
    supplement={'chronologySubgroups':sub,'coverageByGroup':coverage,'symbolMacro':directions,'fullLedgerObservedSummary':s.summarize(ledger)}
    s.write(s.BASE/'supplement.json.gz',supplement)
    with (s.BASE/'paired-summary.csv').open('x',newline='') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['cohort','N','policy','meanBuyImprovementPct','medianBuyImprovementPct','p10','p25','p75','p90','cheaperRate','dearerRate','D5','D10','D15','D30','D30p95','D30ES95','D30worst','remaining30','common60Remaining','lostUpsidePP','capture1','capture2','capture3','capture5'])
        for group,a in r['cohorts'].items():
            for p in s.POLICIES:
                x=a['policies'][p];q=x['buyImprovementPct'];d=x['windows']['30']['downside']
                w.writerow([group,a['n'],p]+[q[k] for k in ['mean','median','p10','p25','p75','p90','positiveRate','negativeRate']]+[x['windows'][str(n)]['downside']['mean'] for n in [5,10,15,30]]+[d[k] for k in ['p95','ES95','max']]+[x['windows']['30']['upside']['mean'],x['common60']['upside']['mean'],x['remainingUpsideLostPP']['mean']]+[x['capture'][str(k)]['lower'] for k in s.LEVELS])
    f=lambda v:'UNKNOWN' if v is None else f'{v:.4f}'
    pct=lambda v:'UNKNOWN' if v is None else f'{100*v:.2f}%'
    a=r['cohorts']['ALL']['policies'];dip=r['cohorts']['FIRST_CLOSED_DIP']['policies'];no=r['cohorts']['NO_FIRST_CLOSED_DIP']['policies']
    lines=['# ENTRY_LOCATION_STUDY_COMPLETE','','## 1. Executive Summary','',
      '即時Entryが全体として高値掴みとは言えない。全員を5分待たせても平均買値は0.0287%高くなり、上昇captureを大きく失う。一方、最初のcompleted CLOSEが下落した328件では即時は相対的に早すぎ、+5分で買値と残存上昇余地が改善する。しかし、その分類は+5分で初めて判明する。t0の振り分けルールへの転用は禁止。',
      '', '今回の結論はEntry位置の診断。EXIT net/PF/勝率/Portfolio/Allocation後成績をGO/KILL判定に使っていない。新Timing Engine・新モデル・Claude Reviewには進まずSTOP。', '',
      '## 2. Dataset / Coverage','',
      'Historical / Development / outcome-exposed。2024-09-17〜2025-01-09の76sessions、3,800 selected eventsからoutcome非依存のfirst symbol-session2,743 anchors。旧E[L] gateは不使用。Full ledgerは全2,743行を保持。', '',
      '| Panel | N | 用途 |','|---|---:|---|',
      '| Full anchors | 2,743 | 欠測を含む全件ledger |',
      '| 共通selection+60m・連続5m経路 | 878 / 430 symbols / 76 sessions | Primary、同じ候補で5方式比較 |',
      '| 各Entry+60mを全方式で観測 | 693 | 最大selection+70m、別population |',
      '| 各Entry→saved regular-session endを全方式で観測 | 363 | 別population・auction未認証 |',
      '| Primaryの全barでobservedMinutes=5 | 249 | 完全分足数metadata sensitivityのみ、1m研究ではない |','',
      'Primary除外1,865件(67.99%)。完全経路選択によるcoverage biasがあるため、878件を全2,743件へ一般化しない。Full first-dipは580、no-dip1,327、UNKNOWN836。Primaryでは328/550。群ごとのcoverageはsupplement.json.gz。', '',
      '除外内訳（相互排他）：連続session外353件、60分窓がsession境界を跨ぐ493件、必要5分bar欠測/無効1,019件。coverage-audit.csvはdip/no-dip、時刻、segmentごとに全分母とpaired採用数を保存。欠測補完なし。', '',
      '| Policy | Reference OPEN | UNKNOWN | Boundary expired |','|---|---:|---:|---:|']
    for p,counts in r['coverage']['fullLedgerEntryStates'].items():lines.append(f'| {p} | {counts.get("REFERENCE_OPEN",0)} | {sum(v for k,v in counts.items() if k.startswith("UNKNOWN"))} | {counts.get("EXPIRED_BOUNDARY",0)} |')
    lines+=['',
      'Frozen target Y30は6 closed5m trading observations先のendpoint return。Opportunityは別のdecisionPrice→same-session HIGH。Frozen3,790 HIGH-evaluableの76.39/61.29/47.26/24.99%は変更しない。今回保存経路Censusは2,743分母で2,055/1,619/1,212/609 hitsを再現。欠測下のlower boundでありFrozen aggregateを置換しない。', '',
      '参照Entryは予定5m区間のOPEN。Selector decision CLOSEでのfillではない。ゼロ遅延・queueなしの楽観参照で、実約定・spread・depthは未検証。単一5m内のHIGH/LOW順序も不明。HIGH touchは実現利益ではない。', '',
      '本報告の従来captureはIMMEDIATE OPEN基準の共通60分winner分母（+3=267、+5=123）。元SelectorのDecision Price基準の機会（同60分で+3=296、+5=141）とは異なる。Section9とoriginal-opportunity-preservation.csvで両者を明示的に分離する。IMMEDIATE 100%は自己比較であり、元Opportunity全保持の認定ではない。', '',
      '## 3. Immediate Entry診断','',
      f'30分内にEntryより1%以上下落534/878={pct(534/878)}、2%以上337/878={pct(337/878)}、5%以上78/878={pct(78/878)}、10%以上19/878={pct(19/878)}。Mean D30={f(a["IMMEDIATE"]["windows"]["30"]["downside"]["mean"])}%。早すぎる経路は存在するが、待機すれば一律に良くなるわけではない。', '',
      '## 4. +5m診断','',
      'Mean buy improvement -0.0287%、median0%。安く買える40.66%、高く買う42.26%、同値17.08%。買値悪化側p10=-1.7802%、worst=-14.2857%。平均だけで改善としない。D30低下は3.81%に留まり、+3/+5 captureは71.91%/69.92%。', '',
      '## 5. +10m診断','',
      'Mean buy improvement -0.0357%、買値悪化側p10=-2.1884%。D30=1.9780%と低下する一方、+3/+5 capture=62.92%/63.41%。共通60分Remaining Upsideは2.7522%→2.3422%、平均0.4100pp喪失。+5より安く買える平均的優位もない。', '',
      '## 6. FIRST_CLOSED_DIP','',
      '328 anchors /236symbols /74sessions。最初のcompleted CLOSE<decisionPriceという+5分で判明する事後cohort。', '',
      '| Metric | Immediate | +5m | +10m |','|---|---:|---:|---:|']
    for title,get in [('Mean buy improvement (%)',lambda x:x['buyImprovementPct']['mean']),('Median buy improvement (%)',lambda x:x['buyImprovementPct']['median']),('Mean D30 (%)',lambda x:x['windows']['30']['downside']['mean']),('Own+30 Remaining Upside (%)',lambda x:x['windows']['30']['upside']['mean']),('Common60 Remaining Upside (%)',lambda x:x['common60']['upside']['mean'])]:
        lines.append('| '+title+' | '+' | '.join(f(get(dip[p])) for p in ['IMMEDIATE','WAIT5','WAIT10'])+' |')
    for k in ['3','5']:lines.append('| +'+k+' capture | '+' | '.join(pct(dip[p]['capture'][k]['lower']) for p in ['IMMEDIATE','WAIT5','WAIT10'])+' |')
    lines+=['',
      'Q3/Q4: +5mで平均1.1184%安く買え、D30を34.74%減らし、Remaining Upsideも保持/増加するEntry Location Evidenceがある。同一の+5→+35分経路を即時買値で評価したD30は2.9827%、+5買値では1.8911%。買値効果は1.0915pp改善、評価窓移動効果は0.0847pp悪化、差引1.0068pp改善。単に初動下落を窓から外したための平均改善とは説明できない。ただし事後分類であり底予測の証明ではない。+5で安く買えた299件にも、その後D30>=2%が106件、>=5%が21件ある。安い＝底ではない。',
      '', 'Q5: dip群の+5→+10は買値改善1.1184→1.0662%へ縮小、D301.8911→1.8766%とほぼ横ばい、+3capture56/59→50/59。余分な5分の機会損失に見合うEvidenceは弱い。+5capture21/21は小標本。', '',
      '## 7. NO_FIRST_CLOSED_DIP','',
      '550 anchors。+5mは平均0.7128%高く買い、65.27%のケースで買値悪化。D30は1.6654→2.1366%へ悪化、共通Remaining Upside3.3871→2.5510%で0.8361ppを失う。+3capture136/208=65.38%、+5capture65/102=63.73%。+10mでは56.73%/55.88%へさらに低下。この群をt0で知って即時Entryさせることは未来リーク。', '',
      '## 8. Early / Late Penalty','',
      'Buy improvement=100*(1-delayedBuy/immediateOpen)。Early penaltyは各Entry後のLOWへの逆行幅Dを正値で表示。5/10/15/30分は各Entry後の同じ長さ。Late penaltyはbuy improvementの符号反転、残存上昇余地喪失は共通selection+60mの差分。', '',
      '| Policy | Buy mean | median | p10 | p25 | p75 | p90 | cheaper | dearer |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for p in s.POLICIES:
        x=a[p]['buyImprovementPct'];lines.append('| '+p+' | '+' | '.join(f(x[k]) for k in ['mean','median','p10','p25','p75','p90'])+' | '+pct(x['positiveRate'])+' | '+pct(x['negativeRate'])+' |')
    lines+=['','| Policy | Mean D5 | Mean D10 | Mean D15 | Mean D30 | D30 median | p90 | p95 | ES95 | worst |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for p in s.POLICIES:
        x=a[p];q=x['windows']['30']['downside'];lines.append('| '+p+' | '+' | '.join(f(x['windows'][str(n)]['downside']['mean']) for n in [5,10,15,30])+' | '+' | '.join(f(q[k]) for k in ['median','p90','p95','ES95','max'])+' |')
    lines+=['','全horizonのmean/median/p90/p95/ES95/worstはhorizon-distributions.csvにも保存。Deep counts、subgroup別分布はdeep-adverse-counts.json/result.json.gz。ES95は最大ceil(0.05*N)件の平均。Early-entry PenaltyとPost-Entry Downsideは同一のEntry→future LOW観測量であり、独立の二重Evidenceとして数えない。', '',
      '同一将来経路で買値だけを変更する分解はdenominator-and-window-audit.json.gzのwindowAttributionに保存。FIRST_CLOSED_DIPの+5では買値効果+1.0915pp、窓移動-0.0847pp。NO_DIPでは買値効果-0.5107pp、窓移動+0.0395pp、差引D30が0.4712pp悪化。符号は正=改善。', '',
      '## 9. Remaining Upside / Downside','',
      '| Policy | Own+30 mean upside (878) | Common60 mean upside (878) | Lost common upside pp | +3 capture | +5 capture | Own+60 mean upside (693) | Saved end mean upside (363) |',
      '|---|---:|---:|---:|---:|---:|---:|---:|']
    for p in s.POLICIES:
        x=a[p];lines.append('| '+p+' | '+' | '.join([f(x['windows']['30']['upside']['mean']),f(x['common60']['upside']['mean']),f(x['remainingUpsideLostPP']['mean']),pct(x['capture']['3']['lower']),pct(x['capture']['5']['lower']),f(r['entryPlus60Paired']['policies'][p]['windows']['60']['upside']['mean']),f(r['savedSessionPaired']['policies'][p]['savedSession']['upside']['mean'])])+' |')
    lines+=['','元Decision Price基準の+1/+2/+3/+5 Opportunityを各Entryから同じ%以上のRemaining Upsideとして保持した率（共通selection+60m・878件）。Entry価格差があるためIMMEDIATEも100%にはならない。', '',
      '| Policy | +1 (633) | +2 (440) | +3 (296) | +5 (141) |','|---|---:|---:|---:|---:|']
    for p in s.POLICIES:
        xs=[x for x in audit['originalOpportunityPreservation'] if x['panel']=='PRIMARY_COMMON60_DECISION_PRICE' and x['cohort']=='ALL' and x['policy']==p]
        lines.append('| '+p+' | '+' | '.join(f'{x["preserved"]}/{x["originalKnownWinners"]} ({pct(x["preservationLower"])})' for x in xs)+' |')
    lines+=['','Same-sessionの元Opportunityも同CSVに保存。完全な全方式paired363件で元+3/+5 winner=148/75。Immediate保持130/148・69/75、WAIT5保持118/148・63/75、WAIT10保持107/148・53/75。Full2,743件の観測winnerは2,055/1,619/1,212/609を維持し、各方式の保持/既知喪失/UNKNOWN/境界Entry不可を別計上。欠測下の未到達を不達と断定しない。', '',
      '693/363は別populationであり878との水準差をholding-time効果としない。Full ledgerの不完全same-session経路はexact=NULL、観測HIGH/LOWのみlower boundとして別保存。Closing auctionは認証されていない。', '',
      '## 10. Entry Efficiency','',
      'Zero divisionや極端値を避けratioは不使用。Own+30 upside×downsideの固定2D binsとpaired非悪化件数を保存。entry-efficiency-2d.csvのU0..U4境界は1/2/3/5%、D0..D4境界は1/2/5/10%。下限を含み上限を含まない。これは診断binであり新Entry thresholdではない。', '',
      '| Cohort / +5 vs Immediate | N | Upside>= & downside<= | Both worse |','|---|---:|---:|---:|']
    for group in ['ALL','FIRST_CLOSED_DIP','NO_FIRST_CLOSED_DIP']:
        z=r['cohorts'][group]['policies']['WAIT5']['balanceVsImmediate'];lines.append(f'| {group} | {z["n"]} | {z["bothNonworse"]} | {z["bothWorse"]} |')
    lines+=['','全体で最良の時刻は認定できない。ImmediateはOpportunity保持、+5はdip群の位置改善、+10は若干の逆行削減と大きな機会損失というtrade-off。事後winner群を選んで最良方式を認定しない。', '',
      '## 11. High-price / Early / Late判定','',
      '- Q1: 全体を高値掴みと断定しない。+5/+10の平均買値はむしろ高い。',
      '- Q2: Immediate後D30>=2%は38.38%、>=5%は8.88%、>=10%は2.16%（878panel）。',
      '- Q3/Q4: First dip群では相対的な早すぎEvidence。ただし+5時点でのみ利用可能。',
      '- Q5/Q6: 余分な待機、特にno-dip群は高値買いとRemaining Upside喪失。',
      '- Q7: 全体最良なし。2次元trade-offと群別の反転が重要。',
      '- Q8: 最初の5分足は「+5以降の状況把握」には記述的価値があるが、t0のroute選択力は今回測っていない。',
      '- Q9: 5mで状態を利用する余地は残るが、実用Timing Engine成立は未証明。1mが必要/十分とも本研究では結論しない。', '',
      '## 12. Robustness','',
      '76sessionsを連続19sessions×4blockに固定。旧報告のfold区切りと同一とは仮定しない。Fresh/OOS検証ではない。', '',
      '| Block | N | Immediate D30 | WAIT5 D30 | WAIT10 D30 | WAIT5 +3 / +5 capture |','|---|---:|---:|---:|---:|---:|']
    for k,x in r['chronology'].items():
        ps=x['policies'];lines.append(f'| {k} | {x["n"]} | '+ ' | '.join(f(ps[p]['windows']['30']['downside']['mean']) for p in ['IMMEDIATE','WAIT5','WAIT10'])+' | '+pct(ps['WAIT5']['capture']['3']['lower'])+' / '+pct(ps['WAIT5']['capture']['5']['lower'])+' |')
    lines+=['','| Sensitivity | N | WAIT5 +3 / +5 | WAIT10 +3 / +5 |','|---|---:|---:|---:|']
    for name,x in r['symbolSensitivity'].items():lines.append(f'| {name} | {x["n"]} | '+ ' | '.join(pct(x['policies'][p]['capture']['3']['lower'])+' / '+pct(x['policies'][p]['capture']['5']['lower']) for p in ['WAIT5','WAIT10'])+' |')
    lines += ['',f'Anchor-count HHI={r["countHHI"]:.6f}、top3 count symbols={r["top3CountSymbols"]}。Top-count除去は診断だけでblacklistではない。銘柄別差分とsymbol等重みdirectionを保存し反復銘柄を独立証拠に水増ししない。',
      '', 'DIP/no-dip各block詳細・time-of-day・segment分解・coverage内訳を保存。Segmentはdated Masterから取得できるがrelease clock未監査のため**PIT-safeと認定しないsupporting diagnostic**。Prime/Standard/Growth filterは作らない。', '',
      '## 13. KILLしたTiming','',
      'WAIT5、WAIT10、DIP_CLOSE_FALLBACK10、OBSERVE5_DELAY_DIP10を「完成Entry」として採用しない。全体のcapture喪失が大きく、待機は一律の価格改善にもならない。今回新しいperformance gateは作らず、EXIT成績を根拠にもしていない。弱い方式の延命・+7.5/+8などの追加探索なし。Immediateも最適/利益保証/新Final Entryに昇格しない。', '',
      '## 14. 残すEvidence','',
      'dip群では位置改善と残存上昇余地の両立がある一方、no-dip群では反転する。この状態差を+5時点以降の設計にどう扱うかが次の独立Architecture Reviewの論点。価格改善後の続落、待機中に消費した上昇余地、coverageと実約定不確実性を同時に保持する。', '',
      '## 15. Claudeへ渡す10項目以内','',
      '1. Frozen Y30とsame-session HIGH評価は別。2,743 anchors維持。Immediate capture100%はOPEN基準の自己比較。元Decision Price基準では同60分の+3/+5保持88.18%/83.69%。',
      '2. 878 complete60m panelで既存Timingのbuy/D30/captureを再現。残る1,865件は消さない。',
      '3. 全員WAIT5/WAIT10は買値平均を改善せず、+3/+5機会を大きく失う。',
      '4. FIRST_CLOSED_DIP328件：WAIT5でbuy+1.1184%、D30-34.74%、+3capture94.92%、+5capture100%(21件)。',
      '5. Dip後さらに10分まで待つと、D30の追加改善は小さく+3capture84.75%へ低下。',
      '6. NO_DIP550件：WAIT5でbuy0.7128%悪化、D30も悪化、Remaining Upside0.8361pp喪失。',
      '7. Dip群の+5改善は同一将来窓の買値効果+1.0915pp、窓移動-0.0847pp。安く買えた299件でも、その後>=2%逆行106件。底確認を意味しない。',
      '8. First-bar情報は+5時点のみ既知。no-dipだけt0 Entryの混合は未来リーク。',
      '9. 時期・top-count-symbol除去・完全分足数metadataの感度分析でも一律待機の機会損失は残る。',
      '10. Reference OPEN/HIGH/LOWであり実約定未認証。5mの限界から1m必須とは断定せず、EXIT/Capital/Portfolioの損益は今回の主軸から除外。', '',
      '## 16. GitHub / SHA / Tests / Safety','',
      'Branch `research/phase57-long-only-cash-equity` / PR #587。Start head `'+c['head']+'`、既存protocol記録時のmain参照 `'+c['latestMain']+'`。今回のmain確認値はscope-audit.jsonへ記録。Final headとCIは公開commitに対する最終報告に記載。',
      '', 'Protocol SHA `'+r['protocolSHA']+'`。Anchor SHA `'+s.ANCHOR_SHA+'`。全source SHAはprotocol.json、出力/コード/test SHAはmanifest.json。',
      '', '23 Python tests（causality、missing、session境界、Frozen identity、既存値parity、40,000超の独立normalized対absolute outcomeチェック、分母・窓分解・集計再計算・manifest照合）。Node wrapperで既存Predict CIに接続。workflow変更0。実行結果はverification.jsonと最終headのCIを参照。',
      '', '既存1mコード・テスト・Evidenceは保存、変更0。Sourceは既存5m projectionだけ。外部ZIP再取得・復号・export・新provider accessなし。新Architecture/Claude Review未実施。',
      '', 'Selector変更0 / Entry runtime変更0 / 新モデルfit・prediction0 / Fresh・OOS0 / 新価格provider request0 / 1分研究0 / EXIT・Capital・Portfolio tuning0 / Safety9項目全false / main未merge。STOP。','']
    with (s.BASE/'REPORT.md').open('x') as out:out.write('\n'.join(lines))


if __name__=='__main__':run()
