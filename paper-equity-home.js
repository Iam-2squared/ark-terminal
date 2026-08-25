const LOCAL_DATA_URL = "./data/home/paper-equity.json";
const REMOTE_DATA_URL = "https://raw.githubusercontent.com/Iam-2squared/ark-terminal/automation/home-paper-equity-data/data/home/paper-equity.json";
const DEFAULT_VARIANT = "DYNAMIC_50";

function ensureStyles(){
  if(document.getElementById("paperEquityHomeStyles")) return;
  const style=document.createElement("style");
  style.id="paperEquityHomeStyles";
  style.textContent=`
    .paperPortfolio .paperEquityChart{position:absolute;inset:0;width:100%;height:100%;z-index:2;overflow:visible}
    .paperPortfolio .paperEquityChart .axis{stroke:rgba(148,163,184,.10);stroke-width:1}
    .paperPortfolio .paperEquityChart .line{fill:none;stroke-width:2;vector-effect:non-scaling-stroke}
    .paperPortfolio .paperEquityChart .d30{stroke:#60a5fa}.paperPortfolio .paperEquityChart .d40{stroke:#22d3ee}.paperPortfolio .paperEquityChart .d50{stroke:#a78bfa}
    .paperPortfolio .paperEquityChart .dot{stroke-width:0}
    .paperPortfolio .paperEquityChart .dot.d30{fill:#60a5fa}.paperPortfolio .paperEquityChart .dot.d40{fill:#22d3ee}.paperPortfolio .paperEquityChart .dot.d50{fill:#a78bfa}
    .paperEquityLegend{position:absolute;left:12px;right:12px;bottom:10px;z-index:3;display:flex;gap:12px;flex-wrap:wrap;color:#6f839c;font-size:8px;font-weight:800;letter-spacing:.06em}
    .paperEquityLegend span{display:inline-flex;align-items:center;gap:5px}.paperEquityLegend i{width:7px;height:7px;border-radius:50%;display:inline-block}
    .paperEquityLegend .d30{background:#60a5fa}.paperEquityLegend .d40{background:#22d3ee}.paperEquityLegend .d50{background:#a78bfa}
    .paperEquityMeta{position:absolute;left:12px;top:10px;z-index:3;color:#50647c;font-size:8px;letter-spacing:.06em}
    .paperPortfolio .portfolioStatusLine strong.ready{color:#89e8f8}
    .paperEquityVariants{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}
    .paperEquityPill{padding:4px 6px;border:1px solid rgba(148,163,184,.10);border-radius:6px;color:#7890aa;font-size:8px;font-variant-numeric:tabular-nums}
  `;
  document.head.appendChild(style);
}

async function fetchData(){
  for(const url of [REMOTE_DATA_URL,LOCAL_DATA_URL]){
    try{
      const response=await fetch(url,{cache:"no-store"});
      if(!response.ok) continue;
      const data=await response.json();
      if(data?.mode==="ENTRY_ONLY_RESEARCH_EQUITY") return data;
    }catch{}
  }
  throw new Error("Entry-only equity data unavailable");
}

function yen(value){
  return new Intl.NumberFormat("ja-JP",{style:"currency",currency:"JPY",maximumFractionDigits:0}).format(Number(value));
}
function pct(value){
  const n=Number(value); return `${n>=0?"+":""}${n.toFixed(2)}%`;
}
function labelDate(value){
  const [,m,d]=String(value).split("-"); return `${Number(m)}/${Number(d)}`;
}

function buildPolyline(points,min,max,width=1000,height=260){
  if(!points.length) return "";
  const padX=34,padY=28,range=Math.max(1,max-min);
  return points.map((p,i)=>{
    const x=points.length===1?width/2:padX+i*(width-padX*2)/(points.length-1);
    const y=height-padY-((Number(p.equityJpy)-min)/range)*(height-padY*2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
}

function renderChart(container,data){
  const variants=["DYNAMIC_30","DYNAMIC_40","DYNAMIC_50"].filter(v=>Array.isArray(data.series?.[v]));
  const values=variants.flatMap(v=>data.series[v].map(p=>Number(p.equityJpy))).filter(Number.isFinite);
  const min=Math.min(...values),max=Math.max(...values);
  const classFor={DYNAMIC_30:"d30",DYNAMIC_40:"d40",DYNAMIC_50:"d50"};
  const lines=variants.map(v=>`<polyline class="line ${classFor[v]}" points="${buildPolyline(data.series[v],min,max)}"></polyline>`).join("");
  const dots=variants.map(v=>data.series[v].map((p,i,arr)=>{
    const coords=buildPolyline(arr,min,max).split(" ")[i].split(",");
    return `<circle class="dot ${classFor[v]}" cx="${coords[0]}" cy="${coords[1]}" r="4"></circle>`;
  }).join("")).join("");
  const latestDate=variants.map(v=>data.series[v].at(-1)?.date).filter(Boolean).sort().at(-1)??"—";
  container.innerHTML=`
    <svg class="paperEquityChart" viewBox="0 0 1000 260" preserveAspectRatio="none" aria-label="Entry-only research equity curve">
      <line class="axis" x1="34" y1="232" x2="966" y2="232"></line>
      ${lines}${dots}
    </svg>
    <div class="paperEquityMeta">START ${yen(data.startingCapitalJpy)} · LATEST ${labelDate(latestDate)}</div>
    <div class="paperEquityLegend"><span><i class="d30"></i>D30</span><span><i class="d40"></i>D40</span><span><i class="d50"></i>D50 FULL PREFIX</span></div>`;
}

function render(data){
  const panel=document.querySelector(".paperPortfolio");
  if(!panel) return;
  const series=data.series?.[DEFAULT_VARIANT]??[];
  const latest=series.at(-1);
  const previous=series.at(-2)??{equityJpy:data.startingCapitalJpy};
  if(!latest) return;

  const value=panel.querySelector(".portfolioValue");
  const sub=panel.querySelector(".portfolioSubValue");
  const change=panel.querySelector(".portfolioChange");
  const chart=panel.querySelector(".portfolioChart");
  const stats=panel.querySelectorAll(".portfolioFooterStats strong");
  const statusText=panel.querySelector(".portfolioStatusLine span");
  const statusStrong=panel.querySelector(".portfolioStatusLine strong");

  if(value) value.textContent=yen(latest.equityJpy);
  if(sub) sub.textContent=`ENTRY-ONLY · ${DEFAULT_VARIANT.replace("_"," ")} (full precommitted prefix, not winner-selected)`;
  if(change){change.textContent=`DAILY ${pct(latest.dailyReturnPct)}`;change.style.color=Number(latest.dailyReturnPct)>=0?"#7dd3fc":"#fda4af";}
  if(chart) renderChart(chart,data);
  if(stats[0]) stats[0].textContent=yen(data.startingCapitalJpy);
  if(stats[1]) stats[1].textContent=yen(Number(latest.equityJpy)-Number(previous.equityJpy));
  if(stats[2]) stats[2].textContent=`${Number(latest.maxDrawdownPct??0).toFixed(2)}%`;
  if(statusText) statusText.textContent=`Formal Entry-only scorecard · ${latest.date} · ${latest.resolvedEntries} resolved · PF ${Number(latest.profitFactor??0).toFixed(2)}`;
  if(statusStrong){statusStrong.textContent="RESEARCH EQUITY";statusStrong.classList.add("ready");}

  const identity=panel.querySelector(".portfolioIdentity");
  if(identity&&!identity.querySelector(".paperEquityVariants")){
    const row=document.createElement("div");row.className="paperEquityVariants";
    for(const variant of ["DYNAMIC_30","DYNAMIC_40","DYNAMIC_50"]){
      const p=data.series?.[variant]?.at(-1); if(!p) continue;
      const pill=document.createElement("span");pill.className="paperEquityPill";
      pill.textContent=`${variant.replace("DYNAMIC_","D")} ${yen(p.equityJpy)} · ${pct(p.dailyReturnPct)}`;row.appendChild(pill);
    }
    identity.appendChild(row);
  }
}

export async function loadPaperEquityHome(){
  ensureStyles();
  try{render(await fetchData());}
  catch(error){console.warn("Paper Entry-only equity could not be loaded:",error);}
}

loadPaperEquityHome();
