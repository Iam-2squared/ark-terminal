import {createHash} from 'node:crypto';

export const PHASE57_US_CROSS_MARKET_SAFETY=Object.freeze({
  phase:'57.us-cross-market',mode:'READ_ONLY_US_CROSS_MARKET_PROSPECTIVE_RESEARCH',researchOnly:true,
  executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,
  transmitted:false,freshHoldoutConsumed:false,
});

export const PHASE57_US_CROSS_MARKET_POLICY=Object.freeze({
  candidateId:'US_CROSS_MARKET_V1',
  market:'US',
  exchanges:Object.freeze(['NASDAQ','NYSE','NYSE_ARCA','NYSE_AMERICAN']),
  timezone:'America/New_York',
  regularSession:Object.freeze({open:'09:30',close:'16:00',barMinutes:5,expectedBars:78}),
  firstFreshEligibleDate:'2026-08-31',
  purpose:'CROSS_MARKET_PROSPECTIVE_VALIDATION_NOT_JPX_OOS_SUBSTITUTE',
  universe:Object.freeze({
    commonStocksOnly:true,etfs:false,otc:false,preferred:false,warrants:false,rights:false,units:false,
    requireUsdQuote:true,requireActiveListing:true,minimumPriceUsd:1,minimumMedianDollarVolumeUsd:5_000_000,
    freezeBeforeRegularOpen:true,
  }),
  lanes:Object.freeze([
    'US_D50_FIXED','US_D50_V3','US_D50_V4',
    'US_DYNAMIC5M_V1_V3','US_DYNAMIC5M_V1_V4','US_DYNAMIC5M_V2_V3','US_DYNAMIC5M_V2_V4',
  ]),
  allocationProfiles:Object.freeze(['MAX_10','MAX_4','MAX_3','MAX_2','ADAPTIVE_EQUAL','ADAPTIVE_RANK','ADAPTIVE_SCORE']),
  methodology:Object.freeze({
    jpxEvidenceUntouched:true,jpxFormalOosSubstitution:false,crossMarketEvidenceSeparate:true,
    sameFrozenEntryLogicRequested:true,exitV3Frozen:true,exitV4Frozen:true,adaptiveAllocationV2Frozen:true,
    usOutcomeUsedForFitting:false,resultBasedRetuning:false,postHocWinnerFiltering:false,
    missingBucketsNeverFabricated:true,regularSessionOnly:true,preMarketAndAfterHoursExcluded:true,
  }),
});

export const PHASE57_US_CROSS_MARKET_POLICY_SHA256=createHash('sha256').update(JSON.stringify(PHASE57_US_CROSS_MARKET_POLICY)).digest('hex');

export function assertPhase57UsCrossMarketSafety(){
  for(const k of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed']){
    if(PHASE57_US_CROSS_MARKET_SAFETY[k]!==false)throw new Error(`unsafe ${k}`);
  }
  return true;
}
