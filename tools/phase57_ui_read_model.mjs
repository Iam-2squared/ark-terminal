import {createHash} from 'node:crypto';

export const ARK_TERMINAL_UI_READ_MODEL_SCHEMA = 'ARK_TERMINAL_UI_READ_MODEL_V1';
export const ARK_ACCOUNT_SNAPSHOT_SCHEMA = 'ARK_ACCOUNT_READONLY_SNAPSHOT_V2';

const CRITICAL_FALSE_FLAGS = Object.freeze([
  'executionAllowed',
  'brokerWriteAllowed',
  'excelOrderWriteAllowed',
  'rssOrderFunctionAllowed',
  'liveTradingAllowed',
  'paperTradingAllowed',
  'automaticPromotionAllowed',
  'productionUpdateAllowed',
  'transmitted',
]);

const clone = value => value === undefined ? undefined : structuredClone(value);
const finite = value => typeof value === 'number' && Number.isFinite(value);
const asText = value => value === null || value === undefined ? null : String(value).trim() || null;
const canonical = value => Array.isArray(value)
  ? value.map(canonical)
  : value && typeof value === 'object'
    ? Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])]))
    : value;
const sha256 = value => createHash('sha256').update(JSON.stringify(canonical(value))).digest('hex');

function optionalNumber(value) {
  if (value === null || value === undefined || value === '' || typeof value === 'boolean') return null;
  const number = Number(value);
  return finite(number) ? number : null;
}

function isoMs(value) {
  const ms = Date.parse(String(value ?? ''));
  return Number.isFinite(ms) ? ms : null;
}

function normalizeSymbol(value) {
  const raw = String(value ?? '').trim().toUpperCase();
  if (/^[0-9A-Z]{4}$/.test(raw)) return `${raw}.T`;
  if (/^[0-9A-Z]{4}\.T$/.test(raw)) return raw;
  return raw || null;
}

function blockerList(pipeline) {
  if (!pipeline || typeof pipeline !== 'object') return [];
  const values = [];
  for (const key of ['candidate', 'reconciliation', 'preflight']) {
    const blockers = pipeline[key]?.blockers;
    if (!Array.isArray(blockers)) continue;
    for (const blocker of blockers) {
      const text = asText(blocker);
      if (text && !values.includes(text)) values.push(text);
    }
  }
  return values;
}

function snapshotIntegrity(snapshot) {
  const violations = [];
  if (!snapshot || typeof snapshot !== 'object') {
    violations.push('ACCOUNT_SNAPSHOT_UNAVAILABLE');
  } else {
    if (snapshot.schemaId !== ARK_ACCOUNT_SNAPSHOT_SCHEMA) violations.push('ACCOUNT_SNAPSHOT_SCHEMA_INVALID');
    if (snapshot.mode !== 'READ_ONLY') violations.push('ACCOUNT_SNAPSHOT_NOT_READ_ONLY');
    if (!Array.isArray(snapshot.positions)) violations.push('ACCOUNT_SNAPSHOT_POSITIONS_ARRAY_REQUIRED');
    if (!Array.isArray(snapshot.orders)) violations.push('ACCOUNT_SNAPSHOT_ORDERS_ARRAY_REQUIRED');
    if (!Array.isArray(snapshot.executions)) violations.push('ACCOUNT_SNAPSHOT_EXECUTIONS_ARRAY_REQUIRED');
    const buyingPower = optionalNumber(snapshot.buyingPower);
    if (buyingPower === null || buyingPower < 0) violations.push('ACCOUNT_SNAPSHOT_BUYING_POWER_INVALID');
  }
  return Object.freeze({state: violations.length ? 'BLOCKED' : 'VALID', violations: Object.freeze(violations)});
}

function snapshotFreshness(snapshot, generatedAtMs, maxAgeSeconds) {
  if (!snapshot || typeof snapshot !== 'object') {
    return Object.freeze({state: 'UNAVAILABLE', ageSeconds: null, timestamp: null});
  }
  const timestamp = snapshot.captureCompletedAt || snapshot.capturedAt;
  const timestampMs = isoMs(timestamp);
  if (timestampMs === null || generatedAtMs === null) {
    return Object.freeze({state: 'INVALID', ageSeconds: null, timestamp: asText(timestamp)});
  }
  const ageSeconds = (generatedAtMs - timestampMs) / 1000;
  if (ageSeconds < -5) {
    return Object.freeze({state: 'INVALID', ageSeconds, timestamp: new Date(timestampMs).toISOString()});
  }
  return Object.freeze({
    state: ageSeconds <= maxAgeSeconds ? 'FRESH' : 'STALE',
    ageSeconds: Math.max(0, ageSeconds),
    timestamp: new Date(timestampMs).toISOString(),
  });
}

function sourceSafety(snapshot) {
  const source = snapshot?.safety;
  const violations = [];
  if (!source || typeof source !== 'object') {
    violations.push('SOURCE_SAFETY_FLAGS_MISSING');
  } else {
    for (const key of CRITICAL_FALSE_FLAGS) {
      if (source[key] !== false) violations.push(`SOURCE_SAFETY_${key}_NOT_FALSE`);
    }
  }
  return Object.freeze({
    state: violations.length ? 'BLOCKED' : 'LOCKED',
    violations: Object.freeze(violations),
    cashOnly: true,
    marginTradingAllowed: false,
    shortSellingAllowed: false,
    marginFallbackAllowed: false,
    executionAllowed: false,
    brokerWriteAllowed: false,
    excelOrderWriteAllowed: false,
    rssOrderFunctionAllowed: false,
    liveTradingAllowed: false,
    paperTradingAllowed: false,
    transmitted: false,
  });
}

function ownershipProjection(ownershipBaseline) {
  const unavailable = state => Object.freeze({state, baselineSha256: null, capturedAt: null, external: new Map(), managed: new Map()});
  if (!ownershipBaseline) return unavailable('UNAVAILABLE');
  try {
    if (ownershipBaseline.schemaId !== 'ARK_CASH_OWNERSHIP_BASELINE_V1' || ownershipBaseline.frozen !== true) throw new Error('OWNERSHIP_BASELINE_INVALID');
    if (isoMs(ownershipBaseline.capturedAt) === null) throw new Error('OWNERSHIP_BASELINE_INVALID');
    const {baselineSha256, ...core} = ownershipBaseline;
    if (!/^[a-f0-9]{64}$/i.test(String(baselineSha256 ?? '')) || sha256(core) !== baselineSha256) throw new Error('OWNERSHIP_BASELINE_HASH_MISMATCH');
    if (!Array.isArray(ownershipBaseline.externalPositions) || !Array.isArray(ownershipBaseline.arkManagedPositions)) throw new Error('OWNERSHIP_BASELINE_INVALID');

    const external = new Map();
    const managed = new Map();
    for (const row of ownershipBaseline.externalPositions) {
      const symbol = normalizeSymbol(row?.symbol);
      const quantity = optionalNumber(row?.quantity);
      if (!/^[0-9A-Z]{4}\.T$/.test(String(symbol ?? '')) || quantity === null || quantity <= 0 || external.has(symbol)) throw new Error('OWNERSHIP_BASELINE_INVALID');
      external.set(symbol, quantity);
    }
    for (const row of ownershipBaseline.arkManagedPositions) {
      const symbol = normalizeSymbol(row?.symbol);
      const quantity = optionalNumber(row?.quantity);
      if (!/^[0-9A-Z]{4}\.T$/.test(String(symbol ?? '')) || quantity === null || quantity <= 0 || !Number.isInteger(quantity) || quantity % 100 !== 0 || managed.has(symbol) || external.has(symbol)) throw new Error('OWNERSHIP_BASELINE_INVALID');
      managed.set(symbol, quantity);
    }
    return Object.freeze({
      state: 'AVAILABLE',
      baselineSha256,
      capturedAt: new Date(ownershipBaseline.capturedAt).toISOString(),
      external,
      managed,
    });
  } catch {
    return unavailable('INVALID');
  }
}

function projectPositions(rows, ownership) {
  if (!Array.isArray(rows)) return [];
  return rows.map(row => {
    const symbol = normalizeSymbol(row?.symbol);
    const quantity = optionalNumber(row?.quantity);
    let owner = 'UNKNOWN';
    let expectedQuantity = null;
    if (symbol && ownership.state === 'AVAILABLE') {
      if (ownership.external.has(symbol)) {
        owner = 'EXTERNAL';
        expectedQuantity = ownership.external.get(symbol);
      } else if (ownership.managed.has(symbol)) {
        owner = 'ARK_MANAGED';
        expectedQuantity = ownership.managed.get(symbol);
      }
    }
    return Object.freeze({
      symbol,
      name: asText(row?.name),
      accountType: asText(row?.account ?? row?.accountType),
      quantity,
      ownership: owner,
      ownershipExpectedQuantity: expectedQuantity,
      ownershipQuantityMatch: quantity !== null && expectedQuantity !== null ? quantity === expectedQuantity : null,
      averagePrice: optionalNumber(row?.averagePrice),
      marketPrice: optionalNumber(row?.marketPrice),
      marketValue: optionalNumber(row?.marketValue),
      unrealizedPnl: optionalNumber(row?.unrealizedPnl),
      unrealizedPnlPercent: optionalNumber(row?.unrealizedPnlPercent),
      updatedAt: asText(row?.updatedAt),
      readOnly: true,
    });
  });
}

function projectOrders(rows) {
  if (!Array.isArray(rows)) return [];
  return rows.map(row => Object.freeze({
    orderNumber: asText(row?.orderNumber),
    status: asText(row?.status),
    symbol: normalizeSymbol(row?.symbol),
    quantity: optionalNumber(row?.quantity),
    filledQuantity: optionalNumber(row?.filledQty ?? row?.filledQuantity),
    readOnly: true,
  }));
}

function projectExecutions(rows) {
  if (!Array.isArray(rows)) return [];
  return rows.map(row => Object.freeze({
    executionDate: asText(row?.executionDate),
    symbol: normalizeSymbol(row?.symbol),
    accountType: asText(row?.account ?? row?.accountType),
    side: asText(row?.side),
    quantity: optionalNumber(row?.quantity),
    price: optionalNumber(row?.price),
    readOnly: true,
  }));
}

function pipelineProjection(lockedPipeline) {
  if (!lockedPipeline || typeof lockedPipeline !== 'object') {
    return Object.freeze({state: 'UNAVAILABLE', status: null, stage: null, blockers: Object.freeze([]), lineage: null});
  }
  const status = asText(lockedPipeline.status);
  const stage = asText(lockedPipeline.stage);
  const valid = ['BLOCKED', 'LOCKED_READY'].includes(status) && Boolean(stage);
  return Object.freeze({
    state: valid ? (status === 'BLOCKED' ? 'BLOCKED' : 'LOCKED_READY') : 'INVALID',
    status: valid ? status : null,
    stage: valid ? stage : null,
    blockers: Object.freeze(blockerList(lockedPipeline)),
    lineage: lockedPipeline.upstreamLineage && typeof lockedPipeline.upstreamLineage === 'object' ? Object.freeze(clone(lockedPipeline.upstreamLineage)) : null,
  });
}

function runtimeSafetyProjection(runtimeSafety) {
  if (!runtimeSafety || typeof runtimeSafety !== 'object') {
    return Object.freeze({state: 'UNKNOWN', killSwitchLatched: null, faults: Object.freeze([])});
  }
  const faults = Array.isArray(runtimeSafety.faults) ? runtimeSafety.faults.map(asText).filter(Boolean) : [];
  const latched = runtimeSafety.killSwitchLatched === true;
  return Object.freeze({state: latched || faults.length ? 'BLOCKED' : 'CLEAR', killSwitchLatched: latched, faults: Object.freeze(faults)});
}

export function buildArkTerminalUiReadModel({
  accountSnapshot = null,
  lockedPipeline = null,
  ownershipBaseline = null,
  runtimeSafety = null,
  generatedAt = new Date().toISOString(),
  maxSnapshotAgeSeconds = 30,
} = {}) {
  const generatedAtMs = isoMs(generatedAt);
  if (generatedAtMs === null) throw new Error('UI_READ_MODEL_GENERATED_AT_INVALID');
  if (!finite(maxSnapshotAgeSeconds) || maxSnapshotAgeSeconds <= 0) throw new Error('UI_READ_MODEL_MAX_AGE_INVALID');

  const integrity = snapshotIntegrity(accountSnapshot);
  const schemaValid = integrity.state === 'VALID';
  const freshness = schemaValid
    ? snapshotFreshness(accountSnapshot, generatedAtMs, maxSnapshotAgeSeconds)
    : Object.freeze({state: accountSnapshot ? 'INVALID' : 'UNAVAILABLE', ageSeconds: null, timestamp: null});
  const safety = sourceSafety(schemaValid ? accountSnapshot : null);
  const ownership = ownershipProjection(ownershipBaseline);
  const pipeline = pipelineProjection(lockedPipeline);
  const runtime = runtimeSafetyProjection(runtimeSafety);
  const positions = projectPositions(schemaValid ? accountSnapshot.positions : [], ownership);
  const orders = projectOrders(schemaValid ? accountSnapshot.orders : []);
  const executions = projectExecutions(schemaValid ? accountSnapshot.executions : []);

  const criticalSourceProblem = integrity.state !== 'VALID' || freshness.state !== 'FRESH' || safety.state !== 'LOCKED';
  const runtimeNotClear = runtime.state !== 'CLEAR';
  const ownershipRequiredButUnknown = positions.length > 0 && ownership.state !== 'AVAILABLE';
  const readiness = criticalSourceProblem || runtimeNotClear || ownershipRequiredButUnknown || pipeline.state === 'BLOCKED' || pipeline.state === 'INVALID'
    ? 'BLOCKED'
    : pipeline.state === 'LOCKED_READY'
      ? 'LOCKED_READY'
      : 'LOCKED_NO_INTENT';

  const buyingPower = schemaValid ? optionalNumber(accountSnapshot.buyingPower) : null;
  const activeIntent = lockedPipeline?.draft && typeof lockedPipeline.draft === 'object'
    ? Object.freeze({
        symbol: normalizeSymbol(lockedPipeline.draft.symbol),
        side: asText(lockedPipeline.draft.side),
        quantity: optionalNumber(lockedPipeline.draft.quantity),
        positionEffect: asText(lockedPipeline.draft.positionEffect),
      })
    : null;

  return Object.freeze({
    schemaId: ARK_TERMINAL_UI_READ_MODEL_SCHEMA,
    generatedAt: new Date(generatedAtMs).toISOString(),
    readOnly: true,
    mutationCapabilities: Object.freeze({
      orderSubmit: false,
      orderCancel: false,
      killSwitchChange: false,
      strategyEdit: false,
      brokerWrite: false,
      excelOrderWrite: false,
      rssOrderFunction: false,
    }),
    source: Object.freeze({
      schemaValid,
      integrity,
      source: schemaValid ? asText(accountSnapshot.source) : null,
      mode: schemaValid ? asText(accountSnapshot.mode) : null,
      freshness,
    }),
    safety,
    system: Object.freeze({
      health: criticalSourceProblem || runtime.state === 'BLOCKED' ? 'BLOCKED' : 'READ_ONLY_OK',
      tradeReadiness: readiness,
      reconciliation: Object.freeze({
        state: lockedPipeline?.reconciliation?.status ? asText(lockedPipeline.reconciliation.status) : 'UNAVAILABLE',
        blockers: Object.freeze(Array.isArray(lockedPipeline?.reconciliation?.blockers) ? clone(lockedPipeline.reconciliation.blockers) : []),
      }),
      pipeline,
      runtimeSafety: runtime,
      ownership: Object.freeze({
        state: ownership.state,
        baselineSha256: ownership.baselineSha256,
        capturedAt: ownership.capturedAt,
      }),
    }),
    home: Object.freeze({
      totalAssets: null,
      totalAssetsState: 'UNAVAILABLE',
      buyingPower,
      buyingPowerState: buyingPower === null ? 'UNAVAILABLE' : freshness.state,
      positionsCount: positions.length,
      openOrdersCount: orders.length,
      executionsCount: executions.length,
      activeIntent,
      activeIntentLineage: pipeline.lineage,
    }),
    selector: Object.freeze({
      state: 'UNAVAILABLE',
      reason: 'SELECTOR_READ_MODEL_NOT_CONNECTED',
      activeIntentLineage: pipeline.lineage,
      candidates: Object.freeze([]),
    }),
    positions: Object.freeze(positions),
    orders: Object.freeze(orders),
    executions: Object.freeze(executions),
    performance: Object.freeze({
      state: 'UNAVAILABLE',
      reason: 'PERFORMANCE_READ_MODEL_NOT_CONNECTED',
    }),
  });
}

export const ArkTerminalUiReadModelInternals = Object.freeze({
  optionalNumber,
  normalizeSymbol,
  snapshotIntegrity,
  snapshotFreshness,
  sourceSafety,
  ownershipProjection,
  projectPositions,
  projectOrders,
  projectExecutions,
  pipelineProjection,
  runtimeSafetyProjection,
});
