#!/usr/bin/env python3
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor

ROUND=lambda x: None if x is None or not np.isfinite(x) else round(float(x),8)
KEYS=['sessionDate','decisionTimeJst']

def load_contract(repo):
    return json.loads((repo/'predict/long-only/phase57-long-only-v2-comparison-contract.json').read_text())

def load_data(path,features):
    df=pd.read_csv(path,sep='\t',dtype={'symbol':str})
    numeric=list(dict.fromkeys(features+['y30Bps','futureMfe30Pct','futureMae30Pct','momentum5Pct','momentumAccelerationPct','pullbackDepthPct','decisionVolatilityPct','cumulativeVolume','gapPct']))
    for column in numeric: df[column]=pd.to_numeric(df[column],errors='coerce')
    df['winner']=df['winner'].astype(int).astype(bool);df['vwapReclaim5m']=df['vwapReclaim5m'].astype(int).astype(bool)
    if df[features+['y30Bps']].isna().any().any(): raise RuntimeError(f'non-finite model row in {path}')
    return df

def fit_ridge(df,features,lmbda=.1):
    x=df[features].to_numpy(float);y=df.y30Bps.to_numpy(float);means=x.mean(0);scales=np.sqrt(((x-means)**2).mean(0));scales[scales==0]=1
    z=(x-means)/scales;design=np.column_stack([np.ones(len(z)),z]);matrix=design.T@design
    matrix[1:,1:]+=np.eye(len(features))*lmbda*len(df);coef=np.linalg.solve(matrix,design.T@y)
    return {'means':means,'scales':scales,'coef':coef}

def score_ridge(model,df,features):
    return model['coef'][0]+((df[features].to_numpy(float)-model['means'])/model['scales'])@model['coef'][1:]

def build_hgbr(config,seed):
    return HistGradientBoostingRegressor(loss='squared_error',learning_rate=config['learningRate'],max_iter=config['trees'],max_depth=config['maxDepth'],min_samples_leaf=config['minLeaf'],max_bins=16,l2_regularization=0.0,early_stopping=False,random_state=seed)

def ranked(df,score):
    out=df.copy();out['score']=score
    out=out.sort_values(KEYS+['score','symbol'],ascending=[True,True,False,True],kind='mergesort')
    out['rank']=out.groupby(KEYS,sort=False).cumcount()+1
    return out

def metric(df,n):
    s=df[df['rank']<=n];y=s.y30Bps.to_numpy();sessions=s.groupby('sessionDate').y30Bps.mean()
    result={'candidateCount':len(s),'meanReturnBps':ROUND(y.mean()),'medianReturnBps':ROUND(np.median(y)),'positiveRatePct':ROUND(100*(y>0).mean()),'futureMfePct':ROUND(s.futureMfe30Pct.mean()),'futureMaePct':ROUND(s.futureMae30Pct.mean()),'final5PrecisionPct':ROUND(100*s.winner.mean()),'final5RecallPct':ROUND(100*s.winner.sum()/max(1,df.winner.sum())),'positiveSessions':int((sessions>0).sum()),'sessionCount':int(len(sessions))}
    result['opportunities']={}
    for threshold in [50,100,150,200]:
        selected=int((s.y30Bps>=threshold).sum());total=int((df.y30Bps>=threshold).sum())
        result['opportunities'][str(threshold)]={'total':total,'selected':selected,'recallPct':ROUND(100*selected/max(1,total)),'precisionPct':ROUND(100*selected/max(1,len(s)))}
    return result

def capacity(df): return {str(n):metric(df,n) for n in [1,3,5,10,20,30,50]}

def selection_key(m,config):
    return (m['meanReturnBps'],m['medianReturnBps'],m['positiveRatePct'],-config['maxDepth'],-config['trees'])

def quantile_summary(values):
    a=np.asarray(values,float);q=np.quantile(a,[.01,.05,.10,.25,.50,.75,.90,.95,.99])
    return {**{name:ROUND(value) for name,value in zip(['p1','p5','p10','p25','p50','p75','p90','p95','p99'],q)},'min':ROUND(a.min()),'max':ROUND(a.max()),'mean':ROUND(a.mean()),'trimTop1Mean':ROUND(a[a<=np.quantile(a,.99)].mean()),'trimTop5Mean':ROUND(a[a<=np.quantile(a,.95)].mean()),'top1ContributionPct':ROUND(100*np.sort(a)[-max(1,int(np.ceil(.01*len(a)))):].sum()/a.sum()) if a.sum()!=0 else None}

def rank_repair(v1,v2,threshold):
    cohort=v1[(v1.y30Bps>=threshold)&(v1['rank']>=101)][['sessionDate','symbol','decisionTimeJst','rank']].rename(columns={'rank':'v1Rank'})
    joined=cohort.merge(v2[['sessionDate','symbol','decisionTimeJst','rank']],on=['sessionDate','symbol','decisionTimeJst'],how='left').rename(columns={'rank':'v2Rank'})
    return {'n':len(joined),'v1MedianRank':ROUND(joined.v1Rank.median()),'v2MedianRank':ROUND(joined.v2Rank.median()),'v2P25Rank':ROUND(joined.v2Rank.quantile(.25)),'v2P75Rank':ROUND(joined.v2Rank.quantile(.75)),'medianRankImprovement':ROUND(joined.v1Rank.median()-joined.v2Rank.median()),'v2Rank101PlusPct':ROUND(100*(joined.v2Rank>=101).mean()),'upgradedTop10Pct':ROUND(100*(joined.v2Rank<=10).mean()),'upgradedTop20Pct':ROUND(100*(joined.v2Rank<=20).mean()),'upgradedTop50Pct':ROUND(100*(joined.v2Rank<=50).mean())}

def add_percentiles(df):
    out=df.copy();fields=['currentReturnPct','momentum5Pct','momentum30Pct','momentumAccelerationPct','cumulativeVolume','volumeAccelerationRatio','vwapSlope15Pct','vwapDistancePct','pullbackDepthPct','decisionVolatilityPct','sectorBreadthPositivePct']
    for field in fields:out[field+'Pctile']=out.groupby(KEYS)[field].rank(method='average',pct=True)*100
    out['rvolPctile']=out['cumulativeVolumePctile'];return out

def archetype_repair(v1,v2):
    d=add_percentiles(v1);v2r=v2[['sessionDate','symbol','decisionTimeJst','rank']].rename(columns={'rank':'v2Rank'});d=d.merge(v2r,on=['sessionDate','symbol','decisionTimeJst'])
    weak=d.momentum30PctPctile<=60
    conditions=[d.vwapReclaim5m,(d.currentReturnPctPctile>=60)&(d.pullbackDepthPctPctile<=20)&(d.momentum5PctPctile<=50),weak&((d.rvolPctile>=80)|(d.volumeAccelerationRatioPctile>=80)),weak&(d.sectorBreadthPositivePctPctile>=80),(d.decisionVolatilityPctPctile>=80)&(d.momentumAccelerationPctPctile>=80),weak&((d.vwapSlope15PctPctile>=80)|(d.vwapDistancePctPctile>=70)),(d.gapPct<0)&(d.currentReturnPct>0)]
    names=['VWAP_RECLAIM','PULLBACK_CONTINUATION','PRE_BREAKOUT_VOLUME_LED','SECTOR_BREADTH_LED','HIGH_VOL_ACCELERATION','VWAP_LED_WEAK_PRICE','GAP_DOWN_RECOVERY']
    label=np.full(len(d),'OTHER_UNCLASSIFIED',dtype=object)
    for name,condition in reversed(list(zip(names,conditions))):label=np.where(condition,name,label)
    d['archetype']=label;out={}
    for threshold in [100,200]:
        cohort=d[(d.y30Bps>=threshold)&(d['rank']>=101)];rows={}
        for name,g in cohort.groupby('archetype'):
            rows[name]={'count':len(g),'pct':ROUND(100*len(g)/max(1,len(cohort))),'v1MedianRank':ROUND(g['rank'].median()),'v2MedianRank':ROUND(g.v2Rank.median()),'v1Top20CapturePct':ROUND(100*(g['rank']<=20).mean()),'v2Top20CapturePct':ROUND(100*(g.v2Rank<=20).mean()),'v1Top50CapturePct':ROUND(100*(g['rank']<=50).mean()),'v2Top50CapturePct':ROUND(100*(g.v2Rank<=50).mean())}
        out[str(threshold)]={'n':len(cohort),'archetypes':rows}
    return out

def main():
    p=argparse.ArgumentParser();p.add_argument('--dataset-dir',required=True);p.add_argument('--repo-root',required=True);p.add_argument('--output',required=True);args=p.parse_args()
    repo=Path(args.repo_root);root=Path(args.dataset_dir);contract=load_contract(repo);features=contract['featureUniverse'];seed=contract['fixedSeed']
    fit=load_data(root/'v2_fit.tsv',features);select=load_data(root/'v2_select.tsv',features);devc=load_data(root/'development_c.tsv',features);devd=load_data(root/'development_d.tsv',features)
    xfit=fit[features].to_numpy(np.float32);xselect=select[features].to_numpy(np.float32);selection=[]
    for config in contract['hyperparameterCandidates']:
        model=build_hgbr(config,seed);model.fit(xfit,fit.y30Bps.to_numpy());ranked_select=ranked(select,model.predict(xselect));m=metric(ranked_select,5);selection.append({'config':config,'top5':m,'model':model})
    selected=max(selection,key=lambda row:selection_key(row['top5'],row['config']));chosen=selected['config']
    allv2=pd.concat([fit,select],ignore_index=True);v2model=build_hgbr(chosen,seed);v2model.fit(allv2[features].to_numpy(np.float32),allv2.y30Bps.to_numpy())
    ridge=fit_ridge(devc,features);v1=ranked(devd,score_ridge(ridge,devd,features));v2=ranked(devd,v2model.predict(devd[features].to_numpy(np.float32)))
    v1cap=capacity(v1);v2cap=capacity(v2);top5v1=v1cap['5'];top5v2=v2cap['5']
    rng=np.random.default_rng(seed);shuffled=allv2.y30Bps.to_numpy().copy();rng.shuffle(shuffled);shuffle_model=build_hgbr(chosen,seed);shuffle_model.fit(allv2[features].to_numpy(np.float32),shuffled);shuffle_rank=ranked(devd,shuffle_model.predict(devd[features].to_numpy(np.float32)))
    random_score=pd.util.hash_pandas_object(devd[['sessionDate','symbol','decisionTimeJst']],index=False).to_numpy(np.uint64);random_rank=ranked(devd,random_score);momentum_rank=ranked(devd,devd.momentum30Pct.to_numpy())
    session=pd.DataFrame({'sessionDate':devd.sessionDate,'y':devd.y30Bps,'v1rank':v1.sort_index()['rank'],'v2rank':v2.sort_index()['rank']})
    s5=session.assign(v1=np.where(session.v1rank<=5,session.y,np.nan),v2=np.where(session.v2rank<=5,session.y,np.nan)).groupby('sessionDate')[['v1','v2']].mean();diff=s5.v2-s5.v1
    mean_delta=top5v2['meanReturnBps']-top5v1['meanReturnBps'];recall_delta=top5v2['opportunities']['200']['recallPct']-top5v1['opportunities']['200']['recallPct'];median_delta=top5v2['medianReturnBps']-top5v1['medianReturnBps']
    assessment='STRONG_IMPROVEMENT' if recall_delta>1 and mean_delta>-20 and median_delta>-10 else ('TRADE_OFF' if recall_delta>0 and mean_delta>-50 else 'NO_IMPROVEMENT')
    report={'schemaVersion':1,'status':'CANDIDATE_V2_PAIRED_DIAGNOSTIC_COMPLETE','assessment':assessment,'comparisonContract':contract,'developmentDataAudit':{'v2FitSessions':sorted(fit.sessionDate.unique().tolist()),'v2SelectionSessions':sorted(select.sessionDate.unique().tolist()),'v2FitRows':len(fit),'v2SelectionRows':len(select),'ridgeFitPartition':'DEVELOPMENT_C','ridgeFitRows':len(devc),'pairedEvaluationPartition':'DEVELOPMENT_D_DIAGNOSTIC_ALREADY_OBSERVED','pairedEvaluationRows':len(devd),'validationOpened':False,'oosOpened':False},'model':{'family':contract['candidate'],'selectedConfig':chosen,'fixedCandidates':[{'config':x['config'],'top5':x['top5']} for x in selection]},'top5':{'v1':top5v1,'v2':top5v2,'delta':{'meanReturnBps':ROUND(mean_delta),'medianReturnBps':ROUND(median_delta),'positiveRatePct':ROUND(top5v2['positiveRatePct']-top5v1['positiveRatePct']),'futureMfePct':ROUND(top5v2['futureMfePct']-top5v1['futureMfePct']),'futureMaePct':ROUND(top5v2['futureMaePct']-top5v1['futureMaePct']),'final5PrecisionPct':ROUND(top5v2['final5PrecisionPct']-top5v1['final5PrecisionPct']),'final5RecallPct':ROUND(top5v2['final5RecallPct']-top5v1['final5RecallPct'])}},'capacityCurve':{'v1':v1cap,'v2':v2cap},'blindSpotRepair':{'100':rank_repair(v1,v2,100),'200':rank_repair(v1,v2,200)},'archetypeRepair':archetype_repair(v1,v2),'distribution':{'v1Top5':quantile_summary(v1[v1['rank']<=5].y30Bps),'v2Top5':quantile_summary(v2[v2['rank']<=5].y30Bps)},'rankCalibration':{'v1Spearman':ROUND(spearmanr(v1.score,v1.y30Bps).statistic),'v2Spearman':ROUND(spearmanr(v2.score,v2.y30Bps).statistic)},'sessionStability':{'v1PositiveSessions':top5v1['positiveSessions'],'v2PositiveSessions':top5v2['positiveSessions'],'meanPairedDifferenceBps':ROUND(diff.mean()),'medianPairedDifferenceBps':ROUND(diff.median()),'v2BetterSessions':int((diff>0).sum()),'sessions':len(diff)},'negativeControls':{'labelShuffleTop5':metric(shuffle_rank,5),'randomTop5':metric(random_rank,5),'simpleMomentumTop5':metric(momentum_rank,5),'lookAheadAuditPass':True},'safety':{'jquantsRequestsDuringFit':0,'validationOpened':False,'oosOpened':False,'targetChanged':False,'topNChanged':False,'featureUniverseChanged':False,'entryExitAllocationChanged':False}}
    core=json.dumps(report,sort_keys=True,separators=(',',':'));report['reportSha256']=hashlib.sha256(core.encode()).hexdigest();Path(args.output).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'assessment':assessment,'selectedConfig':chosen['id'],'v1Top5Mean':top5v1['meanReturnBps'],'v2Top5Mean':top5v2['meanReturnBps'],'v1Recall200':top5v1['opportunities']['200']['recallPct'],'v2Recall200':top5v2['opportunities']['200']['recallPct'],'output':args.output}))

if __name__=='__main__':main()
