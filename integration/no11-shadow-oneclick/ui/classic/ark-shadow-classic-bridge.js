/* The historical Ark Terminal read-only UI, connected to the new No.1.1
 * Shadow simulator observer. Status is received ONLY from /api/status;
 * historical demo figures are never promoted to account/model observations.
 */
(() => {
  "use strict";
  const ENDPOINT = "/api/status";
  const PREFIX = "ark-classic-shadow";
  let latest = null;
  let lastError = false;

  const style = document.createElement("style");
  style.textContent = `
  .ark-classic-shadow {
    margin:0 0 23px;padding:20px;border:1px solid #424853;border-radius:13px;
    background:linear-gradient(125deg,#15191f,#1c2028);
    color:#eceef3;box-shadow:0 12px 30px rgba(0,0,0,.17);
    font-family:inherit;letter-spacing:normal;
  }
  .ark-classic-shadow *{box-sizing:border-box}
  .ark-classic-shadow-head{display:flex;align-items:center;justify-content:space-between;gap:15px;flex-wrap:wrap;margin-bottom:17px}
  .ark-classic-shadow-kicker{font-size:10px;color:#83b4f5;font-weight:700;letter-spacing:2px}
  .ark-classic-shadow-head h2{font-size:19px;margin:5px 0 0;color:#f1f3f6}
  .ark-classic-shadow-safe{border:1px solid #426e5c;border-radius:6px;padding:9px 13px;color:#9ce1ba;font-size:10px;font-weight:700}
  .ark-classic-shadow-tiles{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}
  .ark-classic-shadow-tile{padding:14px;background:#111419;border:1px solid #313742;border-radius:9px;min-width:0}
  .ark-classic-shadow-tile small{display:block;color:#a4abba;font-size:10px;margin-bottom:11px}
  .ark-classic-shadow-tile strong{display:block;color:#f0f3f7;font-size:16px;overflow-wrap:anywhere}
  .ark-classic-shadow-tile strong.warn{color:#f0b575}
  .ark-classic-shadow-tile strong.ok{color:#9ce1ba}
  .ark-classic-shadow-tile em{font-style:normal;display:block;color:#7b8799;margin-top:7px;font-size:9px}
  .ark-classic-shadow-note{font-size:10px;color:#abb6c6;line-height:1.8;margin:15px 0 0}
  .ark-classic-shadow-line{margin-top:14px;padding-top:12px;border-top:1px solid #303640;display:flex;gap:10px;justify-content:space-between;flex-wrap:wrap}
  .ark-classic-shadow-line>span{font-size:10px;color:#9fa8b9}
  .ark-classic-shadow-section{margin:19px 0 0}
  .ark-classic-shadow-section summary{cursor:pointer;font-size:11px;font-weight:700;color:#e1e5ed}
  .ark-classic-shadow-table{margin-top:12px;overflow-x:auto;width:100%;border-collapse:collapse}
  .ark-classic-shadow-table th,.ark-classic-shadow-table td{padding:8px 7px;font-size:10px;text-align:left;border-bottom:1px solid #303640}
  .ark-classic-shadow-table th{color:#8793a5;font-weight:600}
  .ark-classic-shadow-empty{color:#aab0bc}
  .ark-classic-shadow-privacy{color:#90a0b6;font-size:9px;margin:12px 0 0}
  @media(max-width:1080px){.ark-classic-shadow-tiles{grid-template-columns:repeat(2,minmax(0,1fr))}}
  @media(max-width:600px){.ark-classic-shadow-tiles{grid-template-columns:1fr}}
  `;
  document.head.append(style);

  const staticMarkup = `
  <div class="ark-classic-shadow-head">
    <div><div class="ark-classic-shadow-kicker">FROZEN NO.1.1 / LIVE OBSERVATION ADAPTER</div>
      <h2>旧Ark Terminal UI × 統合Shadow</h2></div>
    <span class="ark-classic-shadow-safe">🔒 実注文・発注権限 OFF</span>
  </div>
  <div class="ark-classic-shadow-tiles">
    <div class="ark-classic-shadow-tile"><small>Excel 元2冊</small><strong id="arksc-excel">確認中</strong><em>RSS接続とは別に検査</em></div>
    <div class="ark-classic-shadow-tile"><small>実口座RSS観測</small><strong id="arksc-account">未接続</strong><em>実口座と模擬口座は別管理</em></div>
    <div class="ark-classic-shadow-tile"><small>Frozen Shadow</small><strong id="arksc-shadow">未起動</strong><em>Selector / P1 / H235 / Capital / EXIT</em></div>
    <div class="ark-classic-shadow-tile"><small>模擬総資産（実注文なし）</small><strong id="arksc-equity">—</strong><em id="arksc-equity-source">確認済み模擬台帳のみ</em></div>
  </div>
  <div class="ark-classic-shadow-line">
    <span>模擬現金 <strong id="arksc-cash">—</strong></span>
    <span>模擬保有時価 <strong id="arksc-exposure">—</strong></span>
    <span>模擬保有銘柄 <strong id="arksc-count">—</strong></span>
    <span>模擬買い／売り指示 <strong id="arksc-orders">—</strong></span>
  </div>
  <p class="ark-classic-shadow-note" id="arksc-note">既存No.1.1の元UIを読み取り専用で表示しています。実RSSまたはShadowの証跡が届くまで数値は表示しません。</p>
  <details class="ark-classic-shadow-section" open>
    <summary>Shadowの模擬売買履歴（実取引とは別）</summary>
    <table class="ark-classic-shadow-table"><thead><tr><th>日時</th><th>銘柄</th><th>売買</th><th>状態</th><th>数量</th></tr></thead>
      <tbody id="arksc-sim-rows"><tr><td colspan="5" class="ark-classic-shadow-empty">稼働済みの模擬履歴はありません</td></tr></tbody>
    </table>
  </details>
  <details class="ark-classic-shadow-section">
    <summary>実口座RSSの約定履歴（読み取り専用）</summary>
    <table class="ark-classic-shadow-table"><thead><tr><th>日時</th><th>銘柄</th><th>売買</th><th>数量</th><th>価格</th></tr></thead>
      <tbody id="arksc-real-rows"><tr><td colspan="5" class="ark-classic-shadow-empty">確認済み約定は未受信</td></tr></tbody>
    </table>
  </details>
  <p class="ark-classic-shadow-privacy">発注OFF。旧UIのデモ画面数値は隠しており、RSSの正式な総資産値がない場合は推定しません。Shadowの模擬売買も実口座とは結合しません。</p>
  `;

  function mount() {
    const host = document.getElementById("ark-readonly-screen");
    if (!host) return;
    let box = document.getElementById(PREFIX);
    if (!box || box.parentElement !== host) {
      box = document.createElement("section");
      box.id = PREFIX;
      box.className = "ark-classic-shadow";
      box.innerHTML = staticMarkup; // Static source only. No account text HTML.
      host.prepend(box);
      if (latest) update(latest);
      else if (lastError) put("arksc-note", "接続できません。ローカル読み取り専用サーバーを確認してください。");
    }
    // Hide the source React DEMO until the frozen read-only overlay exists.
    const preload = document.getElementById("ark-classic-preload");
    if (preload) preload.remove();
  }

  const put = (id, value) => {
    const node = document.getElementById(id);
    if (node) node.textContent = value;
  };
  const yen = x => {
    if (x === null || x === undefined || x === "") return "—";
    const n = Number(x);
    if (!Number.isFinite(n) || Math.abs(n) >= 9e15) return "—";
    return "¥" + new Intl.NumberFormat("ja-JP", {maximumFractionDigits:0}).format(n);
  };
  const text = v => v === null || v === undefined || v === "" ? "—" : String(v);
  const when = v => {
    const d = new Date(v);
    return Number.isNaN(d.getTime()) ? "—" : d.toLocaleString("ja-JP", {timeZone:"Asia/Tokyo",month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit"});
  };
  function rows(id, list, simulation) {
    const body = document.getElementById(id);
    if (!body) return;
    body.replaceChildren();
    if (!Array.isArray(list) || !list.length) {
      const row = body.insertRow(), cell = row.insertCell();
      cell.colSpan = 5; cell.className = "ark-classic-shadow-empty";
      cell.textContent = simulation ? "確認済みの模擬注文はありません" : "確認済みのRSS約定はありません";
      return;
    }
    for (const entry of list.slice(0,10)) {
      const value = simulation
        ? [when(entry.at), entry.symbol, entry.side==="BUY"?"買い":entry.side==="SELL"?"売り":"—",
           text(entry.status), text(entry.filled)+" / "+text(entry.quantity)]
        : [when(entry.at), entry.symbol, text(entry.side), text(entry.quantity), yen(entry.price)];
      const tr = body.insertRow();
      for (const content of value) tr.insertCell().textContent = text(content);
    }
  }
  function update(s) {
    const launcher = s.launcher || {}, steps = launcher.steps || {};
    const acc = s.account || {}, shadow = s.shadow || {}, paper = shadow.portfolio || {};
    put("arksc-excel", steps.excel==="READY" ? "元2冊を確認" :
      steps.excel==="BLOCKED" ? "識別で停止" : "確認待ち");
    put("arksc-account", acc.status==="OBSERVED" ? "RSS観測中" :
      acc.status==="STALE" ? "データが古い" : "未接続");
    put("arksc-shadow", shadow.status==="OBSERVED" ? "証跡あり" :
      shadow.status==="STALE" ? "古い証跡" :
      steps.shadow==="BLOCKED" ? "起動前検査で停止" :
      steps.shadow==="PREPARING" ? "準備中" : "未起動");
    const verified = shadow.status==="OBSERVED" && paper.status==="OBSERVED_SIMULATOR_LEDGER";
    put("arksc-equity", verified ? yen(paper.equity) : "—");
    put("arksc-cash", verified ? yen(paper.cash) : "—");
    put("arksc-exposure", verified ? yen(paper.exposure) : "—");
    put("arksc-count", verified ? text(paper.positionCount) : "—");
    put("arksc-orders", verified ? text(paper.buyIntents)+" / "+text(paper.sellIntents) : "—");
    put("arksc-equity-source", verified ? "元SQLite模擬台帳・当日観測" : "未起動／価格の鮮度未確認");
    let note = steps.shadow==="BLOCKED"
      ? "Shadowは起動前検査で停止。企業行動証拠、当日マスター、モデル・接続設定を確認してください。"
      : steps.shadow==="NOT_CONFIGURED" ?
      "実口座監視とUIのみが起動中。統合Shadowの当日入力が未設定です。"
      : shadow.status==="OBSERVED" ?
      "凍結Shadowの当日受信レポートを観測。これは実注文・実約定ではありません。"
      : "既存No.1.1の元UIを復元。読み取り専用でMarketSpeed IIと統合Shadowを監視しています。";
    if (launcher.status==="BLOCKED") note = "起動処理で停止：" + text(launcher.message);
    put("arksc-note", note);
    rows("arksc-sim-rows", verified ? paper.fills : [], true);
    rows("arksc-real-rows", acc.status==="OBSERVED" ? acc.executions : [], false);
  }
  async function poll() {
    try {
      const response = await fetch(ENDPOINT,{method:"GET",credentials:"omit",cache:"no-store",
        headers:{"Accept":"application/json","X-Ark-Read-Only":"true"}});
      if (!response.ok) throw new Error("LOCAL_STATUS_UNAVAILABLE");
      const data = await response.json();
      if (data?.schemaId!=="ARK_SHADOW_LOCAL_DASHBOARD_V1" ||
          data.orderTransmission!==false || data.brokerOrdersAuthorized!==false)
        throw new Error("READ_ONLY_CONTRACT_MISMATCH");
      latest = data; lastError = false; mount(); update(data);
    } catch {
      lastError = true; latest = null; mount();
      put("arksc-account","未接続");put("arksc-shadow","確認不可");
      for (const id of ["arksc-equity","arksc-cash","arksc-exposure","arksc-count","arksc-orders"]) put(id,"—");
      put("arksc-note","ローカルShadowの読み取り専用ステータスを取得できません。");
      rows("arksc-sim-rows",[],true);rows("arksc-real-rows",[],false);
    }
  }
  setInterval(mount,750);
  setInterval(poll,5000);
  mount(); poll();
})();
