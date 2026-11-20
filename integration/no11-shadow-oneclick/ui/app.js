"use strict";
const el=id=>document.getElementById(id);
const jpy=x=>{if(x===null||x===undefined||x==="")return "—";let n=Number(x);return Number.isFinite(n)?"¥"+new Intl.NumberFormat("ja-JP",{maximumFractionDigits:0}).format(n):"—"};
const quantity=x=>Number.isInteger(x)?new Intl.NumberFormat("ja-JP").format(x):"—";
const time=x=>{if(!x)return "未受信";const d=new Date(x);return Number.isFinite(d.getTime())?d.toLocaleString("ja-JP",{timeZone:"Asia/Tokyo",month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit",second:"2-digit"}):String(x).slice(0,22)};
const state=(id,label,cls)=>{const item=el(id);item.textContent=label;item.className="statusval "+cls};
const set=(id,value)=>{el(id).textContent=value};
function rows(id,items,columns,empty){
 const body=el(id);body.replaceChildren();
 if(!Array.isArray(items)||!items.length){const tr=document.createElement("tr"),td=document.createElement("td");td.colSpan=columns;td.className="empty";td.textContent=empty;tr.append(td);body.append(tr);return}
 for(const item of items){const tr=document.createElement("tr");for(let i=0;i<columns;i++){const td=document.createElement("td");const entry=(id==="paper-history")?
 [time(item.at),item.symbol,item.side==="BUY"?"買い":"売り",item.status,quantity(item.filled)+" / "+quantity(item.quantity)]:
 [time(item.at),item.symbol,item.side,quantity(item.quantity),jpy(item.price)];
 td.textContent=entry[i]??"—";if(i===2){if(item.side==="BUY"||item.side==="買")td.className="side-buy";if(item.side==="SELL"||item.side==="売")td.className="side-sell"}tr.append(td)}body.append(tr)}
}
function render(s){
 set("session",s.sessionDate||"—");
 const steps=s.launcher?.steps||{};
 const excel=steps.excel||"NOT_CHECKED",msii=steps.marketSpeed||"NOT_CHECKED";
 state("excel-state",excel==="READY"?"RSS / READY":excel==="BLOCKED"?"確認が必要":excel==="WAITING"?"起動・接続中":"確認待ち",excel==="READY"?"ok":excel==="BLOCKED"?"bad":"warn");
 const a=s.account||{},p=s.shadow?.portfolio||{},sh=s.shadow||{};
 state("account-state",a.status==="OBSERVED"?"観測中":a.status==="STALE"?"データ古い":a.status==="BLOCKED"?"受信不可":"未接続",a.status==="OBSERVED"?"ok":"warn");
 const running=sh.status==="OBSERVED"&&p.status==="OBSERVED_SIMULATOR_LEDGER";
 state("shadow-state",running?"稼働データ確認":sh.status==="STALE"?"データ古い":steps.shadow==="BLOCKED"?"起動不可":steps.shadow==="START_REQUESTED"?"起動確認中":"未起動",running?"ok":steps.shadow==="BLOCKED"?"bad":"warn");
 set("real-equity",jpy(a.totalAssets));
 set("real-power",jpy(a.buyingPower));
 set("real-value",jpy(a.marketValue));
 set("real-pnl",jpy(a.unrealizedPnl));
 set("real-count",a.positionCount==null?"—":quantity(a.positionCount)+"銘柄");
 set("real-asof",time(a.asOf));
 set("paper-equity",jpy(p.equity));
 set("paper-cash",jpy(p.cash));
 set("paper-value",jpy(p.exposure));
 set("paper-count",p.positionCount==null?"—":quantity(p.positionCount)+"銘柄");
 set("paper-intents",p.buyIntents==null||p.sellIntents==null?"—":p.buyIntents+" / "+p.sellIntents);
 set("paper-asof",time(sh.updatedAt));
 rows("paper-history",p.fills,5,"元のShadow台帳に模擬売買記録はありません");
 rows("real-history",a.executions,5,"RSS約定データがありません");
 if(steps.shadow==="BLOCKED"){set("notice-title","Shadowの起動前検査で停止");set("notice-body",s.launcher.message||"不足資料や実機検査を確認してください。実注文は常にOFFです。")}
 else if(steps.shadow==="NOT_CONFIGURED"){set("notice-title","Shadow入力設定が未登録");set("notice-body","ローカルUIと口座監視は動作します。確認済み当日マスター・企業行動資料・Pinned FrozenモデルのPreflight合格後に模擬運用を開始できます。")}
 else if(running){set("notice-title","受信済み模擬データを表示中");set("notice-body","元のShadowが生成した模擬約定を表示しています。これは実口座の買付や約定ではありません。")}
 else{set("notice-title","読み取り専用で準備中");set("notice-body",s.launcher?.message||"RSSとShadowの検査状況を確認中です。");}
 set("last-refresh","LOCAL ONLY ・ "+time(s.updatedAtJst));
}
async function poll(){
 try{const response=await fetch("/api/status",{cache:"no-store",credentials:"omit"});if(!response.ok)throw Error("HTTP "+response.status);const json=await response.json();if(json.orderTransmission!==false)throw Error("Unsafe status");render(json)}
 catch{state("excel-state","接続を確認","warn");state("shadow-state","情報取得失敗","bad");set("notice-title","ローカル画面のデータを取得できません");set("notice-body","起動処理・ログを確認してください。注文はできません。")}
}
function tick(){el("clock").textContent=new Date().toLocaleString("ja-JP",{timeZone:"Asia/Tokyo",hour:"2-digit",minute:"2-digit",second:"2-digit"})+" JST"}
tick();poll();setInterval(tick,1000);setInterval(poll,8000);
