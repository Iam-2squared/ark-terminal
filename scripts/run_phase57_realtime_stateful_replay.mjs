import fs from "node:fs";
import {
  STRATEGY_IDS,
  createRealtimeSessionState,
  appendLedgerEvent,
  dashboardSnapshot,
} from "../predict/realtime/phase57-stateful-contract.js";

const inputPath = process.argv[2];
if (!inputPath) throw new Error("usage: node scripts/run_phase57_realtime_stateful_replay.mjs <json>");
const input = JSON.parse(fs.readFileSync(inputPath, "utf8"));
const state = createRealtimeSessionState({ sessionDate: input.sessionDate, initialCapital: input.initialCapital });

for (const point of input.points ?? []) {
  if (!point.at) throw new Error("point.at required");
  if (state.lastBarTime && point.at <= state.lastBarTime) throw new Error("points must be strictly increasing");
  state.lastBarTime = point.at;
  state.selection.V1 = [...(point.selectedV1 ?? [])];
  state.selection.V2 = [...(point.selectedV2 ?? [])];
  appendLedgerEvent(state, {
    eventId: `${input.sessionDate}:${point.at}:BAR`,
    at: point.at,
    type: "BAR_COMMITTED",
    selectionV1: state.selection.V1,
    selectionV2: state.selection.V2,
  });
  for (const strategyId of STRATEGY_IDS) {
    appendLedgerEvent(state, {
      eventId: `${input.sessionDate}:${point.at}:SNAPSHOT:${strategyId}`,
      at: point.at,
      type: "STRATEGY_SNAPSHOT",
      snapshot: dashboardSnapshot(state, point.at).strategies.find((x) => x.strategyId === strategyId),
    });
  }
}

process.stdout.write(`${JSON.stringify({
  contract: "phase57-realtime-stateful-r1",
  sessionDate: state.sessionDate,
  lastBarTime: state.lastBarTime,
  strategyCount: STRATEGY_IDS.length,
  ledgerEventCount: state.ledger.length,
  dashboard: dashboardSnapshot(state),
  safety: state.safety,
}, null, 2)}\n`);
