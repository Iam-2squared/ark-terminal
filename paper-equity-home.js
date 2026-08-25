const LOCAL_DATA_URL = "./data/home/paper-equity.json";
const REMOTE_DATA_URL = "https://raw.githubusercontent.com/Iam-2squared/ark-terminal/automation/home-paper-equity-data/data/home/paper-equity.json";
const DEFAULT_VARIANT = "DYNAMIC_50";
const VARIANTS = ["DYNAMIC_30", "DYNAMIC_40", "DYNAMIC_50"];

function ensureStyles(){
  if(document.getElementById("paperEquityHomeStyles")) return;
  const style=document.createElement("style");
  style.id="paperEquityHomeStyles";
  style.textContent=`
    .paperPortfolio .portfolioChart{cursor:pointer}
    .paperPortfolio .paperEquityChart{position:absolute;inset:0;width:100%;height:100%;z-index:2;overflow:visible}
    .paperPortfolio .paperEquityChart .axis,.paperPortfolio .paperEquityChart .grid{stroke:rgba(148,163,184,.11);stroke-width:1;vector-effect:non-scaling-stroke}
    .paperPortfolio .paperEquityChart .grid{stroke-dasharray:3 5;opacity:.65}
    .paperPortfolio .paperEquityChart .axisLabel{fill:#60758f;font-size:22px;font-family:system-ui,sans-serif}
    .paperPortfolio .paperEquityChart .line{fill:none;stroke-width:2;vector-effect:non-scaling-stroke}
    .paperPortfolio .paperEquityChart .d30{stroke:#60a5fa}.paperPortfolio .paperEquityChart .d40{stroke:#22d3ee}.paperPortfolio .paperEquityChart .d50{stroke:#a78bfa}
    .paperPortfolio .paperEquityChart .dot{stroke-width:0}
    .paperPortfolio .paperEquityChart .dot.d30{fill:#60a5fa}.paperPortfolio .paperEquityChart .dot.d40{fill:#22d3ee}.paperPortfolio .paperEquityChart .dot.d50{fill:#a78bfa}
    .paperEquityLegend{position:absolute;left:54px;right:12px;bottom:8px;z-index:3;display:flex;gap:12px;flex-wrap:wrap;color:#6f839c;font-size:8px;font-weight:800;letter-spacing:.06em}
    .paperEquityLegend span{display:inline-flex;align-items:center;gap:5px}.paperEquityLegend i{width:7px;height:7px;border-radius:50%;display:inline-block}
    .paperEquityLegend .d30{background:#60a5fa}.paperEquityLegend .d40{background:#22d3ee}.paperEquityLegend .d50{background:#a78bfa}
    .paperEquityMeta{position:absolute;left:54px;top:8px;z-index:3;color:#50647c;font-size:8px;letter-spacing:.06em}
    .paperEquityOpen{position:absolute;right:10px;top:8px;z-index:4;padding:5px 8px;border:1px solid rgba(148,163,184,.12);border-radius:6px;background:rgba(4,11,20,.72);color:#89a4c0;font-size:8px;font-weight:800;text-decoration:none;letter-spacing:.06em}
    .paperEquityOpen:hover{color:#d7f6ff;border-color:rgba(34,211,238,.26)}
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
function compactYen(value){
  const n=Number(value);
  if(Math.abs(n)>=1000000) return `¥${(n/1000000).toFixed(2)}M`;
  if(Math.abs(n)>=1000) return `¥${Math.round(n/1000)}k`;
  return `¥${Math.round(n)}`;
}
function pct(value){
  const n=Number(value); return `${n>=0?"+":""}${n.toFixed(2)}%`;
}
function labelDate(value){
  const [,m,d]=String(value).split("-"); return `${Number(m)}/${Number(d)}`;
}
function monthLabel(value){
  const [y,m]=String(value).split("-"); return `${String(y).slice(2)}年${Number(m)}月`;
}

function withVisualLeadIn(points){
  if(!Array.isArray(points)||points.length===0) return [];
  const first=points[0];
  return [
    {...first,_visualLeadIn:true},
    {...first,_visualLeadIn:true},
    ...points,
  ];
}

function chartGeometry(points,min,max,width=1000,height=260){
  const pad={left:92,right:34,top:32,bottom:48};
  const range=Math.max(1,max-min);
  const innerWidth=width-pad.left-pad.right;
  const innerHeight=height-pad.top-pad.bottom;
  const coords=points.map((p,i)=>({
    x:points.length===1?pad.left+innerWidth/2:pad.left+i*innerWidth/(points.length-1),
    y:pad.top+(max-Number(p.equityJpy))*innerHeight/range,
  }));
  return {pad,coords,innerWidth,innerHeight};
}

function polyline(coords){
  return coords.map(p=>`${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
}

function renderChart(container,data){
  const variants=VARIANTS.filter(v=>Array.isArray(data.series?.[v])&&data.series[v].length);
  const visualSeries=Object.fromEntries(variants.map(v=>[v,withVisualLeadIn(data.series[v])]));
  const values=variants.flatMap(v=>data.series[v].map(p=>Number(p.equityJpy))).filter(Number.isFinite);
  if(!values.length) return;
  let min=Math.min(...values),max=Math.max(...values);
  const spread=Math.max(1000,max-min);
  min-=spread*.18; max+=spread*.18;
  const classFor={DYNAMIC_30:"d30",DYNAMIC_40:"d40",DYNAMIC_50:"d50"};
  const lines=variants.map(v=>{
    const {coords}=chartGeometry(visualSeries[v],min,max);
    return `<polyline class="line ${classFor[v]}" points="${polyline(coords)}"></polyline>`;
  }).join("");
  const dots=variants.map(v=>{
    const points=visualSeries[v],{coords}=chartGeometry(points,min,max);
    return points.map((p,i)=>p._visualLeadIn?"":`<circle class="dot ${classFor[v]}" cx="${coords[i].x.toFixed(1)}" cy="${coords[i].y.toFixed(1)}" r="4"></circle>`).join("");
  }).join("");
  const guide=[0,.5,1].map(r=>{
    const value=max-(max-min)*r;
    const y=32+(260-32-48)*r;
    return `<line class="grid" x1="92" y1="${y}" x2="966" y2="${y}"></line><text class="axisLabel" x="8" y="${y+7}">${compactYen(value)}</text>`;
  }).join("");
  const dates=variants.flatMap(v=>data.series[v].map(p=>p.date)).filter(Boolean).sort();
  const firstDate=dates[0],latestDate=dates.at(-1);
  const xLabels=firstDate?`<text class="axisLabel" x="92" y="248">${monthLabel(firstDate)}</text>${latestDate!==firstDate?`<text class="axisLabel" x="966" y="248" text-anchor="end">${monthLabel(latestDate)}</text>`:""}`:"";
  container.innerHTML=`
    <svg class="paperEquityChart" viewBox="0 0 1000 260" preserveAspectRatio="none" aria-label="Entry-only research equity curve">
      ${guide}
      <line class="axis" x1="92" y1="212" x2="966" y2="212"></line>
      <line class="axis" x1="92" y1="32" x2="92" y2="212"></line>
      ${xLabels}${lines}${dots}
    </svg>
    <div class="paperEquityMeta">START ${yen(data.startingCapitalJpy)} · LATEST ${labelDate(latestDate)}</div>
    <a class="paperEquityOpen" href="./paper-equity.html" aria-label="仮想口座資産推移を拡大表示">EXPAND ↗</a>
    <div class="paperEquityLegend"><span><i class="d30"></i>D30</span><span><i class="d40"></i>D40</span><span><i class="d50"></i>D50 FULL PREFIX</span></div>`;
  container.addEventListener("click",event=>{
    if(event.target.closest("a")) return;
    globalThis.location.href="./paper-equity.html";
  },{once:true});
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
    for(const variant of VARIANTS){
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
