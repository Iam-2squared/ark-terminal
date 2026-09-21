"""Phase57 State additional diagnostics v1.
Read-only diagnostics over saved G measurement. No definition changes, PnL, providers, or protected data.
"""
from __future__ import annotations
import argparse,csv,gzip,hashlib,json,math,statistics
from collections import Counter,defaultdict
from pathlib import Path

SEED="phase57-state-additional-diagnostics-v1-seed-20260921"
SAFETY={k:False for k in ("executionAllowed","brokerWriteAllowed","excelOrderWriteAllowed","rssOrderFunctionAllowed","liveTradingAllowed","paperTradingAllowed","automaticPromotionAllowed","productionUpdateAllowed","transmitted")}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
def read_jsonl_gz(p):
 with gzip.open(p,"rt",encoding="utf-8") as f:
  for line in f:
   if line.strip():yield json.loads(line)
def rel(a,b):
 if a>b:return "UP"
 if a<b:return "DOWN"
 return "EQ"
def signature(piv):
 hs=[p for p in piv if p.get("kind")=="HIGH"];ls=[p for p in piv if p.get("kind")=="LOW"]
 if len(hs)<2 or len(ls)<2:return None
 return f"H_{rel(hs[-1]['price'],hs[-2]['price'])}|L_{rel(ls[-1]['price'],ls[-2]['price'])}"
def q(v,qs=(.25,.5,.75)):
 a=sorted(v)
 if not a:return {str(x):None for x in qs}
 def one(x):
  z=(len(a)-1)*x;i=int(z);j=min(i+1,len(a)-1);f=z-i
  return a[i]*(1-f)+a[j]*f
 return {str(x):one(x) for x in qs}
def tband(m):
 return "OPEN_0900_1000" if m<600 else "AM_1000_1130" if m<690 else "PM_EARLY_1230_1400" if m<840 else "PM_LATE_1400_CLOSE"
def hhmm(s):h,m=map(int,s.split(":"));return h*60+m
def med(x):return statistics.median(x) if x else None
def main(a):
 root=Path(a.measurement);out=Path(a.output);out.mkdir(parents=True,exist_ok=False)
 # Verify saved measurement against its own manifest before diagnostics.
 manifest=json.loads((root/"manifest.json").read_text())
 bad=[n for n,h in manifest.items() if not (root/n).exists() or sha(root/n)!=h]
 if bad:raise SystemExit("MANIFEST_MISMATCH:"+",".join(bad[:5]))
 rows=[]
 with gzip.open(root/"checkpoints.csv.gz","rt",encoding="utf-8",newline="") as f:
  rows=list(csv.DictReader(f))
 raw_by_oid={};ctx_by_oid={}
 for p in sorted((root/"raw").glob("*.jsonl.gz")):
  for x in read_jsonl_gz(p):raw_by_oid.setdefault(x["opportunity"],[]).append(x)
 for p in sorted((root/"contexts").glob("*.jsonl.gz")):
  for x in read_jsonl_gz(p):ctx_by_oid[x["opportunity"]]=x
 # raw files are checkpoint records, not source minute input. Pull pivots/events/descriptors per checkpoint.
 keyraw={}
 for oid,xs in raw_by_oid.items():
  for x in xs:keyraw[(oid,x["asOfJST"][11:16])]=x
 # Input source has exact today/previous rows for diagnostic 4 and density.
 inputs={}
 for x in read_jsonl_gz(root/"inputs.jsonl.gz"):inputs[x["id"]]=x
 # Diagnostic 1 / 5 source D and all pivot>=4.
 d=[];all4=[]
 for r in rows:
  x=keyraw.get((r["opportunity"],r["asOf"]))
  if not x:continue
  piv=x["reference"]["state"].get("pivots",[])
  sig=signature(piv)
  if len(piv)>=4:all4.append((r,x,sig))
  if r["observation"]=="COMPLETE" and r["scaleStatus"]=="AVAILABLE" and len(piv)>=4 and not r["structure"]:
   d.append((r,x,sig))
 strict=[];desc=Counter()
 for r,x,sig in d:
  direction=bool(r["direction"])
  phase=bool(r["phase"])
  attrs=[z for z in r["attributes"].split("|") if z]
  chop="CHOPPINESS" in attrs
  other=bool([z for z in attrs if z!="CHOPPINESS"])
  lev=bool(x.get("levelEvents"))
  vw=bool(x.get("vwapRelations"))
  flags={"direction":direction,"phase":phase,"chop":chop,"otherAttributes":other,"levelEvent":lev,"vwapEvent":vw}
  for k,v in flags.items():desc[k]+=int(v)
  if not any(flags.values()):strict.append((r,x,sig))
 # Diagnostic 2 deterministic stratified sample: one checkpoint/opportunity, <=6/signature, diversify band/session by round-robin rank.
 candidates=defaultdict(list)
 for r,x,sig in d:
  token=hashlib.sha256((SEED+"|"+r["opportunity"]+"|"+r["asOf"]).encode()).hexdigest()
  candidates[sig].append((token,r,x))
 selected=[]
 for sig,xs in sorted(candidates.items()):
  xs=sorted(xs)
  # first keep unique opportunity; score favors unseen session/band dynamically, hash tie-break.
  pool=[];seen_o=set()
  for token,r,x in xs:
   if r["opportunity"] not in seen_o:pool.append((token,r,x));seen_o.add(r["opportunity"])
  chosen=[];ss=set();bb=set()
  while pool and len(chosen)<6:
   pool.sort(key=lambda z:(-(z[1]["session"] not in ss)-(tband(hhmm(z[1]["asOf"])) not in bb),z[0]))
   z=pool.pop(0);chosen.append(z);ss.add(z[1]["session"]);bb.add(tband(hhmm(z[1]["asOf"])))
  for token,r,x in chosen:selected.append({"signature":sig,"opportunity":r["opportunity"],"session":r["session"],"asOf":r["asOf"],"timeBand":tband(hhmm(r["asOf"])),"hashRank":token,"scale":r["scale"],"pivotN":r["pivotN"],"phase":r["phase"],"attributes":r["attributes"]})
 # Diagnostic 3 B time to next identified Structure.
 by_o=defaultdict(list)
 for r in rows:by_o[r["opportunity"]].append(r)
 bstats=defaultdict(list)
 for oid,xs in by_o.items():
  xs.sort(key=lambda z:int(z["elapsedActiveMinutes"]))
  inp=inputs[oid];today=inp["today"];sel=hhmm(xs[0]["selectorTime"])
  # observed density to asOf: regular raw minute starts whose end<=asOf / scheduled active minutes elapsed from day open through asOf.
  for i,r in enumerate(xs):
   if not(r["observation"]=="COMPLETE" and r["scaleStatus"]=="AVAILABLE" and not r["structure"] and int(r["pivotN"])<4):continue
   k=int(r["pivotN"]);asof=hhmm(r["asOf"])
   obs=sum(1 for z in today if ((540<=z[0]<690) or (750<=z[0]<925)) and z[0]+1<=asof)
   sched=sum(1 for t in list(range(541,691))+list(range(751,926)) if t<=asof)
   density=obs/sched if sched else 0
   nxt=next((z for z in xs[i+1:] if z["structure"]),None)
   dt=None if nxt is None else int(nxt["elapsedActiveMinutes"])-int(r["elapsedActiveMinutes"])
   bstats[k].append((density,dt))
 # quartiles globally for density.
 dens=[v[0] for vs in bstats.values() for v in vs];cuts=q(dens)
 def dq(v):
  return "Q1" if v<=cuts["0.25"] else "Q2" if v<=cuts["0.5"] else "Q3" if v<=cuts["0.75"] else "Q4"
 b_report={}
 for k,vs in sorted(bstats.items()):
  for label,sub in [("ALL",vs)]+[(qq,[z for z in vs if dq(z[0])==qq]) for qq in ("Q1","Q2","Q3","Q4")]:
   if not sub:continue
   dts=[z[1] for z in sub if z[1] is not None];qq=q(dts)
   b_report[f"pivot{k}/{label}"]={"n":len(sub),"resolved":len(dts),"resolvedRate":len(dts)/len(sub),"rightCensored":len(sub)-len(dts),"timeToNextStructureResolved":{"p25":qq["0.25"],"median":qq["0.5"],"p75":qq["0.75"]}}
 # Diagnostic 4 Opportunity-scale groups.
 scale_group={oid:ctx_by_oid[oid]["scale"]["status"] for oid in ctx_by_oid}
 opp_metrics=defaultdict(list)
 for oid,inp in inputs.items():
  g=scale_group.get(oid)
  if g not in ("AVAILABLE","SCALE_INSUFFICIENT"):continue
  today=inp["today"];prev=inp["previous"];selector=hhmm(inp["selectorAt"][11:16])
  reg=lambda z: (540<=z[0]<690) or (750<=z[0]<925)
  tr=[z for z in today if reg(z)];pr=[z for z in prev if reg(z)]
  open30=[z for z in tr if 540<=z[0]<570]
  pre=[z for z in tr if z[0]+1<=selector]
  ov=sum(z[6] for z in open30 if z[6] is not None);pv=sum(z[6] for z in pr if z[6] is not None)
  opp_metrics[g].append({"previousObserved1m":len(pr),"todayObserved1m":len(tr),"todayObservedToSelector":len(pre),"opening30Value":ov,"previousRegularValue":pv,"ratio":ov/pv if pv else None,"openingGtPrevious":bool(pv and ov>pv)})
 scale_report={}
 for g,xs in opp_metrics.items():
  def s(k):v=[z[k] for z in xs if z[k] is not None];return {"n":len(v),"median":med(v),"p25":q(v)["0.25"],"p75":q(v)["0.75"]}
  scale_report[g]={"opportunities":len(xs),"previousObserved1m":s("previousObserved1m"),"todayObserved1m":s("todayObserved1m"),"todayObservedToSelector":s("todayObservedToSelector"),"opening30Value":s("opening30Value"),"previousRegularValue":s("previousRegularValue"),"opening30OverPreviousValue":s("ratio"),"openingGtPreviousFullDayRate":sum(z["openingGtPrevious"] for z in xs)/len(xs)}
 # Diagnostic 5
 grid=defaultdict(Counter)
 for r,x,sig in all4:grid[r["structure"] or "UNIDENTIFIED"][sig]+=1
 result={"version":"phase57-state-additional-diagnostics-v1","sourceMeasurementFilesVerified":len(manifest),"sourceCheckpointN":len(rows),"diagnostic1":{"D":len(d),"descriptorAvailability":dict(desc),"strictResidual":len(strict),"strictResidualUniqueOpportunities":len({z[0]["opportunity"] for z in strict})},"diagnostic2":{"seed":SEED,"selectedN":len(selected),"uniqueOpportunities":len({z["opportunity"] for z in selected}),"selected":selected},"diagnostic3":{"densityQuartiles":cuts,"groups":b_report},"diagnostic4":scale_report,"diagnostic5":{k:dict(v) for k,v in grid.items()},"guards":{"definitionChanges":0,"thresholdSearch":0,"providerRequests":0,"protectedDataOpened":0,"pnlUsed":False,"causalRecognition":False,"signal":False,"buyWait":False},"safety":SAFETY,"stop":True}
 dump(out/"diagnostics.json",result)
 # Compact deterministic CSV for chart selection. Rendering is separate and must use source raw input.
 with (out/"chart-sample.csv").open("w",newline="",encoding="utf-8") as f:
  w=csv.DictWriter(f,fieldnames=list(selected[0]) if selected else ["signature"]);w.writeheader();w.writerows(selected)
 print(json.dumps({"D":len(d),"strictResidual":len(strict),"chartN":len(selected),"B":sum(len(v) for v in bstats.values()),"scale":{k:len(v) for k,v in opp_metrics.items()}},sort_keys=True))
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--measurement",required=True);p.add_argument("--output",required=True);main(p.parse_args())
