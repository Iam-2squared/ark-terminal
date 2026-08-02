export const TRADE_HISTORY_ENRICHER_VERSION =
  "trade-history-enricher-v1";

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function number(value,fallback=null){
  return finite(value)
    ? Number(value)
    : fallback;
}

export function enrichTrade(trade={}){

  const gross =
    number(trade.grossPnl);

  const commission =
    number(trade.commissionCost,0);

  const spread =
    number(trade.spreadCost,0);

  const slippage =
    number(trade.slippageCost,0);

  const totalTradingCost =
    commission+
    spread+
    slippage;

  const net =
    finite(gross)
      ? gross-totalTradingCost
      : number(trade.netPnl);

  return{
    ...trade,

    grossPnl:gross,
    commissionCost:commission,
    spreadCost:spread,
    slippageCost:slippage,

    totalTradingCost,

    netPnl:net,

    highestPrice:
      number(
        trade.highestPrice ??
        trade.maxPrice,
      ),

    lowestPrice:
      number(
        trade.lowestPrice ??
        trade.minPrice,
      ),
  };
}

export function enrichTradeHistory(
  trades=[],
){
  return trades.map(
    enrichTrade,
  );
}

export const
TradeHistoryEnricherInternals={
  finite,
  number,
};