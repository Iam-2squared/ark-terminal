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
    if (Array.isArray(blockers)) {
      for (const blocker of blockers) {
        const text = asText(blocker);
        if (text && !values.includes(text)) values.push(text);
      }
    }
  }
  return values;
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
  if (!ownershipBaseline) {
    return Object.freeze({state: 'UNAVAILABLE', baselineSha256: null, capturedAt: null, external: new Map(), managed: new Map()});
  }
  try {
    if (ownershipBaseline.schemaId !== 'ARK_CASH_OWNERSHIP_BASELINE_V1' || ownershipBaseline.frozen !== true) {
      throw new Error('OWNERSHIP_BASELINE_INVALID');
    }
    const external = new Map();
    const managed = new Map();
    for (const row of ownershipBaseline.externalPositions ?? []) {
      const symbol = normalizeSymbol(row?.symbol);
      const quantity = Number(row?.quantity);
      if (!symbol || !finite(quantity) || quantity <= 0 || external.has(symbol)) throw new Error('OWNERSHIP_BASELINE_INVALID');
      external.set(symbol, quantity);
    }
    for (const row of ownershipBaseline.arkManagedPositions ?? []) {
      const symbol = normalizeSymbol(row?.symbol);
      const quantity = Number(row?.quantity);
      if (!symbol || !finite(quantity) || quantity <= 0 || managed.has(symbol) || external.has(symbol)) throw new Error('OWNERSHIP_BASELINE_INVALID');
      managed.set(symbol, quantity);
    }
    return Object.freeze({
      state: 'AVAILABLE',
      baselineSha256: asText(ownershipBaseline.baselineSha256),
      capturedAt: asText(ownershipBaseline.capturedAt),
      external,
      managed,
    });
  } catch {
    return Object.freeze({state: 'INVALID', baselineSha256: null, capturedAt: null, external: new Map(), managed: new Map()});
  }
}

function projectPositions(rows, ownership) {
  if (!Array.isArray(rows)) return [];
  return rows.map(row => {
    const symbol = normalizeSymbol(row?.symbol);
    const quantity = Number(row?.quantity);
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
      quantity: finite(quantity) ? quantity : null,
      ownership: owner,
      ownershipExpectedQuantity: expectedQuantity,
      ownershipQuantityMatch: finite(quantity) && finite(expectedQuantity) ? quantity === expectedQuantity : null,
      averagePrice: finite(Number(row?.averagePrice)) ? Number(row.averagePrice) : null,
      marketPrice: finite(Number(row?.marketPrice)) ? Number(row.marketPrice) : null,
      marketValue: finite(Number(row?.marketValue)) ? Number(row.marketValue) : null,
      unrealizedPnl: finite(Number(row?.unrealizedPnl)) ? Number(row.unrealizedPnl) : null,
      unrealizedPnlPercent: finite(Number(row?.unrealizedPnlPercent)) ? Number(row.unrealizedPnlPercent) : null,
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
    quantity: finite(Number(row?.quantity)) ? Number(row.quantity) : null,
    filledQuantity: finite(Number(row?.filledQty ?? row?.filledQuantity)) ? Number(row.filledQty ?? row.filledQuantity) : null,
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
    quantity: finite(Number(row?.quantity)) ? Number(row.quantity) : null,
    price: finite(Number(row?.price)) ? Number(row.price) : null,
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

  const schemaValid = accountSnapshot?.schemaId === ARK_ACCOUNT_SNAPSHOT_SCHEMA;
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

  const criticalSourceProblem = freshness.state !== 'FRESH' || safety.state !== 'LOCKED';
  const runtimeBlocked = runtime.state === 'BLOCKED';
  const readiness = criticalSourceProblem || runtimeBlocked || pipeline.state === 'BLOCKED' || pipeline.state === 'INVALID'
    ? 'BLOCKED'
    : pipeline.state === 'LOCKED_READY'
      ? 'LOCKED_READY'
      : 'LOCKED_NO_INTENT';

  const buyingPower = schemaValid && finite(Number(accountSnapshot.buyingPower)) ? Number(accountSnapshot.buyingPower) : null;
  const activeIntent = lockedPipeline?.draft && typeof lockedPipeline.draft === 'object'
    ? Object.freeze({
        symbol: normalizeSymbol(lockedPipeline.draft.symbol),
        side: asText(lockedPipeline.draft.side),
        quantity: finite(Number(lockedPipeline.draft.quantity)) ? Number(lockedPipeline.draft.quantity) : null,
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
      source: schemaValid ? asText(accountSnapshot.source) : null,
      mode: schemaValid ? asText(accountSnapshot.mode) : null,
      freshness,
    }),
    safety,
    system: Object.freeze({
      health: criticalSourceProblem || runtimeBlocked ? 'BLOCKED' : 'READ_ONLY_OK',
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
  normalizeSymbol,
  snapshotFreshness,
  sourceSafety,
  ownershipProjection,
  projectPositions,
  projectOrders,
  projectExecutions,
  pipelineProjection,
  runtimeSafetyProjection,
});
