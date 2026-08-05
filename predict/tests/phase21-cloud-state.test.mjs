import assert from "node:assert/strict";
import test from "node:test";

import {
  buildCloudRecordEnvelope,
  validateCloudCollection,
  validateCloudRecordId,
  assertNoSensitiveCloudFields,
} from "../../api/cloud-state.js";

import {
  executeCloudKvCommand,
  getAllCloudHashFields,
  resolveCloudKvConfig,
} from "../../api/_cloud-kv.js";

test(
  "Cloud state accepts only allowlisted learning collections",
  () => {
    assert.equal(
      validateCloudCollection("predictions"),
      "predictions",
    );

    assert.equal(
      validateCloudCollection("forward_test_results"),
      "forward_test_results",
    );

    assert.throws(
      () => validateCloudCollection("real_account"),
      /クラウド保存できません/,
    );

    assert.throws(
      () => validateCloudCollection("broker_credentials"),
      /クラウド保存できません/,
    );
  },
);

test(
  "Cloud state rejects invalid ids and sensitive nested fields",
  () => {
    assert.equal(
      validateCloudRecordId("prediction-123:5d"),
      "prediction-123:5d",
    );

    assert.throws(
      () => validateCloudRecordId("bad id with spaces"),
      /IDが不正/,
    );

    assert.throws(
      () => assertNoSensitiveCloudFields({
        model: {
          api_key:
            "must-not-leave-server",
        },
      }),
      /機密情報/,
    );

    assert.throws(
      () => assertNoSensitiveCloudFields({
        broker: {
          accountNumber:
            "12345678",
        },
      }),
      /機密情報/,
    );
  },
);

test(
  "Cloud record envelope preserves creation time on updates",
  () => {
    const first = buildCloudRecordEnvelope({
      collection:
        "predictions",
      id:
        "prediction-1",
      data: {
        symbol:
          "7203.T",
        status:
          "pending",
      },
      now:
        () => new Date("2026-08-01T00:00:00.000Z"),
    });

    const second = buildCloudRecordEnvelope({
      collection:
        "predictions",
      id:
        "prediction-1",
      data: {
        symbol:
          "7203.T",
        status:
          "resolved",
      },
      existing:
        first,
      now:
        () => new Date("2026-08-06T00:00:00.000Z"),
    });

    assert.equal(
      second.createdAt,
      first.createdAt,
    );

    assert.equal(
      second.updatedAt,
      "2026-08-06T00:00:00.000Z",
    );

    assert.equal(
      second.data.status,
      "resolved",
    );
  },
);

test(
  "REST KV adapter keeps credentials server-side",
  async () => {
    const environment = {
      ARK_KV_REST_API_URL:
        "https://kv.example.invalid",
      ARK_KV_REST_API_TOKEN:
        "server-only-token",
    };

    const requests = [];
    const fetchImpl = async (url, options) => {
      requests.push({
        url,
        options,
      });

      return {
        ok: true,
        status: 200,
        json:
          async () => ({
            result:
              "OK",
          }),
      };
    };

    const result = await executeCloudKvCommand(
      ["PING"],
      {
        environment,
        fetchImpl,
      },
    );

    assert.equal(result, "OK");
    assert.equal(requests.length, 1);
    assert.equal(
      requests[0].options.headers.Authorization,
      "Bearer server-only-token",
    );
    assert.equal(
      requests[0].options.body,
      '["PING"]',
    );

    assert.deepEqual(
      resolveCloudKvConfig(environment),
      {
        configured: true,
        url:
          "https://kv.example.invalid",
        token:
          "server-only-token",
      },
    );
  },
);

test(
  "REST KV HGETALL accepts array responses",
  async () => {
    const entries = await getAllCloudHashFields(
      "predictions",
      {
        environment: {
          ARK_KV_REST_API_URL:
            "https://kv.example.invalid",
          ARK_KV_REST_API_TOKEN:
            "token",
        },
        fetchImpl:
          async () => ({
            ok: true,
            status: 200,
            json:
              async () => ({
                result: [
                  "id-1",
                  '{"value":1}',
                  "id-2",
                  '{"value":2}',
                ],
              }),
          }),
      },
    );

    assert.deepEqual(
      entries,
      [
        {
          id: "id-1",
          value: '{"value":1}',
        },
        {
          id: "id-2",
          value: '{"value":2}',
        },
      ],
    );
  },
);
