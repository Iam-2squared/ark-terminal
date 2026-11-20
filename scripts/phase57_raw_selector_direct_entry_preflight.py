"""Metadata-only raw Selector census. No model, outcomes, Entry or EXIT replay."""
import argparse
import collections
import gzip
import hashlib
import json
import statistics
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'docs/evidence/phase57-raw-selector-direct-entry-v1/preflight'
SOURCE=ROOT/'docs/evidence/phase57-selector-min-price75-v1/measurement/selector/selector-ledger.json.gz'
TIMES=('09:30','10:00','10:30','11:00','11:30','13:00','13:30','14:00','14:30','15:00')
FIELDS=('selectorEventId','sessionDate','symbol','decisionTimestamp','decisionTimeJst','decisionPrice','decisionPriceAvailableAtJst','decisionPriceKind','referenceAgeMin','savedV1Score','newEligibleRank')
SAFETY={k:False for k in ('executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted')}


def read(p):
    p=Path(p);data=p.read_bytes()
    return json.loads(gzip.decompress(data) if p.suffix=='.gz' else data)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def enc(x):return (json.dumps(x,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n').encode()
def write(p,x):
    data=enc(x)
    if str(p).endswith('.gz'):data=gzip.compress(data,mtime=0)
    with Path(p).open('xb') as f:f.write(data)


def project(rows):
    return sorted([{k:r[k] for k in FIELDS} for r in rows],key=lambda r:(r['decisionTimestamp'],r['newEligibleRank']))


def known_state(rows,session,symbol,timestamp):
    """No invented selection/drop/updated score at unobserved Selector time."""
    observed={r['decisionTimestamp'] for r in rows if r['sessionDate']==session and r['decisionTimestamp']<=timestamp}
    if timestamp not in observed:return {'status':'UNOBSERVED_NO_SELECTOR_DECISION','currentRank':None,'currentScore':None}
    prior=[r for r in rows if r['sessionDate']==session and r['symbol']==symbol and r['decisionTimestamp']<=timestamp]
    prior.sort(key=lambda r:r['decisionTimestamp'])
    current=next((r for r in prior if r['decisionTimestamp']==timestamp),None)
    schedule=sorted(observed);indices=[schedule.index(r['decisionTimestamp']) for r in prior]
    gap_count=sum(b>a+1 for a,b in zip(indices,indices[1:]))
    run=0
    if current:
        run=1
        for a,b in reversed(list(zip(indices,indices[1:]))):
            if b!=a+1:break
            run+=1
    return {'status':('RESELECTED' if len(indices)>1 and indices[-1]>indices[-2]+1 else 'SELECTED') if current else 'OBSERVED_DROPPED' if prior else 'NOT_YET_SELECTED',
        'currentRank':current['newEligibleRank'] if current else None,'currentScore':current['savedV1Score'] if current else None,
        'currentDecisionPrice':current['decisionPrice'] if current else None,'firstSelectedTimestamp':prior[0]['decisionTimestamp'] if prior else None,
        'lastSelectedTimestamp':prior[-1]['decisionTimestamp'] if prior else None,'selectionCountKnown':len(prior),'consecutiveObservedSelectionCount':run,
        'selectionGapsKnown':gap_count,'rankHistory':[r['newEligibleRank'] for r in prior],'scoreHistory':[r['savedV1Score'] for r in prior],
        'selectedTimesKnown':[r['decisionTimestamp'] for r in prior]}


def episodes(rows):
    groups=collections.defaultdict(list)
    for r in rows:groups[(r['sessionDate'],r['symbol'])].append(r)
    out=[]
    for (date,symbol),rs in sorted(groups.items()):
        rs.sort(key=lambda r:r['decisionTimestamp']);slots=[TIMES.index(r['decisionTimeJst']) for r in rs]
        maxrun=run=1
        for a,b in zip(slots,slots[1:]):
            run=run+1 if b==a+1 else 1;maxrun=max(maxrun,run)
        gaps=sum(b>a+1 for a,b in zip(slots,slots[1:]))
        out.append({'id':date+'|'+symbol,'session':date,'symbol':symbol,'firstSelectedTimestamp':rs[0]['decisionTimestamp'],
            'lastSelectedTimestamp':rs[-1]['decisionTimestamp'],'selectionCount':len(rs),'maxConsecutiveObservedSelections':maxrun,
            'selectionGapCount':gaps,'metadataEpisodeClass':'HAS_RESELECTION' if gaps else 'SINGLE_OBSERVED_SELECTION_RUN',
            'crossLunchSelectedPairs':sum(a['decisionTimeJst']=='11:30' and b['decisionTimeJst']=='13:00' for a,b in zip(rs,rs[1:])),
            'selections':rs})
    return out


def census(rows):
    ep=episodes(rows);counts=collections.Counter(r['decisionTimestamp'] for r in rows)
    return {'sessions':len({r['sessionDate'] for r in rows}),'timestamps':len(counts),'rawSelectedRows':len(rows),
        'candidateCountDistribution':dict(sorted(collections.Counter(counts.values()).items())),
        'candidateCountMean':statistics.mean(counts.values()),'candidateCountMedian':statistics.median(counts.values()),
        'symbolSessionEpisodes':len(ep),'singleObservedSelectionRun':sum(r['selectionGapCount']==0 for r in ep),
        'withObservedReselection':sum(r['selectionGapCount']>0 for r in ep),
        'selectionCountDistribution':dict(sorted(collections.Counter(r['selectionCount'] for r in ep).items())),
        'maxConsecutiveObservedSelectionsDistribution':dict(sorted(collections.Counter(r['maxConsecutiveObservedSelections'] for r in ep).items())),
        'overlappingPersistencePanels':{'selectedOnce':sum(r['selectionCount']==1 for r in ep),'maxConsecutive2':sum(r['maxConsecutiveObservedSelections']==2 for r in ep),
            'maxConsecutive3Plus':sum(r['maxConsecutiveObservedSelections']>=3 for r in ep),'maxConsecutive5Plus':sum(r['maxConsecutiveObservedSelections']>=5 for r in ep)},
        'selectionTimeJstCounts':dict(sorted(collections.Counter(r['decisionTimeJst'] for r in rows).items()))}


def verify_sources():
    frozen=read(ROOT/'predict/research/phase57-long-only-frozen-selector-min-price75-v1.json')
    assert frozen['status']=='FROZEN_LONG_SELECTOR_WITH_MIN_PRICE_75'
    for f,h in frozen['freezePayload']['filePins'].items():assert sha(ROOT/f)==h,f
    assert frozen['freezePayload']['eligibleComparator']=='decisionPrice > 75'
    assert frozen['freezePayload']['safety']==SAFETY
    integrated=read(ROOT/'docs/evidence/phase57-integrated-long-entry-v1/closure-manifest.json')
    for f,h in integrated['filePins'].items():assert sha(ROOT/f)==h,f
    for f,h in integrated['sourcePins'].items():assert sha(ROOT/f)==h,f
    return frozen,integrated


def build():
    frozen,integrated=verify_sources()
    rows=project(read(SOURCE)['new']);p=read(ROOT/'docs/evidence/phase57-integrated-long-entry-v1/protocol.json')
    assert len(rows)==len({r['selectorEventId'] for r in rows})==3800
    assert set(r['decisionTimeJst'] for r in rows)==set(TIMES)
    groups=collections.defaultdict(list)
    for r in rows:
        groups[r['decisionTimestamp']].append(r)
        assert r['decisionPrice']>75
        age=(datetime.fromisoformat(r['decisionTimestamp'])-datetime.fromisoformat(r['decisionPriceAvailableAtJst'])).total_seconds()/60
        assert 0<=age<=5 and age==r['referenceAgeMin']
    assert len(groups)==760
    for rs in groups.values():
        assert len(rs)==5
        assert [r['newEligibleRank'] for r in sorted(rs,key=lambda r:(-r['savedV1Score'],r['symbol']))]==[1,2,3,4,5]
    old=read(ROOT/'docs/evidence/phase57-price75-entry-opportunity-timestamp-counts-v1/summary.json')
    confusion=old['panels']['FROZEN_SELECTOR_DECISION_TIMESTAMPS']
    assert confusion['opportunityEvents']==2841 and abs(confusion['candidateSymbols']['mean']-2841/760)<1e-12
    summary={'status':'DATA_CONTRACT_BLOCKED_RAW_5M_SELECTOR_STREAM_UNAVAILABLE','sourceHead':'727277a2e726805ee58c4a21603ee7604ed2cefc',
        'scope':'Metadata identity/cadence and observed episode census only; no Entry candidate or future outcomes.',
        'raw':census(rows),'byPartition':{k:census([r for r in rows if r['sessionDate'] in ds]) for k,ds in p['split'].items()},
        'split':p['split'],'misidentifiedCount':{'actualMeaning':'INITIAL Opportunity emissions at original Selector timestamps after first-per-symbol-session compression','rawSelectorCount':False,'savedPanel':confusion},
        'cadence':{'frozenDecisionTimesJst':list(TIMES),'regularWithinSegmentGapMinutes':30,'lunchGapMinutes':90,
            'fiveMinuteUpdatedScoresRanksSaved':False,'fiveMinutePriceBarsAreSelectorState':False,
            'missingSelectorTicks':'UNOBSERVED, never DROP or repeated SELECTED; no forward-fill/interpolation of score/rank'},
        'episodeCensusSemantics':'One symbol-session identity. Consecutive means adjacent observed frozen schedule slots, NOT five-minute persistence; includes 11:30 to13:00 as adjacent observed slots, cross-lunch pairs identified separately. This is a census, not an adopted Entry contract.',
        'blockers':['No 5m raw Selector state stream in canonical frozen ledger. Frozen schedule is ten30m decision times/day.','5m OHLC alone cannot reconstruct full-universe PIT features, eligibility and top5 scores/ranks.','No matching full-universe minute-pages/dataset TSV cache found in workspace or /tmp metadata file search. No provider acquisition or source expansion authorized.'],
        'possibleSeparateContracts':['Keep exact30m frozen Selector updates; Entry WATCH may inspect completed5m price bars while score/rank age grows explicitly. This tests a different hypothesis and needs confirmation.','A genuinely refreshed5m Selector stream needs an explicit source/cadence contract and complete verified inputs; not produced or acquired here.'],
        'modelFits':0,'candidateCount':0,'validationCandidateEvaluations':0,'developmentTestCandidateEvaluations':0,'economicEvaluations':0,
        'metadataOnlyAcross76Sessions':True,'freshOOSOpened':False,'providerRequests':0,'selectorMutation':False,'safety':SAFETY}
    return rows,episodes(rows),summary


def report(s):
    a=s['raw'];out=['# Raw Selector Direct Entry — Source Preflight','', '**'+s['status']+'**','',
        '初回Validation測定は未実施。Candidate/fit/Entry・EXIT評価は0。性能FAILではなく、要求された5分Selector streamが正本に存在しないという入力契約の停止。','',
        '| 項目 | 指示書の前提 | 保存済み正本 |','| --- | --- | --- |',
        '| Decision timestamps | 760 | 760 |','| cadence | 5分 | 通常30分、昼休み間90分 |','| selected rows | 平均3.7382×760相当 | 3800 |',
        '| mean / median / max candidates | 3.7382 / 4 / 5 | 5 / 5 / 5 |','| 0/1/2/3/4/5銘柄timestamp分布 | 1/17/99/180/229/234 | 0/0/0/0/0/760 |','',
        '3.7382はFrozen NEW EntryのINITIAL発行数2841÷760。raw Top5ではない。原reportもSAVED_OPPORTUNITY_TIMESTAMP_SYMBOL_COUNT_ONLYと明記している。過去Evidenceは書き換えていない。','',
        'Frozen時刻: '+', '.join(TIMES)+'。Decision Priceは既存の因果的available CLOSE、最大age5分、価格Gateは厳密に>75円。これらを変更していない。','',
        '## Episode metadata census','',
        '| partition | sessions | Selector時刻 | raw rows | symbol-session | 単一観測run | 再選択あり |','| --- | --- | --- | --- | --- | --- | --- |']
    for k,v in [('ALL',a),*s['byPartition'].items()]:out.append('| '+' | '.join(str(x) for x in [k,v['sessions'],v['timestamps'],v['rawSelectedRows'],v['symbolSessionEpisodes'],v['singleObservedSelectionRun'],v['withObservedReselection']])+' |')
    out+=['','選択回数分布: `'+json.dumps(a['selectionCountDistribution'],sort_keys=True)+'`。最大連続観測選択回数: `'+json.dumps(a['maxConsecutiveObservedSelectionsDistribution'],sort_keys=True)+'`。','',
        '連続は保存されている30分schedule上の隣接であり、09:35等の未観測時刻で選択が継続したことを証明しない。再選択は観測済みscheduleで一度非選択になった後の再登場。1 symbol-sessionを重複tradeとして数えていない。全76sessionのmetadata censusであり、Validation/DEV TESTの候補推論・将来outcome評価ではない。','',
        '## Blocking reason','',
        '5分OHLCは保存されていても、同時刻の全銘柄Selector特徴・eligibility・score・rankを代替できない。09:30のscoreを09:35/09:40へコピーすると、指示された「更新されたSelector confidence」の検証にならない。欠けた時刻をDROPとも扱わない。','',
        '既存workspaceと/tmpに対応する全銘柄元キャッシュは見つからなかった。新provider/1m取得、Selector cadence・features・score変更は行わず、今回の学習・Validationを開始しない。','',
        '確認が必要な具体案: **現存の30分Selector更新を厳密に維持し、Entryだけ5分価格WATCHで再評価する別contract**。この場合、WATCH中のscore/rankは最新観測時刻とageを明示する。真の5分score/rank更新仮説とは区別する。','',
        '代替案をユーザーが選ぶ前にCandidateを作らない。Frozen NEW Entry/Comprehensive v1-v3/Integrated v1/Candidate Aは保存。Fresh/OOS未開封、Safety9項目false、main未マージ。','']
    return '\n'.join(out)


def run(outdir):
    out=Path(outdir);out.mkdir(parents=True,exist_ok=False);rows,ep,s=build()
    write(out/'raw-selector-metadata.json.gz',rows);write(out/'episode-metadata.json.gz',ep);write(out/'summary.json',s)
    with (out/'REPORT.md').open('x') as f:f.write(report(s))
    pins=['predict/research/phase57-long-only-frozen-selector-min-price75-v1.json','predict/research/phase57-long-only-frozen-selector-v1.json',str(SOURCE.relative_to(ROOT)),
        'docs/evidence/phase57-price75-entry-opportunity-timestamp-counts-v1/summary.json','scripts/phase57_opportunity_timestamp_counts.py','docs/evidence/phase57-integrated-long-entry-v1/closure-manifest.json']
    write(out/'manifest.json',{'status':s['status'],'sourceHead':s['sourceHead'],'sourcePins':{f:sha(ROOT/f) for f in pins},
        'codeSHA256':sha(__file__),'outputPins':{f.name:sha(f) for f in sorted(out.iterdir())},'safety':SAFETY,'fitCalls':0,'candidateEvaluations':0})
    print(json.dumps(s['raw'],indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();run(a.out)
