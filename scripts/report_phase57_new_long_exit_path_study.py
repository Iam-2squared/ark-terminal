"""Japanese report from saved Path Study aggregates; no market replay."""
from scripts import phase57_new_long_exit_path_study as s

def f(x):return 'N/A' if x is None else f'{x:.3f}'
def r(v):return f"{v['n']}/{v['denominator']}"+(f" ({100*v['rate']:.1f}%)" if v['rate'] is not None else ' (N/A)')
def med(v):return f"{f(v['median'])} [n={v['n']}]"
def render():
    x=s.read(s.BASE/'summary.json.gz');lines=[]
    def a(t=''):lines.append(t)
    def section(n,t):a(f'\n## {n}. {t}\n')
    def table(headers,rows):
        a('| '+' | '.join(headers)+' |');a('| '+' | '.join(['---']*len(headers))+' |')
        for row in rows:a('| '+' | '.join(map(str,row))+' |')
        a()
    cohorts=[('INITIAL',x['cohorts'][s.TYPES[0]]),('DIP_REPRICE',x['cohorts'][s.TYPES[1]])]
    a('# NEW_LONG_EXIT_PATH_STUDY_COMPLETE')
    a('\nArk Terminal Phase57 — NEW LONG EXIT Path Study / Zero-Based Research')
    a('\n2026-09-18 JST。Historical Development / outcome-exposed。価格経路の記述研究であり、EXITの売買判断・学習・最適化は実施していない。')
    section(1,'Executive Summary')
    a('結論は「逆行・回復・利益吐き出しを区別する観測が必要。ただし、観測された形をそのままEXIT条件にはできない」。'
      '前回提案のDEFENSIVE中2連続下落CLOSEは採用も実装もしていない。既存EXITは保存した。')
    a('\n各Entryから60分の同一定義で、INITIAL878件、DIP264件を主集計。t+5 negativeから後に初めて+3/+5へ達する機会は'
      'INITIAL56/267・23/123 winner、DIP22/69・11/27 winner。これは後のHIGH機会であり、実現利益や約定ではない。')
    a('\n106件と21件はそれぞれ全IDを追跡した。後付け集団の価格分布は時間とともに異なるが、'
      '早期に完全分離するsignatureは確認できない。Giveback後に再高値となる例も残るため、一律の早切り・利確は支持できない。')
    section(2,'Dataset / Coverage')
    table(['Cohort','全Opportunity n','参照価格あり n/全件','own60 complete n/全件','own60 銘柄/営業日'],[
        [name,c['opportunities'],r(s.rate(c['referenceStates'].get('REFERENCE_OPEN',0),c['opportunities'])),r(c['own60Coverage']),f"{c['own60Symbols']}/{c['own60Sessions']}"] for name,c in cohorts])
    a(f"期間{x['dateRange'][0]}〜{x['dateRange'][1]}、全anchor2743、全{x['fullAnchorSymbols']}銘柄、76営業日。"
      'Entry元のprimary878（430銘柄/76営業日）、dip328、non-dip550を保持。DIP own60は264件/206銘柄/74営業日であり、328と混同しない。')
    table(['比較panel','n/対象','意味'],[
        ['OWN60 INITIAL','878/2743','INITIALから60分、連続セッション・全12足'],
        ['OWN60 DIP','264/541','DIPから60分、連続セッション・全12足'],
        ['MATCHED_OWN60','264/541 DIP','同一anchor・両方60分。終点の時計時刻は異なる'],
        ['COMMON_T0_60_DIP328','328/541 DIP','同一anchor・同じ時計終点。INITIAL60分、DIP55分'],
        ['追加下落2% cohort','106/299 cheaper DIP','元のD30ラベルそのまま。common55は106/106、own60は85/106'],
        ['追加下落5% cohort','21/299 cheaper DIP','元のD30ラベルそのまま。common55は21/21、own60は16/21']])
    a('全3284行をledgerに保存。full identity SHA256: `'+s.ANCHOR_SHA+'`。'
      '価格は保存OPEN referenceで、実行可能なfillの認証ではない。今回はgross price-pathのみ、cost/PnL/quantity/Allocationを定義していない。')
    for num,(name,c) in enumerate(cohorts,3):
        section(num,name+' Path')
        m=c['own60']['metrics']
        table(['own60 metric','観測n/own60','中央値 [n]','平均 [n]'],[[key,f"{m[key]['n']}/{c['own60Coverage']['n']}",med(m[key]),f"{f(m[key]['mean'])} [n={m[key]['n']}]"] for key in
            ['mfePct','maePct','endpointPct','endpointGivebackPP','maeStrictlyBeforeMfeBarPct','maeIncludingMfeBarPct']])
        if num==3:a('INITIAL全体を、将来DIPになるかどうかでEntry判断へ逆流させていない。HIGH opportunityとendpoint CLOSEは別物。MFEが正でもendpointは負になり得る。')
        else:a('DIPでもown60 MAE<=−2%は118/264、<=−5%は32/264。これは今回のown60集団であり、元のcheaper-D30 106/21とは別の分母。'
               'referenceを安く付け替えた事実は、反発確認・安全・底確認を意味しない。')
    section(5,'Winner Path — Q1 / Q2 / Q5')
    a('winnerは各cohortの同じown60 complete集団に対するMFE>=+1/+2/+3/+5。'
      'MFE到達前MAEは「MFEの足より前」と「MFEの足を含む」の両方を保存する。後者のLOWがHIGHより先だったかは不明。')
    table(['Cohort','水準','winner n/同じpanel','MFE前MAE平均 % [n]','同中央値 % [n]','MFE足を含むMAE中央値 % [n]','MFE前MAE p05 % [n]'],[
        [name,k,r(w['count']),f"{f(w['metrics']['maeStrictlyBeforeMfeBarPct']['mean'])} [n={w['count']['n']}]",
         med(w['metrics']['maeStrictlyBeforeMfeBarPct']),med(w['metrics']['maeIncludingMfeBarPct']),f"{f(w['metrics']['maeStrictlyBeforeMfeBarPct']['p05'])} [n={w['count']['n']}]"]
        for name,c in cohorts for k,w in c['own60']['winners'].items()])
    a('Q1/Q2：+3 winnerのMFE足より前の逆行中央値はINITIAL−0.622%、DIP−0.762%。'
      '+5ではINITIAL−0.669%、DIP−1.146%。分布の裾は深く、「小さな逆行のみ許せば十分」とは言えない。')
    table(['Cohort','後のwinner水準','先行逆行','後続足winner n/逆行あり','同一足のみ・順序不明 n/逆行あり','最初のwinner到達より前の逆行 n/winner'],[
        [name,k,'−'+depth+'%',r(v['confirmedLaterWinnerGivenAdverse']),r(v['sameBarPossibleOnlyGivenAdverse']),r(v['adverseStrictlyBeforeFirstWinner'])]
        for name,c in cohorts for k,w in c['own60']['winners'].items() for depth,v in w['adverse'].items()])
    a('Q5：次表は「その時点がnegativeで、その後に水準へ到達する機会」の数。EXITを実装・replayした成績ではない。'
      '「後で再到達」と「まだ一度も到達していなかったwinner」を分ける。')
    table(['Cohort','時点','水準','negative n/panel','後続HIGH到達 n/negative','初到達前に失う n/winner','残存上昇中央値 % [n]'],[
        [name,h,k,r(v['negativePopulation']),r(v['laterLevelHit']),r(v['notYetFirstHitWinner']),med(v['remainingUpsidePct'])]
        for name,c in cohorts for k in ('3','5') for h,v in c['own60']['winners'][k]['negativeSnapshots'].items()])
    table(['Cohort','winner水準','MFE前最大running giveback中央値 pp [n]','MFE足CLOSE giveback中央値 pp [n]','MFE後最大CLOSE giveback中央値 pp [n]'],[
        [name,k,med(w['metrics']['maxRunningGivebackBeforeMfeBarPP']),med(w['metrics']['givebackAtMfeBarClosePP']),med(w['metrics']['worstCompletedCloseGivebackAfterMfePP'])]
        for name,c in cohorts for k,w in c['own60']['winners'].items()])
    section(6,'Deterioration Path')
    a('loserはown60 endpoint CLOSE<referenceという記述ラベル。先にHIGH winnerとなってからloserになる経路もあり、winner/loserは排他的ではない。'
      'never-positiveは完成足CLOSEの履歴で、HIGHが一度もEntryを超えないという意味ではない。')
    table(['Cohort','経路群','n/own60','MFE中央値 % [n]','MAE中央値 % [n]','endpoint中央値 % [n]','t5/t10/t15 current中央値 %'],[
        [name,label,r(g['count']),med(g['metrics']['mfePct']),med(g['metrics']['maePct']),med(g['metrics']['endpointPct']),
         ' / '.join(f"{h}:{med(g['evolution'][str(h)]['prefix']['currentReturnPct'])}" for h in (5,10,15))]
        for name,c in cohorts for label,g in c['loserGroups'].items()])
    for num,depth,title in [(7,2,'Continued Drop 2% — 106 cohort / Q3'),(8,5,'Deep Drop 5% — 21 cohort / Q4 / Q6')]:
        section(num,title);risk=x['riskCohorts'][str(depth)]
        a(f"元の{risk['cohortN']}件は{risk['cohortN']}/{risk['cohortN']}全IDでearly状態とcommon55 outcomeを保存。対照は同じcheaper299中の残り{299-risk['cohortN']}件。"
          'いずれも未来D30で分けた集団であり、下表はpredictive classifierの検証ではない。')
        table(['DIPから分','risk current中央値 % [n]','対照中央値 % [n]','risk current IQR %','risk negative n/群','一度もpositiveなし n/群','回復試行あり n/群','lower-close streak件数 / 分母'],[
            [h,med(t['risk']['prefix']['currentReturnPct']),med(t['control']['prefix']['currentReturnPct']),
             f"{f(t['risk']['prefix']['currentReturnPct']['p25'])}〜{f(t['risk']['prefix']['currentReturnPct']['p75'])}",
             r(t['risk']['negativeClose']),r(t['risk']['neverPositiveClose']),r(t['risk']['anyRecoveryAttempt']),
             f"{t['risk']['lowerCloseStreakCounts']} / {risk['cohortN']}"] for h,t in sorted(risk['earlyEvolution'].items(),key=lambda kv:int(kv[0]))])
        m=risk['common55']['metrics']
        table(['common55観測','n/群'],[['一度positiveからnegative endpoint',r(m['positiveThenNegative'])],['一度もpositive CLOSEなし',r(m['neverPositiveClose'])],
            ['−2%到達後、later CLOSE reclaimなし',r(m['adverse2NoReclaim'])],['−1%→reclaim→後の+3',r(m['recovery1Then3'])]])
        table(['待った時計時点','n/群','t5からCLOSE変化 平均pp','同中央値pp','running MAE変化 平均pp'],[
            [h,r(v['coverage']),f(v['closeChangeFrom5PP']['mean']),f(v['closeChangeFrom5PP']['median']),f(v['runningMaeChangeFrom5PP']['mean'])]
            for h,v in risk['lossExpansion'].items()])
        if depth==2:a('Q3：中央値差はt5から見えるが、中心50%分布はt5/t10/t15で重なる。t20でIQRが初めて離れるものの、'
            '境界差は約0.004ppにすぎず、裾も重なる。対照193件は「すべて回復winner」ではないため、単なる押しとの識別時刻が確立したとは言わない。'
            '106件内にも−1%→reclaim→+3が16/106ある。状態に差が出ることと、EXIT時点で識別できることは別。')
        else:a('Q4：t5 negativeは12/21、t10は15/21、t15は18/21。t5でnegativeという共通signatureはない。'
            't15のlower-close streak=2も8/21にとどまる。IQRの分離はt15から見えるが、後付け集団・21例であり閾値化しない。'
            'Q6：t5からt10までCLOSEは平均−0.400pp、t15まで−1.746pp悪化。running MAEはそれぞれ平均−0.865pp、−2.105pp深くなる。'
            'これは価格の変化であって、待機EXIT戦略の損益・最適時刻ではない。')
    section(9,'Recovery Path — Q7')
    a('adverse LOWより後の別足でCLOSE>=Entryとなることをreclaimと定義。同じ足内の回復順序は都合よく数えない。'
      'durationはLOW発生足の始端/終端による幅を持ち、完成足時刻だけを厳密に扱う。')
    table(['Cohort','逆行深さ','逆行 n/panel','reclaim n/逆行','回復時間中央値上限 分 [n]','前CLOSE回復 n/逆行','回復後観測あり n/reclaim','回復後+3 n/後続観測','回復後残存上昇中央値 % [n]'],[
        [name,k,r(v['adverse']),r(v['reclaimed']),med(v['durationUpperMinutes']),r(v['priorCloseReclaimed']),r(v['postReclaimObserved']),r(v['postReclaimWinners']['3']),med(v['postReclaimRemainingUpsidePct'])]
        for name,c in cohorts for k,v in c['own60']['recovery'].items()])
    table(['Cohort','逆行深さ','逆行後high更新 n/逆行','更新時刻中央値 分 [n]','reclaim後high更新 n/reclaim','更新時刻中央値 分 [n]'],[
        [name,k,r(v['newRunningHigh']),med(v['newRunningHighUpperMinutes']),r(v['newRunningHighAfterReclaim']),med(v['newRunningHighAfterReclaimUpperMinutes'])]
        for name,c in cohorts for k,v in c['own60']['recovery'].items()])
    a('Q7：−1%→reclaim→後の+3はINITIAL100/878、DIP32/264。該当例のreclaimまでの逆行深さ中央値は約−1.995%／−2.015%、'
      'duration上限中央値は両方10分。だがreclaimしただけで後に+3になるわけではなく、後続観測可能なreclaim中では100/344、32/116。'
      '回復の途中経過を保持する根拠はあるが、reclaim=勝ちというruleは作れない。')
    section(10,'Giveback / Profit Protection — Q8 / Q9')
    a('全てthen-running HIGHから完成CLOSEへのgiveback。1/2/3pp、50%、Entryまで、negativeを観測イベントとして保存。'
      '売買閾値ではない。event後の足がない場合はNO_POST_EVENT_WINDOWとし、再上昇失敗扱いしない。')
    table(['Cohort','MFE水準','giveback観測','event n/winner','post-event n/event','時刻中央値 分 [n]','後に再高値 n/post-event'],[
        [name,k,typ,r(v['events']),r(v['postEventObserved']),med(v['timeMinutes']),r(v['reHighLater'])]
        for name,c in cohorts for k,g in c['own60']['giveback'].items() for typ,v in g.items()])
    a('Q8：+3到達後1pp givebackの4分類を例示する。再高値更新と最終positiveを混同しない。'
      'eventの時刻・残り観測時間も違うため、群間差をそのまま識別ruleにできない。')
    table(['Cohort','後付けoutcome','n/post-event','event時刻中央値 分 [n]','event時CLOSE中央値 % [n]','lower streak中央値 [n]'],[
        [name,outcome,r(v['count']),med(v['elapsedMinutes']),med(v['closePct']),med(v['lowerCloseStreak'])]
        for name,c in cohorts for outcome,v in c['own60']['giveback']['3']['1pp']['outcomes'].items()])
    a('Q9：利益保全を観測・検討する必要性はある。+3 winnerがEntryまで戻るのはINITIAL107/267、DIP27/69。'
      '一方、1pp giveback後の再高値は86/242、23/61。PROTECTを独立stateとして固定すべきか、どの時点でexitするかはまだ未判定。')
    section(11,'Time-to-MFE / Time-to-MAE')
    table(['Cohort','n/own60','MFE時刻中央値 分 [MFE>0 n]','MAE時刻中央値 分 [MAE<0 n]','MFE IQR 分','MAE IQR 分'],[
        [name,r(c['own60Coverage']),med(c['own60']['metrics']['timeToMfeUpperMinutes']),med(c['own60']['metrics']['timeToMaeUpperMinutes']),
         f"{f(c['own60']['metrics']['timeToMfeUpperMinutes']['p25'])}〜{f(c['own60']['metrics']['timeToMfeUpperMinutes']['p75'])}",
         f"{f(c['own60']['metrics']['timeToMaeUpperMinutes']['p25'])}〜{f(c['own60']['metrics']['timeToMaeUpperMinutes']['p75'])}"] for name,c in cohorts])
    a('表は極値を含む足の終端時刻。実時刻はその5分区間内で、厳密に20分で最大利益になる等の主張はしない。'
      '正のMFEなし、負のMAEなしは時刻N/A。最初の極値到達足を採用。')
    table(['Cohort','winner水準','n/panel','最初の水準HIGH時刻中央値 分 [n]','MFE時刻中央値 分 [n]','MAE時刻中央値 分 [n]'],[
        [name,k,r(w['count']),med(w['firstLevelHitUpperMinutes']),med(w['metrics']['timeToMfeUpperMinutes']),med(w['metrics']['timeToMaeUpperMinutes'])]
        for name,c in cohorts for k,w in c['own60']['winners'].items()])
    section(12,'t+5 to t+60 State Evolution')
    a('同じown60集団を全時点で使用し、前半・後半で分母が変わる見かけの改善を避ける。'
      '別列のall-prefix coverageは全opportunityに対する実観測数。残存上昇/将来下落/次方向はevaluator-only。')
    table(['Cohort','分','同一own60 n','all-prefix n/全件','current中央値 %','running MFE中央値 %','running MAE中央値 %','giveback中央値 pp','残存上昇中央値 % [suffix n]','将来下落中央値 % [suffix n]'],[
        [name,h,c['own60Coverage']['n'],r(c['allOpportunityEvolution'][str(h)]['coverage']),
         f(e['prefix']['currentReturnPct']['median']),f(e['prefix']['runningMfePct']['median']),f(e['prefix']['runningMaePct']['median']),f(e['prefix']['givebackPP']['median']),
         med(e['evaluatorOnly']['remainingUpsidePct']),med(e['evaluatorOnly']['futureDownsidePct'])]
        for name,c in cohorts for h in s.HORIZONS for e in [c['own60']['evolution'][str(h)]]])
    table(['Cohort','分','all-prefix n/全件','次足観測 n/prefix','次足UP/DOWN/FLAT件数'],[
        [name,h,r(e['coverage']),r(e['nextIntervalCoverage']),str(e['nextIntervalDirections'])]
        for name,c in cohorts for h in s.HORIZONS for e in [c['allOpportunityEvolution'][str(h)]]])
    a('t60のfutureはWINDOW_ENDED/NULL。own60が欠測でも次の1足だけ観測できる場合は、その次方向のcoverageを別集計した。')
    section(13,'INITIAL vs DIP_REPRICE — Q10 / Q11')
    table(['Panel','同一anchor n/541 DIP','metric','INITIAL中央値 [n]','DIP中央値 [n]','DIP−INITIAL平均pp [n]'],[
        [panel,f"{p['matchedAnchors']}/541",key,med(p['INITIAL']['metrics'][key]),med(p['DIP']['metrics'][key]),f"{f(p['DIP_minus_INITIAL'][key]['mean'])} [n={p['matchedAnchors']}]"]
        for panel,p in x['pairedPanels'].items() for key in ('mfePct','maePct','endpointPct','endpointGivebackPP')])
    table(['Panel','側','n/同一panel','−1%→reclaim→+3','−2%→reclaimなし','time MFE中央値 [n]','time MAE中央値 [n]'],[
        [panel,side,f"{p['matchedAnchors']}/{p['matchedAnchors']}",r(m['recovery1Then3']),r(m['adverse2NoReclaim']),med(m['timeToMfeUpperMinutes']),med(m['timeToMaeUpperMinutes'])]
        for panel,p in x['pairedPanels'].items() for side in ('INITIAL','DIP') for m in [p[side]['metrics']]])
    a('DIPのreference-location改善は同一anchorでも残るが、追加adverseは消えない。'
      'Q10：共通の観測schema（Entryからの距離、peak、逆行履歴、reclaim、時計）は合理的。同じstate数・遷移・EXIT条件で十分かは未検証。'
      '別々のthresholdを作る根拠にもしていない。Q11：Entry sourceはPIT-safeな監査inputとして保持すべき。'
      'ただしINITIAL時点に「将来DIPになる」ラベルを渡してはいけない。DIPイベントが発行された時点でのみ、そのsourceは既知。')
    section(14,'What Existing EXIT Misses')
    a('保存済み前工程の比較では、既存policyがDIP397件で平均・PFを悪化させ、106/21件でも平均を悪化させた。今回はそれを再replayしていない。'
      'Path Studyは、早期negativeでも上がる経路、reclaim後に上がる経路、HIGH機会後にCLOSEが崩れる経路が共存することを示す。'
      '完成CLOSEの単純な下落回数だけで全てを区別できるEvidenceはない。ただし個々の既存ruleが失敗の原因だと因果断定するablationも行っていない。')
    section(15,'What Not To Build')
    a('- 「t5 negativeなら全てEXIT」：後続winnerを失う。\n- 「DIPだから安全・stop不要」：106/21の追加下落が残る。\n'
      '- 「reclaimしたら勝ち確定」：回復後winner率は100%ではない。\n- 「一定givebackなら崩壊確定」：その後の再高値がある。\n'
      '- 既存BAR5/2連続CLOSE思想の自動継承、前回DEFENSIVE拡張案の自動採用。\n- 106/21だけに合わせた閾値・銘柄除外rule。\n'
      '- 観測不足をloserや0として学習するモデル。\n- future MFE/MAE・最終peak・将来DIPラベルを入力にしたstate判定。')
    section(16,'Candidate States for NEW EXIT')
    table(['観測すべき概念','整理','根拠 / n'],[
        ['逆行中のriskと経過','必要そう','追加下落106/299・21/299。Entry距離と時間の分布を保存'],
        ['回復の進行・失敗','必要そう','−1%→reclaim→+3：INITIAL100/878、DIP32/264'],
        ['上昇機会の維持・利益吐き出し','必要そう','+3からEntryへ：107/267・27/69。ただし再高値も存在'],
        ['持続的悪化と一時的押しの区別','まだ識別不能','106 vs193、21 vs278の早期分布が重なる'],
        ['HOLD/DEFENSIVE/RECOVERY/PROTECT等の固定名称・独立state数','未確定','今回stateの割当・遷移・行動は0'],
        ['Entry sourceだけで別EXIT ruleへ分岐','必要性未確認','matched264とcommon328は保存。別ruleの評価0'],
        ['欠測・境界の独立な処理','必要','全3284行でUNKNOWN/BOUNDARYを保持'],
        ['EXIT行動','今回は定義しない','NEW EXIT implementation 0']])
    section(17,'5m Sufficiency / 1m Question — Q12 / Q13')
    a('Q12：5m完成足でEntry距離・running peak/MAE・CLOSE回復・giveback等は観測でき、状態認識を研究する余地はある。'
      'ただし未来のwinner/loserを有効に識別できることは未検証で、5mだけで十分という証明ではない。')
    table(['Cohort','同じ5m足に+1%HIGHと−1%LOWがあるpath n/panel','+3%HIGHと−2%LOW n/panel','全足observedMinutes=5 n/own60'],[
        [name,r(c['own60']['metrics']['sameBarPlus1Minus1Paths']),r(c['own60']['metrics']['sameBarPlus3Minus2Paths']),
         r(s.rate(x['robustness'][s.TYPES[i]]['fullUnderlyingMinutes']['complete']['n'],c['own60Coverage']['n']))]
        for i,(name,c) in enumerate(cohorts)])
    a('Q13：足内順序や疎な元minute coverageが未解決であるEvidenceはある。だが1mでその欠測が解消し、識別や結果が改善するEvidenceはない。'
      '1mが必要と断定しない。自動再開なし。minute coverageは保存メタデータだけを読み、1m価格は取得していない。')
    section(18,'Robustness')
    a('76営業日を時系列順19日×4に固定。winner countや端点結果で分割していない。nが小さい層を一般化しない。')
    table(['Cohort','block','own60 n/全opportunity','MFE中央値 % [n]','MAE中央値 % [n]','t5 negative→後の+3 n/negative','同+5 n/negative'],[
        [name,b,r(v['complete']),med(v['metrics']['mfePct']),med(v['metrics']['maePct']),r(v['metrics']['negative5LaterLevel']['3']),r(v['metrics']['negative5LaterLevel']['5'])]
        for i,(name,c) in enumerate(cohorts) for b,v in x['robustness'][s.TYPES[i]]['chronologicalBlocks'].items()])
    a('t5 negative後の+3は両cohortの全4blockに存在。DIPの+5はblock2で0/23であり、比率が安定とは言わない。')
    table(['Cohort','時間帯','own60 n/opportunity','MFE中央値 % [n]','MAE中央値 % [n]','t5 negative→後の+3 n/negative'],[
        [name,b,r(v['complete']),med(v['metrics']['mfePct']),med(v['metrics']['maePct']),r(v['metrics']['negative5LaterLevel']['3'])]
        for i,(name,c) in enumerate(cohorts) for b,v in x['robustness'][s.TYPES[i]]['timeOfDay'].items()])
    a('事前定義global top-frequency3は21340(63/2743)、89180(63/2743)、67400(59/2743)。'
      'DIPにはこの3銘柄のOpportunityがなく、除外しても変化しないためDIPの頑健性根拠とはしない。'
      'このcoverage問題を確認後、cohort内頻度だけで選ぶtop1/3除外を補足追加した。後付け補足と明示し、成績順位による除外はしない。')
    robustness_rows=[]
    for i,(name,c) in enumerate(cohorts):
        rb=x['robustness'][s.TYPES[i]]
        for key in ('excludeTopFrequency1','excludeTopFrequency3','fullUnderlyingMinutes'):
            v=rb[key];robustness_rows.append([name,key,r(v['complete']),r(v['metrics']['negative5LaterLevel']['3']),r(v['metrics']['negative5LaterLevel']['5'])])
        for key in ('excludeTop1','excludeTop3'):
            v=rb['cohortFrequencySupplement'][key];robustness_rows.append([name,'補足cohort '+key,r(v['complete']),r(v['metrics']['negative5LaterLevel']['3']),r(v['metrics']['negative5LaterLevel']['5'])])
    table(['Cohort','感度分析','complete n/対象','negative5後+3 n/negative','同+5 n/negative'],robustness_rows)
    for depth in (2,5):
        rb=x['riskCohorts'][str(depth)]['robustness'];n=x['riskCohorts'][str(depth)]['cohortN']
        top=sorted(rb['symbols'].items(),key=lambda z:(-z[1],z[0]))[:3]
        a(f"追加下落{depth}%群：{n}件/{len(rb['symbols'])}銘柄。最大頻度の例："+'、'.join(f'{sym} {v}/{n}' for sym,v in top)+'。')
    table(['Risk群','block','complete n/群内block','common55 endpoint平均 % [n]'],[
        [depth,b,r(v['complete']),f"{f(v['metrics']['endpointPct']['mean'])} [n={v['metrics']['endpointPct']['n']}]"]
        for depth,risk in x['riskCohorts'].items() for b,v in risk['robustness']['byBlock'].items()])
    a('全symbol別集計もsummaryに保存。top-frequency除外はdiagnosticだけで、blacklist・銘柄専用ruleへ使っていない。')
    section(19,'Missing / Causality Audit')
    table(['Cohort','own60 status','n/全Opportunity'],[[name,status,f'{n}/{c["opportunities"]}'] for name,c in cohorts for status,n in c['own60Statuses'].items()])
    a('KNOWN referenceがあっても、その後の欠測・昼休み・終端でown60は不成立になる。'
      '未来HIGH/LOW、Remaining Upside、将来下落、next direction、winner/riskタグはevaluatorOnlyに保存。'
      'causalPrefixはtimestampまでの完成足だけ。未来suffix改変でもprefixが変わらないテストを実施した。'
      '時間順序不明なLOW→HIGHは同一足内で勝手に並べず、MFE前MAEの上下限・same-bar unknownとして保持する。'
      'source status EXPIRED_BOUNDARYとstudy status BOUNDARY_EXPIREDは出所を区別してそのまま表示した。')
    a('\n新しいEXIT runtime/API/state transitionはない。評価器のimportはPython標準ライブラリのみ。'
      'Unknownを0やnegativeに変換しない。補間・forward-fill・別provider・再Entry研究は0。'
      '表の割合は観測された分母に限定し、complete subsetを2743全体へ外挿しない。')
    section(20,'Architecture Review Evidence <=10 — Q14')
    points=[
      'Entryは固定。全2743 INITIAL +541 DIPを保持し、own60 878/264・matched264・common328を混同しない。',
      '早期negativeはwinner排除の十分条件ではない。t5で初到達前に失う+3/+5はINITIAL56/267・23/123、DIP22/69・11/27。',
      'DIP winnerにも逆行がある。+3 winnerのMFE前MAE中央値−0.762%、+5では−1.146%。',
      '106/21の早期分布は重なる。t20/t15のIQR差を識別時刻やthresholdへ変換しない。',
      '21件ではt5→t15のCLOSE平均−1.746pp、running MAE平均−2.105pp。待つ側にも具体的な追加riskがある。',
      '回復履歴の保持は重要。−1%→reclaim→後の+3はINITIAL100/878、DIP32/264だが、reclaim即winnerではない。',
      '利益保全の観測は必要。+3からEntryへ戻る107/267・27/69と、1pp giveback後に再高値86/242・23/61が共存する。',
      'INITIAL/DIPには共通の観測座標を使える。Entry sourceは発行時点で既知の情報として保持するが、別ruleの必要性は未確定。',
      'chronological/symbol/time-of-day/coverage sensitivitiesを保存した。小標本、元minute疎性、観測選択、足内順序は残る。',
      '次はEvidenceを用いたArchitecture Review。今回rule・state遷移・model・1m・Fresh/OOS・Portfolioへ進まずSTOP。']
    for i,p in enumerate(points,1):a(f'{i}. {p}')
    section(21,'GitHub / SHA / Tests / CI / Safety')
    a('Repo `Iam-2squared/ark-terminal`、branch `research/phase57-long-only-cash-equity`、PR #587 Draft/unmerged。'
      '開始HEAD `7d8f507809c7d4800a42e76eb5d8ae3a4b4f72af`をGitHubで確認。'
      '測定前protocol公開commit `815c2c9557a9ca867ed81bc0a4b25b3e319d2402`。'
      'Frozen Entry source `6fabde7dfe208e19d5611e0a290b4df6724e562e`。')
    a('\n- `protocol.json` / `protocol.md`：測定前の定義・source pins。\n- `ledger.json.gz`：全3284 opportunityとprefix/evaluator/panel/riskタグ。\n'
      '- `summary.json.gz`：A〜E、winner/deep cohort、全symbol、robustness。\n- `manifest.json`：source/output SHA256・zero counters。\n'
      '- `audit.json`：実施・再現確認・GitHub receipt。\n- `scripts/phase57_new_long_exit_path_study.py`：標準ライブラリのみの評価器。\n'
      '- `scripts/test_phase57_new_long_exit_path_study.py`：13 tests。\n- `scripts/report_phase57_new_long_exit_path_study.py`：本報告の再生成。')
    a('\n```bash\nARK_TEST_OFFLINE=1 python3 scripts/offline/kernel_exec.py python3 -m scripts.phase57_new_long_exit_path_study --out /tmp/phase57-path-repro\n'
      'ARK_TEST_OFFLINE=1 python3 scripts/offline/kernel_exec.py python3 -m unittest scripts.test_phase57_new_long_exit_path_study\n'
      'python3 -m scripts.report_phase57_new_long_exit_path_study\n```')
    a('\n13 testsと全出力のdeterministic regenerationを確認。ネットワークsocketをkernelで遮断して測定・テストした。'
      '本publishing commitのCIはGitHub Actions receiptと最終メッセージで確認する。green CIは科学的/OOS検証済みを意味しない。')
    a('\n**STOP — NEW_LONG_EXIT_PATH_STUDY_COMPLETE**')
    a('\nSelector変更0 / NEW Entry変更0 / Entry Timing再探索0 / NEW EXIT implementation 0 / model fit/prediction 0 / '
      'Fresh/OOS 0 / new provider request 0 / 1m research 0 / Capital/Portfolio tuning 0 / main未merge / Safety全false。')
    (s.BASE/'REPORT.md').write_text('\n'.join(lines)+'\n')
    return '\n'.join(lines)

if __name__=='__main__':render()
