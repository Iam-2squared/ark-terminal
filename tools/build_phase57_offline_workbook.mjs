// Run with @oai/artifact-tool installed. No Excel, broker, COM or RSS connection is made.
import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const [repo,output]=process.argv.slice(2);
if(!repo||!output)throw Error('usage: builder REPO OUTPUT_DIRECTORY');
const map=JSON.parse(await fs.readFile(path.join(repo,'tools/phase57-parity-field-map.json'),'utf8'));
await fs.mkdir(output,{recursive:true});
const wb=Workbook.create();
const data={
  ARK_CONFIG:[['Key','Value'],['schemaId',map.schemaId],['mode','OFFLINE_FIXTURE_ONLY'],['fixtureClass','SYNTHETIC_TRANSPORT_TEST'],['realCaptureEnabled',false],['strategyFreezeSha256','f0ea365e5cf73b3394779ae1be3ea99e268f9d6cede8160a703ed24cab5c0a14'],['barLabel','START'],['source','Synthetic fixture; no market data'],['reservedDataOpened',false]],
  ARK_MARKET:[['Field (official mapping in JSON)','Status'],...['Last price','Last price detailed time','Volume','Volume weighted average price','Best ask','Best bid','Best ask size','Best bid size'].map(x=>[x,'NOT_CAPTURED'])],
  ARK_CHART_5M:[map.chart.columns],
  ARK_TICKS:[['Field (official mapping in JSON)','Status'],...['Time','Volume','Execution price'].map(x=>[x,'NOT_CAPTURED_DIAGNOSTIC_ONLY'])],
  ARK_INDEX:[['Source','Status'],['Index diagnostics','NOT_CAPTURED_NOT_A_NEW_MODEL_FEATURE']],
  ARK_ACCOUNT_READONLY:[['Source','Status'],['Account information','DISABLED_SHADOW_USES_OWN_CAPITAL']],
  ARK_HEALTH:[['Check','Status'],['Workbook purpose','OFFLINE_FIXTURE_ONLY'],['RSS connection','NOT_CONNECTED'],['Excel COM','NOT_USED'],['Order transmission','DISABLED'],['Real session capture','NOT_MEASURED'],['Future / reserved data','LOCKED'],['Real RSS bar-label semantics','UNVERIFIED']]
};
const closes=[100,101,100.5,102,101.8,103,102.5];
for(let i=0;i<7;i++){const start=new Date(Date.parse('2026-08-13T09:00:00+09:00')+i*300000),end=new Date(start.getTime()+300000).toISOString();data.ARK_CHART_5M.push([0,1,'0000.T','2026-08-13',new Date(start.getTime()+32400000).toISOString().slice(11,19),closes[i],closes[i]+1,closes[i]-1,closes[i],1000+i*100,"UTC "+end,"UTC "+end,true]);}
for(const [name,rows] of Object.entries(data)){
  const s=wb.worksheets.add(name),last=String.fromCharCode(64+rows[0].length),range=s.getRange(`A1:${last}${rows.length}`);if(name==='ARK_CHART_5M')s.getRange('K2:L8').setNumberFormat('@');range.values=rows;s.showGridLines=false;
  range.format.font={name:'Arial',size:10};range.format.rowHeight=22;range.format.columnWidth=19;
  s.getRange(`A1:${last}1`).format={fill:'#23364D',font:{name:'Arial',bold:true,color:'#FFFFFF'},rowHeight:26};
  if(rows[0].length===2){s.getRange(`A1:A${rows.length}`).format.columnWidth=35;s.getRange(`B1:B${rows.length}`).format.columnWidth=name==='ARK_CONFIG'?76:49;}
  else{s.getRange('A1:B8').format.columnWidth=11;s.getRange('F2:J8').setNumberFormat('0.00');s.getRange('K1:L8').format.columnWidth=28;s.freezePanes.freezeRows(1);}
}
wb.recalculate();
for(const [name,rows] of Object.entries(data)){
  const last=String.fromCharCode(64+rows[0].length),range=wb.worksheets.getItem(name).getRange(`A1:${last}${rows.length}`);
  if(JSON.stringify(range.values)!==JSON.stringify(rows))throw Error('WORKBOOK_VALUES_MISMATCH:'+name);
  const image=await wb.render({sheetName:name,range:`A1:${last}${rows.length}`,scale:1,format:'png'});await fs.writeFile(path.join(output,name+'.png'),new Uint8Array(await image.arrayBuffer()));
}
await (await SpreadsheetFile.exportXlsx(wb)).save(path.join(output,'ArkParityOffline.xlsx'));
await fs.writeFile(path.join(output,'workbook-source.json'),JSON.stringify(data,null,2)+'\n');
console.log('OFFLINE_WORKBOOK_EXPORTED_NO_ACTIVE_FORMULAS');
