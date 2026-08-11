import {
  PHASE57_CHART_PERCEPTION_SAFETY,
} from './phase57-chart-perception-2.js';
import {
  buildSessionAwareMultiTimeframePerception,
  resampleTokyoCashSession,
  resampleCompletedTokyoDaily,
} from './phase57-chart-perception-session-aware.js';

export const P23_12_VISUAL_REASONING_POLICY = Object.freeze({
  phase: '57.p23.12',
  id: 'VISUAL_CHART_REASONING_V1',
  purpose: 'HUMAN_STYLE_CHART_GEOMETRY_BEFORE_FORECAST',
  outcomeTuned: false,
  futureOutcomeUsed: false,
  scoreUsedAsEntryGate: false,
  modelApiBound: false,
  externalVisionCallEnabled: false,
  renderFormat: 'SVG',
  visualBands: Object.freeze({ A: 0.72, B: 0.60, C: 0.48 }),
  recommendationAllowed: false,
  edgeClaimAllowed: false,
});

export const PHASE57_P23_12_SAFETY = Object.freeze({
  ...PHASE57_CHART_PERCEPTION_SAFETY,
  mode: 'PHASE57_P23_12_VISUAL_CHART_REASONING_READ_ONLY_RESEARCH',
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  overnightHoldingAllowed: false,
  transmitted: false,
});

const finite = value => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
const clamp = (value, lo = 0, hi = 1) => Math.max(lo, Math.min(hi, Number(value)));
const mean = values => values.length ? values.reduce((sum, value) => sum + Number(value), 0) / values.length : null;
const median = values => {
  if (!values.length) return null;
  const sorted = [...values].map(Number).sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
};

function normalizeBars(input = []) {
  return (Array.isArray(input) ? input : [])
    .map(bar => ({
      timestamp: new Date(bar.timestamp ?? bar.time).toISOString(),
      open: Number(bar.open), high: Number(bar.high), low: Number(bar.low), close: Number(bar.close),
      volume: finite(bar.volume) ? Number(bar.volume) : 0,
    }))
    .filter(bar => [bar.open, bar.high, bar.low, bar.close].every(Number.isFinite) && bar.high >= bar.low)
    .sort((a, b) => a.timestamp.localeCompare(b.timestamp));
}

function signFromDirection(direction) {
  if (direction === 1 || direction === 'UP' || direction === 'LONG') return 1;
  if (direction === -1 || direction === 'DOWN' || direction === 'SHORT') return -1;
  return 0;
}

function regimeSign(regime) {
  if (regime === 'UPTREND') return 1;
  if (regime === 'DOWNTREND') return -1;
  return 0;
}

function trueRangeSeries(bars) {
  return bars.map((bar, index) => {
    const previous = index ? bars[index - 1].close : bar.open;
    return Math.max(bar.high - bar.low, Math.abs(bar.high - previous), Math.abs(bar.low - previous));
  });
}

function atr(bars, length = 14) {
  const clean = normalizeBars(bars);
  if (!clean.length) return null;
  const values = trueRangeSeries(clean).slice(-Math.max(1, Number(length) || 14));
  return mean(values);
}

function linearSlopePctPerBar(bars, lookback = 12) {
  const clean = normalizeBars(bars).slice(-Math.max(3, Number(lookback) || 12));
  if (clean.length < 3) return 0;
  const ys = clean.map(row => row.close);
  const n = ys.length;
  const xMean = (n - 1) / 2;
  const yMean = mean(ys) ?? 0;
  let numerator = 0;
  let denominator = 0;
  for (let i = 0; i < n; i += 1) {
    numerator += (i - xMean) * (ys[i] - yMean);
    denominator += (i - xMean) ** 2;
  }
  const slope = denominator ? numerator / denominator : 0;
  return yMean ? slope / yMean * 100 : 0;
}

function candleGeometry(bar) {
  const range = Math.max(1e-12, Number(bar.high) - Number(bar.low));
  const body = Number(bar.close) - Number(bar.open);
  return Object.freeze({
    directionSign: Math.sign(body),
    bodyRatio: Math.abs(body) / range,
    upperWickRatio: (Number(bar.high) - Math.max(Number(bar.open), Number(bar.close))) / range,
    lowerWickRatio: (Math.min(Number(bar.open), Number(bar.close)) - Number(bar.low)) / range,
    closeLocation: (Number(bar.close) - Number(bar.low)) / range,
  });
}

function directionalPressure(bars, sign, lookback = 6) {
  const clean = normalizeBars(bars).slice(-Math.max(2, Number(lookback) || 6));
  if (!clean.length || !sign) return 0.5;
  let directionalBody = 0;
  let totalRange = 0;
  for (const bar of clean) {
    directionalBody += (bar.close - bar.open) * sign;
    totalRange += Math.max(1e-12, bar.high - bar.low);
  }
  const normalized = totalRange ? directionalBody / totalRange : 0;
  return clamp((normalized + 0.5) / 1.0);
}

function wickControl(bars, sign, lookback = 4) {
  const clean = normalizeBars(bars).slice(-Math.max(1, Number(lookback) || 4));
  if (!clean.length || !sign) return 0.5;
  const adverse = clean.map(bar => {
    const shape = candleGeometry(bar);
    return sign === 1 ? shape.upperWickRatio : shape.lowerWickRatio;
  });
  return clamp(1 - (mean(adverse) ?? 0.5));
}

function participationScore(bars) {
  const clean = normalizeBars(bars);
  if (clean.length < 4) return 0.5;
  const current = clean.at(-1).volume;
  const prior = clean.slice(-21, -1).map(row => row.volume).filter(value => value > 0);
  const baseline = median(prior) ?? mean(prior) ?? 0;
  if (!(baseline > 0)) return 0.5;
  const ratio = current / baseline;
  return clamp((ratio - 0.60) / 1.60);
}

function volatilityTransitionScore(bars, setup) {
  const clean = normalizeBars(bars);
  if (clean.length < 16) return 0.5;
  const ranges = clean.map(row => row.high - row.low);
  const recent = mean(ranges.slice(-3)) ?? 0;
  const prior = mean(ranges.slice(-15, -3)) ?? 0;
  const ratio = prior > 0 ? recent / prior : 1;
  const name = String(setup ?? '');
  if (name.startsWith('BREAKOUT_') || name.startsWith('MOMENTUM_') || name.startsWith('FAILED_BREAKOUT_')) {
    return clamp((ratio - 0.65) / 1.10);
  }
  if (name.startsWith('TREND_PULLBACK_') || name.startsWith('RETEST_')) {
    const distance = Math.abs(Math.log(Math.max(1e-9, ratio)));
    return clamp(1 - distance / Math.log(2.5));
  }
  return clamp(1 - Math.abs(ratio - 1) / 1.5);
}

function extensionHealthScore(bars, sign) {
  const clean = normalizeBars(bars).slice(-24);
  if (clean.length < 5 || !sign) return 0.5;
  const a = atr(clean, 14);
  if (!(a > 0)) return 0.5;
  const current = clean.at(-1).close;
  const center = median(clean.slice(-20).map(row => row.close)) ?? current;
  const signedExtensionAtr = (current - center) * sign / a;
  if (signedExtensionAtr <= -0.5) return 0.35;
  if (signedExtensionAtr <= 1.75) return 1;
  if (signedExtensionAtr >= 4.5) return 0;
  return clamp(1 - (signedExtensionAtr - 1.75) / 2.75);
}

function structureCoherence(perception, sign) {
  if (!sign) return 0.5;
  const weights = Object.freeze({ '5m': 0.10, '15m': 0.30, '60m': 0.35, '1d': 0.25 });
  let total = 0;
  let used = 0;
  for (const [tf, weight] of Object.entries(weights)) {
    const row = perception?.timeframes?.[tf];
    if (!row || row.status !== 'CHART_PERCEPTION_READY') continue;
    const vote = regimeSign(row?.structure?.regime);
    const value = vote === sign ? 1 : vote === 0 ? 0.5 : 0;
    total += weight * value;
    used += weight;
  }
  return used ? clamp(total / used) : 0.5;
}

function localExtremaLevels(bars, side, radius = 2) {
  const clean = normalizeBars(bars);
  const levels = [];
  for (let i = radius; i < clean.length - radius; i += 1) {
    const window = clean.slice(i - radius, i + radius + 1);
    if (side === 'HIGH') {
      if (window.every((row, j) => j === radius || clean[i].high >= row.high)) levels.push(clean[i].high);
    } else if (window.every((row, j) => j === radius || clean[i].low <= row.low)) levels.push(clean[i].low);
  }
  return levels;
}

function obstacleRoomScore({ bars5m, bars15m, bars60m, bars1d, sign }) {
  const clean5 = normalizeBars(bars5m);
  if (!clean5.length || !sign) return Object.freeze({ score: 0.5, roomAtr: null, nearestObstacle: null, openSpace: false });
  const current = clean5.at(-1).close;
  const a = atr(clean5, 14);
  if (!(a > 0)) return Object.freeze({ score: 0.5, roomAtr: null, nearestObstacle: null, openSpace: false });

  const pools = [
    normalizeBars(bars15m).slice(-64),
    normalizeBars(bars60m).slice(-48),
    normalizeBars(bars1d).slice(-40),
  ];
  const side = sign === 1 ? 'HIGH' : 'LOW';
  const levels = pools.flatMap(rows => localExtremaLevels(rows, side, 1)).filter(finite);
  const beyond = sign === 1
    ? levels.filter(level => level > current * 1.0002)
    : levels.filter(level => level < current * 0.9998);
  if (!beyond.length) return Object.freeze({ score: 1, roomAtr: Infinity, nearestObstacle: null, openSpace: true });
  const nearest = sign === 1 ? Math.min(...beyond) : Math.max(...beyond);
  const room = Math.max(0, (nearest - current) * sign);
  const roomAtr = room / a;
  return Object.freeze({ score: clamp(roomAtr / 2.0), roomAtr, nearestObstacle: nearest, openSpace: false });
}

function setupGeometryFit({ setup, tf5, sign }) {
  const name = String(setup ?? '');
  if (!tf5 || !sign) return 0.5;
  const state = String(tf5?.breakout?.state ?? 'NONE');
  const phase = String(tf5?.phase?.phase ?? 'BALANCED');
  const body = Number(tf5?.currentCandle?.bodyStrength ?? 0);
  const closeLocation = Number(tf5?.currentCandle?.closeLocation ?? 0.5);
  const directionalClose = sign === 1 ? closeLocation : 1 - closeLocation;
  if (name.startsWith('BREAKOUT_CONTINUATION_')) {
    const stateFit = state === (sign === 1 ? 'BREAKOUT_UP' : 'BREAKOUT_DOWN') ? 1 : 0.3;
    return clamp(0.55 * stateFit + 0.25 * body + 0.20 * directionalClose);
  }
  if (name.startsWith('RETEST_CONTINUATION_')) {
    const stateFit = state === (sign === 1 ? 'RETEST_HOLD_UP' : 'RETEST_HOLD_DOWN') ? 1 : 0.3;
    return clamp(0.65 * stateFit + 0.35 * directionalClose);
  }
  if (name.startsWith('FAILED_BREAKOUT_REVERSAL_')) {
    const expected = sign === 1 ? 'FAILED_BREAKOUT_DOWN' : 'FAILED_BREAKOUT_UP';
    return clamp(0.65 * (state === expected ? 1 : 0.3) + 0.35 * directionalClose);
  }
  if (name.startsWith('TREND_PULLBACK_')) {
    const expected = sign === 1 ? 'UPTREND_PULLBACK' : 'DOWNTREND_PULLBACK';
    return clamp(0.65 * (phase === expected ? 1 : 0.3) + 0.35 * directionalClose);
  }
  if (name.startsWith('MOMENTUM_CONTINUATION_')) {
    const expected = sign === 1 ? 'UPTREND_IMPULSE' : 'DOWNTREND_IMPULSE';
    return clamp(0.55 * (phase === expected ? 1 : 0.3) + 0.25 * body + 0.20 * directionalClose);
  }
  return 0.5;
}

function visualBand(score) {
  const s = Number(score);
  if (!finite(s)) return 'UNSCORED';
  if (s >= P23_12_VISUAL_REASONING_POLICY.visualBands.A) return 'V_A_CLEAN';
  if (s >= P23_12_VISUAL_REASONING_POLICY.visualBands.B) return 'V_B_GOOD';
  if (s >= P23_12_VISUAL_REASONING_POLICY.visualBands.C) return 'V_C_MIXED';
  return 'V_D_WEAK';
}

function visualNarrative({ score, components, setup, sign, room }) {
  const observations = [];
  if (components.structureCoherence >= 0.70) observations.push('HIGHER_TIMEFRAME_SUPPORTIVE');
  else if (components.structureCoherence <= 0.35) observations.push('HIGHER_TIMEFRAME_CONFLICT');
  if (components.directionalPressure >= 0.70) observations.push('DIRECTIONAL_CANDLE_PRESSURE');
  if (components.wickControl <= 0.40) observations.push('ADVERSE_WICK_REJECTION');
  if (components.participation >= 0.65) observations.push('VOLUME_PARTICIPATION');
  if (components.extensionHealth <= 0.35) observations.push('OVEREXTENSION_RISK');
  if (room?.openSpace) observations.push('OPEN_SPACE_AHEAD');
  else if (components.spaceToObstacle <= 0.30) observations.push('NEARBY_STRUCTURE_OBSTACLE');
  if (components.volatilityTransition >= 0.65) observations.push('VOLATILITY_BEHAVIOR_SUPPORTIVE');
  const primary = score >= P23_12_VISUAL_REASONING_POLICY.visualBands.A
    ? 'CLEAN_VISUAL_STRUCTURE'
    : score >= P23_12_VISUAL_REASONING_POLICY.visualBands.B
      ? 'USABLE_BUT_NOT_CLEAN'
      : score >= P23_12_VISUAL_REASONING_POLICY.visualBands.C
        ? 'MIXED_VISUAL_STRUCTURE'
        : 'WEAK_OR_CROWDED_STRUCTURE';
  return Object.freeze({
    primary,
    setup: String(setup ?? ''),
    direction: sign === 1 ? 'UP' : sign === -1 ? 'DOWN' : 'NONE',
    observations: Object.freeze(observations),
  });
}

export function deriveVisualChartReasoning({ symbol, bars5m = [], setupInfo = {} } = {}) {
  const clean5 = normalizeBars(bars5m);
  const perception = buildSessionAwareMultiTimeframePerception({ bars5m: clean5 });
  const sign = signFromDirection(setupInfo?.directionSign ?? setupInfo?.direction);
  const setup = String(setupInfo?.setup ?? 'NO_CLEAR_SETUP');
  const bars15m = resampleTokyoCashSession(clean5, 15);
  const bars60m = resampleTokyoCashSession(clean5, 60);
  const bars1d = resampleCompletedTokyoDaily(clean5);
  const tf5 = perception?.timeframes?.['5m'];
  const room = obstacleRoomScore({ bars5m: clean5, bars15m, bars60m, bars1d, sign });
  const components = Object.freeze({
    structureCoherence: structureCoherence(perception, sign),
    directionalPressure: directionalPressure(clean5, sign, 6),
    wickControl: wickControl(clean5, sign, 4),
    participation: participationScore(clean5),
    extensionHealth: extensionHealthScore(clean5, sign),
    spaceToObstacle: room.score,
    volatilityTransition: volatilityTransitionScore(clean5, setup),
    setupGeometryFit: setupGeometryFit({ setup, tf5, sign }),
  });
  const weights = Object.freeze({
    structureCoherence: 0.18,
    directionalPressure: 0.14,
    wickControl: 0.10,
    participation: 0.10,
    extensionHealth: 0.12,
    spaceToObstacle: 0.16,
    volatilityTransition: 0.08,
    setupGeometryFit: 0.12,
  });
  const score = Object.entries(weights).reduce((sum, [key, weight]) => sum + weight * Number(components[key] ?? 0.5), 0);
  const normalizedScore = clamp(score);
  const geometry = Object.freeze({
    slope5mPctPerBar: linearSlopePctPerBar(clean5, 12),
    slope15mPctPerBar: linearSlopePctPerBar(bars15m, 12),
    slope60mPctPerBar: linearSlopePctPerBar(bars60m, 10),
    slope1dPctPerBar: linearSlopePctPerBar(bars1d, 10),
    nearestObstacle: room.nearestObstacle,
    obstacleRoomAtr: Number.isFinite(room.roomAtr) ? room.roomAtr : null,
    openSpaceAhead: room.openSpace,
    currentAtr5m: atr(clean5, 14),
  });
  return Object.freeze({
    phase: '57.p23.12-visual-chart-reasoning',
    status: sign ? 'VISUAL_REASONING_READY' : 'VISUAL_REASONING_OBSERVE',
    symbol: String(symbol ?? ''),
    setup,
    direction: sign === 1 ? 'UP' : sign === -1 ? 'DOWN' : 'NONE',
    score: normalizedScore,
    band: visualBand(normalizedScore),
    components,
    geometry,
    narrative: visualNarrative({ score: normalizedScore, components, setup, sign, room }),
    causalCutoff: clean5.at(-1)?.timestamp ?? null,
    sourceCounts: Object.freeze({ bars5m: clean5.length, bars15m: bars15m.length, bars60m: bars60m.length, bars1d: bars1d.length }),
    futureBarsUsed: false,
    outcomeUsed: false,
    scoreUsedAsEntryGate: false,
    externalVisionCallUsed: false,
    recommendationAllowed: false,
    transmitted: false,
    ...PHASE57_P23_12_SAFETY,
    safety: PHASE57_P23_12_SAFETY,
  });
}

function xmlEscape(value) {
  return String(value ?? '').replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');
}

function renderFrame({ bars, x, y, width, height, title }) {
  const clean = normalizeBars(bars);
  if (!clean.length) return `<g><rect x="${x}" y="${y}" width="${width}" height="${height}" fill="#fff" stroke="#bbb"/><text x="${x + 8}" y="${y + 18}" font-size="12">${xmlEscape(title)} NO DATA</text></g>`;
  const shown = clean.slice(-72);
  const minPrice = Math.min(...shown.map(row => row.low));
  const maxPrice = Math.max(...shown.map(row => row.high));
  const priceSpan = Math.max(1e-12, maxPrice - minPrice);
  const maxVolume = Math.max(1, ...shown.map(row => row.volume));
  const priceHeight = height * 0.76;
  const volumeTop = y + priceHeight + 4;
  const volumeHeight = height - priceHeight - 8;
  const step = width / shown.length;
  const candleWidth = Math.max(1, step * 0.62);
  const py = price => y + 22 + (maxPrice - price) / priceSpan * (priceHeight - 28);
  const pieces = [`<g>`,`<rect x="${x}" y="${y}" width="${width}" height="${height}" fill="#fff" stroke="#bbb"/>`,`<text x="${x + 8}" y="${y + 16}" font-size="12" font-family="sans-serif">${xmlEscape(title)}</text>`];
  shown.forEach((bar, index) => {
    const cx = x + (index + 0.5) * step;
    const up = bar.close >= bar.open;
    const color = up ? '#246b45' : '#9a3440';
    const yHigh = py(bar.high), yLow = py(bar.low), yOpen = py(bar.open), yClose = py(bar.close);
    const bodyY = Math.min(yOpen, yClose);
    const bodyH = Math.max(1, Math.abs(yClose - yOpen));
    pieces.push(`<line x1="${cx.toFixed(2)}" y1="${yHigh.toFixed(2)}" x2="${cx.toFixed(2)}" y2="${yLow.toFixed(2)}" stroke="${color}" stroke-width="1"/>`);
    pieces.push(`<rect x="${(cx - candleWidth / 2).toFixed(2)}" y="${bodyY.toFixed(2)}" width="${candleWidth.toFixed(2)}" height="${bodyH.toFixed(2)}" fill="${color}"/>`);
    const vh = Math.max(0, bar.volume / maxVolume * volumeHeight);
    pieces.push(`<rect x="${(cx - candleWidth / 2).toFixed(2)}" y="${(volumeTop + volumeHeight - vh).toFixed(2)}" width="${candleWidth.toFixed(2)}" height="${vh.toFixed(2)}" fill="#888" opacity="0.45"/>`);
  });
  pieces.push('</g>');
  return pieces.join('');
}

export function renderMultiTimeframeChartSvg({ symbol, bars5m = [], setupInfo = {}, width = 1200, height = 800 } = {}) {
  const clean5 = normalizeBars(bars5m);
  const bars15m = resampleTokyoCashSession(clean5, 15);
  const bars60m = resampleTokyoCashSession(clean5, 60);
  const bars1d = resampleCompletedTokyoDaily(clean5);
  const reasoning = deriveVisualChartReasoning({ symbol, bars5m: clean5, setupInfo });
  const gap = 16;
  const outer = 24;
  const header = 54;
  const panelW = (width - outer * 2 - gap) / 2;
  const panelH = (height - outer * 2 - header - gap) / 2;
  const title = `${String(symbol ?? '')} | ${String(setupInfo?.setup ?? 'NO_CLEAR_SETUP')} | ${reasoning.band} ${(reasoning.score * 100).toFixed(1)}`;
  const frames = [
    renderFrame({ bars: clean5.slice(-72), x: outer, y: outer + header, width: panelW, height: panelH, title: '5m' }),
    renderFrame({ bars: bars15m.slice(-72), x: outer + panelW + gap, y: outer + header, width: panelW, height: panelH, title: '15m' }),
    renderFrame({ bars: bars60m.slice(-48), x: outer, y: outer + header + panelH + gap, width: panelW, height: panelH, title: '60m' }),
    renderFrame({ bars: bars1d.slice(-40), x: outer + panelW + gap, y: outer + header + panelH + gap, width: panelW, height: panelH, title: '1d completed only' }),
  ];
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}"><rect width="100%" height="100%" fill="#f7f7f7"/><text x="${outer}" y="${outer + 24}" font-size="18" font-family="sans-serif">${xmlEscape(title)}</text>${frames.join('')}</svg>`;
}

export function buildMultimodalChartReasoningManifest({ symbol, bars5m = [], setupInfo = {} } = {}) {
  const reasoning = deriveVisualChartReasoning({ symbol, bars5m, setupInfo });
  return Object.freeze({
    schema: 'ARK_MULTIMODAL_CHART_REASONING_MANIFEST_V1',
    symbol: String(symbol ?? ''),
    causalCutoff: reasoning.causalCutoff,
    visualReasoning: reasoning,
    expectedImage: Object.freeze({ format: 'SVG_OR_RASTERIZED_EQUIVALENT', panels: Object.freeze(['5m','15m','60m','1d']), volumeIncluded: true }),
    reasoningOrder: Object.freeze([
      'DESCRIBE_VISIBLE_MARKET_STRUCTURE',
      'IDENTIFY_IMPULSE_PULLBACK_BREAKOUT_RETEST_OR_FAILURE',
      'LOCATE_NEAREST_VISIBLE_OBSTACLE_AND_INVALIDATION',
      'ASSESS_EXTENSION_REJECTION_VOLUME_AND_VOLATILITY',
      'COMPARE_5M_15M_60M_1D_CONTEXT',
      'STATE_PRIMARY_AND_ALTERNATIVE_SCENARIO',
      'ONLY_AFTER_DESCRIPTION_COMPARE_HISTORICAL_EVIDENCE',
    ]),
    requiredOutputFields: Object.freeze([
      'visibleStructure','setupInterpretation','higherTimeframeContext','nearestObstacle','extensionRisk','rejectionEvidence','volumeEvidence','primaryScenario','alternativeScenario','invalidationEvidence','uncertainty',
    ]),
    externalModelBinding: 'UNBOUND_UNTIL_CURRENT_API_IS_VERIFIED',
    externalVisionCallEnabled: false,
    futureDataIncluded: false,
    executableTradingInstructionAllowed: false,
    recommendationAllowed: false,
    transmitted: false,
    ...PHASE57_P23_12_SAFETY,
  });
}

export default {
  P23_12_VISUAL_REASONING_POLICY,
  PHASE57_P23_12_SAFETY,
  deriveVisualChartReasoning,
  renderMultiTimeframeChartSvg,
  buildMultimodalChartReasoningManifest,
};
