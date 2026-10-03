"""Exact v0 assessor with precommitted calendar-index split adaptation only."""
from scripts.phase57_research_dictionary_v0 import *

def assess(data,cov,eligible,p,returns):
 index={d:i for i,d in enumerate(p['sessions'])};A=np.arange(index[p['split']['A'][0]],index[p['split']['A'][-1]]+1);B=np.arange(index[p['split']['B'][0]],index[p['split']['B'][-1]]+1);pool=np.r_[A,B];rng=np.random.default_rng(p['statistics']['seed']);perm=rng.permutation(pool);RA,RB=perm[:len(A)],perm[len(A):]
 wa=block_weights(len(A),500,rng);wb=block_weights(len(B),500,rng)
 shock=np.abs(returns);med=np.nanmedian(shock,axis=1);tail=sorted(pool,key=lambda i:(-(med[i] if np.isfinite(med[i]) else -1),i))[:3];TA=np.array([i for i in A if i not in tail]);TB=np.array([i for i in B if i not in tail])
 results=[];profiles=[];acceptedVectors={}
 for k,item in enumerate(p['catalog']):
  name,kind=item['id'],item['transform'];tier=0 if item['tier']=='daily' else 1;z=transform(data[:,:,k],kind)
  av,ar,an,ae=profile(z[A],kind);bv,br,bn,be=profile(z[B],kind);ca=mean(cov[A]);cb=mean(cov[B]);minobs=8 if name in CONDITIONAL else 20
  fitmask=(eligible[A,:,tier].sum(0)>=20)&(an>=minobs)&np.isfinite(av)&np.all(np.isfinite(ca),axis=1)
  bmask=(eligible[B,:,tier].sum(0)>=20)&(bn>=minobs)&np.isfinite(bv)&np.all(np.isfinite(cb),axis=1)
  mask=fitmask&bmask
  n=int(mask.sum());r={'id':name,'family':item['family'],'tier':item['tier'],'pairedSymbols':n,'status':'INSUFFICIENT','p':1.,'q':1.,'reasons':[]}
  allraw={'id':name,'allSymbolRawA':ar.tolist(),'allSymbolRawB':br.tolist(),'allSymbolNEffA':ae.tolist(),'allSymbolNEffB':be.tolist(),'allSymbolNSessionsA':an.tolist(),'allSymbolNSessionsB':bn.tolist(),'allSymbolStatus':['ELIGIBLE' if v else 'INSUFFICIENT' for v in mask],'insufficientShrinkWeight':0,'insufficientEstimate':'PRIOR_ONLY; peer prior undefined when no valid A fit'}
  if n<100:r['reasons']=['PAIRED_SAMPLE_BELOW100'];results.append(r);profiles.append(allraw);continue
  a,b=av[mask],bv[mask];xf,_,beta,mu,sd=fit_peer((ca[fitmask],ca[fitmask]),av[fitmask],av[fitmask])
  xa=np.column_stack([np.ones(len(a)),(ca[mask]-mu)/sd]);xb=np.column_stack([np.ones(len(a)),(cb[mask]-mu)/sd]);pa,pb=xa@beta,xb@beta;aa,bb=a-pa,b-pb
  raw=spearman(a,b)
  # Rank must not turn floating-point remnants of an exact peer proxy into a trait.
  peer_degenerate=np.allclose(a,pa,rtol=1e-10,atol=1e-12) or np.allclose(b,pb,rtol=1e-10,atol=1e-12)
  inc=None if peer_degenerate else spearman(aa,bb)
  w=ae[mask]/(ae[mask]+20);posterior=pa+w*aa
  # Rates use Beta posterior at peer logistic mean, then return to logit for calibration.
  if kind=='rate':
   priorprob=1/(1+np.exp(-np.clip(pa,-30,30)));postprob=(ae[mask]*(ar[mask])+20*priorprob)/(ae[mask]+20);posterior=np.log(np.clip(postprob,1e-9,1-1e-9)/(1-np.clip(postprob,1e-9,1-1e-9)))
  x=posterior-pa;den=np.sum((x-x.mean())**2);slope=float(np.sum((x-x.mean())*(bb-bb.mean()))/den) if den>0 else None
  # Session-block bootstrap peer residualization, re-fit coefficients for each bootstrap sample with fixed A design.
  bf=boot_profile(z[A][:,fitmask],wa,kind);ba=boot_profile(z[A][:,mask],wa,kind);bc=boot_profile(z[B][:,mask],wb,kind);coeff=np.full((len(bf),xf.shape[1]),np.nan)
  for bi,row in enumerate(bf):
   finite=np.isfinite(row)
   if finite.sum()>=100:coeff[bi]=np.linalg.lstsq(xf[finite],row[finite],rcond=1e-10)[0]
  ba-=coeff@xa.T;bc-=coeff@xb.T;boot=corr_rows(ba,bc);boot=boot[np.isfinite(boot)];lo,hi=np.quantile(boot,[.025,.975]) if len(boot)>=400 else (-1.,1.);pv=(1+np.sum(np.abs(boot-(inc or 0))>=abs(inc or 0)))/(len(boot)+1)
  qr=np.quantile(aa,[.2,.8]);spread=float(np.mean(bb[aa>=qr[1]])-np.mean(bb[aa<=qr[0]]))
  # Reverse direction is an auxiliary fit only, never supplies primary priors.
  bx,ax,betab,_,_=fit_peer((cb[mask],ca[mask]),b,a);reverse=spearman(b-bx@betab,a-ax@betab)
  cuts=np.quantile(ca[mask,0],[1/3,2/3]);strata=[]
  for ix in range(3):
   st=np.digitize(ca[mask,0],cuts)==ix;rr=spearman(aa[st],bb[st]);strata.append({'n':int(st.sum()),'incremental':rr,'pass':bool(st.sum()>=30 and rr is not None and rr>0)})
  rv1,_,rn1,_=profile(z[RA],kind);rv2,_,rn2,_=profile(z[RB],kind);rm=mask&np.isfinite(rv1)&np.isfinite(rv2)&(rn1>=minobs)&(rn2>=minobs)
  random_r=spearman(rv1[rm],rv2[rm]);ratio=raw/random_r if raw is not None and random_r and random_r>0 else None
  ta,_,tn1,_=profile(z[TA],kind);tb,_,tn2,_=profile(z[TB],kind)
  tm=mask&np.isfinite(ta)&np.isfinite(tb)&(tn1>=minobs)&(tn2>=minobs)&(eligible[TA,:,tier].sum(0)>=20)&(eligible[TB,:,tier].sum(0)>=20)
  tr=ti=None
  if tm.sum()>=100:
   tc1=mean(cov[TA])[tm];tc2=mean(cov[TB])[tm];xx,yy,bt,_,_=fit_peer((tc1,tc2),ta[tm],tb[tm]);tr=spearman(ta[tm],tb[tm]);ti=spearman(ta[tm]-xx@bt,tb[tm]-yy@bt)
  market=z-np.nanmedian(z,axis=1)[:,None]
  mr=spearman(mean(market[A])[mask],mean(market[B])[mask])
  checks={'residualIdentifiable':not peer_degenerate,'raw':raw is not None and raw>=.30,'incremental':inc is not None and inc>=.15,'CI':lo>0,'calibration':slope is not None and .5<=slope<=1.5,'direction':inc is not None and reverse is not None and inc>0 and reverse>0,'strata':sum(x['pass'] for x in strata)>=2,'timeRandom':ratio is not None and ratio>=.7,'tail':tr is not None and ti is not None and tr>=.30 and ti>=.15}
  r.update(peerResidualDegenerate=bool(peer_degenerate),rawSplitHalf=raw,spearmanBrown=2*raw/(1+raw) if raw is not None and raw>-1 else None,incremental=inc,reverseIncremental=reverse,ci=[float(lo),float(hi)],p=float(pv),calibrationSlope=slope,quintileBSpread=spread,liquidityStrata=strata,randomSplit=random_r,timeRandomRatio=ratio,tailRaw=tr,tailIncremental=ti,tailPairedSymbols=int(tm.sum()),marketRelative=mr,checks=checks,reasons=[x for x,v in checks.items() if not v],status='WATCH')
  # Save all symbol estimates including insufficient. Join key is never a predictor.
  residualvar=mean((z[A]-mean(z[A])[None,:])**2)[mask];psd=np.sqrt(np.maximum(residualvar,0)/(ae[mask]+20))
  if kind=='rate':
   alpha=ae[mask]*ar[mask]+20*priorprob;beta_rate=ae[mask]*(1-ar[mask])+20*(1-priorprob)
   probvar=alpha*beta_rate/((alpha+beta_rate)**2*(alpha+beta_rate+1));psd=np.sqrt(probvar)/np.maximum(postprob*(1-postprob),1e-12)
  profiles.append({**allraw,'id':name,'indices':np.flatnonzero(mask).tolist(),'rawA':ar[mask].tolist(),'rawB':br[mask].tolist(),'transformedA':a.tolist(),'peerPredictionA':pa.tolist(),'peerRelativeA':aa.tolist(),'posteriorA':posterior.tolist(),'shrink_w':w.tolist(),'posterior_sd':psd.tolist(),'nEffA':ae[mask].tolist(),'nEffB':be[mask].tolist(),'nSessionsA':an[mask].tolist(),'nSessionsB':bn[mask].tolist(),'priorFit':'A_ONLY','covariateMean':mu.tolist(),'covariateSD':sd.tolist(),'peerCoefficients':beta.tolist(),'excludedSymbolsPriorOnly':int(len(mask)-n)})
  acceptedVectors[name]=(mask,av);results.append(r)
  print(json.dumps({'trait':name,'paired':n,'measured':True}),flush=True)
 qs=fdr([x['p'] for x in results]);selected=[];correlations=[]
 for r,q in zip(results,qs):
  r['q']=float(q)
  if r['status']=='INSUFFICIENT':continue
  if q>.1:r['reasons'].append('FDR')
  if not r['reasons']:
   mask,a=acceptedVectors[r['id']]
   for old in selected:
    om,oa=acceptedVectors[old];mm=mask&om;rr=spearman(a[mm],oa[mm]);correlations.append({'left':old,'right':r['id'],'rho':rr})
    if rr is not None and abs(rr)>=.8:r['reasons'].append('REDUNDANT_WITH:'+old);break
   if not r['reasons']:r['status']='USABLE';selected.append(r['id'])
 usable=[r for r in results if r['status']=='USABLE'];families=sorted({x['family'] for x in usable});daily=sum(x['tier']=='daily' for x in usable);intra=len(usable)-daily
 complete=len(usable)>=8 and len(families)>=4 and daily>=2 and intra>=2
 return results,profiles,{'usable':len(usable),'families':families,'daily':daily,'intraday':intra,'status':'RESEARCH_STOCK_BEHAVIOR_DICTIONARY_V0_COMPLETE' if complete else 'V0_TRAIT_RELIABILITY_INSUFFICIENT','complete':complete,'acceptedCorrelations':correlations,'excludedTailSessions':[p['sessions'][i] for i in tail]}

