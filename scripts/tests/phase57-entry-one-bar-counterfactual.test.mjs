import test from 'node:test';
import assert from 'node:assert/strict';
import {exactGrid,excursion,stats} from '../phase57-entry-one-bar-counterfactual.mjs';

const date='2025-10-09',bar=(hm,close,high=close,low=close)=>{const timestamp=`${date}T${hm}:00+09:00`;return {sessionDate:date,timestamp:new Date(timestamp).toISOString(),availableAt:new Date(Date.parse(timestamp)+300000).toISOString(),open:close,high,low,close,volume:1};};
test('exact grid crosses lunch but never invents a bar',()=>{
 const bars=[bar('11:25',100),bar('12:30',101),bar('12:35',102)];
 assert.deepEqual(exactGrid(bars,Date.parse(`${date}T11:30:00+09:00`),date,2).map(x=>x?.close),[101,102]);
 assert.equal(exactGrid(bars,Date.parse(`${date}T12:35:00+09:00`),date,2)[1],null);
});
test('directional return, cost, MAE and MFE are symmetric',()=>{
 const p=[bar('09:00',110,112,90)];
 const l=excursion(100,'LONG',p),s=excursion(100,'SHORT',p);
 const close=(a,b)=>assert(Math.abs(a-b)<1e-9);
 close(l.gross,1000);close(l.net,995);close(l.mae,1000);close(l.mfe,1200);
 close(s.gross,-1000);close(s.net,-1005);close(s.mae,1200);close(s.mfe,1000);
});
test('missing path fails closed and percentiles are deterministic',()=>{
 assert.equal(excursion(100,'LONG',[null]),null);
 assert.deepEqual(stats([1,2,3,4]),{n:4,mean:2.5,median:2.5,p25:1.75,p75:3.25,p90:3.7});
});
