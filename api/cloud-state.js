import {
  requestHasCloudSession,
  requestIsSameOrigin,
} from "./_cloud-auth.js";

import {
  cloudKvConfigured,
  deleteCloudHashField,
  getAllCloudHashFields,
  getCloudHashField,
  setCloudHashField,
  setCloudHashFields,
} from "./_cloud-kv.js";

export const CLOUD_RECORD_VERSION =
  "ark-cloud-record-v1";

export const ALLOWED_CLOUD_COLLECTIONS = Object.freeze([
  "predictions",
  "prediction_outcomes",
  "paper_orders",
  "paper_positions",
  "paper_account_snapshots",
  "learning_reports",
  "candidate_models",
  "model_versions",
  "forward_test_results",
]);

const ALLOWED_COLLECTION_SET =
  new Set(ALLOWED_CLOUD_COLLECTIONS);

const MAX_RECORD_BYTES = 96_000;
const MAX_BATCH_BYTES = 700_000;
const MAX_BATCH_RECORDS = 100;
const MAX_LIST_RECORDS = 500;

const FORBIDDEN_NORMALIZED_KEYS = new Set([
  "password",
  "passphrase",
  "secret",
  "clientsecret",
  "apikey",
  "accesstoken",
  "refreshtoken",
  "authorization",
  "cookie",
  "setcookie",
  "brokercredentials",
  "accountnumber",
  "loginid",
  "rsspassword",
  "brokerpassword",
  "privatekey",
]);

class CloudStateError extends Error {
  constructor(message, status = 400, code = "CLOUD_STATE_ERROR") {
    super(message);
    this.name = "CloudStateError";
    this.status = status;
    this.code = code;
  }
}

function normalizedKey(value) {
  return String(value ?? "")
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "");
}

export function validateCloudCollection(value) {
  const collection = String(value ?? "")
    .trim()
    .toLowerCase();

  if (!ALLOWED_COLLECTION_SET.has(collection)) {
    throw new CloudStateError(
      "この種類のデータはクラウド保存できません。",
      400,
      "COLLECTION_NOT_ALLOWED",
    );
  }

  return collection;
}

export function validateCloudRecordId(value) {
  const id = String(value ?? "").trim();

  if (!/^[A-Za-z0-9][A-Za-z0-9._:-]{0,159}$/.test(id)) {
    throw new CloudStateError(
      "クラウドレコードIDが不正です。",
      400,
      "INVALID_RECORD_ID",
    );
  }

  return id;
}

export function assertNoSensitiveCloudFields(
  value,
  path = "data",
  seen = new WeakSet(),
) {
  if (
    value === null ||
    value === undefined ||
    typeof value !== "object"
  ) {
    return;
  }

  if (seen.has(value)) {
    throw new CloudStateError(
      "循環参照を含むデータは保存できません。",
      400,
      "CYCLIC_DATA_NOT_ALLOWED",
    );
  }

  seen.add(value);

  if (Array.isArray(value)) {
    value.forEach((item, index) =>
      assertNoSensitiveCloudFields(
        item,
        `${path}[${index}]`,
        seen,
      ),
    );
    seen.delete(value);
    return;
  }

  for (const [key, nested] of Object.entries(value)) {
    if (FORBIDDEN_NORMALIZED_KEYS.has(normalizedKey(key))) {
      throw new CloudStateError(
        `機密情報の可能性がある項目は保存できません: ${path}.${key}`,
        400,
        "SENSITIVE_FIELD_REJECTED",
      );
    }

    assertNoSensitiveCloudFields(
      nested,
      `${path}.${key}`,
      seen,
    );
  }

  seen.delete(value);
}

function parseJsonBody(body, maximumBytes) {
  if (typeof body === "string") {
    if (Buffer.byteLength(body, "utf8") > maximumBytes) {
      throw new CloudStateError(
        "送信データが大きすぎます。",
        413,
        "REQUEST_TOO_LARGE",
      );
    }

    try {
      return JSON.parse(body);
    }
    catch {
      throw new CloudStateError(
        "JSONを読み取れませんでした。",
        400,
        "INVALID_JSON",
      );
    }
  }

  let serialized;

  try {
    serialized = JSON.stringify(body ?? {});
  }
  catch {
    throw new CloudStateError(
      "JSONへ変換できないデータです。",
      400,
      "INVALID_JSON_VALUE",
    );
  }

  if (Buffer.byteLength(serialized, "utf8") > maximumBytes) {
    throw new CloudStateError(
      "送信データが大きすぎます。",
      413,
      "REQUEST_TOO_LARGE",
    );
  }

  return body ?? {};
}

function validateRecordData(data) {
  if (!data || typeof data !== "object" || Array.isArray(data)) {
    throw new CloudStateError(
      "保存データはJSONオブジェクトである必要があります。",
      400,
      "INVALID_RECORD_DATA",
    );
  }

  assertNoSensitiveCloudFields(data);

  const serialized = JSON.stringify(data);

  if (Buffer.byteLength(serialized, "utf8") > MAX_RECORD_BYTES) {
    throw new CloudStateError(
      "1件の保存データが大きすぎます。",
      413,
      "RECORD_TOO_LARGE",
    );
  }

  return data;
}

function parseStoredEnvelope(value) {
  if (!value) return null;

  try {
    const parsed = JSON.parse(String(value));

    if (
      parsed?.version !== CLOUD_RECORD_VERSION ||
      !parsed?.id ||
      !parsed?.collection ||
      !parsed?.data
    ) {
      return null;
    }

    return parsed;
  }
  catch {
    return null;
  }
}

export function buildCloudRecordEnvelope({
  collection,
  id,
  data,
  existing = null,
  now = () => new Date(),
} = {}) {
  const safeCollection = validateCloudCollection(collection);
  const safeId = validateCloudRecordId(id);
  const safeData = validateRecordData(data);
  const timestamp = now().toISOString();

  return {
    version: CLOUD_RECORD_VERSION,
    collection: safeCollection,
    id: safeId,
    createdAt:
      existing?.createdAt ??
      timestamp,
    updatedAt: timestamp,
    data: safeData,
  };
}

function queryValue(request, name) {
  const direct = request?.query?.[name];

  if (Array.isArray(direct)) {
    return direct[0];
  }

  if (direct !== undefined) {
    return direct;
  }

  try {
    const url = new URL(
      request?.url ?? "",
      "https://ark-terminal.invalid",
    );

    return url.searchParams.get(name);
  }
  catch {
    return null;
  }
}

function setCommonHeaders(response) {
  response.setHeader("Cache-Control", "no-store");
  response.setHeader("X-Content-Type-Options", "nosniff");
  response.setHeader(
    "Access-Control-Allow-Methods",
    "GET, PUT, POST, DELETE, OPTIONS",
  );
  response.setHeader(
    "Access-Control-Allow-Headers",
    "Content-Type",
  );
}

function assertCloudReady(request) {
  if (!cloudKvConfigured(process.env)) {
    throw new CloudStateError(
      "クラウド保存先が設定されていません。",
      503,
      "CLOUD_STORAGE_NOT_CONFIGURED",
    );
  }

  if (!requestHasCloudSession(request, {
    environment: process.env,
  })) {
    throw new CloudStateError(
      "クラウド保存へ接続してください。",
      401,
      "CLOUD_SESSION_REQUIRED",
    );
  }
}

async function readOne(collection, id) {
  const stored = await getCloudHashField(
    collection,
    id,
  );

  return parseStoredEnvelope(stored);
}

async function readMany(collection, limit) {
  const entries = await getAllCloudHashFields(
    collection,
  );

  return entries
    .map((entry) => parseStoredEnvelope(entry.value))
    .filter(Boolean)
    .sort((first, second) =>
      String(second.updatedAt)
        .localeCompare(String(first.updatedAt)),
    )
    .slice(0, limit);
}

async function writeOne(payload) {
  const collection = validateCloudCollection(payload?.collection);
  const id = validateCloudRecordId(payload?.id);
  const existing = await readOne(collection, id);
  const envelope = buildCloudRecordEnvelope({
    collection,
    id,
    data: payload?.data,
    existing,
  });

  await setCloudHashField(
    collection,
    id,
    JSON.stringify(envelope),
  );

  return envelope;
}

async function writeBatch(payload) {
  const collection = validateCloudCollection(payload?.collection);
  const records = Array.isArray(payload?.records)
    ? payload.records
    : [];

  if (records.length === 0 || records.length > MAX_BATCH_RECORDS) {
    throw new CloudStateError(
      `一括保存は1〜${MAX_BATCH_RECORDS}件で指定してください。`,
      400,
      "INVALID_BATCH_SIZE",
    );
  }

  const timestamp = new Date();
  const envelopes = records.map((record) =>
    buildCloudRecordEnvelope({
      collection,
      id: record?.id,
      data: record?.data,
      now: () => timestamp,
    }),
  );

  await setCloudHashFields(
    collection,
    envelopes.map((envelope) => ({
      id: envelope.id,
      value: JSON.stringify(envelope),
    })),
  );

  return envelopes;
}

export default async function handler(request, response) {
  setCommonHeaders(response);

  if (request.method === "OPTIONS") {
    return response.status(204).end();
  }

  try {
    if (
      ["PUT", "POST", "DELETE"].includes(request.method) &&
      !requestIsSameOrigin(request)
    ) {
      throw new CloudStateError(
        "同一オリジンからのみ更新できます。",
        403,
        "ORIGIN_NOT_ALLOWED",
      );
    }

    assertCloudReady(request);

    if (request.method === "GET") {
      const collection = validateCloudCollection(
        queryValue(request, "collection"),
      );
      const rawId = queryValue(request, "id");

      if (rawId) {
        const id = validateCloudRecordId(rawId);
        const record = await readOne(collection, id);

        if (!record) {
          return response.status(404).json({
            error: "クラウドレコードが見つかりません。",
            code: "RECORD_NOT_FOUND",
          });
        }

        return response.status(200).json({
          record,
          meta: {
            brokerWriteAllowed: false,
            realAccountUploadAllowed: false,
          },
        });
      }

      const limit = Math.min(
        MAX_LIST_RECORDS,
        Math.max(
          1,
          Math.floor(Number(queryValue(request, "limit")) || 100),
        ),
      );
      const records = await readMany(collection, limit);

      return response.status(200).json({
        records,
        count: records.length,
        limit,
        meta: {
          brokerWriteAllowed: false,
          realAccountUploadAllowed: false,
        },
      });
    }

    if (request.method === "PUT") {
      const payload = parseJsonBody(
        request.body,
        MAX_RECORD_BYTES + 8_192,
      );
      const record = await writeOne(payload);

      return response.status(200).json({
        saved: true,
        record,
      });
    }

    if (request.method === "POST") {
      const payload = parseJsonBody(
        request.body,
        MAX_BATCH_BYTES,
      );
      const records = await writeBatch(payload);

      return response.status(200).json({
        saved: true,
        count: records.length,
        records,
      });
    }

    if (request.method === "DELETE") {
      const collection = validateCloudCollection(
        queryValue(request, "collection"),
      );
      const id = validateCloudRecordId(
        queryValue(request, "id"),
      );

      const deleted = await deleteCloudHashField(
        collection,
        id,
      );

      return response.status(200).json({
        deleted: Number(deleted) > 0,
        collection,
        id,
      });
    }

    return response.status(405).json({
      error: "GET・PUT・POST・DELETEのみ利用できます。",
      code: "METHOD_NOT_ALLOWED",
    });
  }
  catch (error) {
    if (error instanceof CloudStateError) {
      return response.status(error.status).json({
        error: error.message,
        code: error.code,
      });
    }

    console.error("Cloud state API:", error);

    return response.status(502).json({
      error: "クラウド保存先へ接続できませんでした。",
      code: error?.code ?? "CLOUD_STORAGE_ERROR",
    });
  }
}

export const CloudStateInternals = {
  CloudStateError,
  FORBIDDEN_NORMALIZED_KEYS,
  MAX_BATCH_BYTES,
  MAX_BATCH_RECORDS,
  MAX_LIST_RECORDS,
  MAX_RECORD_BYTES,
  normalizedKey,
  parseJsonBody,
  parseStoredEnvelope,
  queryValue,
  readMany,
  readOne,
  validateRecordData,
  writeBatch,
  writeOne,
};
