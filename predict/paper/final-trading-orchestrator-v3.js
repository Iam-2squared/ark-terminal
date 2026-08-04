import {
  StrategyEngineV3,
} from "../analysis/strategy-engine-v3.js";

import {
  RiskManagementEngineV3,
} from "../portfolio/risk-management-engine-v3.js";

import {
  PortfolioEngineV3,
} from "../portfolio/portfolio-engine-v3.js";

import {
  PerformanceAnalyticsEngineV3,
} from "../portfolio/performance-analytics-engine-v3.js";

import {
  ExecutionSimulatorV3,
} from "./execution-simulator-v3.js";

import {
  TransactionCostEngineV3,
} from "./transaction-cost-engine-v3.js";

export const FINAL_TRADING_ORCHESTRATOR_V3_VERSION =
  "final-trading-orchestrator-v3";

const STATES =
  Object.freeze({
    IDLE:
      "IDLE",

    ANALYZING:
      "ANALYZING",

    BLOCKED:
      "BLOCKED",

    ORDER_READY:
      "ORDER_READY",

    ORDER_OPEN:
      "ORDER_OPEN",

    PARTIALLY_FILLED:
      "PARTIALLY_FILLED",

    FILLED:
      "FILLED",

    FAILED:
      "FAILED",

    STOPPED:
      "STOPPED",
  });

function clone(value) {
  return value === undefined
    ? undefined
    : structuredClone(value);
}

function finiteNumber(
  value,
  fallback = 0,
) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return fallback;
  }

  const number =
    Number(value);

  return Number.isFinite(number)
    ? number
    : fallback;
}

function positiveNumber(
  value,
  fallback = 0,
) {
  return Math.max(
    0,
    finiteNumber(
      value,
      fallback,
    ),
  );
}

function round(
  value,
  digits = 6,
) {
  if (!Number.isFinite(value)) {
    return null;
  }

  const factor =
    10 ** digits;

  return (
    Math.round(
      value *
      factor,
    ) /
    factor
  );
}

function normalizeTimestamp(value) {
  const milliseconds =
    typeof value === "number"
      ? value
      : Date.parse(
          value ??
          new Date().toISOString(),
        );

  if (!Number.isFinite(milliseconds)) {
    throw new TypeError(
      "Trading orchestrator timestamp is invalid.",
    );
  }

  return new Date(
    milliseconds,
  ).toISOString();
}

function normalizeSymbol(value) {
  const symbol =
    String(
      value ??
      "",
    )
      .trim()
      .toUpperCase();

  if (!symbol) {
    throw new TypeError(
      "Trading orchestrator symbol is required.",
    );
  }

  return symbol;
}

function createId(
  prefix,
  sequence,
) {
  return `${prefix}-${String(sequence).padStart(8, "0")}`;
}

function portfolioContext(
  portfolioEngine,
) {
  const statistics =
    portfolioEngine
      .calculateStatistics();

  return {
    cash:
      statistics.account.cash,

    equity:
      statistics.account.equity,

    marketValue:
      statistics.account.marketValue,

    realizedPnl:
      statistics.account.realizedPnl,

    unrealizedPnl:
      statistics.account.unrealizedPnl,

    dailyReturnPercent:
      statistics.performance
        .dailyReturnPercent,

    drawdownPercent:
      statistics.risk
        .maximumDrawdownPercent,

    portfolioBeta:
      statistics.risk
        .portfolioBeta,

    portfolioVolatility:
      statistics.risk
        .portfolioVolatility,

    positions:
      portfolioEngine
        .getPositions(),
  };
}

function deriveSide(action) {
  if (action === "BUY") {
    return "BUY";
  }

  if (action === "SELL") {
    return "SELL";
  }

  return null;
}

function orderStatusToState(status) {
  switch (status) {
    case "FILLED":
      return STATES.FILLED;

    case "PARTIALLY_FILLED":
      return STATES.PARTIALLY_FILLED;

    case "OPEN":
      return STATES.ORDER_OPEN;

    default:
      return STATES.IDLE;
  }
}

export class FinalTradingOrchestratorV3 {
  constructor({
    initialCash = 1000000,
    strategyConfig = {},
    riskConfig = {},
    portfolioConfig = {},
    executionConfig = {},
    transactionCostConfig = {},
    performanceConfig = {},
  } = {}) {
    this.strategy =
      new StrategyEngineV3(
        strategyConfig,
      );

    this.risk =
      new RiskManagementEngineV3({
        limits:
          riskConfig,
      });

    this.portfolio =
      new PortfolioEngineV3({
        initialCash,

        ...portfolioConfig,
      });

    this.execution =
      new ExecutionSimulatorV3(
        executionConfig,
      );

    this.transactionCost =
      new TransactionCostEngineV3(
        transactionCostConfig,
      );

    this.performance =
      new PerformanceAnalyticsEngineV3(
        performanceConfig,
      );

    this.state =
      STATES.IDLE;

    this.enabled = true;
    this.killSwitch = false;
    this.killSwitchReason = null;

    this.cycleSequence = 0;
    this.eventSequence = 0;

    this.cycles = [];
    this.events = [];
    this.pendingOrders =
      new Map();

    this.lastError = null;
  }

  recordEvent({
    type,
    data = {},
    timestamp =
      new Date().toISOString(),
  }) {
    this.eventSequence += 1;

    const event = {
      id:
        createId(
          "ORCH-EVENT",
          this.eventSequence,
        ),

      type:
        String(type),

      timestamp:
        normalizeTimestamp(
          timestamp,
        ),

      data:
        clone(data),
    };

    this.events.push(
      event,
    );

    return clone(
      event,
    );
  }

  activateKillSwitch(
    reason =
      "MANUAL_KILL_SWITCH",
  ) {
    this.killSwitch = true;

    this.killSwitchReason =
      String(reason);

    this.enabled = false;
    this.state =
      STATES.STOPPED;

    this.risk
      .activateKillSwitch(
        this.killSwitchReason,
      );

    this.recordEvent({
      type:
        "KILL_SWITCH_ACTIVATED",

      data: {
        reason:
          this.killSwitchReason,
      },
    });

    return this.getState();
  }

  deactivateKillSwitch() {
    this.killSwitch = false;
    this.killSwitchReason = null;
    this.enabled = true;
    this.state =
      STATES.IDLE;

    this.risk
      .deactivateKillSwitch();

    this.recordEvent({
      type:
        "KILL_SWITCH_DEACTIVATED",
    });

    return this.getState();
  }

  disable() {
    this.enabled = false;
    this.state =
      STATES.STOPPED;

    this.recordEvent({
      type:
        "ORCHESTRATOR_DISABLED",
    });

    return this.getState();
  }

  enable() {
    if (this.killSwitch) {
      throw new Error(
        "Cannot enable while kill switch is active.",
      );
    }

    this.enabled = true;
    this.state =
      STATES.IDLE;

    this.recordEvent({
      type:
        "ORCHESTRATOR_ENABLED",
    });

    return this.getState();
  }

  analyze({
    symbol,
    price,
    sector = "UNKNOWN",
    regime = "NEUTRAL",
    marketScore = 50,
    liquidityScore = 50,
    riskScore = 50,
    volatilityPercent = 0,
    signals = [],
    stopPrice = 0,
    requestedQuantity = null,
    timestamp =
      new Date().toISOString(),
  } = {}) {
    const evaluatedAt =
      normalizeTimestamp(
        timestamp,
      );

    const normalizedSymbol =
      normalizeSymbol(
        symbol,
      );

    const normalizedPrice =
      positiveNumber(
        price,
        0,
      );

    if (normalizedPrice <= 0) {
      throw new TypeError(
        "Trading price must be greater than zero.",
      );
    }

    this.cycleSequence += 1;

    const cycleId =
      createId(
        "TRADE-CYCLE",
        this.cycleSequence,
      );

    if (
      !this.enabled ||
      this.killSwitch
    ) {
      const blocked = {
        id:
          cycleId,

        timestamp:
          evaluatedAt,

        symbol:
          normalizedSymbol,

        state:
          STATES.BLOCKED,

        decision:
          "BLOCK",

        blockers: [
          this.killSwitch
            ? "KILL_SWITCH_ACTIVE"
            : "ORCHESTRATOR_DISABLED",
        ],
      };

      this.cycles.push(
        blocked,
      );

      return clone(
        blocked,
      );
    }

    this.state =
      STATES.ANALYZING;

    const portfolio =
      portfolioContext(
        this.portfolio,
      );

    const currentPosition =
      this.portfolio
        .getPosition(
          normalizedSymbol,
        );

    const strategyResult =
      this.strategy.evaluate({
        context: {
          symbol:
            normalizedSymbol,

          price:
            normalizedPrice,

          regime,

          riskScore,

          marketScore,

          liquidityScore,

          volatilityPercent,

          signals,

          currentPosition:
            currentPosition.quantity,

          portfolioExposurePercent:
            portfolio.equity <= 0
              ? 0
              : portfolio.marketValue /
                portfolio.equity *
                100,

          drawdownPercent:
            portfolio.drawdownPercent,
        },

        timestamp:
          evaluatedAt,
      });

    const side =
      deriveSide(
        strategyResult.action,
      );

    if (!side) {
      const cycle = {
        id:
          cycleId,

        timestamp:
          evaluatedAt,

        symbol:
          normalizedSymbol,

        state:
          strategyResult.action ===
            "BLOCK"
            ? STATES.BLOCKED
            : STATES.IDLE,

        decision:
          strategyResult.action,

        strategy:
          strategyResult,

        risk:
          null,

        order:
          null,
      };

      this.state =
        cycle.state;

      this.cycles.push(
        cycle,
      );

      this.recordEvent({
        type:
          "STRATEGY_NO_ORDER",

        data: {
          cycleId,

          symbol:
            normalizedSymbol,

          action:
            strategyResult.action,
        },

        timestamp:
          evaluatedAt,
      });

      return clone(
        cycle,
      );
    }

    let quantity =
      requestedQuantity ===
        null ||
      requestedQuantity ===
        undefined
        ? 0
        : Math.floor(
            positiveNumber(
              requestedQuantity,
              0,
            ),
          );

    if (
      side === "BUY" &&
      quantity <= 0 &&
      stopPrice > 0
    ) {
      const sizing =
        this.risk
          .calculatePositionSize({
            equity:
              portfolio.equity,

            entryPrice:
              normalizedPrice,

            stopPrice,

            riskPerTradePercent:
              1,

            lotSize:
              1,
          });

      quantity =
        sizing.quantity;
    }

    if (
      side === "SELL" &&
      quantity <= 0
    ) {
      quantity =
        Math.floor(
          currentPosition.quantity,
        );
    }

    if (quantity <= 0) {
      const cycle = {
        id:
          cycleId,

        timestamp:
          evaluatedAt,

        symbol:
          normalizedSymbol,

        state:
          STATES.BLOCKED,

        decision:
          "BLOCK",

        blockers: [
          "NO_APPROVED_QUANTITY",
        ],

        strategy:
          strategyResult,

        risk:
          null,

        order:
          null,
      };

      this.state =
        STATES.BLOCKED;

      this.cycles.push(
        cycle,
      );

      return clone(
        cycle,
      );
    }

    const riskResult =
      this.risk.evaluateOrder({
        order: {
          symbol:
            normalizedSymbol,

          side,

          quantity,

          price:
            normalizedPrice,

          stopPrice,

          sector,

          confidence:
            strategyResult.confidence,

          riskScore:
            riskScore,
        },

        portfolio,

        timestamp:
          evaluatedAt,
      });

    if (
      riskResult.decision ===
      "BLOCK" ||
      riskResult.approvedQuantity <=
      0
    ) {
      const cycle = {
        id:
          cycleId,

        timestamp:
          evaluatedAt,

        symbol:
          normalizedSymbol,

        state:
          STATES.BLOCKED,

        decision:
          "BLOCK",

        blockers:
          riskResult.blockers,

        strategy:
          strategyResult,

        risk:
          riskResult,

        order:
          null,
      };

      this.state =
        STATES.BLOCKED;

      this.cycles.push(
        cycle,
      );

      this.recordEvent({
        type:
          "ORDER_BLOCKED_BY_RISK",

        data: {
          cycleId,

          symbol:
            normalizedSymbol,

          blockers:
            riskResult.blockers,
        },

        timestamp:
          evaluatedAt,
      });

      return clone(
        cycle,
      );
    }

    const approvedQuantity =
      riskResult
        .approvedQuantity;

    const estimatedCost =
      this.transactionCost
        .estimate({
          trade: {
            symbol:
              normalizedSymbol,

            side,

            quantity:
              approvedQuantity,

            price:
              normalizedPrice,

            referencePrice:
              normalizedPrice,

            bid:
              normalizedPrice,

            ask:
              normalizedPrice,

            dailyVolume:
              0,

            volatilityPercent,

            market:
              "JP",
          },

          timestamp:
            evaluatedAt,
        });

    const orderProposal = {
      symbol:
        normalizedSymbol,

      side,

      type:
        "MARKET",

      quantity:
        approvedQuantity,

      price:
        normalizedPrice,

      stopPrice:
        positiveNumber(
          stopPrice,
          0,
        ),

      sector:
        String(
          sector ??
          "UNKNOWN",
        )
          .trim()
          .toUpperCase(),

      estimatedCost:
        estimatedCost.totalCost,
    };

    const cycle = {
      id:
        cycleId,

      timestamp:
        evaluatedAt,

      symbol:
        normalizedSymbol,

      state:
        STATES.ORDER_READY,

      decision:
        side,

      strategy:
        strategyResult,

      risk:
        riskResult,

      transactionCost:
        estimatedCost,

      order:
        orderProposal,
    };

    this.state =
      STATES.ORDER_READY;

    this.cycles.push(
      cycle,
    );

    this.recordEvent({
      type:
        "ORDER_PROPOSAL_READY",

      data: {
        cycleId,

        order:
          orderProposal,
      },

      timestamp:
        evaluatedAt,
    });

    return clone(
      cycle,
    );
  }

  submit({
    cycleId,
    timestamp =
      new Date().toISOString(),
  } = {}) {
    const submittedAt =
      normalizeTimestamp(
        timestamp,
      );

    if (
      !this.enabled ||
      this.killSwitch
    ) {
      throw new Error(
        "Trading orchestrator is not enabled.",
      );
    }

    const cycle =
      this.cycles.find(
        (
          candidate,
        ) =>
          candidate.id ===
          cycleId,
      );

    if (!cycle) {
      throw new Error(
        `Trading cycle not found: ${cycleId}`,
      );
    }

    if (
      cycle.state !==
      STATES.ORDER_READY
    ) {
      throw new Error(
        `Trading cycle is not order-ready: ${cycle.state}`,
      );
    }

    const submittedOrder =
      this.execution
        .submitOrder({
          symbol:
            cycle.order.symbol,

          side:
            cycle.order.side,

          type:
            cycle.order.type,

          quantity:
            cycle.order.quantity,

          metadata: {
            cycleId,

            sector:
              cycle.order.sector,

            signalScore:
              cycle.strategy
                .finalScore,
          },

          timestamp:
            submittedAt,
        });

    cycle.executionOrderId =
      submittedOrder.id;

    cycle.state =
      STATES.ORDER_OPEN;

    this.pendingOrders.set(
      submittedOrder.id,
      {
        cycleId,

        sector:
          cycle.order.sector,

        referencePrice:
          cycle.order.price,
      },
    );

    this.state =
      STATES.ORDER_OPEN;

    this.recordEvent({
      type:
        "ORDER_SUBMITTED",

      data: {
        cycleId,

        executionOrderId:
          submittedOrder.id,
      },

      timestamp:
        submittedAt,
    });

    return {
      cycle:
        clone(cycle),

      order:
        clone(
          submittedOrder,
        ),
    };
  }

  processMarket({
    symbol,
    bid,
    ask,
    last,
    volume = 0,
    availableLiquidity =
      Number.MAX_SAFE_INTEGER,
    volatilityPercent = 0,
    timestamp =
      new Date().toISOString(),
  } = {}) {
    const processedAt =
      normalizeTimestamp(
        timestamp,
      );

    const normalizedSymbol =
      normalizeSymbol(
        symbol,
      );

    const results =
      this.execution
        .processMarketSnapshot({
          markets: {
            [normalizedSymbol]: {
              bid,

              ask,

              last,

              volume,

              availableLiquidity,

              volatilityPercent,

              timestamp:
                processedAt,
            },
          },

          timestamp:
            processedAt,
        });

    const processed = [];

    for (
      const result of
      results
    ) {
      if (!result.execution) {
        processed.push(
          result,
        );

        continue;
      }

      const pending =
        this.pendingOrders.get(
          result.execution
            .orderId,
        );

      if (!pending) {
        processed.push(
          result,
        );

        continue;
      }

      const cycle =
        this.cycles.find(
          (
            candidate,
          ) =>
            candidate.id ===
            pending.cycleId,
        );

      const execution =
        result.execution;

      const transaction =
        this.transactionCost
          .estimate({
            trade: {
              symbol:
                execution.symbol,

              side:
                execution.side,

              quantity:
                execution.quantity,

              price:
                execution.executionPrice,

              referencePrice:
                execution.referencePrice,

              bid:

              ask,

              dailyVolume:
                volume,

              volatilityPercent,

              market:
                "JP",
            },

            timestamp:
              processedAt,
          });

      if (
        execution.side ===
        "BUY"
      ) {
        this.portfolio.buy({
          symbol:
            execution.symbol,

          quantity:
            execution.quantity,

          price:
            execution.executionPrice,

          sector:
            pending.sector,

          fee:
            transaction.totalCost,

          timestamp:
            processedAt,
        });
      }
      else {
        this.portfolio.sell({
          symbol:
            execution.symbol,

          quantity:
            execution.quantity,

          price:
            execution.executionPrice,

          fee:
            transaction.totalCost,

          timestamp:
            processedAt,
        });
      }

      const portfolio =
        portfolioContext(
          this.portfolio,
        );

      this.performance
        .addEquityPoint({
          timestamp:
            processedAt,

          equity:
            portfolio.equity,
        });

      if (cycle) {
        cycle.state =
          orderStatusToState(
            result.order.status,
          );

        cycle.execution =
          clone(
            execution,
          );

        cycle.actualTransactionCost =
          clone(
            transaction,
          );

        cycle.portfolioAfter =
          clone(
            portfolio,
          );
      }

      if (
        result.order.status ===
        "FILLED"
      ) {
        this.pendingOrders.delete(
          result.execution
            .orderId,
        );
      }

      this.state =
        orderStatusToState(
          result.order.status,
        );

      this.recordEvent({
        type:
          "EXECUTION_PROCESSED",

        data: {
          cycleId:
            pending.cycleId,

          execution,

          portfolio,
        },

        timestamp:
          processedAt,
      });

      processed.push({
        ...result,

        transactionCost:
          transaction,

        portfolio,
      });
    }

    return clone(
      processed,
    );
  }

  cancel({
    orderId,
    timestamp =
      new Date().toISOString(),
  } = {}) {
    const cancelled =
      this.execution
        .cancelOrder({
          orderId,

          timestamp,
        });

    const pending =
      this.pendingOrders.get(
        orderId,
      );

    if (pending) {
      const cycle =
        this.cycles.find(
          (
            candidate,
          ) =>
            candidate.id ===
            pending.cycleId,
        );

      if (cycle) {
        cycle.state =
          "CANCELLED";
      }

      this.pendingOrders.delete(
        orderId,
      );
    }

    this.state =
      STATES.IDLE;

    this.recordEvent({
      type:
        "ORDER_CANCELLED",

      data: {
        orderId,
      },

      timestamp,
    });

    return clone(
      cancelled,
    );
  }

  analyzePerformance({
    timestamp =
      new Date().toISOString(),
  } = {}) {
    if (
      this.performance
        .snapshot()
        .equityCurve
        .length === 0
    ) {
      const statistics =
        this.portfolio
          .calculateStatistics();

      this.performance
        .addEquityPoint({
          timestamp,

          equity:
            statistics.account
              .equity,
        });
    }

    return this.performance
      .analyze({
        timestamp,
      });
  }

  getCycle(cycleId) {
    return clone(
      this.cycles.find(
        (
          cycle,
        ) =>
          cycle.id ===
          cycleId,
      ) ??
      null,
    );
  }

  getCycles() {
    return clone(
      this.cycles,
    );
  }

  getEvents() {
    return clone(
      this.events,
    );
  }

  getState() {
    return {
      version:
        FINAL_TRADING_ORCHESTRATOR_V3_VERSION,

      state:
        this.state,

      enabled:
        this.enabled,

      killSwitch:
        this.killSwitch,

      killSwitchReason:
        this.killSwitchReason,

      cycleCount:
        this.cycles.length,

      eventCount:
        this.events.length,

      pendingOrderCount:
        this.pendingOrders.size,

      portfolio:
        this.portfolio
          .calculateStatistics(),

      lastError:
        clone(
          this.lastError,
        ),
    };
  }

  snapshot() {
    return {
      version:
        FINAL_TRADING_ORCHESTRATOR_V3_VERSION,

      state:
        this.state,

      enabled:
        this.enabled,

      killSwitch:
        this.killSwitch,

      killSwitchReason:
        this.killSwitchReason,

      cycleSequence:
        this.cycleSequence,

      eventSequence:
        this.eventSequence,

      cycles:
        clone(
          this.cycles,
        ),

      events:
        clone(
          this.events,
        ),

      pendingOrders:
        clone(
          [
            ...this.pendingOrders
              .entries(),
          ],
        ),

      portfolio:
        this.portfolio
          .snapshot(),

      strategy:
        this.strategy
          .snapshot(),

      performance:
        this.performance
          .snapshot(),
    };
  }

  restore(snapshot) {
    if (
      !snapshot ||
      typeof snapshot !==
        "object"
    ) {
      throw new TypeError(
        "Trading orchestrator snapshot is required.",
      );
    }

    this.state =
      snapshot.state ??
      STATES.IDLE;

    this.enabled =
      snapshot.enabled !==
      false;

    this.killSwitch =
      snapshot.killSwitch ===
      true;

    this.killSwitchReason =
      snapshot.killSwitchReason ??
      null;

    this.cycleSequence =
      positiveNumber(
        snapshot.cycleSequence,
        0,
      );

    this.eventSequence =
      positiveNumber(
        snapshot.eventSequence,
        0,
      );

    this.cycles =
      clone(
        snapshot.cycles ??
        [],
      );

    this.events =
      clone(
        snapshot.events ??
        [],
      );

    this.pendingOrders =
      new Map(
        clone(
          snapshot.pendingOrders ??
          [],
        ),
      );

    this.portfolio
      .restore(
        snapshot.portfolio,
      );

    this.strategy
      .restore(
        snapshot.strategy,
      );

    this.performance
      .restore(
        snapshot.performance,
      );

    if (this.killSwitch) {
      this.risk
        .activateKillSwitch(
          this.killSwitchReason ??
          "RESTORED_KILL_SWITCH",
        );
    }
    else {
      this.risk
        .deactivateKillSwitch();
    }

    return this.snapshot();
  }

  reset({
    timestamp =
      new Date().toISOString(),
  } = {}) {
    this.state =
      STATES.IDLE;

    this.enabled = true;
    this.killSwitch = false;
    this.killSwitchReason = null;

    this.cycleSequence = 0;
    this.eventSequence = 0;

    this.cycles = [];
    this.events = [];
    this.pendingOrders.clear();
    this.lastError = null;

    this.strategy.reset();
    this.risk.reset();
    this.execution.reset();
    this.transactionCost.reset();
    this.performance.reset();

    this.portfolio.reset({
      timestamp,
    });

    return this.getState();
  }
}

export const finalTradingOrchestratorV3 =
  new FinalTradingOrchestratorV3();

export default FinalTradingOrchestratorV3;