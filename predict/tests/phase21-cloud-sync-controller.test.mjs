import assert from "node:assert/strict";
import test from "node:test";

import {
  CloudSyncControllerInternals,
} from "../cloud/cloud-sync-controller.js";

function element() {
  return {
    textContent:
      "",
    hidden:
      false,
    disabled:
      false,
    dataset:
      {},
  };
}

test(
  "Cloud sync UI shows connected and disconnected states",
  () => {
    const elements = {
      status:
        element(),
      secret:
        element(),
      connect:
        element(),
      disconnect:
        element(),
      message:
        element(),
    };

    CloudSyncControllerInternals.renderState(
      elements,
      {
        configured:
          true,
        authenticated:
          true,
        loading:
          false,
      },
    );

    assert.equal(
      elements.status.textContent,
      "接続済み",
    );
    assert.equal(
      elements.secret.hidden,
      true,
    );
    assert.equal(
      elements.connect.hidden,
      true,
    );
    assert.equal(
      elements.disconnect.hidden,
      false,
    );

    CloudSyncControllerInternals.renderState(
      elements,
      {
        configured:
          false,
        authenticated:
          false,
        loading:
          false,
      },
    );

    assert.equal(
      elements.status.textContent,
      "未設定",
    );
    assert.equal(
      elements.connect.disabled,
      true,
    );
  },
);

test(
  "Cloud sync message records its semantic kind",
  () => {
    const elements = {
      message:
        element(),
    };

    CloudSyncControllerInternals.displayMessage(
      elements,
      "同期完了",
      "success",
    );

    assert.equal(
      elements.message.textContent,
      "同期完了",
    );
    assert.equal(
      elements.message.dataset.kind,
      "success",
    );
  },
);
