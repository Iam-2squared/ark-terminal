const LOCAL_DATA_URL = "./data/home/paper-equity.json";
const REMOTE_DATA_URL = "https://raw.githubusercontent.com/Iam-2squared/ark-terminal/automation/home-paper-equity-data/data/home/paper-equity.json";
const VARIANTS = ["DYNAMIC_30", "DYNAMIC_40", "DYNAMIC_50"];

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
  const n=Number(value);return `${n>=0?"+":""}${n.toFixed(2)}%`;
}
function monthLabel(value){
  const [y,m]=String(value).split("-");return `${y}/${String(Number(m)).padStart(2,"0")}`;
}
function withLead(points){
  if(!points?.length) return [];
  return [{...points[0],_lead:true},{...points[0],_lead:true},...points];
}
function geometry(points,min,max,width=1400,height=720){
  const pad={left:118,right:42,top:46,bottom:72};
  const range=Math.max(1,max-min),innerW=width-pad.left-pad.right,innerH=height-pad.top-pad.bottom;
  return points.map((p,i)=>({
    x:pad.left+(points.length===1?innerW/2:i*innerW/(points.length-1)),
    y:pad.top+(max-Number(p.equityJpy))*innerH/range,
  }));
}
function compact(value){
  const n=Number(value);
  if(Math.abs(n)>=1000000)return `¥${(n/1000000).toFixed(2)}M`;
  if(Math.abs(n)>=1000)return `¥${Math.round(n/1000)}k`;
  return `¥${Math.round(n)}`;
}
function render(data){
  const shell=document.getElementById("equityChartShell");
  const summary=document.getElementById("equitySummary");
  const variants=VARIANTS.filter(v=>data.series?.[v]?.length);
  const values=variants.flatMap(v=>data.series[v].map(p=>Number(p.equityJpy))).filter(Number.isFinite);
  let min=Math.min(...values),max=Math.max(...values);
  const spread=Math.max(1000,max-min);min-=spread*.2;max+=spread*.2;
  const width=1400,height=720;
  const classes={DYNAMIC_30:"d30",DYNAMIC_40:"d40",DYNAMIC_50:"d50"};
  const colors={d30:"#60a5fa",d40:"#22d3ee",d50:"#a78bfa"};
  const guides=Array.from({length:6},(_,i)=>{
    const r=i/5,y=46+(height-46-72)*r,value=max-(max-min)*r;
    return `<line x1="118" y1="${y}" x2="1358" y2="${y}" stroke="rgba(148,163,184,.10)" stroke-dasharray="4 7"/><text x="18" y="${y+7}" fill="#60758f" font-size="20">${compact(value)}</text>`;
  }).join("");
  const lines=variants.map(v=>{
    const pts=withLead(data.series[v]);
    const coords=geometry(pts,min,max,width,height);
    const points=coords.map(p=>`${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
    const dots=pts.map((p,i)=>p._lead?"":`<circle cx="${coords[i].x}" cy="${coords[i].y}" r="5" fill="${colors[classes[v]]}"/>`).join("");
    return `<polyline points="${points}" fill="none" stroke="${colors[classes[v]]}" stroke-width="3" vector-effect="non-scaling-stroke"/>${dots}`;
  }).join("");
  const dates=variants.flatMap(v=>data.series[v].map(p=>p.date)).filter(Boolean).sort();
  const first=dates[0],last=dates.at(-1);
  const xLabels=first?`<text x="118" y="688" fill="#60758f" font-size="20">${monthLabel(first)}</text>${last!==first?`<text x="1358" y="688" text-anchor="end" fill="#60758f" font-size="20">${monthLabel(last)}</text>`:""}`:"";
  shell.innerHTML=`<svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="Entry-only research equity curve with monthly x axis and yen y axis">${guides}<line x1="118" y1="648" x2="1358" y2="648" stroke="rgba(148,163,184,.16)"/><line x1="118" y1="46" x2="118" y2="648" stroke="rgba(148,163,184,.16)"/>${xLabels}${lines}</svg>`;
  const d50=data.series?.DYNAMIC_50??[],latest=d50.at(-1),firstPoint=d50[0];
  summary.innerHTML=`
    <div><span>STARTING CAPITAL</span><strong>${yen(data.startingCapitalJpy)}</strong></div>
    <div><span>D50 CURRENT EQUITY</span><strong>${latest?yen(latest.equityJpy):"—"}</strong></div>
    <div><span>D50 TOTAL RETURN</span><strong>${latest?pct((Number(latest.equityJpy)/Number(data.startingCapitalJpy)-1)*100):"—"}</strong></div>
    <div><span>PERIOD</span><strong>${firstPoint&&latest?`${monthLabel(firstPoint.date)} → ${monthLabel(latest.date)}`:"—"}</strong></div>`;
}

fetchData().then(render).catch(error=>{
  document.getElementById("equityChartShell").innerHTML=`<div style="padding:24px;color:#8aa0b8">資産推移データを読み込めませんでした。</div>`;
  console.error(error);
});
