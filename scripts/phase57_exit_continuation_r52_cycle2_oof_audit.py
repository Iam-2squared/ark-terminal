"""No-fit audit of saved temporal OOF coverage before reading EXIT performance."""
from __future__ import annotations
import argparse, collections, json
from pathlib import Path
import numpy as np

from scripts import phase57_exit_continuation_r52 as r
from scripts import phase57_development_integrated_v0 as v0

def audit(source:Path,result:Path,out:Path):
    import joblib
    from sklearn.linear_model import Ridge
    p=r.protocol();receipt,arrays,identities,groups=r.load_checkpoints(source)
    manifest=json.loads((result/'manifest.json').read_text())
    fits=json.loads((result/'fit-manifest.json').read_text())
    support=json.loads((result/'label-support.json').read_text())
    v0.require(len(fits)==16 and manifest['modelFits']==16 and
               manifest['protocolSha256']==v0.digest(r.PRECOMMIT),'OOF_FROZEN_MANIFEST')
    v0.require(v0.digest(result/'oof-predictions.npz')==manifest['predictionSha256'],
               'OOF_PREDICTION_BYTES')
    sessions=np.asarray([x['session'] for x in identities]);arms=np.asarray([x['arm'] for x in identities])
    nows=np.asarray([x['now'] for x in identities]);expected=np.zeros(len(identities),dtype=bool)
    slices=[];filenames=[];features_by_candidate={}
    for fold in p['folds']:
        v0.require(max(fold['train'])<min(fold['purge']) and
                   max(fold['purge'])<min(fold['score']), 'OOF_TEMPORAL_PURGE')
        for arm in v0.ARMS:
            te=r.score_rows(arms,sessions,nows,arm,fold['score'])
            v0.require(len(te)>0 and not np.any(expected[te]), 'OOF_DUPLICATE_SCORE_ROW')
            expected[te]=True
            pair=[row for row in fits if row['fold']==fold['fold'] and row['arm']==arm]
            v0.require(len(pair)==2 and {row['candidate'] for row in pair}==set(r.CANDIDATES),
                       'OOF_FIT_PAIR_SCOPE')
            for row in pair:
                v0.require(row['scoreRows']==len(te) and row['trainMax']<row['scoreMin']
                           and row['trainMax']<min(fold['purge']) and
                           row['scoreMin']==min(fold['score']) and
                           row['imputerFits']==row['scalerFits']==row['estimatorFits']==1,
                           'OOF_FIT_TEMPORAL_SUPPORT')
                path=result/'models'/row['modelFile']
                v0.require(v0.digest(path)==row['modelSha256'],'OOF_MODEL_BYTES')
                bundle=joblib.load(path)
                clf=bundle['model']
                v0.require(isinstance(clf,Ridge) and clf.alpha==p['model']['alpha'] and
                           clf.solver==p['model']['solver'] and
                           clf.max_iter==p['model']['max_iter'] and
                           clf.tol==p['model']['tol'] and
                           clf.fit_intercept==p['model']['fit_intercept'],
                           'OOF_MODEL_IDENTITY')
                names=bundle['features'];c=row['candidate']
                approved=(list(r.CORE_NUMERIC)+
                          (list(r.EXTRA_NUMERIC) if c==r.CANDIDATES[1] else [])+
                          list(r.CATEGORICAL)+
                          (list(receipt['patternColumns']) if c==r.CANDIDATES[1] else []))
                v0.require(names==approved,'OOF_FEATURE_ORDER')
                features_by_candidate[c]=len(names)
                filenames.append(row['modelFile'])
            slices.append({'fold':fold['fold'],'arm':arm,'scoreRows':len(te),'firstSession':min(sessions[te]),
                           'lastSession':max(sessions[te])})
    v0.require(len(filenames)==len(set(filenames))==16 and len(slices)==8,
               'OOF_MODEL_UNIQUENESS')
    v0.require(int(expected.sum())==381223 and
               int(np.count_nonzero(expected&np.isin(sessions,p['sessions'])))==272803,
               'OOF_SOURCE_GEOMETRY')
    with np.load(result/'oof-predictions.npz',allow_pickle=False) as z:
        v0.require(set(z.files)==set(r.CANDIDATES),'OOF_CANDIDATE_IDENTITY')
        for candidate in r.CANDIDATES:
            a=z[candidate]
            v0.require(a.dtype==np.float32 and len(a)==len(identities) and
                       np.isfinite(a[expected]).all() and np.isnan(a[~expected]).all(),
                       'OOF_PREDICTION_FINITENESS_AND_EXACT_SCOPE')
    v0.require(support['trainingOnlyLabels'] and
               len(support['folds'])==8 and
               all(x['trainMax']<x['scoreMin'] for x in support['folds']),
               'OOF_LABEL_CUTOFF')
    output={'schema':'phase57-r52-cycle2-prediction-only-independent-oof-audit-v1',
            'status':'PASS','protocolSha256':v0.digest(r.PRECOMMIT),
            'executionSha':manifest['executionSha'],'predictionSha256':manifest['predictionSha256'],
            'sourceFeatureSha256':r.FEATURE_SHA,'sourceIdentitySha256':r.IDENTITY_SHA,
            'scoreRowsUnique':int(expected.sum()),'windowScoreRows':272803,
            'terminalAndUnscoredRowsNaN':int((~expected).sum()),'foldArmSlices':slices,
            'candidateFeatureCounts':features_by_candidate,'modelFiles':sorted(filenames),
            'estimatorFitsInArtifact':16,'additionalFits':0,'candidatePerformanceRead':False,
            'providerRequests':0,'protectedPartitionsOpened':0,'safety':p['safety']}
    out.write_bytes(v0.canonical(output))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--result',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();audit(a.source,a.result,a.out)

if __name__=='__main__':main()
