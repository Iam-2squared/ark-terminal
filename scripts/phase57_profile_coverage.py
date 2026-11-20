"""Offline coverage of frozen profiles; confidence is descriptive precision, not promotion."""
import argparse,collections,csv,gzip,hashlib,html,io,json,math
from pathlib import Path
import numpy as np
from scripts import phase57_dictionary_anatomy as a
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'docs/evidence/phase57-profile-coverage-v1'
SOURCE=a.SOURCE
LEVELS=['HIGH','MEDIUM','LOW','INSUFFICIENT']
WINDOWS=[20,60,250]
def read(p):return a.read(p)
def clean(x):
 if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
 if isinstance(x,(list,tuple)):return [clean(v) for v in x]
 if isinstance(x,np.generic):x=x.item()
 if isinstance(x,float):return x if math.isfinite(x) else None
 return x
def write(p,x):p.write_text(json.dumps(clean(x),ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n')
def num(x):return isinstance(x,(int,float,np.number)) and not isinstance(x,bool) and np.isfinite(x)
def stats(vals):
 z=np.array([float(x) for x in vals if num(x)])
 return {'n':len(z),'p10':float(np.quantile(z,.1)) if len(z) else None,'median':float(np.median(z)) if len(z) else None,'p90':float(np.quantile(z,.9)) if len(z) else None}
def confidence(c,p):
 if not c['eligible'] or any(not num(c[k]) for k in ['posterior','posterior_sd','peer_prediction','shrinkWeight']) or c['posterior_sd']<0:return 'INSUFFICIENT'
 for state in ['HIGH','MEDIUM']:
  q=p[state]
  if any(c[k]<q[v] for k,v in [('nSessions','nSessionsMin'),('nEff','nEffMin'),('shrinkWeight','shrinkWeightMin'),('coverage','coverageMin')]):continue
  if not num(c['normalizedUncertainty']) or c['normalizedUncertainty']>q['posteriorSdOverReferenceSdMax']:continue
  if c['driftFlag'] is True or state=='HIGH' and c['driftFlag'] is not False:continue
  return state
 return 'LOW'
def differentiate(c):
 return bool(all(num(c[k]) for k in ['posterior','peer_prediction','posterior_sd']) and abs(c['posterior']-c['peer_prediction'])>1.96*c['posterior_sd'])
def bins(vals):
 out={k:0 for k in ['0','1-2','3-5','6-10','11+']}
 for n in vals:out['0' if n==0 else '1-2' if n<=2 else '3-5' if n<=5 else '6-10' if n<=10 else '11+']+=1
 return out
def solve_identity(rows):
 if len(rows)<6:return [None]*4,{'status':'INSUFFICIENT_EQUATIONS'}
 xy=np.array(rows,float);X,y=xy[:,:4],xy[:,4];T=X[:-2];ty=y[:-2];scale=np.linalg.norm(T,axis=0);scale=np.where(scale>0,scale,1.)
 U,s,V=np.linalg.svd(T/scale,full_matrices=False);rank=int(sum(s>s[0]*1e-10)) if len(s) and s[0]>0 else 0
 if not rank:return [None]*4,{'status':'NO_RANK'}
 condition=float(s[0]/s[rank-1]);coef=V[:rank].T@((U[:,:rank].T@ty)/s[:rank]);x=coef/scale
 residual=np.abs(X@x-y)/(1+np.abs(y));identifiable=np.sum(V[rank:]**2,axis=0)<1e-8 if rank<4 else np.ones(4,bool)
 if condition>1e8 or max(residual)>1e-8:return [None]*4,{'status':'VALIDATION_FAILED','condition':condition,'maxRelativeResidual':float(max(residual))}
 return [float(v) if ok else None for v,ok in zip(x,identifiable)],{'status':'VERIFIED_FULL' if all(identifiable) else 'VERIFIED_PARTIAL','rank':rank,'condition':condition,'maxRelativeResidual':float(max(residual)),'equations':len(rows)}
def reconstruct(profiles):
 codes=profiles['codeJoinKeys'];equations=[[] for _ in codes];ps={x['id']:x for x in profiles['profiles']}
 for p in profiles['profiles']:
  if 'peerCoefficients' not in p:continue
  b=np.array(p['peerCoefficients']);mu=np.array(p['covariateMean']);sd=np.array(p['covariateSD']);slope=b[1:]/sd;inter=b[0]-slope@mu
  for i,pred in zip(p['indices'],p['peerPredictionA']):equations[i].append([*slope,float(pred-inter)])
 tv=ps['trading_value'];reference=dict(zip(tv.get('indices',[]),tv.get('transformedA',[])));values=[];audit=[]
 for i,rows in enumerate(equations):
  val,rec=solve_identity(rows)
  if val[0] is not None and i in reference:
   err=abs(val[0]-reference[i]);rec['logVaReferenceAbsError']=err
   if err>1e-7:val=[None]*4;rec['status']='LOGVA_REFERENCE_FAILED'
  values.append(val);audit.append(rec)
 strata={};cuts={}
 for name,j in [('liquidity',0),('volatility',1),('price',2)]:
  finite=[x[j] for x in values if x[j] is not None];q=np.quantile(finite,[1/3,2/3]) if finite else None;cuts[name]=q.tolist() if q is not None else None
  strata[name]=['UNKNOWN' if x[j] is None or q is None else ['LOW','MID','HIGH'][int(np.digitize(x[j],q))] for x in values]
 return strata,{'method':'A_ONLY_LINEAR_IDENTITIES_WITH_HELD_OUT_EQUATION_VALIDATION','coordinateOrder':['meanLogVa','meanLogS','meanLogPrice','meanCoverage'],'counts':dict(collections.Counter(x['status'] for x in audit)),'cuts':cuts,'values':dict(zip(codes,values)),'audits':dict(zip(codes,audit)),'caveat':'A historical strata, not current-window market attributes; unidentified values UNKNOWN'}
def fraction(n,total):return {'n':n,'pct':100*n/total if total else None}
def aggregate(cells):
 total=len(cells);ok=[x for x in cells if x['confidence']!='INSUFFICIENT'];hm=[x for x in cells if x['confidence'] in ['HIGH','MEDIUM']]
 metrics=['nSessions','nEff','episodes','eventPositiveSessions','shrinkWeight','posterior_sd','CI_low','CI_high','normalizedUncertainty','raw','transformed','peer_relative','posterior','coverage']
 return {'totalSymbols':total,'profileComputable':fraction(len(ok),total),'confidence':{s:fraction(sum(c['confidence']==s for c in cells),total) for s in LEVELS},'highMedium':fraction(len(hm),total),'metricsAll':{k:stats(c[k] for c in cells) for k in metrics},'metricsComputable':{k:stats(c[k] for c in ok) for k in metrics},'peerDifferentiated':fraction(sum(c['peerDifferentiated'] for c in cells),total),'highMediumPeerDifferentiated':fraction(sum(c['peerDifferentiated'] for c in hm),total),'driftTrue':sum(c['driftFlag'] is True for c in cells),'driftUnknown':sum(c['driftFlag'] is None for c in cells)}
def run(out):
 out=Path(out);out.mkdir(parents=True,exist_ok=False);policy=read(BASE/'protocol.json');start=read(BASE/'start-state.json')
 for p,h in start['files'].items():assert a.sha(ROOT/p)==h,'START_HASH_MISMATCH:'+p
 manifest=read(SOURCE/'manifest.json');assert all(a.sha(SOURCE/k)==h for k,h in manifest.items())
 reg=read(ROOT/'docs/evidence/phase57-research-dictionary-v0/registry.json');defs={x['id']:x for x in reg['catalog']}
 summaries=[];primary={};sets={};allcodes={};stratum_meta={};target_counts={};endpoints={}
 fields=['lane','symbol','trait','globalStatus','window','computed_through','raw','transformed','peer_relative','peer_prediction','posterior','confidence','nSessions','nEff','episodes','eventPositiveSessions','shrinkWeight','posterior_sd','CI_low','CI_high','normalizedUncertainty','coverage','driftFlag','peerDifferentiated','priorSaved','liquidityStratum','priceStratum','volatilityStratum']
 with (out/'all-symbol-profiles.csv.gz').open('wb') as raw:
  with gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as gz:
   with io.TextIOWrapper(gz,encoding='utf-8',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');writer.writeheader()
    for lane in ['daily','intraday']:
     profiles=read(SOURCE/(lane+'-profiles.json.gz'));windows=read(SOURCE/(lane+'-windows.json.gz'));results=read(SOURCE/(lane+'-reliability.json'))
     ps={x['id']:x for x in profiles['profiles']};ws={(x['trait'],x['window']):x for x in windows['profiles']};codes=windows['codeJoinKeys'];assert codes==profiles['codeJoinKeys'];allcodes[lane]=codes
     strata,stratum_meta[lane]=reconstruct(profiles)
     targets=[r for r in results if r['status']=='USABLE' or r['status']=='WATCH' and r['reasons']==['calibration']];target_counts[lane]=len(targets)
     primary[lane]={c:[] for c in codes};sets[lane]={w:{c:{'available':set(),'hm':set()} for c in codes} for w in WINDOWS}
     for r in targets:
      p=ps[r['id']];ref=float(np.std(p.get('peerRelativeA',[]))) if p.get('peerRelativeA') else None
      av=p['allSymbolRawA'];bv=p['allSymbolRawB'];ma=np.nanmedian(np.asarray(av,float));mb=np.nanmedian(np.asarray(bv,float))
      signs=[np.sign(x-ma)==np.sign(y-mb) for x,y in zip(av,bv) if num(x) and num(y) and x!=ma and y!=mb]
      for window in WINDOWS:
       w=ws[r['id'],window];endpoints[lane]=w['computed_through'];ix={k:j for j,k in enumerate(w.get('indices',[]))};cells=[]
       for i,code in enumerate(codes):
        j=ix.get(i)
        def get(k):return w[k][j] if j is not None and k in w else None
        sd=get('posterior_sd');n=w['n_sessions'][i];raw_value=w['raw'][i]
        c={'lane':lane,'symbol':code,'trait':r['id'],'globalStatus':r['status'],'window':window,'computed_through':w['computed_through'],'raw':raw_value,'transformed':w['transformed'][i],'eligible':w['status'][i]=='ELIGIBLE','nSessions':n,'nEff':w['nEff'][i],'episodes':w['episodes'][i] if w['episodes'] is not None else None,'eventPositiveSessions':raw_value*n if defs[r['id']]['transform']=='rate' and num(raw_value) else None,'shrinkWeight':get('shrink_w'),'peer_relative':get('peer_relative'),'peer_prediction':get('peer_prediction'),'posterior':get('posterior'),'posterior_sd':sd,'CI_low':get('CI')[0] if get('CI') is not None else None,'CI_high':get('CI')[1] if get('CI') is not None else None,'normalizedUncertainty':sd/ref if num(sd) and num(ref) and ref>0 else None,'coverage':w['coverage'][i],'driftFlag':w['drift']['driftFlag'][i],'priorSaved':get('peer_prediction') is not None,'liquidityStratum':strata['liquidity'][i],'priceStratum':strata['price'][i],'volatilityStratum':strata['volatility'][i]}
        c['confidence']=confidence(c,policy);c['peerDifferentiated']=differentiate(c);cells.append(c);writer.writerow(clean(c))
        if window==60:primary[lane][code].append(c)
        if r['status']=='USABLE':
         if c['confidence']!='INSUFFICIENT':sets[lane][window][code]['available'].add(r['id'])
         if c['confidence'] in ['HIGH','MEDIUM']:sets[lane][window][code]['hm'].add(r['id'])
       row={'lane':lane,'trait':r['id'],'globalStatus':r['status'],'globalReasons':r['reasons'],'window':window,'computed_through':w['computed_through'],'definition':defs[r['id']]['definition'],'transform':defs[r['id']]['transform'],'referenceResidualSD':ref,**aggregate(cells),'globalReliability':r,'signStability':{'globalIncrementalPositive':num(r.get('incremental')) and r['incremental']>0,'globalReversePositive':num(r.get('reverseIncremental')) and r['reverseIncremental']>0,'rawCenteredAtoBAgreement':float(np.mean(signs)) if signs else None,'rawCenteredPaired':len(signs),'meaning':'Descriptive raw-centered agreement; NOT B peer-residual validation'},'strata':{name:{s:aggregate([c for c in cells if c[name+'Stratum']==s]) for s in ['LOW','MID','HIGH','UNKNOWN']} for name in ['liquidity','price','volatility']}}
       if r['status']=='WATCH':row['calibrationAssessment']={'slope':r['calibrationSlope'],'failureReason':'BELOW_0.5' if r['calibrationSlope']<.5 else 'ABOVE_1.5','otherFixedGatesPassed':True,'potential':'HYPOTHESIS_ONLY: A-only finite calibration and separate temporal Development validation required. No B-slope correction or promotion. Regime shift, shrinkage and misspecification remain alternatives.','correctionFitted':False}
       summaries.append(row)
     del windows,profiles,ws,ps
 assert target_counts=={'daily':18,'intraday':14}
 dist={lane:{str(w):{kind:bins(len(x[kind]) for x in sets[lane][w].values()) for kind in ['available','hm']} for w in WINDOWS} for lane in sets}
 union=sorted(set(allcodes['daily'])|set(allcodes['intraday']));intersection=sorted(set(allcodes['daily'])&set(allcodes['intraday']));integrated={}
 for w in WINDOWS:
  integrated[str(w)]={}
  for name,universe in [('union',union),('intersection',intersection)]:
   integrated[str(w)][name]={'symbols':len(universe)}
   for kind in ['available','hm']:
    integrated[str(w)][name][kind]=bins(len(sets['daily'][w].get(c,{}).get(kind,set())|sets['intraday'][w].get(c,{}).get(kind,set())) for c in universe)
 integrated.update(endpointDates=endpoints,dedup='Same trait ID counted once; estimates never pooled',validatedHandoffSymbols=0,reason='Different endpoints, symbol temporal reliability not established and Reader blockers')
 chosen=[]
 for state in LEVELS:
  candidates=[c for c in allcodes['intraday'] if next(x for x in primary['intraday'][c] if x['trait']=='pdh_break')['confidence']==state]
  if candidates:chosen.append((candidates[0],'first_code_PDH_'+state))
 cv=sorted(len(sets['intraday'][60][c]['hm']) for c in allcodes['intraday'])
 for n in [cv[0],cv[len(cv)//2],cv[-1]]:
  chosen.append((next(c for c in allcodes['intraday'] if len(sets['intraday'][60][c]['hm'])==n),'first_code_HM_count_'+str(n)))
 examples=[];seen=set()
 for c,why in chosen:
  if c in seen:continue
  seen.add(c);examples.append({'symbol':c,'selection':why,'records':primary['daily'].get(c,[])+primary['intraday'].get(c,[])})
 write(out/'01_trait_coverage.json',summaries);write(out/'02_trait_count_distribution.json',dist);write(out/'03_integrated_coverage.json',integrated);write(out/'04_representative_profiles.json',examples);write(out/'05_strata_reconstruction.json',stratum_meta)
 with (out/'all-symbol-trait-counts.csv').open('w',newline='') as f:
  wr=csv.writer(f);wr.writerow(['symbol','dailyAvailable60','dailyHM60','intradayAvailable60','intradayHM60','archivalUniqueAvailable60','archivalUniqueHM60','validatedHandoff'])
  for c in union:
   d=sets['daily'][60].get(c,{'available':set(),'hm':set()});i=sets['intraday'][60].get(c,{'available':set(),'hm':set()})
   wr.writerow([c,len(d['available']),len(d['hm']),len(i['available']),len(i['hm']),len(d['available']|i['available']),len(d['hm']|i['hm']),False])
 write(out/'06_integrity.json',{'sourceHashes':manifest,'protocolHash':a.sha(BASE/'protocol.json'),'correctionSpecHash':a.sha(BASE/'correction-spec.json'),'targets':target_counts,'primaryWindow':60,'exportPrecision':'NATIVE_FLOAT64_NO_DECIMAL_ROUNDING','newProtectedReads':0,'newProviderRequests':0,'rawRemeasurements':0,'registryGateChanged':False,'entryExitTrials':0,'safety':start['safety']})
 report(out,summaries,dist,integrated,examples,stratum_meta)
 assert all(a.sha(SOURCE/k)==h for k,h in manifest.items())
 write(out/'manifest.json',{p.name:a.sha(p) for p in sorted(out.iterdir())})
def report(out,rows,dist,integrated,examples,strata):
 selected=[x for x in rows if x['window']==60]
 lines=['# 銘柄別Dictionary Profile coverage','',
 '**判定：標本精度のcoverageは定量化。NEW LONG Entry/EXITへの引渡しは未成立。**','',
 '事前固定した60-position snapshotを主表とし20/250も全件保存。HIGH/MEDIUMは標本精度の診断ラベルであり、銘柄固有の時間再現性・校正済み信頼確率・収益性の認定ではない。旧registry・Gate・判定は不変。','',
 '## 1–2. 固定USABLEの個別Profile','',
 '| lane / trait | 全銘柄 | 算出可 | HIGH | MEDIUM | LOW | INSUFFICIENT | H+M割合 |',
 '|---|---:|---:|---:|---:|---:|---:|---:|']
 for x in selected:
  if x['globalStatus']=='USABLE':
   lines.append(f"| {x['lane']} / {x['trait']} | {x['totalSymbols']} | {x['profileComputable']['n']} | "+' | '.join(str(x['confidence'][s]['n']) for s in LEVELS)+f" | {x['highMedium']['pct']:.2f}% |")
 lines+=['','各traitの人数/割合、nSessions/nEff/episodesのp10/median/p90、shrinkWeight、posterior SD、正規化不確実性、trait値、peer差、層別coverageは01_trait_coverage.json。全対象銘柄と算出可能銘柄の統計を分離。セルごとの全値はall-symbol-profiles.csv.gz。','',
 'episodesは条件付きtraitのevent-bearing sessionsのみ。非条件付きPDH break等の正の発生session数はeventPositiveSessionsであり、個別episode数とは異なる。INSUFFICIENTで数値peer priorが存在するとは限らない。','',
 '## 3. Calibration-only WATCH23判定','',
 '| lane / trait | raw | incremental | slope | H+M / 全銘柄 | peer差あり H+M |','|---|---:|---:|---:|---:|---:|']
 for x in selected:
  if x['globalStatus']=='WATCH':
   r=x['globalReliability'];lines.append(f"| {x['lane']} / {x['trait']} | {r['rawSplitHalf']:.4f} | {r['incremental']:.4f} | {r['calibrationSlope']:.4f} | {x['highMedium']['n']} / {x['totalSymbols']} | {x['highMediumPeerDifferentiated']['n']} |")
 lines+=['','23は日足14＋分足9のlane別判定数。calibration以外の旧Gateは通過。global/reverseの符号とA/B raw中心化符号一致はJSON。B peer残差が保存されていないため、後者を個別銘柄のpeer残差sign persistenceとは呼ばない。','',
 '補正可能性は仮説。観測したB slopeを掛けて同じBで合格とはしない。A内の有限方式と別時間Development区間で校正・誤差・driftを検証する必要がある。今回は補正fit/USABLE昇格なし。','',
 '## 4–5. Trait数分布と統合','',
 '| 対象（60 window） | 0 | 1–2 | 3–5 | 6–10 | 11+ |','|---|---:|---:|---:|---:|---:|']
 for lane in ['daily','intraday']:
  for kind in ['available','hm']:lines.append('| '+lane+' '+kind+' | '+' | '.join(str(dist[lane]['60'][kind][k]) for k in ['0','1-2','3-5','6-10','11+'])+' |')
 for kind in ['available','hm']:lines.append('| archival union '+kind+' | '+' | '.join(str(integrated['60']['union'][kind][k]) for k in ['0','1-2','3-5','6-10','11+'])+' |')
 lines+=['',f"コード和集合{integrated['60']['union']['symbols']}、共通集合{integrated['60']['intersection']['symbols']}。同じtrait IDは重複カウントしない。推定値は混合しない。available=有限Profile、hm=USABLEかつHIGH/MEDIUM。WATCHはtrait数に含まない。",'',
 f"日足終端{integrated['endpointDates']['daily']}、分足終端{integrated['endpointDates']['intraday']}。統合は履歴上の和集合であり同時点のProfileではない。Reader未成立・銘柄別再現性未検証も含め、現在検証済みでEntry/EXITへ渡せる銘柄は0。性格が存在しないという意味ではなく引渡し条件未達。",'',
 '## 代表銘柄：保存されている知識','',
 'PDH confidence群とH+M trait数からコード順で機械選択。値はraw、peer差は変換後で単位が異なる。driftは保存済み指標、銘柄別時間再現性は未確認。']
 for ex in examples:
  lines+=['',f"### Code {ex['symbol']} — {ex['selection']}",'','| lane / trait | raw | peer差 | confidence | nEff / event sessions | drift |','|---|---:|---:|---|---|---|']
  for c in ex['records']:
   if c['globalStatus']!='USABLE':continue
   fmt=lambda z:'—' if z is None else f'{z:.4g}'
   lines.append(f"| {c['lane']} / {c['trait']} | {fmt(c['raw'])} | {fmt(c['peer_relative'])} | {c['confidence']} | {fmt(c['nEff'])} / {fmt(c['episodes'])} | {'UNKNOWN' if c['driftFlag'] is None else c['driftFlag']} |")
 lines+=['','## 層別coverageの根拠','',
 'A peer予測/係数/標準化パラメータの線形恒等式から共変量を復元。6式以上、末尾2式の検算、rank/条件数/残差/logVa参照値の検証を要求。識別不能座標はUNKNOWN。層は現在価格等ではなくA-period履歴層。']
 for lane in ['daily','intraday']:lines+=['',lane+': '+json.dumps(strata[lane]['counts'],ensure_ascii=False)]
 lines+=['','peer差ありは |posterior−peer prediction| > 1.96×posterior SD の探索的分類。prior fit不確実性や多重比較を完全に反映せず、銘柄別有意差証明ではない。','',
 '## 6. Sparse Dictionary','',
 'globalStatus=USABLEかつHIGH/MEDIUMのみ候補payload。LOW/INSUFFICIENTはabstain、WATCHは研究sidecar。definition hash、units/transform、nEff、SD/CI、drift、computed_throughを保持。時点・単位・Reader freshnessが未成立ならpayload全体を引渡し不可。confidenceラベルを新しい実用Gateに自動昇格しない。','',
 '## 7. 事前固定した修正仕様','',
 'correction-spec.jsonが正本。Pullbackは同一session/phaseの連続5m列で確認済み上昇impulse→直後の確認済み下落correctionを比率化。欠損/昼休みでreset、availabilityはcorrectionの確認時刻。旧trait不変、新registry候補のみ。','',
 'Readerはdaily.Date/barValueを明示adapterで正規化。完全に閉じた5本から5m barを作る。lastCompletedBarは現在phaseのfloor(t/5)*5と一致、最大staleness4分。昼休み・phase外・最新bar欠測はUNAVAILABLE。古いbarへfallbackしない。今回は仕様のみで実装/再測定なし。','',
 '## 8. NEW LONG Entry/EXITへ渡すまで','',
 '(1)有限のPullback/Reader修正実装と因果性/鮮度検証、(2)同時点Profileと単位の整合、(3)銘柄別/peer別時間再現性とconfidence校正のDevelopment検証、(4)仕様固定が必要。HIGH/MEDIUMは(3)の代用ではない。成立した次工程でNEW LONG Entry/EXITを再設計し、旧版微修正には戻さない。今回は作らずSTOP。','',
 '## 検証・境界','',
 'ci-receipt.jsonとregression/regression.jsonが実行正本。生成2回manifest一致、旧Evidence hash不変、focused testsと全回帰。新規provider取得0、raw再測定0、Common Holdout244/REPORT19/Validation/OOS/Fresh追加payloadアクセス0、Entry/EXIT trial0。過去Exposure維持、Safety9項目false、main未merge。','']
 (out/'REPORT-ja.md').write_text('\n'.join(lines))
 parts=['<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Ark Profile Coverage</title><style>body{font:16px system-ui,sans-serif;max-width:1100px;margin:32px auto;padding:0 18px;color:#172734;background:#f7fafb}table{border-collapse:collapse;width:100%;margin:20px 0}th,td{text-align:left;padding:10px;border-bottom:1px solid #d4dfe5}.scroll{overflow:auto}summary{padding:14px 0;cursor:pointer}</style><h1>Ark — 銘柄Profile coverage</h1><p>60-position snapshot · 標本精度の診断 · 引渡し未成立</p><div class="scroll"><table><tr><th>Lane / trait</th><th>全銘柄</th><th>HIGH</th><th>MEDIUM</th><th>LOW</th><th>INSUFFICIENT</th></tr>']
 for x in selected:
  if x['globalStatus']=='USABLE':parts.append('<tr><td>'+html.escape(x['lane']+'/'+x['trait'])+'</td><td>'+str(x['totalSymbols'])+'</td>'+''.join('<td>'+str(x['confidence'][s]['n'])+'</td>' for s in LEVELS)+'</tr>')
 parts+=['</table></div><h2>代表銘柄</h2><p>rawとpeer差は単位が異なり、日足・分足の終端も異なります。</p>']
 for ex in examples:
  parts+=['<details open><summary>Code '+html.escape(ex['symbol'])+' — '+html.escape(ex['selection'])+'</summary><div class="scroll"><table><tr><th>Lane / trait</th><th>raw</th><th>peer差</th><th>confidence</th><th>nEff</th><th>drift</th></tr>']
  for c in ex['records']:
   if c['globalStatus']=='USABLE':parts.append('<tr>'+''.join('<td>'+html.escape(str(clean(val)) if val is not None else 'UNKNOWN')+'</td>' for val in [c['lane']+'/'+c['trait'],c['raw'],c['peer_relative'],c['confidence'],c['nEff'],c['driftFlag']])+'</tr>')
  parts+=['</table></div></details>']
 parts+=['<p>Global USABLE ≠ 銘柄固有の時間再現性。HIGH/MEDIUM ≠ 売買可能。</p></html>']
 (out/'profile-coverage.html').write_text(''.join(parts))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);run(p.parse_args().output)
