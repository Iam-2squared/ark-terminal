"""Evaluator-only R52 layer-A and recycling attribution from immutable saved ledgers.

This never fits a model, builds predictions, or feeds future outcomes into replay.
Run only after the finite Action and the saved-prediction independent audit PASS.
"""
from __future__ import annotations
import argparse, collections, gzip, hashlib, json, statistics
from decimal import Decimal
from pathlib import Path
import numpy as np

from scripts import phase57_exit_continuation_r52 as r
from scripts import phase57_capital_exit_integrated as integrated
from scripts import phase57_development_integrated_v0 as v0

EVIDENCE = r.EVIDENCE

def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def summary(rows):
    values = [x for x in rows if x['netPct'] is not None]
    nets = [x['netPct'] for x in values]
    pnl = [x['pnlJpy'] for x in values]
    capture = [x['capturePct'] for x in values if x['capturePct'] is not None]
    hold = [x['holdingWallMinutes'] for x in values if x['holdingWallMinutes'] is not None]
    wins = [x for x in pnl if x > 0]
    losses = [x for x in pnl if x < 0]
    return {'n':len(rows),'closed':len(values),'unresolved':len(rows)-len(values),
        'meanNetPct':statistics.fmean(nets) if nets else None,
        'medianNetPct':statistics.median(nets) if nets else None,
        'p05NetPct':float(np.percentile(nets,5)) if nets else None,
        'p10NetPct':float(np.percentile(nets,10)) if nets else None,
        'worstNetPct':min(nets) if nets else None,
        'profitFactor':float(sum(wins,Decimal(0))/-sum(losses,Decimal(0))) if losses else None,
        'winRate':len(wins)/len(values) if values else None,
        'avgWinJpy':str(sum(wins,Decimal(0))/len(wins)) if wins else None,
        'avgLossJpy':str(sum(losses,Decimal(0))/len(losses)) if losses else None,
        'pnlJpy':str(sum(pnl,Decimal(0))),
        'meanCapturePct':statistics.fmean(capture) if capture else None,
        'medianCapturePct':statistics.median(capture) if capture else None,
        'captureEvaluable':len(capture),
        'meanHoldingWallMinutes':statistics.fmean(hold) if hold else None,
        'medianHoldingWallMinutes':statistics.median(hold) if hold else None}

def paired_rows(saved, baseline):
    funded = baseline['funded']
    v0.require({x['entryId'] for x in saved} == set(funded), 'LAYER_A_ID_SCOPE')
    result = {'candidate':[], 'control':[]}
    for row in saved:
        eid = row['entryId'];entry = funded[eid]
        notional = Decimal(entry['notionalJpy']);qty = Decimal(entry['quantity'])
        price = Decimal(entry['effectiveEntryPrice']);upside = row['evaluatorOnlyUpsidePct']
        for key,pnl_key,minute_key in [('candidate','candidatePnlJpy','newExitMinute'),
                                        ('control','controlPnlJpy','controlExitMinute')]:
            pnl = None if row[pnl_key] is None else Decimal(row[pnl_key])
            minute = row[minute_key]
            capture = None
            if pnl is not None and upside is not None and upside > 0:
                exit_price = (notional+pnl)/(qty*Decimal('0.9995'))
                capture = float(Decimal(100)*(exit_price/price-1)/(Decimal(str(upside))/Decimal(100)))
            result[key].append({'entryId':eid,'bucket':integrated.upside_bucket(upside),
                'upsidePct':upside,'netPct':float(Decimal(100)*pnl/notional) if pnl is not None else None,
                'pnlJpy':pnl,'capturePct':capture,
                'holdingWallMinutes':None if minute is None else minute-int(entry['entryMinute'])})
    return result

def layer_a_groups(rows):
    selectors = {'All baseline funded':lambda x:True, '>=5%':lambda x:x['upsidePct'] is not None and x['upsidePct']>=5,
        '>=10%':lambda x:x['upsidePct'] is not None and x['upsidePct']>=10,
        '3–5%':lambda x:x['upsidePct'] is not None and 3<=x['upsidePct']<5,
        '<1%':lambda x:x['upsidePct'] is not None and x['upsidePct']<1}
    groups={name:summary([x for x in rows if predicate(x)]) for name,predicate in selectors.items()}
    for bucket in integrated.BUCKETS:
        groups[bucket]=summary([x for x in rows if x['bucket']==bucket])
    v0.require(sum(groups[b]['n'] for b in integrated.BUCKETS)==len(rows),'LAYER_A_BUCKET_CENSUS')
    return groups

def checkpoint_reason_map():
    manifest=json.loads((EVIDENCE/'BASELINE_CHECKPOINTS_REASSEMBLE.json').read_text())
    parts=[]
    for item in manifest['orderedParts']:
        p=EVIDENCE/item['path'];v0.require(sha256(p)==item['sha256'],'BASELINE_AUDIT_PART')
        parts.append(p.read_bytes())
    compressed=b''.join(parts);v0.require(hashlib.sha256(compressed).hexdigest()==manifest['sha256'],
                                   'BASELINE_AUDIT_REASSEMBLED')
    result={}
    for line in gzip.decompress(compressed).splitlines():
        x=json.loads(line);result[x['arm'],x['entryId'],x['now']]=x['reason']
    return result

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--result',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    p=r.protocol();root=args.result
    manifest=json.loads((root/'manifest.json').read_text());audit=json.loads((root/'independent-audit.json').read_text())
    v0.require(audit['status']=='PASS' and manifest['modelFits']==16 and
               manifest['protocolSha256']==v0.digest(r.PRECOMMIT),'LAYER_A_REQUIRES_FULL_PASS')
    for name,hash_ in manifest['filesSha256'].items():v0.require(sha256(root/name)==hash_,'LAYER_A_RESULT_DIGEST')
    card=json.loads((root/'scorecard.json').read_text())
    _,data,_,_=integrated.load_inputs();evaluation=data[4]
    reason=checkpoint_reason_map();out={};recycling={}
    for arm in v0.ARMS:
        short='IM' if arm==v0.IM else 'R1';control=r.archive_control(arm)
        with gzip.open(root/(short+'_R50_A_CONTROL_ledger.json.gz'),'rt') as f:
            v0.require(v0.canonical(json.load(f))==v0.canonical(control),'ARCHIVED_CONTROL_NOT_IDENTICAL')
        out[short]={};recycling[short]={}
        for candidate in r.CANDIDATES:
            saved=json.loads((root/(short+'_'+candidate+'_layerA.json')).read_text())
            paired=paired_rows(saved,control)
            before=layer_a_groups(paired['control']);after=layer_a_groups(paired['candidate'])
            traces=json.loads(gzip.decompress((root/(candidate+'_decision_trace.json.gz')).read_bytes()))
            decisions={x['entryId']:x for x in traces if x['arm']==arm}
            r50_reasons=collections.Counter()
            for eid in control['funded']:
                x=decisions[eid]
                if x['exitKind']=='MODEL_EXIT':
                    key=(short,eid,x['decisionNow'])
                    r50_reasons[reason.get(key,'OUTSIDE_CONTROL_OWNED_PREFIX')]+=1
                else:r50_reasons['CANDIDATE_FORCE_TERMINAL_OR_UNRESOLVED']+=1
            out[short][candidate]={'scope':'SAME_ARCHIVED_BASELINE_ENTRY_ID_AND_QUANTITY_ONLY',
                'baselineFundedN':len(saved),'control':before,'candidate':after,
                'r50ReasonAtCandidateSellIntent':dict(sorted(r50_reasons.items()))}
            with gzip.open(root/(short+'_'+candidate+'_ledger.json.gz'),'rt') as f:ledger=json.load(f)
            base_ids=set(control['funded']);new_ids=set(ledger['funded'])
            add=new_ids-base_ids;drop=base_ids-new_ids
            ge=lambda ids,cut:sum(evaluation[arm][e]['postUpsidePct'] is not None and
                                   evaluation[arm][e]['postUpsidePct']>=cut for e in ids)
            attribution=r.pnl_delta(control,ledger)
            v0.require(attribution==card[short][candidate]['currencyAttributionVsControl'],
                       'RECYCLED_PNL_IDENTITY')
            recycling[short][candidate]={'scope':'ACTUAL_FIXED_CAPITAL_CHANGED_FUNDING_PATH',
                'newlyFundedIds':sorted(add),'displacedIds':sorted(drop),
                'addedGe5':ge(add,5),'removedGe5':ge(drop,5),
                'addedGe10':ge(add,10),'removedGe10':ge(drop,10),
                'currencyAttribution':attribution}
    args.out.mkdir(parents=True,exist_ok=False)
    (args.out/'LAYER_A_SAME_QUANTITY_COMPARISON.json').write_bytes(v0.canonical(out))
    (args.out/'RECYCLING_IDENTITY_ATTRIBUTION.json').write_bytes(v0.canonical(recycling))
    (args.out/'REPORT_AUDIT.json').write_bytes(v0.canonical({'schema':'phase57-r52-cycle2-evaluator-only-extra-report-v1',
        'status':'PASS','protocolSha256':manifest['protocolSha256'],'predictionSha256':manifest['predictionSha256'],
        'modelFits':0,'controlArchiveIdentical':True,'resultLedgerHashesVerified':True,
        'independentReplayPass':True,'candidateCount':2,'providerRequests':0,'protectedPartitionsOpened':0,'safety':p['safety']}))

if __name__=='__main__':main()
