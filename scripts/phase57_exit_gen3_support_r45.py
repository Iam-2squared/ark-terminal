"""Pre-fit R45 support and independent reference/target verification, no fits."""
from pathlib import Path
import argparse
import gzip
import json
import math
import numpy as np
from scripts.phase57_exit_gen3_runtime_r45 import load_protocol, PROTOCOL_SHA256, HEADS
from scripts.phase57_exit_gen3_data_r45 import build_data, FACT_NAMES
from scripts.phase57_exit_gen3_runner_r45 import support_slices
from scripts.phase57_exit_finite_r36 import read_json, sha, write_json, RAW_PATHS, SAFETY


def independent_labels(root,core):
    """Recompute all targets from raw exact references without the label builder."""
    p=load_protocol();raw=read_json(RAW_PATHS)
    envelopes=read_json(core/'core-a/entry-envelopes.json.gz')
    entries={(a,row['entryId']):row for a,rs in envelopes.items() for row in rs if row['entryId'] is not None}
    with np.load(root/'training-labels.npz',allow_pickle=False) as z:labels={k:z[k] for k in z.files}
    with np.load(root/'decision-facts.npz',allow_pickle=False) as z:fv=z['values'];fresh=z['fresh'];times=z['now']
    schedule=list(range(540,690))+list(range(750,925));cidx=FACT_NAMES.index('certifiedMfePct')
    indices={};checked=0
    with gzip.open(root/'source-row-identity.jsonl.gz','rt') as f:
        for line in f:
            row=json.loads(line);i=row['index'];now=row['now'];entry=entries[(row['arm'],row['entryId'])]
            assert i==checked and now==times[i]
            oid=entry['opportunity']
            if oid not in indices:indices[oid]={int(b[0]):b for b in raw[oid]['today']}
            ix=indices[oid]
            remaining=[t for t in schedule if t>=now];h=min(15,len(remaining))
            result=[None,None,None];maturity=-1
            if fresh[i] and h>=3:
                offsets=[math.ceil(h/3),math.ceil(2*h/3),h]
                refs=[remaining[k] if k<len(remaining) else 930 for k in offsets]
                ts=[remaining[0]]+refs;bars=[ix.get(t) for t in ts]
                good=all(b is not None and type(b[1]) in (int,float) and math.isfinite(b[1]) and b[1]>0 for b in bars)
                if good and 930 in ts:
                    good=all(v==bars[-1][1] and type(v) in (int,float) and math.isfinite(v) and v>0 for v in bars[-1][1:5])
                if good:
                    u=[100*(b[1]-bars[0][1])/entry['price'] for b in bars[1:]]
                    result[0]=int(u[-1]>=p['labels']['continuationMarginPp'] and sum(v>0 for v in u)>=2)
                    result[2]=int(u[-1]<=-p['labels']['deteriorationMarginPp'] and sum(v<0 for v in u)>=2)
                    if np.isfinite(fv[i,cidx]) and fv[i,cidx]>=p['policy']['profitArmMfePp']:
                        result[1]=int(u[-1]<=-p['labels']['protectionMarginPp'])
                    maturity=refs[-1]
                    assert np.allclose(labels['futureUtility'][i],u,rtol=0,atol=1e-12)
                    assert list(labels['sampleReferenceMinutes'][i])==refs
            for head,want in enumerate(result):
                actual=labels['targets'][i,head]
                assert bool(labels['available'][i,head])==(want is not None),(i,head,'MASK')
                assert np.isnan(actual) if want is None else actual==want,(i,head,'TARGET')
                assert labels['knownAt'][i,head]==(-1 if want is None else maturity),(i,head,'MATURITY')
            checked+=1
    assert checked==656247
    return {'rowsChecked':checked,'targetsChecked':checked*3,'mismatches':0,'additionalFits':0,'additionalPolicyReplays':0}


def run(core,out):
    p=load_protocol();data=build_data(core,out/'data',2,p,include_pattern=False)
    _,slices=support_slices(data,p)
    independent=independent_labels(out/'data',core)
    files=['training-labels.npz','decision-facts.npz','source-row-identity.jsonl.gz','categorical-representation.json']
    receipt=dict(status='GEN3_SUPPORT_AND_INDEPENDENT_LABELS_PASS',protocolSha256=PROTOCOL_SHA256,
        slices=slices,independentLabelCheck=independent,
        supportHashes={name:sha(out/'data'/name) for name in files},
        modelFits=0,policyReplays=0,performanceInspections=0,providerRequests=0,protectedPartitionsOpened=0,safety=SAFETY)
    write_json(out/'support-receipt.json',receipt)
    print('SUPPORT_PASS_NO_FITS',len(slices),'slices',independent['rowsChecked'],'rows')
    return receipt

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--core-root',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();run(args.core_root,args.out)
