"""Read-only finite output invariants; runs once after the saved main."""
import pathlib,json,gzip,math,datetime,collections,hashlib
P=pathlib.Path(__file__).resolve().parent
names=['ENTRY_HIGH_ANATOMY.json','PRE_WINNER_DOWNSIDE_ANATOMY.json','INITIAL_WEAKNESS_ANATOMY.json','MILESTONE_PULLBACK_ANATOMY.json','CLOSE_MILESTONE_PULLBACK_ANATOMY.json','OPERATOR_FLOOR_DIAGNOSTIC.json','PATH_STATE_ANATOMY.json','PATH_STATE_AVAILABILITY.json']
M=(.5,1,2,3,5,7,10)

def audit():
    d={n:json.loads((P/n).read_text()) for n in names};errors=[];checks=collections.Counter()
    entries=list(map(json.loads,gzip.open(P/'ENTRY_PATH_ROWS.jsonl.gz','rt')))
    if len(entries)!=1614:errors.append('TOTAL_ENTRY_ROWS')
    if len({(r['arm'],r['entryId']) for r in entries})!=len(entries):errors.append('DUPLICATE_ENTRY')
    for arm,total,funded in [('IM',819,79),('R1',795,32)]:
        for scope,n in [('ALL',total),('FUNDED',funded)]:
            key=arm+':'+scope;row=d['ENTRY_HIGH_ANATOMY.json'][key];ss=[r for r in entries if r['arm']==arm and (scope=='ALL' or r['funded'])]
            if row['totalN']!=n or len(ss)!=n:errors.append(key+'.totalN')
            for fld,flag in [('pathKnownN','pathKnown'),('priceKnownN','priceKnown'),('continuousPathKnownN','continuousPathKnown')]:
                if row[fld]!=sum(r[flag] for r in ss):errors.append(key+'.'+fld)
            if row['pathKnownN']+row['unknownN']!=n:errors.append(key+'.knownUnknown')
            if row['pathKnownN']>row['priceKnownN']:errors.append(key+'.maskOrder')
            for view in ('highMilestoneReached','closeMilestoneReached'):
                counts=[row[view][str(m)] for m in M]
                if any(a<b for a,b in zip(counts,counts[1:])) or counts[0]>row['pathKnownN']:
                    errors.append(key+'.'+view)
            if any(row['closeMilestoneReached'][str(m)]>row['highMilestoneReached'][str(m)] for m in M):errors.append(key+'.highClose')
            if d['PRE_WINNER_DOWNSIDE_ANATOMY.json'][key]['pathKnownN']!=row['pathKnownN']:errors.append(key+'.prewinnerKnown')
            for m,targets in {1:(2,3,5,10),2:(3,5,10),3:(5,7,10),5:(7,10),7:(10,)}.items():
                for t in targets:
                    z=d['MILESTONE_PULLBACK_ANATOMY.json'][key][str(m)][str(t)]
                    if z['anchorReachedN']!=row['highMilestoneReached'][str(m)]:errors.append(key+f'.anchor{m}')
                    if z['laterHigherReachedN']+z['laterHigherNotReachedN']+z['sameAnchorBarHigherN']!=z['anchorReachedN']:errors.append(key+f'.partition{m}-{t}')
                    if z['laterHigherReachedN']>row['highMilestoneReached'][str(t)]:errors.append(key+f'.higher{m}-{t}')
                    if m in (1,2,3):
                        f=d['OPERATOR_FLOOR_DIAGNOSTIC.json'][key][str(m)]['targets'][str(t)]
                        if f['laterWinnerN']!=z['laterHigherReachedN'] or f['definiteCrossBeforeWinnerN']+f['sameBarOrderAmbiguousN']+f['noCrossN']>f['laterWinnerN']:
                            errors.append(key+f'.floor{m}-{t}')
            checks['cohortContracts']+=1
    def visit(o,path=''):
        if isinstance(o,dict):
            if {'n','p10','p25','median','p75','p90','worst'}<=set(o):
                v=[o[x] for x in ('p10','p25','median','p75','p90')]
                if o['n']==0 and any(x is not None for x in v):errors.append(path+'.emptyQuant')
                if o['n']>0 and (any(x is None for x in v) or any(x>y+1e-9 for x,y in zip(v,v[1:]))):errors.append(path+'.quantOrder')
                checks['quantiles']+=1
            for k,v in o.items():
                if isinstance(v,(int,float)) and not isinstance(v,bool) and (not math.isfinite(v) or (k.endswith('N') and v<0)):
                    errors.append(path+'.'+k+'.nonfiniteOrNegativeCount')
                visit(v,path+'.'+str(k))
        elif isinstance(o,list):
            for i,v in enumerate(o):visit(v,path+f'[{i}]')
    for n,x in d.items():visit(x,n)
    status='PASS' if not errors else 'FAIL'
    return {'atJst':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),
      'cycleIdentity':P.name,'basisHead':'1e328c7b47acf6dc9341e784808f691cdbd75f18',
      'status':status,'mainPathAnatomyConsumed':1,'independentConsumed':0,
      'totals':{k:{x:d['ENTRY_HIGH_ANATOMY.json'][k][x] for x in ('totalN','pathKnownN','priceKnownN','stateKnownN','unknownN')} for k in ('IM:ALL','R1:ALL','IM:FUNDED','R1:FUNDED')},
      'checks':dict(checks),'errors':errors,'mainCodeSha256':hashlib.sha256((P/'anatomy.py').read_bytes()).hexdigest(),
      'figures':sorted(x.name for x in (P/'figures').glob('*.png')),
      'resultHashes':{n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in names},
      'caveat':'only complete 1m+930 paths used for negative claims; missing no-trade/halt classification UNKNOWN'}

if __name__=='__main__':
    dest=P/'MAIN_SANITY_AUDIT.json'
    if dest.exists():raise FileExistsError(dest)
    result=audit();dest.write_text(json.dumps(result,sort_keys=True,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('status','totals','checks','errors','figures')},ensure_ascii=False))
