import {assertLongOnlyOrderIntent,PHASE57_LONG_ONLY_SAFETY} from './phase57-long-only-research-contract.js';

export const REPLAY_COMPONENT_CONTRACT=Object.freeze({
  selector:'({datasetId, dailyRows, bars5m}) => candidate[]',
  entry:'({datasetId, candidates, bars5m}) => cash-equity intent[]',
  exit:'({datasetId, intents, bars5m}) => closed trade[]',
  allocation:'({datasetId, trades, dailyRows, bars5m}) => portfolio replay',
});

export async function replayLongOnlyIntegratedStages({dataset,components,initialCashJpy=1_000_000}={}){
  if(!dataset?.datasetId||!dataset?.consumers)throw new Error('integrated research dataset is required');
  for(const name of ['selector','entry','exit','allocation'])if(typeof components?.[name]!=='function')throw new Error(`${name} adapter is required`);
  const selectorView=dataset.consumers.SELECTOR,candidates=await components.selector(selectorView);
  const intents=await components.entry({...dataset.consumers.ENTRY,candidates});
  let availableCashJpy=initialCashJpy;
  for(const intent of intents??[]){assertLongOnlyOrderIntent(intent,{availableCashJpy});availableCashJpy-=Number(intent.quantity)*Number(intent.price);}
  const trades=await components.exit({...dataset.consumers.EXIT,intents});
  const portfolio=await components.allocation({...dataset.consumers.ALLOCATION,trades,initialCashJpy});
  return Object.freeze({datasetId:dataset.datasetId,stages:Object.freeze({SELECTOR_ONLY:Object.freeze({candidates}),SELECTOR_ENTRY:Object.freeze({candidates,intents}),SELECTOR_ENTRY_EXIT:Object.freeze({candidates,intents,trades}),FULL_INTEGRATED_PORTFOLIO:Object.freeze({candidates,intents,trades,portfolio})}),proof:Object.freeze({singleRawDatasetReused:true,shortContribution:0,marginTrades:0}),safety:PHASE57_LONG_ONLY_SAFETY});
}

export default {replayLongOnlyIntegratedStages};
