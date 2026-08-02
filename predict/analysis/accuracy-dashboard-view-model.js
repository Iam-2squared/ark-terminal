export function createAccuracyDashboardViewModel(data = {}) {
  const summary = data.summary ?? {};
  const trade = data.tradePerformance ?? {};
  const risk = data.riskAdjusted ?? {};
  const calibration = data.confidenceCalibration ?? {};
  const health = data.health ?? {};
  const metadata = data.metadata ?? {};

  const percent = (v) =>
    Number.isFinite(Number(v))
      ? `${(Number(v) * 100).toFixed(2)}%`
      : "-";

  const number = (v, d = 2) =>
    Number.isFinite(Number(v))
      ? Number(v).toFixed(d)
      : "-";

  return {
    cards: [
      {
        id: "accuracy",
        title: "Accuracy",
        value: percent(summary.accuracy),
      },
      {
        id: "buy",
        title: "BUY Win Rate",
        value: percent(summary.buy?.winRate),
      },
      {
        id: "sell",
        title: "SELL Win Rate",
        value: percent(summary.sell?.winRate),
      },
      {
        id: "profitFactor",
        title: "Profit Factor",
        value: number(trade.profitFactor),
      },
      {
        id: "sharpe",
        title: "Sharpe",
        value: number(risk.sharpeRatio),
      },
      {
        id: "sortino",
        title: "Sortino",
        value: number(risk.sortinoRatio),
      },
      {
        id: "calmar",
        title: "Calmar",
        value: number(risk.calmarRatio),
      },
      {
        id: "drawdown",
        title: "Max DD",
        value: percent(risk.maxDrawdown),
      },
    ],

    calibration,

    health,

    metadata,

    raw: data,
  };
}

export default createAccuracyDashboardViewModel;
