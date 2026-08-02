export function generateAccuracyDashboardReport(data={}){

const summary=data.summary??{};
const trade=data.tradePerformance??{};
const risk=data.riskAdjusted??{};
const health=data.health??{};

return{

generatedAt:new Date().toISOString(),

overview:{
accuracy:summary.accuracy??0,
profitFactor:trade.profitFactor??0,
sharpe:risk.sharpeRatio??0,
drawdown:risk.maxDrawdown??0,
},

health,

};

}

export default generateAccuracyDashboardReport;
