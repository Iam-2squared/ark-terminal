"""One synthetic end-to-end preflight through the production parser and aggregators."""
import importlib.util, json, pathlib, tempfile
from collections import Counter

HERE=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('phase57_anatomy_v3',HERE/'anatomy.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)


def bar(t,open_=100.,high=100.,low=100.,close=100.):
    return [float(t),open_,high,low,close,100.,10000.]


def dataset(kind):
    rows=[bar(t) for t in a.minutes()]
    at={int(r[0]):r for r in rows}
    if kind=='direct':
        at[540]=bar(540,100,101.2,100,101)
        at[541]=bar(541,101,103.2,101,103)
        at[542]=bar(542,103,105.2,103,105)
        at[543]=bar(543,105,110.2,105,110)
    if kind=='weak':
        at[540]=bar(540,100,100,-0+98.8,99)
        at[541]=bar(541,99,101.2,99,101)
        at[542]=bar(542,101,105.2,100,105)
        at[543]=bar(543,105,110.2,104,110)
    if kind=='pull':
        at[540]=bar(540,100,101.2,100,101)
        at[541]=bar(541,101,101.4,99.8,100.3)
        at[542]=bar(542,100.3,102.2,100,102)
        at[543]=bar(543,102,103.2,101.4,103)
        at[544]=bar(544,103,105.2,102.4,105)
        at[545]=bar(545,105,107.2,104,107)
        at[546]=bar(546,107,110.2,106,110)
    if kind=='break':
        at[540]=bar(540,100,101.2,100,101)
        at[541]=bar(541,101,101.1,99.4,99.5)
        at[542]=bar(542,99.5,100,98,98.5)
    rows=list(at.values())+[bar(690),bar(930,100,100,100,100)]
    if kind=='missing':rows=[r for r in rows if r[0]!=541.]
    if kind=='duplicate':rows.append(bar(541))
    if kind=='fractional':rows.append(bar(540.5))
    return rows


def run():
    assert a.canonical_minute(bar(540))[0]==540
    for value,reason in [(540.5,'TIMESTAMP_FRACTIONAL'),('540','TIMESTAMP_TYPE'),(None,'TIMESTAMP_TYPE'),(float('nan'),'TIMESTAMP_NONFINITE'),(float('inf'),'TIMESTAMP_NONFINITE')]:
        row=bar(540);row[0]=value
        assert a.canonical_minute(row)==(None,reason)
    assert a.active(689,750)==1 and a.delta_active(689,750)==1
    with tempfile.TemporaryDirectory() as tmp:
        a.HERE=pathlib.Path(tmp)
        entries=[];pairs=[];weak=[];states=[];paths={};masks={};prewinner=[];closepairs=[]
        for i,kind in enumerate(('direct','weak','pull','break','missing','duplicate','fractional')):
            arm='IM' if i!=2 else 'R1'
            entry={'entryId':f'2025-07-22|S{i}|540','session':'2025-07-22','symbol':f'S{i}',
                   'entryMinute':540,'entryPrice':100.,'entryCostJpy':10005.}
            bars,mask=a.build_path(entry,dataset(kind));masks[kind]=mask
            base=a.entry_row(arm,entry,False,bars,mask);entries.append(base)
            if not mask['pathKnown']:continue
            for m,targets in a.PAIRS.items():
                anchor=base['highEventIndex'][str(m)]
                if anchor is not None:
                    pairs.extend(a.pullback_row(base,bars,m,t,anchor) for t in targets)
                if base['closeEventIndex'][str(m)] is not None:
                    closepairs.extend(a.close_pullback_row(base,bars,m,t) for t in targets)
            for target in (1,2,3,5,7,10):
                r=a.prewinner_row(base,bars,target)
                if r is not None:prewinner.append(r)
            weak.extend(a.weakness_row(base,bars,t) for t in (-.5,-1))
            state=a.state_row(base,bars)
            if state:
                state['funded']=False
                path=state.pop('returnPath',None)
                if path is not None:paths[(arm,entry['entryId'])]=path
                states.append(state)
        assert masks['direct']['pathKnown'] and masks['weak']['pathKnown'] and masks['pull']['pathKnown']
        assert not masks['missing']['pathKnown'] and not masks['duplicate']['pathKnown']
        assert masks['fractional']['rejectedBarReasons']=={'TIMESTAMP_FRACTIONAL':1}
        assert all(masks[k]['auctionKnown'] for k in masks)
        assert any(r['arm']=='IM' and r['entryId'].endswith('S1|540') and r['laterHigh']['10'] for r in weak if r['thresholdPct']==-1)
        assert any(r['arm']=='R1' and r['anchorPct']==1 and r['targetPct']==5 and r['floorCross']=='DEFINITE_CROSS' for r in pairs)
        opp,initial,pull,floors,state_summary=a.summarize(entries,pairs,weak,states)
        assert opp['IM:ALL']['totalN']==6 and opp['IM:ALL']['unknownN']==2
        assert opp['R1:ALL']['totalN']==1 and floors['R1:ALL']['1']['targets']['5']['definiteCrossBeforeWinnerN']==1
        pre=a.summarize_prewinner(entries,prewinner)
        close=a.summarize_close_pairs(entries,closepairs)
        assert pre['IM:ALL']['targets']['10']['strictEarlierCrossN']['-1']==1
        assert close['R1:ALL']['pairs']['1']['5']['laterHigherReachedN']==1
        for name,data in [('ENTRY_HIGH_ANATOMY.json',opp),('INITIAL_WEAKNESS_ANATOMY.json',initial),('MILESTONE_PULLBACK_ANATOMY.json',pull),('OPERATOR_FLOOR_DIAGNOSTIC.json',floors)]:a.write(name,data)
        a.write('PRE_WINNER_DOWNSIDE_ANATOMY.json',pre)
        a.write('CLOSE_MILESTONE_PULLBACK_ANATOMY.json',close)
        for name,data in [('ENTRY_PATH_ROWS.jsonl.gz',entries),('MILESTONE_PAIR_ROWS.jsonl.gz',pairs),('INITIAL_WEAKNESS_ROWS.jsonl.gz',weak)]:a.gzwrite(name,data)
        a.make_state_summary(states,paths,state_summary)
        a.figures(entries,pairs,weak,states,paths,opp,initial,pull,floors)
        files=sorted(x.name for x in a.HERE.iterdir() if x.is_file())
        figures=sorted(x.name for x in (a.HERE/'figures').iterdir())
        assert len(figures)==6,(figures,masks)
        rendered=f'IM {opp["IM:ALL"]["totalN"]}/{opp["IM:ALL"]["pathKnownN"]} | R1 {opp["R1:ALL"]["totalN"]}/{opp["R1:ALL"]["pathKnownN"]}'
        assert rendered.startswith('IM 6/')
        return {'status':'PASS','cases':list(masks),'masks':masks,'entryRows':len(entries),
                'pairRows':len(pairs),'weakRows':len(weak),'jsonAndRowFiles':files,
                'figures':figures,'renderedTable':rendered,
                'assertions':['float lossless','fractional/string/null/nonfinite rejected','morning/lunch/afternoon/auction','direct +10','dip to +10','floor cross to +5','breakdown','missing/duplicate UNKNOWN','pre-winner -1 cross','Close pair','final aggregation/JSON/table/figures']}

if __name__=='__main__':print(json.dumps(run(),sort_keys=True))
