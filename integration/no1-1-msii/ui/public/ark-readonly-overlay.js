(() => {
  'use strict';

  const MODEL_URL = '/api/ui-read-model';
  const POLL_MS = 3000;
  const MUTATION_SELECTORS = '.preflightButton,.killButton,.stageButton,.cancelOrder';
  const state = { model: null, error: null, scheduled: false };

  const style = document.createElement('style');
  style.textContent = `
    #ark-readonly-screen{display:block!important}
    .ark-ro-state{margin:0 0 22px;padding:14px 17px;border:1px solid #4b4d52;background:#1c1e23;border-radius:10px;display:flex;justify-content:space-between;gap:14px;align-items:center}
    .ark-ro-state.bad{border-color:#765054;background:#35252a}.ark-ro-state.warn{border-color:#6d5a3d;background:#30291f}
    .ark-ro-state strong{font-size:11px}.ark-ro-state span,.ark-ro-note{font-size:9px;color:#a2a5ae}
    .ark-ro-empty{padding:30px 22px;border-top:1px solid #2c2e33;color:#a2a5ae;font-size:11px}.ark-ro-empty strong{display:block;color:#f1f2f4;font-size:13px;margin-bottom:8px}
    .ark-ro-check{display:grid;grid-template-columns:minmax(0,1fr) minmax(100px,auto) 20px;gap:12px;align-items:center;min-height:48px;border-top:1px solid #2c2e33;font-size:10px}.ark-ro-check strong,.ark-ro-check i{text-align:right}.ark-ro-check i{font-style:normal}
    .ark-ro-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.ark-ro-lineage{font-family:"Geist Mono",monospace;font-size:9px;overflow-wrap:anywhere;color:#a2a5ae}
    .ark-ro-owner{display:block;font-size:8px;color:#a2a5ae;margin-top:4px}.ark-ro-note{margin-top:18px;line-height:1.75}
    @media(max-width:760px){.ark-ro-grid{grid-template-columns:1fr}.ark-ro-check{grid-template-columns:1fr auto 16px}}
  `;
  document.head.appendChild(style);

  const esc = v => String(v ?? '').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');
  const finite = v => typeof v === 'number' && Number.isFinite(v);
  const yen = v => finite(v) ? `¥${Math.round(v).toLocaleString('ja-JP')}` : '--';
  const num = v => finite(v) ? v.toLocaleString('ja-JP') : '--';
  const txt = (v, fallback='--') => v === null || v === undefined || v === '' ? fallback : String(v);
  const sum = (rows, key, predicate=()=>true) => { let n=0, seen=false; for (const row of rows||[]) if (predicate(row) && finite(row?.[key])) { n += row[key]; seen=true; } return seen ? n : null; };
  const owner = v => v === 'ARK_MANAGED' ? 'Ark管理' : v === 'EXTERNAL' ? '個人 / 外部' : '所有区分不明';
  const badge = v => { const s=txt(v,'UNAVAILABLE'); const c=/BLOCKED|ERROR|INVALID|STALE|UNKNOWN/.test(s)?'negative':/LOCKED|FRESH|PASS|CLEAR|AVAILABLE/.test(s)?'positive':'warning'; return `<span class="badge ${c}">${esc(s)}</span>`; };

  function readiness(m) {
    const r=txt(m?.system?.tradeReadiness,'UNAVAILABLE'), f=txt(m?.source?.freshness?.state,'UNAVAILABLE');
    return `<div class="ark-ro-state ${r==='BLOCKED'?'bad':r==='LOCKED_READY'?'warn':''}"><strong>${esc(r)}</strong><span>Source ${esc(f)} · READ ONLY · 注文送信なし</span></div>`;
  }

  function positionRows(m) {
    const rows=m?.positions||[];
    if (!rows.length) return '<div class="ark-ro-empty"><strong>現在の保有はありません</strong><span>実口座スナップショット上の保有は0件です。</span></div>';
    return `<div class="positionsList">${rows.map(row=>{
      const mv=finite(row.marketValue)?row.marketValue:(finite(row.marketPrice)&&finite(row.quantity)?row.marketPrice*row.quantity:null);
      const pnl=row.unrealizedPnl, cls=finite(pnl)?(pnl>=0?'positive':'negative'):'';
      return `<div class="positionRow"><span class="stockMark">${esc(txt(row.symbol).slice(0,2))}</span><span class="stockName"><strong>${esc(txt(row.name,txt(row.symbol)))}</strong><small>${esc(txt(row.symbol))} · ${esc(num(row.quantity))}株 · ${esc(owner(row.ownership))}</small><span class="ark-ro-owner">READ ONLY / ${esc(txt(row.accountType,'口座区分--'))}</span></span><span class="positionValue"><strong>${yen(mv)}</strong><small class="${cls}">${yen(pnl)}</small></span>${badge(row.ownership||'UNKNOWN')}</div>`;
    }).join('')}</div>`;
  }

  function footer(m) { return `<footer class="healthbar"><span>${esc(txt(m?.source?.freshness?.state,'UNAVAILABLE'))}</span><div><span>MSII/RSS READ ONLY</span><span>CASH LONG ONLY</span><span>ORDERS DISABLED</span></div><small>LOCAL READ ONLY · 実注文なし</small></footer>`; }

  function home(m) {
    const rows=m.positions||[], invested=sum(rows,'marketValue'), pnl=sum(rows,'unrealizedPnl');
    const counts={ark:rows.filter(x=>x.ownership==='ARK_MANAGED').length, ext:rows.filter(x=>x.ownership==='EXTERNAL').length, unk:rows.filter(x=>x.ownership==='UNKNOWN').length};
    const intent=m.home?.activeIntent, lineage=m.home?.activeIntentLineage;
    const signal=intent?`<div class="signalName"><span>${esc(txt(intent.symbol))} · READ ONLY</span><h2>${esc(txt(intent.side))} ${esc(num(intent.quantity))}株</h2><p>${esc(txt(intent.positionEffect))}</p></div>${badge(m.system?.pipeline?.state)}<p class="ark-ro-lineage">${esc(txt(lineage?.strategyId))} / ${esc(txt(lineage?.sourceIntentId))}</p>`:'<div class="signalName"><span>ACTIVE INTENT</span><h2>NO ACTIVE INTENT</h2><p>現在、表示可能な注文Intentはありません。</p></div>';
    return `${readiness(m)}<section class="equityPanel"><div class="equityTop"><div><span class="metricLabel">TOTAL ASSETS</span><h2 class="assetValue">--</h2><span class="gainLabel">未接続 / 推定しません</span></div><span class="demoBadge">REAL ACCOUNT · READ ONLY</span></div><p class="ark-ro-note">検証済みTotal Assets feedがないため推定表示しません。</p><div class="accountStrip"><div class="metric"><span>Buying Power</span><strong>${yen(m.home?.buyingPower)}</strong><small>${esc(txt(m.home?.buyingPowerState))}</small></div><div class="metric"><span>Invested</span><strong>${yen(invested)}</strong><small>取得可能分のみ</small></div><div class="metric"><span>Unrealized P/L</span><strong>${yen(pnl)}</strong><small>取得可能分のみ</small></div><div class="metric"><span>Positions</span><strong>${rows.length}</strong><small>${counts.ark} Ark / ${counts.ext} External / ${counts.unk} Unknown</small></div></div></section><div class="homeLower"><section class="panel holdingsPanel"><div class="panelTitle"><h2>Positions <span>${rows.length}</span></h2><span class="muted">REAL ACCOUNT</span></div>${positionRows(m)}</section><section class="signalPanel"><div class="signalTop"><span>ACTIVE INTENT</span><span class="signalIndex">RO</span></div>${signal}<p class="ark-ro-note">表示専用。注文・取消・Kill Switch操作は接続されていません。</p></section></div>${footer(m)}`;
  }

  function selector(m) { return `${readiness(m)}<section class="panel"><div class="panelTitle"><h2>Selector</h2>${badge(m.selector?.state)}</div><div class="ark-ro-empty"><strong>Selector候補はまだUI Read Modelへ未接続</strong><span>実戦略の候補・Score・理由をダミー値で代用しません。</span></div><p class="panelNote">Selector / Entry / EXIT / Allocation の仕様はこのUIから変更できません。</p></section>${footer(m)}`; }

  function positions(m) {
    const rows=m.positions||[];
    return `${readiness(m)}<div class="summaryStrip"><div class="metric"><span>MARKET VALUE</span><strong>${yen(sum(rows,'marketValue'))}</strong></div><div class="metric"><span>UNREALIZED P/L</span><strong>${yen(sum(rows,'unrealizedPnl'))}</strong></div><div class="metric"><span>ARK MANAGED</span><strong>${yen(sum(rows,'marketValue',r=>r.ownership==='ARK_MANAGED'))}</strong></div><div class="metric"><span>EXTERNAL</span><strong>${yen(sum(rows,'marketValue',r=>r.ownership==='EXTERNAL'))}</strong></div></div><section class="panel holdingsPanel"><div class="panelTitle"><h2>実口座保有 <span>${rows.length}</span></h2><span class="muted">READ ONLY</span></div>${positionRows(m)}<p class="panelNote">Ownership baselineが未設定ならUNKNOWNのまま表示し、Ark管理と推定しません。</p></section>${footer(m)}`;
  }

  function orders(m) {
    const os=m.orders||[], xs=m.executions||[];
    const list=(rows,execution=false)=>rows.length?rows.map(r=>`<div class="orderRow"><span class="side">${execution?esc(txt(r.side,'FILL')):'RO'}</span><span class="stockName"><strong>${esc(txt(r.symbol))}</strong><small>${esc(num(r.quantity))}株${execution?` × ${yen(r.price)}`:` · filled ${esc(num(r.filledQuantity))}`}</small></span><span class="orderTime mono">${esc(txt(execution?r.executionDate:r.orderNumber))}</span>${badge(execution?'約定':r.status)}</div>`).join(''):'<div class="ark-ro-empty"><strong>0件</strong><span>現在のRead Modelに該当データはありません。</span></div>';
    return `${readiness(m)}<section class="panel"><div class="panelTitle"><h2>Orders</h2><span class="muted">READ ONLY</span></div>${list(os)}<div class="panelTitle" style="margin-top:28px"><h2>Executions</h2><span class="muted">READ ONLY</span></div>${list(xs,true)}<p class="panelNote">注文送信・取消は提供しません。</p></section>${footer(m)}`;
  }

  function performance(m) { return `${readiness(m)}<section class="panel"><div class="panelTitle"><h2>Performance</h2>${badge(m.performance?.state)}</div><div class="ark-ro-empty"><strong>実績集計は未接続</strong><span>日次 / 週次 / 月次P/L、Win Rate、PF、MFE/MAEは検証済み実データが接続されるまで表示しません。</span></div><p class="panelNote">デモの損益・勝率は実運用画面には表示しません。</p></section>${footer(m)}`; }

  function check(label,value,good=null) { const c=good===true?'positive':good===false?'negative':'warning'; return `<div class="ark-ro-check"><span>${esc(label)}</span><strong class="${c}">${esc(txt(value))}</strong><i class="${c}">${good===true?'✓':good===false?'!':'·'}</i></div>`; }

  function system(m) {
    const f=m.source?.freshness?.state, age=m.source?.freshness?.ageSeconds, bridge=m.localBridge, err=bridge?.refresh?.lastError;
    return `${readiness(m)}<section class="systemOverview"><div><span class="statusOrbit ${m.system?.tradeReadiness==='BLOCKED'?'bad':''}">⊙</span><h2>${esc(txt(m.system?.health))}</h2><p>表示経路はRead-only。発注権限とは分離されています。</p></div><button class="preflightButton" disabled>READ ONLY</button><button class="killButton" disabled><span>Kill Switch</span><strong>${esc(txt(m.system?.runtimeSafety?.killSwitchLatched,'UNKNOWN'))}</strong><i></i></button></section><div class="systemGrid"><section class="panel"><div class="panelTitle"><h2>Connections & Data</h2><span class="muted">REAL SNAPSHOT</span></div>${check('Source Schema',m.source?.schemaValid?'VALID':'INVALID',m.source?.schemaValid===true)}${check('Snapshot Freshness',finite(age)?`${f} · ${age.toFixed(1)}s`:f,f==='FRESH')}${check('Account / RSS Safety',m.safety?.state,m.safety?.state==='LOCKED')}${check('Buying Power',yen(m.home?.buyingPower),finite(m.home?.buyingPower))}${check('Local Bridge',bridge?.loopbackOnly?'127.0.0.1 ONLY':'UNAVAILABLE',bridge?.loopbackOnly===true)}${check('Refresh Loop',err?'ERROR':bridge?.refresh?.enabled?'ACTIVE':'MANUAL',err?false:null)}${err?`<p class="ark-ro-note negative">${esc(err)}</p>`:''}</section><section class="panel"><div class="panelTitle"><h2>Safety & Reconciliation</h2><span class="muted">FAIL CLOSED</span></div>${check('Reconciliation',m.system?.reconciliation?.state,m.system?.reconciliation?.state==='RECONCILIATION_PASS'?true:null)}${check('Ownership Baseline',m.system?.ownership?.state,m.system?.ownership?.state==='AVAILABLE'?true:null)}${check('G6-G10 Pipeline',m.system?.pipeline?.state,m.system?.pipeline?.state==='LOCKED_READY'?true:m.system?.pipeline?.state==='BLOCKED'?false:null)}${check('Runtime Safety',m.system?.runtimeSafety?.state,m.system?.runtimeSafety?.state==='CLEAR'?true:m.system?.runtimeSafety?.state==='BLOCKED'?false:null)}${check('Cash Long Lock','LOCKED',true)}${check('Margin / Short','DISABLED',true)}</section><section class="panel"><div class="panelTitle"><h2>Read-only Boundary</h2><span class="muted">NO MUTATIONS</span></div>${['orderSubmit','orderCancel','killSwitchChange','strategyEdit','brokerWrite','excelOrderWrite','rssOrderFunction'].map(k=>check(k,String(m.mutationCapabilities?.[k]),m.mutationCapabilities?.[k]===false)).join('')}</section><section class="panel"><div class="ark-ro-empty"><strong>Risk Limit feedは未接続</strong><span>Daily Loss / Max Positions / Max Order / Capital Usageをデモ値で代用しません。</span></div></section></div>${footer(m)}`;
  }

  function unavailable(message) { return `<div class="ark-ro-state bad"><strong>READ MODEL UNAVAILABLE</strong><span>${esc(message||'waiting for local read-only model')}</span></div><section class="panel"><div class="ark-ro-empty"><strong>実口座表示を停止しています</strong><span>ローカルRead Modelを取得できるまでダミーデータは表示しません。</span></div></section>`; }

  function markup(screen,m) {
    if (!m) return unavailable(state.error);
    switch (screen) {
      case 'HOME': return home(m);
      case 'SELECTOR': return selector(m);
      case 'POSITIONS': return positions(m);
      case 'ORDERS': return orders(m);
      case 'PERFORMANCE': return performance(m);
      case 'SYSTEM': return system(m);
      default: return unavailable(`UNKNOWN SCREEN: ${screen}`);
    }
  }

  function screen() { return (document.querySelector('.sectionLabel')?.textContent||location.hash.slice(1)||'HOME').trim().toUpperCase(); }

  function chrome(m) {
    const b=document.querySelector('.topbar .demoBadge'); if (b && b.textContent!=='READ ONLY') b.textContent='READ ONLY';
    const s=document.querySelector('.demoStamp'); if (s && s.textContent!=='LOCAL READ ONLY') s.textContent='LOCAL READ ONLY';
    const r=document.querySelector('.runStatus'); if (r) { const ok=m?.source?.freshness?.state==='FRESH'&&m?.safety?.state==='LOCKED'; r.textContent=ok?'● READ ONLY':'● BLOCKED'; r.classList.toggle('positive',ok); r.classList.toggle('warning',!ok); }
    document.querySelectorAll(MUTATION_SELECTORS).forEach(button => { button.disabled = true; button.setAttribute('aria-disabled','true'); });
  }

  function render() {
    state.scheduled=false;
    chrome(state.model);
    const main=document.getElementById('main'); if (!main) return;
    const heading=Array.from(main.children).find(x=>x.classList?.contains('screenHeading'));
    for (const child of Array.from(main.children)) { if (child===heading || child.id==='ark-readonly-screen') continue; child.style.display='none'; child.setAttribute('aria-hidden','true'); }
    let mount=document.getElementById('ark-readonly-screen');
    if (!mount || mount.parentElement!==main) { mount=document.createElement('div'); mount.id='ark-readonly-screen'; if (heading?.nextSibling) main.insertBefore(mount,heading.nextSibling); else main.appendChild(mount); }
    const sig=`${screen()}|${state.model?.generatedAt||'none'}|${state.model?.source?.freshness?.state||''}|${state.error||''}`;
    if (mount.dataset.signature!==sig) { mount.dataset.signature=sig; mount.innerHTML=markup(screen(),state.model); }
  }

  function schedule(delay=0) { if (state.scheduled) return; state.scheduled=true; window.setTimeout(render,delay); }

  async function poll() {
    try {
      const response=await fetch(MODEL_URL,{method:'GET',cache:'no-store',credentials:'same-origin',headers:{Accept:'application/json','X-Ark-Read-Only':'true'}});
      const body=await response.json();
      if (!response.ok || body?.schemaId!=='ARK_TERMINAL_UI_READ_MODEL_V1' || body?.readOnly!==true) throw new Error(body?.code||body?.message||`HTTP_${response.status}`);
      state.model=body; state.error=null;
    } catch (error) { state.model=null; state.error=`${error?.name||'Error'}: ${error?.message||error}`; }
    schedule();
  }

  window.addEventListener('hashchange',()=>schedule(30));
  poll();
  window.setInterval(poll,POLL_MS);
  schedule(30);
})();
