"""Audit immutable TRAIN Event evidence and generate the v3 completion report."""
import argparse
import collections
import itertools
import json
from pathlib import Path

from scripts import phase57_comprehensive_entry_v3 as v

m=v.m


def independent_events(states):
    """Fixed predicates + chronological index triples, independent of stage machine."""
    hits=[[] for _ in range(6)]; records={}
    for s in states:
        if s['status']!='AVAILABLE':break
        bars=s['bars']; i=len(bars)-1
        if i<0:continue
        a=bars[i];b=bars[i-1] if i>=1 else None; prior_pb=any(z['c']<0 for z in bars[:i])
        tests=[a['c']<0,
            bool(prior_pb and b and a['l']>=b['l'] and a['c']>=b['c'] and (a['h']-a['l'])<=(b['h']-b['l'])),
            bool(prior_pb and b and a['c']>b['h']),
            bool(prior_pb and i>=2 and b['c']<=bars[i-2]['c'] and a['c']>b['c']),
            bool(prior_pb and b and a['l']<b['l'] and a['c']>b['l']),
            bool(i>=2 and a['c']>b['c']>bars[i-2]['c'] and a['l']>b['l']>bars[i-2]['l'] and a['h']>b['h'])]
        for n,hit in enumerate(tests):
            if hit:hits[n].append(s['delay'])
        records[s['delay']]=s
    out={}
    for n,values in enumerate(hits):
        if values:out[v.EVENTS[n]]=[values[0]]
    for name,indices in v.SEQUENCES.items():
        options=[list(t) for t in itertools.product(*(hits[i] for i in indices)) if t[0]<t[1]<t[2]]
        if options:out[name]=min(options)  # earliest reachable first, middle, final states
    return {name:{'delay':ds[-1],'timestamp':records[ds[-1]]['timestamp'],
        'recognitionClosePct':records[ds[-1]]['bars'][-1]['c'],'sequenceDelays':ds} for name,ds in out.items()}


def fmt(x):
    if x is None:return '—'
    if isinstance(x,float):return f'{x:.4f}'
    return str(x)
def pct(x):return x*100 if x is not None else None
def table(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(fmt(x) for x in row)+' |' for row in rows])


def run(source,outdir):
    source=Path(source);out=Path(outdir)
    if out.exists():raise FileExistsError(out)
    out.mkdir(parents=True)
    p=v.protocol();manifest=m.read(source/'manifest.json');s=m.read(source/'summary.json')
    assert manifest['protocolSHA256']==v.PROTOCOL_SHA
    assert manifest['sourcePins']==p['sourcePins']
    assert manifest['codeSHA256']==m.sha(v.__file__)
    for name,digest in manifest['outputs'].items():assert m.sha(source/name)==digest,name
    assert s['partitionEvaluated']=='TRAIN' and s['validationEvaluations']==s['developmentTestEvaluations']==s['supervisedFits']==0
    assert s['freshOOSOpened'] is False
    states=m.read(source/'train-pit-states.json.gz');baseline=m.read(source/'b0-immediate-train.json.gz')
    assert len(states)==len(baseline)==1760
    assert len({r['id'] for r in states})==1760
    ids=[r['id'] for r in states];byid={r['id']:r for r in states};baseline_byid={r['id']:r for r in baseline}
    independent=0; terminal_count=0
    for r in states:
        assert r['session'] in p['split']['TRAIN']
        assert [z['delay'] for z in r['states']]==list(range(0,31,5))
        terminal=False
        for z in r['states']:
            if z['status']!='AVAILABLE':terminal=True;terminal_count+=1;continue
            assert not terminal
            assert set(z['descriptors'])==set(p['states']['continuousDescriptors'])
            assert all(b['end']<=z['timestamp'] for b in z['bars'])
            assert z['intrabarOrder']=='UNKNOWN_INTRABAR_ORDER'
            assert set(z['features'])==set(m.FEATURES)
        assert independent_events(r['states'])==r['events'],r['id']
        independent+=1
    contexts={};descriptor_classes={}
    for delay in range(0,31,5):
        descriptor_classes[str(delay)]={}
        for cls in v.CLASSES:
            rs=[r['states'][delay//5] for r in states if baseline_byid[r['id']]['pathClass']==cls and r['states'][delay//5]['status']=='AVAILABLE']
            descriptor_classes[str(delay)][cls]={'states':len(rs),'descriptors':{k:m.dist([z['descriptors'][k] for z in rs]) for k in v.protocol_descriptor_names()}}
    for name in v.EVENTS:
        rows=m.read(source/(name.lower()+'-train.json.gz'));assert [r['id'] for r in rows]==ids
        bins=collections.defaultdict(list)
        for r in rows:
            record=byid[r['id']];expected=record['events'].get(name)
            assert r['decision']['event']==expected
            assert r['baseline']==baseline_byid[r['id']]['baseline']
            assert r['source']==record['source']
            if expected:
                assert all(a<b for a,b in zip(expected['sequenceDelays'],expected['sequenceDelays'][1:]))
                assert expected['timestamp']==record['states'][expected['delay']//5]['timestamp']
                assert r['decision']['delay'] in (None,expected['delay'])
                eventstate=record['states'][expected['delay']//5];vol=eventstate['descriptors']['closeVolatility']
                bins['volatility_'+('UNAVAILABLE' if vol is None else 'ZERO' if vol==0 else 'POSITIVE')].append(r)
            else:bins['NO_EVENT'].append(r)
            if r['entry']:
                assert abs(r['entry']['price']-r['decision']['executionPrice'])<1e-8
            assert sum(t['action']=='BUY_NOW' for t in r['decision']['transitions'])<=1
        contexts[name]={key:v.cohort_metrics(rows) for key,rows in bins.items()}
    appendix={'status':'PASS','independentEventEpisodeAudits':independent,'independentEventFamilyEpisodeComparisons':independent*9,
        'terminalStateRecords':terminal_count,'eventLedgersVerified':9,'initialDipIdentity':True,'sourcePins':len(p['sourcePins']),
        'contextPanels':contexts,'descriptorClassDistributions':descriptor_classes,'validationEvaluations':0,'devTestEvaluations':0,
        'freshOOSOpened':False,'supervisedFits':0,'safety':p['safety']}
    m.write(out/'audit-appendix.json',appendix)
    lines=['# Comprehensive LONG Entry Intelligence v3 — Causal Event Study','',f"**{s['status']}**",'',
        'TRAIN上の事前固定6 Event＋3 sequenceを測定。結果後の閾値・feature・sequence追加なし。これはEntry Timing全体の不可能性を示すものではない。','',
        f"Protocol commit: `{v.PROTOCOL_COMMIT}`。SHA256: `{v.PROTOCOL_SHA}`。開始HEAD: `{p['sourceHead']}`。",'',
        '## Lineage / population / exposure','',
        '¥75 Selector、Frozen NEW Entry / Opportunity Generator、INITIAL/DIP identity、Candidate Aは不変。v1 KILL / v2 LIMIT Evidenceを保持。', '',
        table(['Partition','sessions','opportunities','v3 evaluated'],[[k,len(p['split'][k]),p['population'][k],k=='TRAIN'] for k in ('TRAIN','VALIDATION','DEVELOPMENT_TEST')]),'',
        f"TRAIN complete common60: {s['trainCompleteCommon60']}/{s['trainEmitted']}。INITIAL/DIP emitted: {s['sourceCounts']}。",'',
        '元データは76 Development sessionsのimmutable bundle。identity確認後にTRAINへfilterし、Validation/DEV TESTのv3 state/Event/outcomeは評価していない。過去に一般診断へ露出したDevelopmentでありFreshではない。', '',
        '## Precommitted definitions','',table(['Event','Exact definition'],[[k,p['events'][k]] for k in v.EVENTS]),'',
        '数値の深さthreshold探索なし。ゼロ・前barとの順序・連続した符号という構造定義。全Eventは最初の認識のみ。sequenceは各stageを異なるcompleted barで満たす。最大30分・元segment内。', '',
        'StateではOpportunity referenceからの下落、期間、range、wick、close位置、momentum変化等を連続量として保存。動的VWAP/出来高/相対強度/市場index pathはUNAVAILABLE。既存43特徴のanchor snapshotを更新値と偽らない。', '',
        '## Event separation and KEEP/KILL','',
        table(['Event','complete n','Event n','PB occurrence %','Failure occurrence %','gap pp','PB price improvement pp','PB strict30 median improvement pp','PB MFE ratio','verdict'],
        [[k,z['overall']['summary']['commonComplete'],z['overall']['occurrence']['eventN'],pct(z['pullback']['occurrence']['rate']),pct(z['failure']['occurrence']['rate']),pct(z['occurrenceGap']),z['pullback']['summary']['priceImprovement']['mean'],z['pullback']['strict30MedianImprovementPP'],z['pullback']['remainingMFEMeanRatio'],z['verdict']] for k,z in s['events'].items()]),'',
        'PBはPULLBACK_THEN_WINNER＋DEEP_PULLBACK_THEN_WINNER。発生率はbaseline complete cohort全件分母、location/riskはentered pairs分母。両者を混同しない。発生率のWilson区間はJSONに保持し、相関したEpisodeを独立標本と主張しない。', '',
        'KEEPにはPB location/strict30 MAE改善、MFE維持、entered-pair +3/+5維持、failureとの差、INITIAL/DIP、時系列、集中度の全事前条件を要求。KEEPでも全体Entry PASSではない。', '',
        table(['Event','Failed precommitted gates'],[[k,', '.join(z['failedGates']) or 'NONE'] for k,z in s['events'].items()]),'',
        '## B0_IMMEDIATE and each diagnostic Event policy','']
    base=s['baseline']['summary']
    for name in v.EVENTS:
        z=s['events'][name];overall=z['overall'];a=overall['summary'];pb=z['pullback'];f=z['failure']
        lines += ['### '+name,'',table(['Metric','B0 same entered pairs / full base as noted','Event'],[
            ['Opportunity n',base['emitted'],a['emitted']],['Reference ENTER (not real fills)',base['enteredAll'],a['enteredAll']],
            ['Common complete',base['commonComplete'],a['commonComplete']],['Complete ENTER',base['enteredCommon'],a['enteredCommon']],
            ['Entry coverage %',100,pct(a['entryCoverage'])],['Delay mean min',0,a['delay']['mean']],['Delay median min',0,a['delay']['median']],
            ['Paired mean Entry price',overall['baselineEntryPricePaired']['mean'],overall['entryPrice']['mean']],['Mean price improvement pp',0,a['priceImprovement']['mean']],
            ['Strict30 MAE mean',a['baselineStrict30MAE']['mean'],a['entryStrict30MAE']['mean']],['Strict30 MAE median',a['baselineStrict30MAE']['median'],a['entryStrict30MAE']['median']],
            ['Strict30 MAE p10',a['baselineStrict30MAE']['p10'],a['entryStrict30MAE']['p10']],['Strict30 MAE p05',a['baselineStrict30MAE']['p05'],a['entryStrict30MAE']['p05']],
            ['Strict30 worst MAE',a['baselineStrict30MAE']['min'],a['entryStrict30MAE']['min']],['Common remaining MFE mean',a['baselinePairedMFE']['mean'],a['entryPairedMFE']['mean']],
            *[[f'+{k} preservation %',100,pct(a['preservation'][str(k)]['rate'])] for k in (1,2,3,5)],
            *[[k+' entered & remaining+3 %',100,pct(a['classes'][k]['rate3'])] for k in ('IMMEDIATE_WINNER','FAST_WINNER','PULLBACK_WINNER')]]), '',
            table(['Path class','all n','complete n','ENTER complete','waited emitted','NO_EVENT','EXPIRED','UNKNOWN','missed +3','missed +5'],
                [[cls,w['summary']['emitted'],w['summary']['commonComplete'],w['summary']['enteredCommon'],w['summary']['emitted']-w['outcomes'].get('UNKNOWN_REFERENCE',0),w['outcomes'].get('NO_EVENT',0),w['outcomes'].get('EXPIRED_BOUNDARY',0),sum(n for k,n in w['outcomes'].items() if k.startswith('UNKNOWN')),w['summary']['preservation']['3']['missed'],w['summary']['preservation']['5']['missed']] for cls,w in z['classes'].items()]),'',
            table(['Pullback class','complete n','ENTER','price improvement pp','strict30 median improvement pp','strict30 p05 improvement pp','MFE ratio'],
                [[cls,z['classes'][cls]['summary']['commonComplete'],z['classes'][cls]['summary']['enteredCommon'],z['classes'][cls]['summary']['priceImprovement']['mean'],z['classes'][cls]['strict30MedianImprovementPP'],z['classes'][cls]['strict30P05ImprovementPP'],z['classes'][cls]['remainingMFEMeanRatio']] for cls in v.PB]),'',
            table(['Cohort','PB complete','PB ENTER','PB occurrence %','failure occurrence %','PB price pp','PB MAE median improvement pp','PB MFE ratio'],
                [[k,w['pullback']['summary']['commonComplete'],w['pullback']['summary']['enteredCommon'],pct(w['pullback']['occurrence']['rate']),pct(w['failure']['occurrence']['rate']),w['pullback']['summary']['priceImprovement']['mean'],w['pullback']['strict30MedianImprovementPP'],w['pullback']['remainingMFEMeanRatio']] for k,w in z['cohorts'].items()]),'',
            table(['TRAIN block','PB complete','Event n in PB','gap pp','PB price pp','PB MAE median improvement pp','block gate'],
                [[k,w['pullback']['summary']['commonComplete'],w['pullback']['summary']['enteredCommon'],pct(w['occurrenceGap']),w['pullback']['summary']['priceImprovement']['mean'],w['pullback']['strict30MedianImprovementPP'],z['chronologicalPass'][k]] for k,w in z['chronological'].items()]),'',
            table(['MAE tail','B0 all','B0 entered pairs','Event entered pairs','better Entry reduction','not-entered baseline tail'],
                [[k,a['tails'][str(k)]['baselineAll'],a['tails'][str(k)]['baselineEnteredPair'],a['tails'][str(k)]['entryPair'],overall['riskDecomposition'][str(k)]['RISK_REDUCTION_BY_BETTER_ENTRY'],overall['riskDecomposition'][str(k)]['RISK_NOT_ENTERED_NOT_AN_ADOPTED_SKIP_POLICY']] for k in (3,5,10)]),'',
            'RISK_REDUCTION_BY_BETTER_ENTRYは同一Opportunityのbaseline tail−Event tail。非Entry側の件数はSKIPとみなした場合の見かけの減少に相当し、採用済みSKIP policyとは呼ばない。', '',
            f"Delay bins: {overall['delayBins']}。Outcomes: {overall['outcomes']}。",'',
            f"No-event winners (+1/+2/+3/+5): {overall['noEventWinners']}。Winner before event: {overall['winnerBeforeEvent']}。",'',
            f"Evaluator-only IMMEDIATE_ENTRY_REQUIRED tag: {overall['immediateEntryRequiredDiagnosticOnly']}。これは実行時のGuardではない。",'',
            f"Concentration: {z['concentration']}。Top3 exclusion failed gates: {[k for k,b in z['top3Excluded']['gates'].items() if not b]}。",'']
    lines += ['## Architecture / Validation / economics / DEV TEST','',
        f"KEEP mechanics: {s['keepMechanics']}。Selected mechanic: {s['selectedMechanic']}。",'',
        'KEEPがなければArchitecture/modelを作らずLIMIT。Validation・DEV TEST・Candidate A economic比較はいずれも未実行。未実行のmean/PF/p05/Win/HOLDを0やPASSとして表記しない。', '',
        '## Integrity / limitations / STOP','',
        f"Independent predicate/sequence implementation matched {independent} TRAIN episodes ×9 families. Original source pins {len(p['sourcePins'])} verified. Model fits 0。",'',
        'StateとEventはPIT completed prefixのみ。Event後のnext OPENを実行参照とし、signal LOWやoracle bottomで約定しない。future MFE/MAE・path classは別Evaluator。same-bar HIGH/LOW順序UNKNOWN、missing/boundaryはfail-closed。terminal後resurrectionなし。', '',
        'INITIAL/DIP・breadth1..5・朝/午後・TRAIN四分割・symbol HHI・top3除外・Event時点volatility別集計を保存。個別ルールやblacklistへの転用なし。', '',
        'どのPIT情報が不足しているか、5m粒度そのものが限界か、出来高/板/市場contextを加えれば解決するかは今回比較していない。動的contextがUNAVAILABLEである事実と、その追加効果が未検証であることを分ける。新データ取得やCapital/EXITへの移行の優劣も本研究からは判定しない。', '',
        'Exact HEAD・tests・regression・CI receiptは同一HEADのGitHub Actions artifactに保存。CI成功はEvent/Entry性能PASSを意味しない。Fresh/OOS・Capital/Portfolio・EXIT変更・main merge・実取引には進まない。全9 Safety=false。', '',
        '**'+s['status']+'。Candidate Freezeなし。既存Frozen Opportunity Generator維持。Evidence固定してSTOP。**','']
    (out/'REPORT.md').write_text('\n'.join(lines))
    m.write(out/'manifest.json',{'protocolSHA256':v.PROTOCOL_SHA,'sourceManifestSHA256':m.sha(source/'manifest.json'),
        'codeSHA256':m.sha(__file__),'outputs':{f.name:m.sha(f) for f in sorted(out.iterdir())},'safety':p['safety']})
    print(json.dumps({'status':s['status'],'independentEpisodeAudits':independent,'validationEvaluations':0,'developmentTestEvaluations':0,'safety':p['safety']}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--out',required=True);a=p.parse_args();run(a.source,a.out)
