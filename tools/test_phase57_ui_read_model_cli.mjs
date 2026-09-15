import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import {freezeOwnershipBaseline} from './phase57_cash_upstream_request.mjs';
import {exportArkTerminalUiReadModel} from './phase57_ui_read_model_cli.mjs';

const NOW = '2026-09-15T13:00:20.000Z';

function safeSnapshot(capturedAt = '2026-09-15T13:00:01.000Z') {
  return {
    schemaId: 'ARK_ACCOUNT_READONLY_SNAPSHOT_V2',
    capturedAt,
    captureCompletedAt: capturedAt,
    source: 'MARKETSPEED_II_RSS',
    mode: 'READ_ONLY',
    positions: [{symbol: '408A', name: 'fixture', account: '特定', quantity: 180}],
    orders: [],
    executions: [],
    buyingPower: 2605,
    safety: {
      executionAllowed: false,
      brokerWriteAllowed: false,
      excelOrderWriteAllowed: false,
      rssOrderFunctionAllowed: false,
      liveTradingAllowed: false,
      paperTradingAllowed: false,
      automaticPromotionAllowed: false,
      productionUpdateAllowed: false,
      transmitted: false,
    },
  };
}

function writeJson(file, value) {
  fs.writeFileSync(file, JSON.stringify(value));
}

test('file exporter emits only the read-only projection from explicit inputs', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'ark-ui-read-model-'));
  try {
    const snapshotPath = path.join(root, 'snapshot.json');
    const ownershipPath = path.join(root, 'ownership.json');
    const pipelinePath = path.join(root, 'pipeline.json');
    const runtimePath = path.join(root, 'runtime.json');
    const outputPath = path.join(root, 'ui.json');

    writeJson(snapshotPath, safeSnapshot());
    writeJson(ownershipPath, freezeOwnershipBaseline({
      capturedAt: '2026-09-15T12:50:00.000Z',
      source: 'TEST_ONLY',
      externalPositions: [{symbol: '408A', quantity: 180}],
      arkManagedPositions: [],
    }));
    writeJson(pipelinePath, {
      status: 'BLOCKED',
      stage: 'G9',
      reconciliation: {status: 'RECONCILIATION_PASS', blockers: []},
      candidate: {eligible: false, blockers: ['INSUFFICIENT_CASH']},
    });
    writeJson(runtimePath, {killSwitchLatched: false, faults: []});

    const model = exportArkTerminalUiReadModel({
      snapshotPath,
      ownershipPath,
      pipelinePath,
      runtimeSafetyPath: runtimePath,
      outputPath,
      generatedAt: NOW,
    });

    assert.equal(model.source.freshness.state, 'FRESH');
    assert.equal(model.home.buyingPower, 2605);
    assert.equal(model.positions[0].ownership, 'EXTERNAL');
    assert.equal(model.system.pipeline.state, 'BLOCKED');
    assert.equal(model.system.tradeReadiness, 'BLOCKED');
    assert.equal(model.mutationCapabilities.orderSubmit, false);

    const persisted = JSON.parse(fs.readFileSync(outputPath, 'utf8'));
    assert.equal(persisted.schemaId, 'ARK_TERMINAL_UI_READ_MODEL_V1');
    assert.equal(persisted.readOnly, true);
    assert.equal(persisted.mutationCapabilities.rssOrderFunction, false);
  } finally {
    fs.rmSync(root, {recursive: true, force: true});
  }
});

test('file exporter preserves stale semantics and refuses output overwrite', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'ark-ui-read-model-'));
  try {
    const snapshotPath = path.join(root, 'snapshot.json');
    const outputPath = path.join(root, 'ui.json');
    writeJson(snapshotPath, safeSnapshot('2026-09-15T12:00:00.000Z'));

    const model = exportArkTerminalUiReadModel({snapshotPath, outputPath, generatedAt: NOW});
    assert.equal(model.source.freshness.state, 'STALE');
    assert.equal(model.system.tradeReadiness, 'BLOCKED');
    assert.throws(
      () => exportArkTerminalUiReadModel({snapshotPath, outputPath, generatedAt: NOW}),
      /OUTPUT_ALREADY_EXISTS/,
    );
  } finally {
    fs.rmSync(root, {recursive: true, force: true});
  }
});
