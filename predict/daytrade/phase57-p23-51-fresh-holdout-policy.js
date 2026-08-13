export const P23_51_FRESH_HOLDOUT_POLICY=Object.freeze({
  phase:'57.p23.51',
  candidate:'P23.44_CDF_CONTRAST',
  baseline:'P23.30_DYNAMIC_RISK',
  developmentFrozenAt:'2026-08-12T20:50:08Z',
  temporalHoldoutStartJst:'2026-08-12',
  minimumCompletedSessions:10,
  minimumScoredRows:100,
  minimumRowsPerDirection:20,
  candidateRetuningAllowed:false,
  thresholdSearchAllowed:false,
  symbolFilteringAllowed:false,
  entryRetuningAllowed:false,
  setupRuleRetuningAllowed:false,
  winnerSelectionAfterRevealAllowed:false,
  consumeOnlyOnce:true,
  freshHoldoutConsumed:false,
  promotionRequires:Object.freeze({
    overallAucDeltaPositive:true,
    upAucDeltaPositive:true,
    downAucDeltaPositive:true,
    sameCoverage:true,
    invalidationSeparationNonWorse:true,
    adverseReturnSeparationNonWorse:true
  }),
  executionAllowed:false,
  brokerWriteAllowed:false,
  excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,
  automaticPromotionAllowed:false,
  productionUpdateAllowed:false
});

export function assertP2351Safety(p=P23_51_FRESH_HOLDOUT_POLICY){
  for(const k of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed'])if(p[k]!==false)throw Error(`P23.51 unsafe ${k}`);
  for(const k of ['candidateRetuningAllowed','thresholdSearchAllowed','symbolFilteringAllowed','entryRetuningAllowed','setupRuleRetuningAllowed','winnerSelectionAfterRevealAllowed'])if(p[k]!==false)throw Error(`P23.51 methodology violation ${k}`);
  if(p.freshHoldoutConsumed!==false||p.consumeOnlyOnce!==true)throw Error('P23.51 holdout state invalid');
  return true;
}
