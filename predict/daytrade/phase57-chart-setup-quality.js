export const PHASE57_P23_10D_QUALITY_POLICY = Object.freeze({
  phase: '57.p23.10d',
  outcomeTuned: false,
  futureOutcomeUsed: false,
  scoreRole: 'CAUSAL_DESCRIPTIVE_QUALITY_NOT_ENTRY_GATE',
  recommendationAllowed: false,
});

const clamp = (v, lo = 0, hi = 1) => Math.max(lo, Math.min(hi, Number(v)));
const regimeSign = regime => regime === 'UPTREND' ? 1 : regime === 'DOWNTREND' ? -1 : 0;

function alignedCandle(tf5, sign) {
  const dir = tf5?.currentCandle?.direction;
  if (sign === 1) return dir === 'UP' ? 1 : dir === 'FLAT' ? 0.5 : 0;
  if (sign === -1) return dir === 'DOWN' ? 1 : dir === 'FLAT' ? 0.5 : 0;
  return 0.5;
}

function timeframeAgreement(perception, sign) {
  const rows = ['15m','60m','1d'].map(tf => perception?.timeframes?.[tf]).filter(Boolean);
  if (!rows.length) return 0.5;
  let score = 0;
  for (const row of rows) {
    const vote = regimeSign(row?.structure?.regime);
    score += vote === sign ? 1 : vote === 0 ? 0.5 : 0;
  }
  return score / rows.length;
}

function setupStructureFit(tf5, setup) {
  const state = tf5?.breakout?.state ?? 'NONE';
  if (setup.startsWith('BREAKOUT_CONTINUATION_')) return state.startsWith('BREAKOUT_') ? 1 : 0;
  if (setup.startsWith('RETEST_CONTINUATION_')) return state.startsWith('RETEST_HOLD_') ? 1 : 0;
  if (setup.startsWith('FAILED_BREAKOUT_REVERSAL_')) return state.startsWith('FAILED_BREAKOUT_') ? 1 : 0;
  if (setup.startsWith('TREND_PULLBACK_')) return String(tf5?.phase?.phase ?? '').includes('PULLBACK') ? 1 : 0;
  if (setup.startsWith('MOMENTUM_CONTINUATION_')) return String(tf5?.phase?.phase ?? '').includes('IMPULSE') ? 1 : 0;
  return 0.5;
}

function volumeConfirmation(tf5) {
  const ratio = Number(tf5?.volume?.ratio);
  if (!Number.isFinite(ratio)) return 0.5;
  return clamp((ratio - 0.5) / 1.5);
}

function volatilityFit(tf5, setup) {
  const state = tf5?.volatility?.state;
  if (setup.startsWith('BREAKOUT_') || setup.startsWith('MOMENTUM_')) return state === 'EXPANDING' ? 1 : state === 'NORMAL' ? 0.6 : 0.2;
  if (setup.startsWith('TREND_PULLBACK_') || setup.startsWith('RETEST_')) return state === 'NORMAL' ? 1 : state === 'COMPRESSED' ? 0.8 : 0.4;
  if (setup.startsWith('FAILED_BREAKOUT_')) return state === 'EXPANDING' ? 0.8 : 0.6;
  return 0.5;
}

function trendQuality(perception, sign) {
  const rows = ['5m','15m','60m'].map(tf => perception?.timeframes?.[tf]).filter(Boolean);
  const values = rows.map(row => {
    const r = regimeSign(row?.structure?.regime);
    const q = clamp(row?.trendQuality?.score ?? 0);
    return r === sign ? q : r === 0 ? q * 0.5 : 0;
  });
  return values.length ? values.reduce((a,b) => a + b, 0) / values.length : 0;
}

export function scoreHumanStyleSetupQuality(perception = {}, setupInfo = {}) {
  const setup = String(setupInfo?.setup ?? 'NO_CLEAR_SETUP');
  const sign = Number(setupInfo?.directionSign ?? 0);
  if (![1,-1].includes(sign) || !perception?.timeframes?.['5m']) {
    return Object.freeze({ score: null, components: null, qualityRole: PHASE57_P23_10D_QUALITY_POLICY.scoreRole });
  }
  const tf5 = perception.timeframes['5m'];
  const components = Object.freeze({
    higherTimeframeAgreement: timeframeAgreement(perception, sign),
    localTrendQuality: trendQuality(perception, sign),
    setupStructureFit: setupStructureFit(tf5, setup),
    candleConfirmation: alignedCandle(tf5, sign) * clamp(tf5?.currentCandle?.bodyStrength ?? 0),
    volumeConfirmation: volumeConfirmation(tf5),
    volatilityFit: volatilityFit(tf5, setup),
  });
  const score = Object.values(components).reduce((a,b) => a + Number(b), 0) / Object.keys(components).length;
  return Object.freeze({ score: clamp(score), components, qualityRole: PHASE57_P23_10D_QUALITY_POLICY.scoreRole, outcomeUsed: false, futureBarsUsed: false });
}

export default { PHASE57_P23_10D_QUALITY_POLICY, scoreHumanStyleSetupQuality };
