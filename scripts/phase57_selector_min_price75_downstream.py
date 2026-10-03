"""Exact frozen Entry impact audit only; no EXIT replay or architecture change."""
import argparse,collections,hashlib,json
from pathlib import Path
from scripts import phase57_selector_min_price75 as m
from scripts import phase57_new_long_entry_two_opportunity_replay as replay
from scripts import phase57_new_long_entry_exit_conditional as cond
from scripts import phase57_strict30_mae_attribution as mae
ROOT=m.ROOT

def anchors(selected):
    first={}
    for r in sorted(selected,key=lambda x:(x['decisionTimestamp'],x['symbol'])):first.setdefault((r['sessionDate'],r['symbol']),r)
    return sorted(first.values(),key=lambda x:(x['decisionTimestamp'],x['symbol']))
def summarize(rows):
    good=[r for r in rows if r['strict30']['status']=='COMPLETE']
    return {'opportunities':len(rows),'referenceEligible':sum(r['referenceStatus']=='REFERENCE_OPEN' for r in rows),'actualENTER':'NOT_MODELED_NO_FUNDING_OR_FILL','strict30N':len(good),'strict30MAE':cond.dist([r['strict30']['maePct'] for r in good]),'strict30Coverage':dict(sorted(collections.Counter(r['strict30']['status'] for r in rows).items())),
        'tails':{str(k):{'n':sum(r['strict30']['maePct']<=-k for r in good),'symbols':dict(sorted(collections.Counter(r['symbol'] for r in good if r['strict30']['maePct']<=-k).items()))} for k in (3,5,10)},
        'strict30Opportunity':{str(k):cond.rate(sum(r['strict30']['mfePct']>=k for r in good),len(good)) for k in (1,2,3,5)},
        'sessionHighOpportunity':{str(k):cond.rate(sum(r['sessionHighObservedMFE'] is not None and r['sessionHighObservedMFE']>=k for r in rows),sum(r['sessionHighObservedMFE'] is not None for r in rows)) for k in (1,2,3,5)},
        'symbol':m.concentration(rows,'symbol'),'session':m.concentration(rows,'sessionDate')}
def panels(rows):return {'ALL':summarize(rows),**{k:summarize([r for r in rows if r['cohort']==k]) for k in (mae.INITIAL,mae.DIP)}}
def run(source,pathsfile,outdir):
    m.verify();out=Path(outdir)
    if out.exists():raise FileExistsError(out)
    selection=m.read(Path(source)/'selector-ledger.json.gz');sel_summary=m.read(Path(source)/'selector-summary.json')
    saved_parity=m.read(cond.BASE/'entry-parity/ledger.ndjson.gz');parity={r['anchorId']:r for r in saved_parity}
    oldpaths={r['selectorEventId']:r for r in m.read(ROOT/cond.PATHS)['events']}
    newsource=m.read(pathsfile);newpaths={r['selectorEventId']:r for r in newsource['events']}
    saved_mae={(r['anchorId'],r['cohort']):r for r in m.read(mae.BASE/'measurement/ledger.json.gz') if r['panel']=='CURRENT'}
    ledgers={};decisions={};audit={'oldStrict30Parity':0,'retainedDecisionsReused':0,'newAnchorReplay':0}
    for arm,pathmap in [('old',oldpaths),('new',newpaths)]:
        rows=[];dr=[]
        for anchor in anchors(selection[arm]):
            aid=anchor['selectorEventId'];p=pathmap[aid]
            if aid in parity:
                dec=parity[aid]
                if arm=='new':audit['retainedDecisionsReused']+=1
            else:
                assert arm=='new';dec=replay._replay_event(p);audit['newAnchorReplay']+=1
            dr.append(dec)
            for op in [dec['decision']['initialEvent'],dec['decision']['secondaryEvent']]:
                if op is None:continue
                e=cond.adapt(op,p);bars=e.get('future',[])
                z=mae.strict30(bars) if bars else {'status':op['referenceStatus']}
                if z['status']=='COMPLETE':
                    six=z.pop('bars');z.update(maePct=min(0,min(b['l'] for b in six)),mfePct=max(0,max(b['h'] for b in six)))
                if arm=='old':
                    old=saved_mae[(aid,op['eventType'])]['strict30'];assert z['status']==old['status']
                    if z['status']=='COMPLETE':assert z['maePct']==old['maePct'] and z['mfePct']==old['mfePct'];audit['oldStrict30Parity']+=1
                valid=[b for b in bars if cond.valid(b)]
                rows.append({'anchorId':aid,'cohort':op['eventType'],'symbol':anchor['symbol'],'sessionDate':anchor['sessionDate'],'decisionPrice':anchor['decisionPrice'],'entryPrice':op.get('referencePrice'),'referenceStatus':op['referenceStatus'],'entryTimestamp':op.get('referenceTimestamp',op['opportunityTimestamp']),'strict30':z,'sessionHighObservedMFE':max(0,max(b['h'] for b in valid)) if valid else None,'sessionComplete':bool(bars and len(valid)==len(bars))})
        ledgers[arm]=rows;decisions[arm]=dr
    assert len(ledgers['old'])==3284 and audit['oldStrict30Parity']==1697
    ids=lambda rows:{(r['anchorId'],r['cohort']) for r in rows}
    oldids=ids(ledgers['old']);newids=ids(ledgers['new'])
    retained=[r for r in ledgers['new'] if (r['anchorId'],r['cohort']) in oldids]
    removed=[r for r in ledgers['old'] if (r['anchorId'],r['cohort']) not in newids]
    added=[r for r in ledgers['new'] if (r['anchorId'],r['cohort']) not in oldids]
    sessions=sorted({r['sessionDate'] for r in ledgers['old']})
    top3=sel_summary['concentration']['oldTop3FixedExclusion']
    oldtails=[r for r in ledgers['old'] if r['strict30']['status']=='COMPLETE' and r['strict30']['maePct']<=-10]
    tailaudit=[{**r,'sameOpportunityRetained':(r['anchorId'],r['cohort']) in newids,'anchorMinPriceIneligible':m.gate.price_status(r['decisionPrice'])=='INELIGIBLE_MIN_PRICE'} for r in oldtails]
    worstid='2024-12-25|2024-12-25T09:30:00+09:00|57590'
    worst=next(r for r in ledgers['old'] if r['anchorId']==worstid and r['cohort']==mae.INITIAL)
    assert m.gate.price_status(worst['decisionPrice'])=='INELIGIBLE_MIN_PRICE'
    assert worstid not in {r['selectorEventId'] for r in selection['new']}
    preservation={}
    for horizon in ['strict30','sessionHigh']:
        preservation[horizon]={}
        for k in (1,2,3,5):
            wins=[r for r in ledgers['old'] if (r['strict30']['status']=='COMPLETE' and r['strict30']['mfePct']>=k) if horizon=='strict30'] if horizon=='strict30' else [r for r in ledgers['old'] if r['sessionHighObservedMFE'] is not None and r['sessionHighObservedMFE']>=k]
            preservation[horizon][str(k)]=cond.rate(sum((r['anchorId'],r['cohort']) in newids for r in wins),len(wins))
    report={'scope':'FULL_NEW_SELECTION_STREAM_FIRST_PER_SYMBOL_SESSION_EXACT_FROZEN_ENTRY','old':panels(ledgers['old']),'new':panels(ledgers['new']),'retained':panels(retained),'removed':panels(removed),'added':panels(added),'oldWinnerIdentityPreservation':preservation,
        'chronological':{str(i+1):{arm:panels([r for r in rows if r['sessionDate'] in sessions[i*19:(i+1)*19]]) for arm,rows in ledgers.items()} for i in range(4)},
        'excludeOldSelectorFrequencyTop3':{'symbols':top3,**{arm:panels([r for r in rows if r['symbol'] not in top3]) for arm,rows in ledgers.items()}},
        'oldDeep10Identities':tailaudit,'worst17Identity':{**worst,'removedFromSelector':True},'audit':audit,'notes':['Opportunity events and reference eligibility are not funded ENTER/fills.','Session High uses witnessed valid future5m High; full session completeness separately recorded.','New first selections may occur later for the same symbol-session; retained-only filtering is not the new population.','No EXIT replay/change. MAE is secondary raw path diagnostic.'],'safety':m.verify()['safety'],'freshOOSOpened':False}
    out.mkdir(parents=True)
    for n,x in [('entry-ledger.json.gz',ledgers),('entry-decisions.json.gz',decisions),('downstream-summary.json',report)]:m.write(out/n,x)
    m.write(out/'downstream-manifest.json',{'sourcePins':{n:m.sha(Path(source)/n) for n in ['selector-ledger.json.gz','selector-summary.json']},'newPathsSHA256':m.sha(pathsfile),'codePin':m.sha(__file__),'outputPins':{n:m.sha(out/n) for n in ['entry-ledger.json.gz','entry-decisions.json.gz','downstream-summary.json']}})
    print(json.dumps({'old':report['old']['ALL'],'new':report['new']['ALL'],'audit':audit}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--paths',required=True);p.add_argument('--out',required=True);a=p.parse_args();run(a.source,a.paths,a.out)
