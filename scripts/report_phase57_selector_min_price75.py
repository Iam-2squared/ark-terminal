"""Render fixed-policy impact evidence; no policy decisions or data filtering."""
import argparse,collections,csv,json
from pathlib import Path
from scripts import phase57_selector_min_price75 as m

def fmt(x):return 'N/A' if x is None else f'{x:.4f}' if isinstance(x,float) else str(x)
def run(source,outdir):
    source=Path(source);out=Path(outdir)
    if out.exists():raise FileExistsError(out)
    s=m.read(source/'selector/selector-summary.json');d=m.read(source/'downstream/downstream-summary.json');l=m.read(source/'selector/selector-ledger.json.gz')
    entries=m.read(source/'downstream/entry-ledger.json.gz')
    p=m.verify();lines=[]
    def para(x):lines.extend([x,''])
    def table(headers,rows):
        lines.extend(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |'])
        lines.extend('| '+' | '.join(fmt(v) for v in r)+' |' for r in rows);lines.append('')
    para('# Phase57 — ¥75 Minimum Tradable Price Policy Impact')
    para('2026-09-18 JST / Development only / human-defined Safety Policy / outcome-exposed。')
    para('75円以下を選定対象から除外する事前固定policy。予測最適化のthresholdではない。価格境界・score・モデル・Entry・EXIT変更なし。FREEZE判定とexact HEAD/CIは別freeze manifest/receiptに固定する。')
    para(f"Policy `{p['policyId']}`。Digest `{p['policyDigest']}`。測定前commit `{m.PROTOCOL_COMMIT}`。")
    para(f"Parent Selector commit `{p['parentSelectorCommit']}`、payload `{p['parentSelectorPayloadSHA256']}`、model `{p['parentModelDigest']}`。")
    para('## 1. Policy / causal semantics')
    para('Decision Price <=75 JPY → INELIGIBLE_MIN_PRICE、>75 → price gate上eligible。missing / nonnumeric / nonfinite / bool / nonpositiveはBLOCKED。親のPIT freshness（age 0〜5分）を通過後、Gateを適用してscore降順・symbol昇順の既存Top5を構成する。Entry価格による除外ではない。75円超でも他の親eligibility条件を満たさなければ選定されない。')
    para('Decision Priceは親のlatest causally available accepted market CLOSE。価格のavailableAtはdecision timestamp−保存age。future High/Low/Close・MAE・outcomeをGateへ渡さない。保存minute cacheは既存5m adapterの不変再構成にのみ使用し、新しい1m研究・provider取得・fitは行っていない。')
    para('## 2. Basic impact')
    table(['項目','値'],[(k,json.dumps(v,ensure_ascii=False) if isinstance(v,dict) else v) for k,v in s['impact'].items()])
    para('候補数はsymbol×decision timestamp件数。unique symbolsとは別。760 timestampsを完全pairedで比較し、replacementは元eligible universe内のrankとGate後rankをidentity ledgerへ保存。')
    para('## 3. Opportunity trade-off')
    rows=[]
    for k in m.LEVELS:
        for arm in ['old','new']:
            x=s['opportunity'][arm][str(k)]['high'];a=x['metrics'];b=x['distribution']
            rows.append([f'+{k}',arm,a['selectedHits'],a['precisionAt5Pct'],b['meanHitsPerTop5'],b['probabilityPct']['GE1'],a['actualRecallPct'],a['recallLift'],a['precisionLift'],a['opportunities'],a['hitsOverAllSelectedLowerBoundPct']])
    table(['HIGH','arm','hits','Precision %','mean hits/5','P>=1 %','Recall %','recall lift','precision lift','universe opportunities','all-selected LB %'],rows)
    para('Precisionは親evaluatorと同じHigh観測可能選定分母。all-selected lower boundも併記。Recallとrandom liftは各armのeligible universeに対して計算するので、共通旧universe分母のRecallも次に示す。future欠測による選定差し替えはない。')
    table(['HIGH','旧Top5除外winner','replacement winner','selected hit純増減','旧universe共通分母 new Recall %'],[[k,s['opportunity']['removedOldTop5'][str(k)]['highHits'],s['opportunity']['replacements'][str(k)]['highHits'],s['opportunity']['new'][str(k)]['high']['metrics']['selectedHits']-s['opportunity']['old'][str(k)]['high']['metrics']['selectedHits'],s['opportunity']['commonOldUniverseRecallPct'][str(k)]] for k in m.LEVELS])
    table(['HIGH','全除外candidate hits','evaluable','n'],[[k,*[s['opportunity']['excludedCandidates'][str(k)][z] for z in ['highHits','highEvaluable','n']]] for k in m.LEVELS])
    para('75円以下にwinnerが存在してもPolicyを変更しない。精度改善があっても75円が最適だったとは解釈しない。High touchは約定保証ではない。')
    table(['CLOSE','arm','Precision %','Recall %','P>=1 %'],[[k,arm,s['opportunity'][arm][str(k)]['close']['metrics']['precisionAt5Pct'],s['opportunity'][arm][str(k)]['close']['metrics']['actualRecallPct'],s['opportunity'][arm][str(k)]['close']['distribution']['probabilityPct']['GE1']] for k in m.LEVELS for arm in ['old','new']])
    para('## 4. Frozen Entry downstream / population identity')
    para('Gate後の完全なnew selection streamに対して、同一銘柄・sessionの最初の選定をanchorとする親規則を再適用。共通anchorは保存済みdecisionを再利用し、新anchorのみexact Frozen Entry kernel/replayを使用。first selectionが移動する場合を含め、旧母集団の単純filterとは区別する。')
    table(['arm','cohort','opportunities','reference eligible','strict30 n'],[[arm,c,x['opportunities'],x['referenceEligible'],x['strict30N']] for arm in ['old','new','retained','removed','added'] for c,x in d[arm].items()])
    table(['arm','Decision Price<=75 opportunities','Entry reference<=75 opportunities'],[[arm,sum(r['decisionPrice']<=75 for r in rs),sum(r['entryPrice'] is not None and r['entryPrice']<=75 for r in rs)] for arm,rs in entries.items()])
    para('Policy対象はSelector Decision Price。選定後の値動きでEntry参照価格が75円以下になる場合はあり得るため、上表で別監査する。Entryへ追加Gateは導入しない。')
    para('actual ENTER/fillはNOT_MODELED。Entry opportunity、reference eligibility、Capital Allocationによる資金配分・実約定を混同しない。')
    table(['arm','cohort','+1 strict30 %','+2 %','+3 %','+5 %'],[[arm,c,*[None if x['strict30Opportunity'][str(k)]['rate'] is None else 100*x['strict30Opportunity'][str(k)]['rate'] for k in m.LEVELS]] for arm in ['old','new'] for c,x in d[arm].items()])
    table(['horizon','level','旧winner identity retained','旧winner n','preservation %'],[[h,k,x['n'],x['denominator'],None if x['rate'] is None else 100*x['rate']] for h,levels in d['oldWinnerIdentityPreservation'].items() for k,x in levels.items()])
    newids={(r['anchorId'],r['cohort']) for r in entries['new']}
    cohort_preservation=[]
    for cohort in ['INITIAL_ENTRY_OPPORTUNITY','DIP_REPRICE_OPPORTUNITY']:
        for k in m.LEVELS:
            winners=[r for r in entries['old'] if r['cohort']==cohort and r['strict30']['status']=='COMPLETE' and r['strict30']['mfePct']>=k]
            kept=sum((r['anchorId'],r['cohort']) in newids for r in winners)
            cohort_preservation.append([cohort,k,kept,len(winners),100*kept/len(winners) if winners else None])
    table(['cohort','level strict30','旧winner retained','旧winner n','preservation %'],cohort_preservation)
    para('sessionHighのprecision・coverageはdownstream-summary.json。観測された後続Highに基づく機会であり、全session pathが揃うという意味ではない。strict30は前MAE診断と同じ6本連続完成5m、昼休み跨ぎなし。')
    para('## 5. MAE secondary diagnostic')
    table(['arm','cohort','n','MAE median %','p05 %','worst %','<=-3','<=-5','<=-10'],[[arm,c,x['strict30N'],x['strict30MAE']['median'],x['strict30MAE']['p05'],x['strict30MAE']['min'],*[x['tails'][str(k)]['n'] for k in [3,5,10]]] for arm in ['old','new','retained','removed','added'] for c,x in d[arm].items()])
    w=d['worst17Identity'];para(f"旧worst `{w['anchorId']}`: Selector Decision Price {w['decisionPrice']}円 / Entry {w['entryPrice']}円 / strict30 MAE {w['strict30']['maePct']:.4f}%。Selector段階の除外={w['removedFromSelector']}。旧Fixed12/A net −29.4618%は前Evidenceを保持し、今回EXIT再測定はしていない。")
    tails=d['oldDeep10Identities'];para(f"旧<=−10% {len(tails)}件のうち、Decision Price Gate対象 {sum(r['anchorMinPriceIneligible'] for r in tails)}件、同一Entry opportunity非保持 {sum(not r['sameOpportunityRetained'] for r in tails)}件。new全体の残存tailはreplacement・anchor移動も含む上表のnew値。")
    table(['symbol','旧deep10 n','Gate対象','同一opportunity retained'],[[sym,sum(r['symbol']==sym for r in tails),sum(r['symbol']==sym and r['anchorMinPriceIneligible'] for r in tails),sum(r['symbol']==sym and r['sameOpportunityRetained'] for r in tails)] for sym in sorted({r['symbol'] for r in tails})])
    table(['arm','cohort','deep10 n','deep10 symbol HHI','deep10 symbols'],[[arm,c,x['tails']['10']['n'],sum((v/x['tails']['10']['n'])**2 for v in x['tails']['10']['symbols'].values()) if x['tails']['10']['n'] else None,json.dumps(x['tails']['10']['symbols'],sort_keys=True)] for arm in ['old','new'] for c,x in d[arm].items()])
    para('MAE分布変化は上流eligibilityによる母集団変更の記述。EXIT問題の解決、実現利益改善、未知データの再現性を示すものではない。')
    para('## 6. Chronological / concentration')
    table(['block','arm','+3 Precision %','+5 Precision %','+3 P>=1 %','+5 P>=1 %'],[[b,arm,x[arm]['3']['high']['metrics']['precisionAt5Pct'],x[arm]['5']['high']['metrics']['precisionAt5Pct'],x[arm]['3']['high']['distribution']['probabilityPct']['GE1'],x[arm]['5']['high']['distribution']['probabilityPct']['GE1']] for b,x in s['chronological'].items() for arm in ['old','new']])
    table(['selection','n','symbol unique','symbol HHI','session HHI','top symbols'],[[arm,x['n'],x['symbol']['unique'],x['symbol']['HHI'],x['session']['HHI'],json.dumps(x['symbol']['top10'],ensure_ascii=False)] for arm,x in s['concentration'].items() if isinstance(x,dict)])
    para('頻出除外は旧Selectorの固定top3 '+json.dumps(s['concentration']['oldTop3FixedExclusion'])+' を両armに同じように適用した診断のみ。新たなblacklistは作成しない。')
    table(['block','arm','cohort','strict30 n','p05','worst','<=-10'],[[b,arm,c,x['strict30N'],x['strict30MAE']['p05'],x['strict30MAE']['min'],x['tails']['10']['n']] for b,arms in d['chronological'].items() for arm,cs in arms.items() for c,x in cs.items()])
    para('76 session別の全opportunity統計、INITIAL/DIP別集中、固定top3除外後MAEはJSON原本に保存。')
    para('## 7. Integrity / STOP')
    para('Selector audit: '+json.dumps(s['audit'],sort_keys=True))
    para('Entry audit: '+json.dumps(d['audit'],sort_keys=True))
    para('測定時のold Top5 3,800 identity/price/rank完全一致・scoreのCSV表現差監査、旧opportunity集計一致、旧strict30 1,697件一致を必須assertionで確認。runtime Gateと全候補measurementのTop5一致、入力逆順でも同一selectionを確認。')
    para('全9Safety flags false。Fresh/OOS未開封。旧Selector・Entry・Candidate A・旧Evidenceは不変。専用CIでは新measurement 7ファイルのbyte一致を確認し、artifact内容を確認後にFreeze判定する。既存Candidate C KILL gateはそのまま保持。')
    para('本policyのimpact audit完了でSTOP。Entry/EXIT研究、Fresh/OOS、Capital、Portfolio、main merge、実行機能へ進まない。')
    out.mkdir(parents=True);(out/'REPORT.md').write_text('\n'.join(lines))
    fields=['arm','selectorEventId','sessionDate','symbol','decisionTimestamp','decisionPrice','decisionPriceAvailableAtJst','referenceAgeMin','savedV1Score','oldEligibleRank','newEligibleRank','priceGateStatus']
    with (out/'selected-and-excluded-identities.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');writer.writeheader()
        for arm in ['old','new','removedOldTop5','replacements','excludedCandidates']:
            for r in l[arm]:writer.writerow({k:arm if k=='arm' else r.get(k) for k in fields})
    m.write(out/'manifest.json',{'sourceHashes':{str(p.relative_to(source)):m.sha(p) for p in sorted(source.rglob('*')) if p.is_file()},'codePin':m.sha(__file__),'outputPins':{n:m.sha(out/n) for n in ['REPORT.md','selected-and-excluded-identities.csv']}})
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--out',required=True);a=p.parse_args();run(a.source,a.out)
