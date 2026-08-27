const DATA_URL="https://raw.githubusercontent.com/Iam-2squared/ark-terminal/automation/home-paper-equity-data/data/home/paper-equity.json";
const yen=value=>new Intl.NumberFormat("ja-JP",{style:"currency",currency:"JPY",maximumFractionDigits:0}).format(Number(value));
const pct=value=>{const n=Number(value);return `${n>=0?"+":""}${n.toFixed(2)}%`;};

function ensureSplitStyles(){
  if(document.getElementById("paperEquitySplitStyles"))return;
  const style=document.createElement("style");
  style.id="paperEquitySplitStyles";
  style.textContent=`
    .paperEquitySplit{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px}
    .paperEquitySplitCard{padding:9px 10px;border:1px solid rgba(148,163,184,.10);border-radius:8px;background:rgba(255,255,255,.012)}
    .paperEquitySplitCard span{display:block;color:#60758f;font-size:8px;font-weight:900;letter-spacing:.09em}
    .paperEquitySplitCard strong{display:block;margin-top:4px;color:#dbeafe;font-size:13px;font-variant-numeric:tabular-nums}
    .paperEquitySplitCard.v3{border-color:rgba(251,191,36,.22)}
    .paperEquitySplitCard.v3 strong{color:#f3cf72}
    .paperEquitySplitMeta{grid-column:1/-1;color:#6f839c;font-size:8px;line-height:1.55}
  `;
  document.head.appendChild(style);
}

async function load(){
  const panel=document.querySelector(".paperPortfolio");
  if(!panel)return;
  const response=await fetch(DATA_URL,{cache:"no-store"});
  if(!response.ok)throw new Error(`equity split data ${response.status}`);
  const data=await response.json();
  const d50=data.series?.DYNAMIC_50?.at(-1);
  const v3=data.series?.EXIT_V3?.at(-1);
  const meta=data.latestExitV3;
  const label=panel.querySelector(".portfolioValueLabel");
  if(label)label.textContent="D50 CURRENT EQUITY";
  const identity=panel.querySelector(".portfolioIdentity");
  if(!identity||identity.querySelector(".paperEquitySplit"))return;
  const wrap=document.createElement("div");
  wrap.className="paperEquitySplit";
  wrap.innerHTML=`
    <div class="paperEquitySplitCard"><span>D50 ENTRY EQUITY</span><strong>${d50?yen(d50.equityJpy):"—"}</strong></div>
    <div class="paperEquitySplitCard v3"><span>EXIT V3 RESEARCH EQUITY</span><strong>${v3?yen(v3.equityJpy):"—"}</strong></div>
    <div class="paperEquitySplitMeta">EXIT V3 diagnostic: ${meta?`Net ${pct(meta.afterCostNetPct)} · PF ${Number(meta.profitFactor).toFixed(2)} · n=${meta.pairedCount}`:"—"} · fresh OOS pending</div>`;
  identity.appendChild(wrap);
}

ensureSplitStyles();
load().catch(error=>console.warn("D50 / EXIT v3 equity split could not be loaded:",error));
