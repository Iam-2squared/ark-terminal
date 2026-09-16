(() => {
  'use strict';

  const MODEL_URL = '/api/ui-read-model';
  const POLL_MS = 3000;
  const MUTATION_SELECTORS = '.preflightButton,.killButton,.stageButton,.cancelOrder';
  const state = { model: null, error: null, timer: null, queued: false };

  const css = `
    #ark-readonly-screen{display:block!important}
    .ark-ro-status{display:inline-flex;align-items:center;gap:7px;font-size:9px;letter-spacing:.06em}
    .ark-ro-dot{width:6px;height:6px;border-radius:50%;background:#91b7a3;display:inline-block}
    .ark-ro-dot.bad{background:#e29a9f}.ark-ro-dot.warn{background:#d8b884}
    .ark-ro-note{font-size:10px;color:#a2a5ae;line-height:1.75}
    .ark-ro-empty{padding:34px 24px;color:#a2a5ae;font-size:11px;border-top:1px solid #2c2e33}
    .ark-ro-empty strong{display:block;color:#f1f2f4;font-size:13px;margin-bottom:8px}
    .ark-ro-lineage{font-family:"Geist Mono",monospace;font-size:9px;color:#a2a5ae;overflow-wrap:anywhere}
    .ark-ro-check{display:grid;grid-template-columns:minmax(0,1fr) minmax(100px,auto) 20px;gap:12px;align-items:center;min-height:48px;border-top:1px solid #2c2e33;font-size:10px}
    .ark-ro-check strong{text-align:right}.ark-ro-check .mark{text-align:right}
    .ark-ro-panel-note{margin-top:18px;color:#a2a5ae;font-size:10px;line-height:1.75}
    .ark-ro-screen-badge{display:inline-block;padding:4px 7px;border:1px solid #4f5053;color:#c3c4c7;font-size:9px;letter-spacing:.08em;border-radius:4px}
    .ark-ro-readiness{margin:0 0 22px;padding:14px 17px;border:1px solid #4b4d52;background:#1c1e23;border-radius:10px;display:flex;justify-content:space-between;gap:14px;align-items:center}
    .ark-ro-readiness.bad{border-color:#765054;background:#35252a}.ark-ro-readiness.warn{border-color:#6d5a3d;background:#30291f}
    .ark-ro-readiness strong{font-size:11px}.ark-ro-readiness span{font-size:9px;color:#a2a5ae}
    .ark-ro-position-owner{font-size:8px;color:#a2a5ae;margin-top:4px;display:block}
    .ark-ro-subgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:18px}
    .ark-ro-subgrid .metric{border:1px solid #2c2e33;border-radius:9px;padding:14px}
    @media(max-width:760px){.ark-ro-subgrid{grid-template-columns:1fr}.ark-ro-check{grid-template-columns:1fr auto 16px}}
  `;

  const style = document.createElement('style');
  style.id = 'ark-readonly-overlay-style';
  style.textContent = css;
  document.head.appendChild(style);

  const esc = value => String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');

  const finite = value => typeof value === 'number' && Number.isFinite(value);
  const yen = value => finite(value) ? `¥${Math.round(value).toLocaleString('ja-JP')}` : '--';
  const number = value => finite(value) ? value.toLocaleString('ja-JP') : '--';
  const percent = value => finite(value) ? `${value >= 0 ? '+' : ''}${value.toFixed(2)}%` : '--';
  const valueOr = (value, fallback = '--') => value === null || value === undefined || value === '' ? fallback : String(value);
  const sum = (rows, key, predicate = () => true) => {
    let total = 0;
    let seen = false;
    for (const row of rows || []) {
      if (!predicate(row)) continue;
      const value = row?.[key];
      if (finite(value)) { total += value; seen = true; }
    }
    return seen ? total : null;
  };

  function badge(value) {
    const text = valueOr(value, 'UNAVAILABLE');
    const cls = /BLOCKED|ERROR|INVALID|STALE|UNKNOWN/.test(text)
      ? 'negative'
      : /LOCKED|FRESH|PASS|CLEAR|READ_ONLY_OK|AVAILABLE/.test(text)
        ? 'positive'
        : 'warning';
    return `<span class="badge ${cls}">${esc(text)}</span>`;
  }

  function ownerLabel(owner) {
    if (owner === 'ARK_MANAGED') return 'Ark管理';
    if (owner === 'EXTERNAL') return '個人 / 外部';
    return '所有区分不明';
  }

  function positionRows(model) {
    const rows = model?.positions || [];
    if (!rows.length) {
      return `<div class="ark-ro-empty"><strong>現在の保有はありません</strong><span>実口座スナップショット上の保有は0件です。</span></div>`;
    }
    return `<div class="positionsList">${rows.map(row => {
      const mv = finite(row.marketValue) ? row.marketValue : (finite(row.marketPrice) && finite(row.quantity) ? row.marketPrice * row.quantity : null);
      const pnl = row.unrealizedPnl;
      const pnlClass = finite(pnl) ? (pnl >= 0 ? 'positive' : 'negative') : '';
      return `<div class="positionRow" aria-label="${esc(valueOr(row.symbol))} read only position">
        <span class="stockMark">${esc(valueOr(row.symbol, '--').slice(0,2))}</span>
        <span class="stockName">
          <strong>${esc(valueOr(row.name, valueOr(row.symbol)))}</strong>
          <small>${esc(valueOr(row.symbol))} · ${esc(number(row.quantity))}株 · ${esc(ownerLabel(row.ownership))}</small>
          <span class="ark-ro-position-owner">READ ONLY / ${esc(valueOr(row.accountType, '口座区分--'))}</span>
        </span>
        <span class="positionValue">
          <strong>${yen(mv)}</strong>
          <small class="${pnlClass}">${finite(pnl) ? yen(pnl) : '--'} ${finite(row.unrealizedPnlPercent) ? `(${percent(row.unrealizedPnlPercent)})` : ''}</small>
        </span>
        ${badge(row.ownership || 'UNKNOWN')}
      </div>`;
    }).join('')}</div>`;
  }

  function readiness(model) {
    const readiness = valueOr(model?.system?.tradeReadiness, 'UNAVAILABLE');
    const freshness = valueOr(model?.source?.freshness?.state, 'UNAVAILABLE');
    const className = readiness === 'BLOCKED' ? 'bad' : readiness === 'LOCKED_READY' ? 'warn' : '';
    return `<div class="ark-ro-readiness ${className}"><strong>${esc(readiness)}</strong><span>Source ${esc(freshness)} · READ ONLY · 注文送信なし</span></div>`;
  }

  function home(model) {
    const positions = model?.positions || [];
    const invested = sum(positions, 'marketValue');
    const unrealized = sum(positions, 'unrealizedPnl');
    const managedCount = positions.filter(row => row.ownership === 'ARK_MANAGED').length;
    const externalCount = positions.filter(row => row.ownership === 'EXTERNAL').length;
    const unknownCount = positions.filter(row => row.ownership === 'UNKNOWN').length;
    const intent = model?.home?.activeIntent;
    const lineage = model?.home?.activeIntentLineage;
    const signal = intent
      ? `<div class="signalName"><span>${esc(valueOr(intent.symbol))} · READ ONLY</span><h2>${esc(valueOr(intent.side))} ${esc(number(intent.quantity))}株</h2><p>${esc(valueOr(intent.positionEffect))}</p></div>${badge(model?.system?.pipeline?.state)}<div class="ark-ro-subgrid"><div class="metric"><span>Strategy</span><strong>${esc(valueOr(lineage?.strategyId))}</strong></div><div class="metric"><span>Intent ID</span><strong class="ark-ro-lineage">${esc(valueOr(lineage?.sourceIntentId))}</strong></div></div>`
      : `<div class="signalName"><span>ACTIVE INTENT</span><h2>NO ACTIVE INTENT</h2><p>現在、表示可能な注文Intentはありません。</p></div>${badge(model?.system?.pipeline?.state || 'LOCKED_NO_INTENT')}`;
    return `${readiness(model)}
      <section class="equityPanel">
        <div class="equityTop"><div><span class="metricLabel">TOTAL ASSETS</span><h2 class="assetValue">--</h2><span class="gainLabel">未接続 / 推定しません</span></div><span class="ark-ro-screen-badge">REAL ACCOUNT · READ ONLY</span></div>
        <p class="ark-ro-panel-note">Total Assets / 資産推移は現在のRead Modelに検証済みソースがないため表示しません。</p>
        <div class="accountStrip">
          <div class="metric"><span>Buying Power</span><strong>${yen(model?.home?.buyingPower)}</strong><small>${esc(valueOr(model?.home?.buyingPowerState))}</small></div>
          <div class="metric"><span>Invested</span><strong>${yen(invested)}</strong><small>保有時価の取得可能分のみ</small></div>
          <div class="metric"><span>Unrealized P/L</span><strong>${yen(unrealized)}</strong><small>取得可能分のみ</small></div>
          <div class="metric"><span>Positions</span><strong>${positions.length}</strong><small>${managedCount} Ark / ${externalCount} External / ${unknownCount} Unknown</small></div>
        </div>
      </section>
      <div class="homeLower">
        <section class="panel holdingsPanel"><div class="panelTitle"><h2>Positions <span>${positions.length}</span></h2><span class="muted">REAL ACCOUNT</span></div>${positionRows(model)}<div class="holdingsFoot"><span>ARK ${managedCount}</span><span>EXTERNAL ${externalCount}</span><span>UNKNOWN ${unknownCount}</span></div></section>
        <section class="signalPanel"><div class="signalTop"><span>ACTIVE INTENT</span><span class="signalIndex">RO</span></div>${signal}<p class="ark-ro-panel-note">表示専用。注文・取消・Kill Switch操作は接続されていません。</p></section>
      </div>${footer(model)}`;
  }

  function selector(model) {
    const lineage = model?.selector?.activeIntentLineage;
    return `${readiness(model)}<section class="panel"><div class="panelTitle"><h2>Selector</h2>${badge(model?.selector?.state)}</div><div class="ark-ro-empty"><strong>Selector候補はまだUI Read Modelへ未接続</strong><span>実戦略の候補・Score・理由をダミー値で代用しません。</span></div>${lineage ? `<div class="ark-ro-subgrid"><div class="metric"><span>Current Strategy</span><strong>${esc(valueOr(lineage.strategyId))}</strong></div><div class="metric"><span>Source Intent</span><strong class="ark-ro-lineage">${esc(valueOr(lineage.sourceIntentId))}</strong></div></div>` : ''}<p class="panelNote">Selector / Entry / EXIT / Allocation の仕様はこのUIから変更できません。</p></section>${footer(model)}`;
  }

  function positions(model) {
    const rows = model?.positions || [];
    const marketValue = sum(rows, 'marketValue');
    const pnl = sum(rows, 'unrealizedPnl');
    const managedValue = sum(rows, 'marketValue', row => row.ownership === 'ARK_MANAGED');
    const externalValue = sum(rows, 'marketValue', row => row.ownership === 'EXTERNAL');
    return `${readiness(model)}<div class="summaryStrip"><div class="metric"><span>MARKET VALUE</span><strong>${yen(marketValue)}</strong></div><div class="metric"><span>UNREALIZED P/L</span><strong>${yen(pnl)}</strong></div><div class="metric"><span>ARK MANAGED</span><strong>${yen(managedValue)}</strong></div><div class="metric"><span>EXTERNAL</span><strong>${yen(externalValue)}</strong></div></div><section class="panel holdingsPanel"><div class="panelTitle"><h2>実口座保有 <span>${rows.length}</span></h2><span class="muted">READ ONLY</span></div>${positionRows(model)}<p class="panelNote">Ownership baselineが未設定・不正な場合、保有はUNKNOWNのまま表示します。Ark管理と推定しません。</p></section>${footer(model)}`;
  }

  function orderRows(model) {
    const orders = model?.orders || [];
    const executions = model?.executions || [];
    const orderHtml = orders.length ? orders.map(row => `<div class="orderRow"><span class="side">RO</span><span class="stockName"><strong>${esc(valueOr(row.symbol))}</strong><small>${esc(number(row.quantity))}株 · filled ${esc(number(row.filledQuantity))}</small></span><span class="orderTime mono">${esc(valueOr(row.orderNumber))}</span>${badge(row.status)}</div>`).join('') : `<div class="ark-ro-empty"><strong>未処理注文 0件</strong><span>現在のRead Modelに注文はありません。</span></div>`;
    const executionHtml = executions.length ? executions.map(row => `<div class="orderRow"><span class="side ${String(row.side || '').includes('売') || row.side === 'SELL' ? 'sell' : ''}">${esc(valueOr(row.side, 'FILL'))}</span><span class="stockName"><strong>${esc(valueOr(row.symbol))}</strong><small>${esc(number(row.quantity))}株 × ${yen(row.price)}</small></span><span class="orderTime mono">${esc(valueOr(row.executionDate))}</span>${badge('約定')}</div>`).join('') : `<div class="ark-ro-empty"><strong>約定 0件</strong><span>現在のRead Modelに約定はありません。</span></div>`;
    return `<section class="panel"><div class="panelTitle"><h2>Orders</h2><span class="muted">READ ONLY</span></div>${orderHtml}<div class="panelTitle" style="margin-top:28px"><h2>Executions</h2><span class="muted">READ ONLY</span></div>${executionHtml}<p class="panelNote">注文送信・取消ボタンはこの統合では提供しません。</p></section>`;
  }

  function orders(model) {
    return `${readiness(model)}${orderRows(model)}${footer(model)}`;
  }

  function performance(model) {
    return `${readiness(model)}<section class="panel"><div class="panelTitle"><h2>Performance</h2>${badge(model?.performance?.state)}</div><div class="ark-ro-empty"><strong>実績集計は未接続</strong><span>日次 / 週次 / 月次P/L、Win Rate、PF、MFE/MAEは検証済み実データが接続されるまで表示しません。</span></div><p class="panelNote">デモの損益・勝率は実運用画面には表示しません。</p></section>${footer(model)}`;
  }

  function checkRow(label, value, good = null) {
    const cls = good === true ? 'positive' : good === false ? 'negative' : 'warning';
    const mark = good === true ? '✓' : good === false ? '!' : '·';
    return `<div class="ark-ro-check"><span>${esc(label)}</span><strong class="${cls}">${esc(valueOr(value))}</strong><span class="mark ${cls}">${mark}</span></div>`;
  }

  function system(model) {
    const fresh = model?.source?.freshness?.state;
    const age = model?.source?.freshness?.ageSeconds;
    const safety = model?.safety?.state;
    const recon = model?.system?.reconciliation?.state;
    const ownership = model?.system?.ownership?.state;
    const pipeline = model?.system?.pipeline?.state;
    const runtime = model?.system?.runtimeSafety?.state;
    const bridge = model?.localBridge;
    const refreshError = bridge?.refresh?.lastError;
    const blocked = model?.system?.tradeReadiness === 'BLOCKED';
    return `${readiness(model)}
      <section class="systemOverview"><div><span class="statusOrbit ${blocked ? 'bad' : ''}">⊙</span><h2>${esc(valueOr(model?.system?.health))}</h2><p>${blocked ? '新規Entry readinessはBLOCKED。表示経路はRead-onlyです。' : 'Read-onlyデータ経路は正常です。'}</p></div><button class="preflightButton" disabled>READ ONLY</button><button class="killButton" disabled><span>Kill Switch</span><strong>${esc(valueOr(model?.system?.runtimeSafety?.killSwitchLatched, 'UNKNOWN'))}</strong><i></i></button></section>
      <div class="systemGrid">
        <section class="panel"><div class="panelTitle"><h2>Connections & Data</h2><span class="muted">REAL SNAPSHOT</span></div>
          ${checkRow('Source Schema', model?.source?.schemaValid ? 'VALID' : 'INVALID', model?.source?.schemaValid === true)}
          ${checkRow('Snapshot Freshness', finite(age) ? `${fresh} · ${age.toFixed(1)}s` : fresh, fresh === 'FRESH')}
          ${checkRow('Account / RSS Safety', safety, safety === 'LOCKED')}
          ${checkRow('Buying Power', yen(model?.home?.buyingPower), finite(model?.home?.buyingPower))}
          ${checkRow('Local Bridge', bridge?.loopbackOnly ? '127.0.0.1 ONLY' : 'UNAVAILABLE', bridge?.loopbackOnly === true)}
          ${checkRow('Refresh Loop', refreshError ? 'ERROR' : (bridge?.refresh?.enabled ? 'ACTIVE' : 'MANUAL'), refreshError ? false : null)}
          ${refreshError ? `<p class="ark-ro-panel-note negative">${esc(refreshError)}</p>` : ''}
        </section>
        <section class="panel"><div class="panelTitle"><h2>Safety & Reconciliation</h2><span class="muted">FAIL CLOSED</span></div>
          ${checkRow('Reconciliation', recon, recon === 'RECONCILIATION_PASS')}
          ${checkRow('Ownership Baseline', ownership, ownership === 'AVAILABLE' ? true : null)}
          ${checkRow('G6-G10 Pipeline', pipeline, pipeline === 'LOCKED_READY' ? true : pipeline === 'BLOCKED' ? false : null)}
          ${checkRow('Runtime Safety', runtime, runtime === 'CLEAR' ? true : runtime === 'BLOCKED' ? false : null)}
          ${checkRow('Cash Long Lock', 'LOCKED', true)}
          ${checkRow('Margin / Short', 'DISABLED', true)}
          ${checkRow('UI Mutations', 'DISABLED', true)}
        </section>
        <section class="panel"><div class="panelTitle"><h2>Verified Limits</h2><span class="muted">NO GUESSING</span></div><div class="ark-ro-empty"><strong>UI表示用のRisk Limit feedは未接続</strong><span>Daily Loss / Max Positions / Max Order / Capital Usageをデモ設定で代用しません。</span></div></section>
        <section class="panel"><div class="panelTitle"><h2>Read-only Boundary</h2><span class="ark-ro-screen-badge">LOCKED</span></div>
          ${['orderSubmit','orderCancel','killSwitchChange','strategyEdit','brokerWrite','excelOrderWrite','rssOrderFunction'].map(key => checkRow(key, String(model?.mutationCapabilities?.[key]), model?.mutationCapabilities?.[key] === false)).join('')}
        </section>
      </div>
      <section class="panel eventPanel"><div class="panelTitle"><h2>Read-only Event</h2><span class="muted">LOCAL</span></div><ol><li><i></i>${esc(valueOr(model?.generatedAt))} · UI READ MODEL · ${esc(valueOr(model?.source?.freshness?.state))}</li>${(model?.system?.pipeline?.blockers || []).map(item => `<li><i></i>BLOCKER · ${esc(item)}</li>`).join('')}</ol></section>${footer(model)}`;
  }

  function unavailable(error) {
    return `<div class="ark-ro-readiness bad"><strong>READ MODEL UNAVAILABLE</strong><span>${esc(error || 'waiting for local read-only model')}</span></div><section class="panel"><div class="ark-ro-empty"><strong>実口座表示を停止しています</strong><span>ローカルRead Modelを取得できるまでダミーデータは表示しません。</span></div></section>`;
  }

  function footer(model) {
    return `<footer class="healthbar"><span class="ark-ro-status"><i class="ark-ro-dot ${model?.source?.freshness?.state === 'FRESH' ? '' : 'bad'}"></i>${esc(valueOr(model?.source?.freshness?.state, 'UNAVAILABLE'))}</span><div><span>MSII/RSS READ ONLY</span><span>CASH LONG ONLY</span><span>ORDERS DISABLED</span></div><small>LOCAL READ ONLY · 実注文なし</small></footer>`;
  }

  function markupFor(screen, model) {
    if (!model) return unavailable(state.error);
    switch (screen) {
      case 'HOME': return home(model);
      case 'SELECTOR': return selector(model);
      case 'POSITIONS': return positions(model);
      case 'ORDERS': return orders(model);
      case 'PERFORMANCE': return performance(model);
      case 'SYSTEM': return system(model);
      default: return unavailable(`UNKNOWN SCREEN: ${screen}`);
    }
  }

  function updateChrome(model) {
    const demoBadge = document.querySelector('.demoBadge');
    if (demoBadge) demoBadge.textContent = 'READ ONLY';
    const demoStamp = document.querySelector('.demoStamp');
    if (demoStamp) demoStamp.textContent = 'LOCAL READ ONLY';
    const footSmalls = document.querySelectorAll('.sidebarFoot small');
    if (footSmalls.length) footSmalls[footSmalls.length - 1].textContent = '実口座参照 / 実注文なし';
    const run = document.querySelector('.runStatus');
    if (run) {
      const healthy = model?.source?.freshness?.state === 'FRESH' && model?.safety?.state === 'LOCKED';
      run.textContent = healthy ? '● READ ONLY' : '● BLOCKED';
      run.classList.toggle('positive', healthy);
      run.classList.toggle('warning', !healthy);
    }
    const time = document.querySelector('.topTime');
    if (time && model?.generatedAt) {
      const date = new Date(model.generatedAt);
      if (!Number.isNaN(date.getTime())) {
        time.innerHTML = `${esc(date.toLocaleDateString('ja-JP'))} <b>${esc(date.toLocaleTimeString('ja-JP',{hour:'2-digit',minute:'2-digit',second:'2-digit'}))}</b>`;
      }
    }
    document.querySelectorAll(MUTATION_SELECTORS).forEach(button => {
      button.disabled = true;
      button.setAttribute('aria-disabled', 'true');
    });
  }

  function currentScreen() {
    return (document.querySelector('.sectionLabel')?.textContent || 'HOME').trim().toUpperCase();
  }

  function render() {
    state.queued = false;
    updateChrome(state.model);
    const main = document.getElementById('main');
    if (!main) return;
    const heading = Array.from(main.children).find(child => child.classList?.contains('screenHeading'));
    for (const child of Array.from(main.children)) {
      if (child === heading || child.id === 'ark-readonly-screen') continue;
      child.style.display = 'none';
      child.setAttribute('aria-hidden', 'true');
    }
    let mount = document.getElementById('ark-readonly-screen');
    if (!mount || mount.parentElement !== main) {
      mount = document.createElement('div');
      mount.id = 'ark-readonly-screen';
      if (heading?.nextSibling) main.insertBefore(mount, heading.nextSibling);
      else main.appendChild(mount);
    }
    const screen = currentScreen();
    const stamp = `${screen}|${state.model?.generatedAt || 'none'}|${state.error || ''}|${state.model?.source?.freshness?.state || ''}`;
    if (mount.dataset.stamp !== stamp) {
      mount.dataset.stamp = stamp;
      mount.innerHTML = markupFor(screen, state.model);
    }
    document.querySelectorAll(MUTATION_SELECTORS).forEach(button => {
      button.disabled = true;
      button.setAttribute('aria-disabled', 'true');
    });
  }

  function queueRender() {
    if (state.queued) return;
    state.queued = true;
    requestAnimationFrame(render);
  }

  async function poll() {
    try {
      const response = await fetch(MODEL_URL, { method: 'GET', cache: 'no-store', credentials: 'same-origin', headers: { Accept: 'application/json', 'X-Ark-Read-Only': 'true' } });
      const body = await response.json();
      if (!response.ok || body?.schemaId !== 'ARK_TERMINAL_UI_READ_MODEL_V1' || body?.readOnly !== true) {
        throw new Error(body?.code || body?.message || `HTTP_${response.status}`);
      }
      state.model = body;
      state.error = null;
    } catch (error) {
      state.model = null;
      state.error = `${error?.name || 'Error'}: ${error?.message || error}`;
    }
    queueRender();
  }

  const observer = new MutationObserver(queueRender);
  const root = document.getElementById('root');
  if (root) observer.observe(root, { childList: true, subtree: true });
  poll();
  state.timer = window.setInterval(poll, POLL_MS);
  queueRender();
})();
