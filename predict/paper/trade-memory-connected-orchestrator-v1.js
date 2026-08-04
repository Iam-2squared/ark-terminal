import {
  FinalTradingOrchestratorV3,
} from "./final-trading-orchestrator-v3.js";

import {
  saveProcessedExecutionToTradeMemory,
} from "../trading/execution-trade-memory-v1.js";

export const TRADE_MEMORY_CONNECTED_ORCHESTRATOR_V1_VERSION =
  "trade-memory-connected-orchestrator-v1";

export class TradeMemoryConnectedOrchestratorV1
  extends FinalTradingOrchestratorV3 {
  constructor({
    modelVersion = null,
    ...options
  } = {}) {
    super(options);
    this.modelVersion = modelVersion;
  }

  processMarket(snapshot = {}) {
    const processed =
      super.processMarket(snapshot);

    const cycles =
      this.getCycles();

    return processed.map((result) => {
      if (!result?.execution) {
        return result;
      }

      const cycle =
        cycles.find(
          (candidate) =>
            candidate.executionOrderId ===
            result.execution.orderId,
        ) ?? null;

      const tradeMemory =
        saveProcessedExecutionToTradeMemory({
          cycle,
          processedResult: result,
          modelVersion: this.modelVersion,
          timestamp: snapshot.timestamp,
        });

      return {
        ...result,
        tradeMemory,
      };
    });
  }

  getState() {
    return {
      ...super.getState(),
      integrationVersion:
        TRADE_MEMORY_CONNECTED_ORCHESTRATOR_V1_VERSION,
      modelVersion:
        this.modelVersion,
    };
  }
}

export default TradeMemoryConnectedOrchestratorV1;
