"""Render pinned diagnostic evidence; no market access or policy replay."""
import argparse
import collections
import csv
import json
from pathlib import Path
from scripts import phase57_strict30_mae_attribution as m


def num(x):return 'N/A' if x is None else f'{x:.4f}'
def pct(x):return 'N/A' if x is None else f'{x*100:.2f}%'
def rate(x):
    text=f"{x['n']}/{x['denominator']} ({pct(x['rate'])})"
    if x.get('unknown'):text+=f"; unknown {x['unknown']}"
    return text


def run(source,out):
    source,out=Path(source),Path(out)
    if out.exists():raise FileExistsError(out)
    s=m.read(source/'summary.json');rows=m.read(source/'ledger.json.gz')
    lines=[]
    def para(text):lines.extend([text,''])
    def table(headers,rs):
        lines.append('| '+' | '.join(headers)+' |');lines.append('| '+' | '.join('---' for _ in headers)+' |')
        for r in rs:lines.append('| '+' | '.join(str(x).replace('|',' / ') for x in r)+' |')
        lines.append('')
    para('# Phase57 — Strict 30m MAE Tail Attribution Diagnostic')
    para('Date: 2026-09-18 JST。Historical Development / outcome-exposed。診断のみ。')
    para(f"**最終Attribution Verdict: {s['finalAttributionVerdict']}**")
    para('事実としてRecoveryとFailureは混在する。特にFixed12まで観測できたdeep群はMIXED判定。'
         'ただし測定前に固定した主判定はstrict30であり、その判定規則ではINCONCLUSIVE。'
         '結果を見て主horizonや判定条件を変更しない。Entry・Selector・EXITのどれが主原因かの因果断定はできない。')
    para('## 1. 数値の出所を訂正')
    para('指定のmedian −1.53% / p05 −10.26% / worst −35.29%は、旧MSH Entry v1の277 ENTER中strict30を観測できた181件の値。'
         '現行Frozen NEW EntryのINITIAL/DIPとは別母集団・別参照価格。旧181件を正確に再現したうえで、現行3,284 opportunityを独立集計した。')
    table(['Panel','全opportunity/ENTER','strict30 n','MAE median %','p05 %','worst %'],[
        [k,p['population']['all'],p['population']['strict'],num(p['overall']['maePct']['median']),num(p['overall']['maePct']['p05']),num(p['overall']['maePct']['min'])] for k,p in s['panels'].items()])
    para(f"開始GitHub HEAD `{m.START_HEAD}`。測定前protocol commit `{m.PROTOCOL_COMMIT}`。PR #587 Draft / unmerged。")
    para('Source identity: '+json.dumps(s['sourceIdentity'],ensure_ascii=False))
    para('76 Development sessions / 2024-09-17〜2025-01-09。CURRENT overallはopportunity加重。INITIALとDIPは同じanchorに属する場合があり、独立trade数・Portfolio収益ではない。')
    para('旧181と現行1,697の分布差をEntry改善効果とは呼ばない。元母集団、reference、coverageが違い、pairedな改善実験ではない。')
    para('## 2. Coverage / outcome semantics')
    for k,p in s['panels'].items():para(f"{k}: `{json.dumps(p['coverage'],sort_keys=True)}`")
    para('旧LEGACYのFROZEN_DECISION_CLOSE_REFERENCE 20件は保存future配列が空のsession-end群。旧coverageの51 provider gap / 25 lunch / 20 session endを保持。'
         '現行INITIALには保存Entry側のEXPIRED_BOUNDARYもある。unknownを損失ゼロ・安全・失敗にしない。')
    para('strict30=6本の連続5m完成足、30時計分、昼休み跨ぎなし。元minute観測が疎な足を事後除外せず、full-minute感度を別記する。'
         'Fixed12は保存済みcalendar capで昼休みを跨ぐことがある。session結果は全expected regular barが揃った場合のみ。最終auction補間なし。')
    para('Recoveryは将来HIGHのopportunity labelであり約定・実現利益ではない。先に上がって後に暴落した例を回復winnerへ数えない。'
         'HIGH/LOW同一足順序はUNKNOWN_INTRABAR_ORDER。終値はその足のLOWより後だが、保守的later-CLOSE reclaimとは別項目。')
    para('## 3. Deep tail分類とhorizon差')
    para('最初のLOW<=−dをstrict30内で固定し、その後の各horizonを追跡。RECOVERY_WINNER=後続足で+3到達。'
         'RECOVERY_BUT_NO_MAJOR_WIN=明確なCLOSE reclaimのみ。CONTINUED_FAILURE=回復なし、後続足あり、terminal<=−d。その他・順序不明はINCONCLUSIVE。'
         'Winner後に再度損失となる例はrecoveryとして残し、givebackとして別計数する。')
    table(['Panel','Tail','n','horizon','完全観測n','Recovery winner','Reclaim only','Continued failure','Inconclusive（欠測含む）'],[
        [k,'<=-'+d,x['n'],h,v['observed'],v['classes'].get('RECOVERY_WINNER',0),v['classes'].get('RECOVERY_BUT_NO_MAJOR_WIN',0),v['classes'].get('CONTINUED_FAILURE',0),v['classes'].get('INCONCLUSIVE',0)]
        for k,p in s['panels'].items() for d,x in p['deep'].items() for h,v in x['horizons'].items()])
    current=s['panels']['CURRENT_OVERALL']['deep']['3'];strict=current['horizons']['STRICT30'];fixed=current['horizons']['FIXED12_WINDOW']
    para(f"主判定：−3%以下{current['n']}件のstrict30分類は{strict['classes']}。INCONCLUSIVE 121/348=34.77%で、事前規則の1/3上限を超える。最終判定はINCONCLUSIVE。")
    para(f"Fixed12完全観測{fixed['observed']}件では{fixed['completeClassCounts']}。{fixed['verdictCompleteSubsetOnly']}。"
         '残り38件を失敗扱いしない。この混在はINITIAL/DIP双方、4時系列block、頻出3銘柄除外後にも観測される。')
    # Explain residuals without changing classification labels or gate definitions.
    residual={}
    for name in ('CURRENT','LEGACY'):
        counts=collections.Counter()
        for r in rows:
            if r['panel']!=name or '3' not in r.get('deep',{}):continue
            h=r['deep']['3']['horizons']['STRICT30']
            if h['classification']!='INCONCLUSIVE':continue
            cause=('TRIGGER_HIGH_LOW_ORDER_UNKNOWN' if h['recovery']['3']['triggerBarHighOrder']=='UNKNOWN_INTRABAR_ORDER' else
                   'LAST_BAR_BREACH_NO_LATER_OBSERVATION' if not h['laterBars'] else
                   'PARTIAL_RECOVERY_STILL_NEGATIVE_ABOVE_DEEP_THRESHOLD')
            counts[cause]+=1
        residual[name]=dict(counts)
    para('INCONCLUSIVEの内訳（追加の説明であり定義変更なし）：'+json.dumps(residual,ensure_ascii=False))
    para('## 4. Deep tailの回復・EXIT勝率')
    para('下表は全deep nに対する「確認できた回復」の件数/率。最後の足で初めて逆行した等のunknownを成功にも失敗にも確定しない。'
         '観測可能分母での率とunknown数はsummary.jsonに別保存。EXIT Winは両policyを観測できたpaired分母。')
    table(['Panel','tail / n','horizon','後+3 / 全deep','後+5 / 全deep','later reclaim / 全deep','Fixed12 Win','A Win'],[
        [k,'<=-'+d+' / '+str(x['n']),h,
         rate(m.rate(v['recovery']['3']['n'],x['n'])),rate(m.rate(v['recovery']['5']['n'],x['n'])),rate(m.rate(v['laterCloseReclaim']['n'],x['n'])),
         rate(x['fixed12']['win']),rate(x['candidateA']['win'])]
        for k,p in s['panels'].items() for d,x in p['deep'].items() for h in ('STRICT30','FIXED12_WINDOW') for v in [x['horizons'][h]]])
    para('## 5. MAE bucket別 opportunity / recovery / failure / EXIT')
    para('bucketは分布記述のみ。stopやfilterへの採用0。境界はprotocolどおり固定し、累積<=−3/5/10とは分母が違う。')
    for k,p in s['panels'].items():
        para('### '+k)
        table(['MAE bucket','n','strict比','全opportunity比','any +1','any +2','any +3','any +5'],[
            [b,x['n'],pct(x['ofStrictObserved']['rate']),pct(x['ofAllOpportunities']['rate'])]+[rate(x['anyTimeReach30'][str(v)]) for v in m.LEVELS]
            for b in m.BUCKETS for x in [p['buckets'][b]]])
        para('次は最初のglobal30m MAEより後の別足での回復。any-timeの上昇機会とは区別。MAE=0はEntryを基準とする。')
        table(['MAE bucket','after MAE +1','+2','+3','+5','later CLOSE reclaim'],[
            [b]+[rate(x['afterGlobal30Mae']['recovery'][str(v)]) for v in m.LEVELS]+[rate(x['afterGlobal30Mae']['laterCloseReclaim'])]
            for b in m.BUCKETS for x in [p['buckets'][b]]])
        table(['MAE bucket','reclaim中央値 Entry分','+3到達上限中央値 Entry分','+5上限中央値','positive CLOSE','追加下落>=2%','>=5%','session更に悪化'],[
            [b,num(a['reclaimMinutesFromEntry']['median']),num(a['plus3MinutesUpperFromEntry']['median']),num(a['plus5MinutesUpperFromEntry']['median']),rate(a['laterPositiveClose']),rate(a['additionalDrop2']),rate(a['additionalDrop5']),rate(x['furtherSessionWorsening'])]
            for b in m.BUCKETS for x in [p['buckets'][b]] for a in [x['afterGlobal30Mae']]])
        para('追加下落はadverse足のcompleted CLOSEを基準にした後続LOW。Entry基準MAEや既存DIP106/21タグとは別。')
        table(['MAE bucket','MAE median','MFE median','after MAE MFE median','giveback median pp','terminal30 mean %','session terminal mean / n'],[
            [b,num(x['maePct']['median']),num(x['mfePct']['median']),num(x['afterGlobal30Mae']['mfeAfterAnchorPct']['median']),num(x['strict30GivebackPP']['median']),num(x['strict30TerminalPct']['mean']),num(x['sessionTerminalPct']['mean'])+' / '+str(x['sessionTerminalPct']['n'])]
            for b in m.BUCKETS for x in [p['buckets'][b]]])
        table(['MAE bucket','policy','paired n','mean %','median %','PF','p05 %','Win'],[
            [b,arm,x[arm]['n'],num(x[arm]['mean']),num(x[arm]['median']),num(x[arm]['PF']),num(x[arm]['p05']),rate(x[arm]['win'])]
            for b in m.BUCKETS for x in [p['buckets'][b]] for arm in ('fixed12','candidateA')])
    para('## 6. INITIAL / DIP比較とEXIT母集団')
    table(['Panel','tail3 n/strict','tail5','tail10','EXIT paired n','Fixed mean / PF','A mean / PF'],[
        [k,rate(p['deep']['3']['ofStrictObserved']),rate(p['deep']['5']['ofStrictObserved']),rate(p['deep']['10']['ofStrictObserved']),p['overall']['pairedExitN'],
         num(p['overall']['fixed12']['mean'])+' / '+num(p['overall']['fixed12']['PF']),num(p['overall']['candidateA']['mean'])+' / '+num(p['overall']['candidateA']['PF'])]
        for k,p in s['panels'].items()])
    para('今回のCURRENT EXIT paired n=1,396（INITIAL1,072 / DIP324）はstrict30との共通集合。前研究のA baseline1,469（DIP397）と同じ分母ではない。'
         '旧LEGACYのAはpolicyを変更せず旧referenceへ投影した診断値であり、Aの新しいFreeze・validation・採用結果ではない。')
    para('DIPのtail発生率が低いことだけでDIP Entryが因果的に優れるとは断定しない。source構成、参照位置、観測可能範囲が異なる。')
    para('## 7. MAE→MFE順序 / post-exit attribution')
    table(['Panel','MAE→MFE','MFE→MAE','same-bar unknown','MFEなし','逆行なし'],[
        [k]+[p['overall']['ordering'].get(v,0) for v in ('MAE_BEFORE_MFE','MFE_BEFORE_MAE','UNKNOWN_INTRABAR_ORDER','NO_POSITIVE_MFE','NO_ADVERSE_MAE')]
        for k,p in s['panels'].items()])
    for k,p in s['panels'].items():
        for d,x in p['deep'].items():para(f"{k} <=−{d}: A退出との順序 `{json.dumps(x['relativeToCandidateAExit'],sort_keys=True)}`")
    para('A退出OPENより後のLOWはcounterfactual pathであり、A保有中MAEではない。Exit OPEN自身がthreshold以下なら退出時点までの逆行。'
         'global strict30 MAEとA held MAEをtrade ledgerで分離。')
    para('## 8. Worst −35.294118% path')
    for w in s['worstCases']['CURRENT']:
        r=w['record'];x=r['strict30']
        para(f"Identity `{r['anchorId']}` / {r['cohort']} / Entry `{r['entryTimestamp']}` / reference {r['referencePrice']}円。旧181にも同じanchor・同じ17円referenceが存在する。")
        para('MAE: '+json.dumps(x['maeLocation'])+'。MFE: '+json.dumps(x['mfeLocation']))
        para('30m内+1/+2/+3/+5: '+json.dumps(x['anyTimeReach'])+'。strict30/Fixed12ともcompleted CLOSE reclaimなし、CONTINUED_FAILURE。')
        para(f"Fixed12 net {num(r['fixed']['netPct'])}% / A net {num(r['candidateA']['netPct'])}%、{r['candidateA']['status']}。+3未到達のためAはarmしない。")
        table(['5m開始 JST','OPEN円','HIGH円','LOW円','CLOSE円','observed minute n'],[
            [b['start'][11:16]]+[num(b.get(v+'Price')) for v in ('o','h','l','c')]+[b.get('observedMinutes')]
            for b in w['fullSavedPath'][:12]])
        para('17円に対する1円差は5.88%。これは価格尺度の算術であり、tick size・spread・約定可能性の認証ではない。'
             '保存sessionの後半にもさらなる安値は観測されるが全expected barは揃わず、session終端損益はUNKNOWN。銘柄専用ruleは作成しない。')
    para('## 9. Selector opportunityとの接続・集中')
    table(['Panel','score AUC: higher→deep','deep n','nondeep n','<=−10 symbol counts'],[
        [k,num(p['selectorScoreAUC']['aucHigherScoreDeep']),p['selectorScoreAUC']['deepN'],p['selectorScoreAUC']['nondeepN'],json.dumps(p['deep']['10']['symbolCounts'],sort_keys=True)] for k,p in s['panels'].items()])
    para('scoreは損失確率ではない。現行では深い逆行群のscoreが低いとは言えず、粗いupside opportunityとpath riskが共存する。'
         'ただし高scoreだからSelectorが正しかった、とも断定しない。厳密な逆行後recoveryとterminal outcomeを併記する必要がある。')
    para('現行<=−10は25件でINITIALのみ。うち89180が10件、57590が7件。集中を記録するが銘柄除外ルールにはしない。'
         'selector未来MFE/opportunityはevaluatorOnlyとして分離し、decision特徴へは使わない。')
    table(['Panel / group','deep3 n','Fixed12 complete n','recovery winner','continued failure','score AUC'],[
        [k+' / '+g,v['deep3']['n'],h['observed'],h['completeClassCounts'].get('RECOVERY_WINNER',0),h['completeClassCounts'].get('CONTINUED_FAILURE',0),num(v['selectorScoreAUC']['aucHigherScoreDeep'])]
        for k,p in s['panels'].items() for g,v in p['robustness'].items() for h in [v['deep3']['horizons']['FIXED12_WINDOW']]])
    para('rank1〜5の全分布、scoreのbucket別分布、session/symbol concentrationはsummary.json。Outcomeに合わせたrank cutoff・symbol exclusion・time ruleなし。')
    para('## 10. Verification / stop')
    para('Source/PIT/prefix audit: '+json.dumps(s['audit'],sort_keys=True))
    para('18 attribution unit tests: bucket境界、same-bar順序、上昇先行、回復後giveback、missing/lunch、post-exit LOW、future suffix、固定分類gate、上書き拒否。'
         '同じ診断を新directoryへ再生成しbyte一致を確認する。GitHub CIとexact code HEADは別receiptへ追記。')
    para('Candidate A / Frozen Entry / Selector / 既存Evidence変更0。全9Safety flags false。Fresh/OOS未開封、新provider0、1m0、fit0、Capital/Portfolio0、main merge0。')
    para('判断できたこと：deep MAEを一律Entry failure扱いして除外する根拠はない。回復機会を保持する必要がある一方、worstのような実損失もある。'
         'Fixed12 follow-upでは両方が確認できる。今回だけではEntry前に識別できるか、Selector/HOLD/EXITのどこが主原因かは確定しない。')
    para('**診断完了でSTOP。改善案の実装・threshold変更・Fresh/OOS開封は行わない。**')
    out.mkdir(parents=True,exist_ok=False)
    (out/'REPORT.md').write_text('\n'.join(lines))
    fields=['panel','anchorId','cohort','symbol','sessionDate','entryTimestamp','referencePrice','strict30Status','maePct','mfePct','bucket','ordering','fixed12Net','candidateANet','candidateAScope','sessionComplete','sessionTerminalPct','class3_30','class3_Fixed12','class5_30','class5_Fixed12','class10_30','class10_Fixed12']
    with (out/'trade-path-attribution.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');writer.writeheader()
        for r in rows:
            x={k:r.get(k) for k in fields};z=r['strict30'];x.update(strict30Status=z['status'],maePct=z.get('maePct'),mfePct=z.get('mfePct'),ordering=z.get('ordering'),fixed12Net=r['fixed']['netPct'] if r['fixed'] else None,candidateANet=r['candidateA']['netPct'] if r['candidateA'] else None)
            for d in (3,5,10):
                for label,h in [('30','STRICT30'),('Fixed12','FIXED12_WINDOW')]:x[f'class{d}_{label}']=r.get('deep',{}).get(str(d),{}).get('horizons',{}).get(h,{}).get('classification')
            writer.writerow(x)
    (out/'manifest.json').write_bytes(m.encoded({'inputPins':{n:m.sha(source/n) for n in ('summary.json','ledger.json.gz')},'codePin':m.sha(Path(__file__)),
        'outputPins':{n:m.sha(out/n) for n in ('REPORT.md','trade-path-attribution.csv')},'inconclusiveReasons':residual}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--out',required=True);a=p.parse_args();run(a.source,a.out)
