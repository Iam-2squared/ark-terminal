export const P23_11B_RESERVE_HOLDOUT_B_SYMBOLS=Object.freeze([
  '4503.T','4523.T','4568.T','4689.T','4901.T','5108.T','5713.T','5831.T','6178.T','6326.T',
  '6479.T','6645.T','6770.T','6841.T','7003.T','7270.T','7733.T','7832.T','7951.T','8113.T',
  '8267.T','8308.T','8331.T','8601.T','8604.T','8630.T','8725.T','8750.T','8804.T','9005.T',
]);
export const P23_11B_RESERVE_HOLDOUT_B_POLICY=Object.freeze({
  status:'UNIVERSE_RESERVED_BEFORE_ARCHITECTURE_SELECTION_AND_BEFORE_OUTCOME_RETRIEVAL',
  symbolCount:30,
  description:'Independent reserve Japanese-equity historical holdout basket; not claimed to be a current index or liquidity ranking.',
  overlapWithDevelopment30Forbidden:true,
  overlapWithP23_10BHoldout30Forbidden:true,
  outcomeRetrievalAllowed:false,
  architectureNotYetAssigned:true,
  noOutcomeBasedUniverseChanges:true,
});
export default {P23_11B_RESERVE_HOLDOUT_B_SYMBOLS,P23_11B_RESERVE_HOLDOUT_B_POLICY};
