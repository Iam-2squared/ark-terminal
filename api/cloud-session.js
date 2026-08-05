import {
  buildCloudSessionClearCookie,
  buildCloudSessionCookie,
  constantTimeEqual,
  createCloudSessionToken,
  requestHasCloudSession,
  requestIsSameOrigin,
  requestIsSecure,
  resolveCloudSyncSecret,
} from "./_cloud-auth.js";

import {
  cloudKvConfigured,
} from "./_cloud-kv.js";

const MAX_REQUEST_BYTES = 4_096;
const LOGIN_WINDOW_MS = 15 * 60 * 1000;
const MAX_LOGIN_ATTEMPTS = 5;

const loginAttempts =
  globalThis.__arkCloudLoginAttempts ||
  (globalThis.__arkCloudLoginAttempts = new Map());

class CloudSessionError extends Error {
  constructor(message, status = 400, code = "CLOUD_SESSION_ERROR") {
    super(message);
    this.name = "CloudSessionError";
    this.status = status;
    this.code = code;
  }
}

function parseBody(body) {
  if (typeof body === "string") {
    if (Buffer.byteLength(body, "utf8") > MAX_REQUEST_BYTES) {
      throw new CloudSessionError(
        "送信データが大きすぎます。",
        413,
        "REQUEST_TOO_LARGE",
      );
    }

    try {
      return JSON.parse(body);
    }
    catch {
      throw new CloudSessionError(
        "JSONを読み取れませんでした。",
        400,
        "INVALID_JSON",
      );
    }
  }

  const serialized = JSON.stringify(body ?? {});

  if (Buffer.byteLength(serialized, "utf8") > MAX_REQUEST_BYTES) {
    throw new CloudSessionError(
      "送信データが大きすぎます。",
      413,
      "REQUEST_TOO_LARGE",
    );
  }

  return body ?? {};
}

function clientKey(request) {
  const forwarded = request?.headers?.["x-forwarded-for"];
  const value = Array.isArray(forwarded)
    ? forwarded[0]
    : forwarded;

  return String(
    value ??
    request?.socket?.remoteAddress ??
    "unknown",
  )
    .split(",")[0]
    .trim();
}

function assertLoginAllowed(request, now = Date.now()) {
  const key = clientKey(request);
  const current = Number(now);
  const stored = loginAttempts.get(key) ?? {
    startedAt: current,
    failures: 0,
  };

  if (current - stored.startedAt >= LOGIN_WINDOW_MS) {
    loginAttempts.set(key, {
      startedAt: current,
      failures: 0,
    });
    return;
  }

  if (stored.failures >= MAX_LOGIN_ATTEMPTS) {
    const retryAfter = Math.max(
      1,
      Math.ceil((LOGIN_WINDOW_MS - (current - stored.startedAt)) / 1000),
    );

    const error = new CloudSessionError(
      "クラウド接続の試行回数が多すぎます。時間を置いて再試行してください。",
      429,
      "TOO_MANY_ATTEMPTS",
    );
    error.retryAfter = retryAfter;
    throw error;
  }
}

function recordLoginFailure(request, now = Date.now()) {
  const key = clientKey(request);
  const current = Number(now);
  const stored = loginAttempts.get(key);

  if (!stored || current - stored.startedAt >= LOGIN_WINDOW_MS) {
    loginAttempts.set(key, {
      startedAt: current,
      failures: 1,
    });
    return;
  }

  stored.failures += 1;
  loginAttempts.set(key, stored);
}

function clearLoginFailures(request) {
  loginAttempts.delete(clientKey(request));
}

function setCommonHeaders(response) {
  response.setHeader("Cache-Control", "no-store");
  response.setHeader("X-Content-Type-Options", "nosniff");
  response.setHeader(
    "Access-Control-Allow-Methods",
    "GET, POST, DELETE, OPTIONS",
  );
  response.setHeader(
    "Access-Control-Allow-Headers",
    "Content-Type",
  );
}

export default async function handler(request, response) {
  setCommonHeaders(response);

  if (request.method === "OPTIONS") {
    return response.status(204).end();
  }

  const environment = process.env;
  const secret = resolveCloudSyncSecret(environment);
  const storageConfigured = cloudKvConfigured(environment);

  if (request.method === "GET") {
    return response.status(200).json({
      configured: Boolean(secret && storageConfigured),
      authConfigured: Boolean(secret),
      storageConfigured,
      authenticated: requestHasCloudSession(request, {
        environment,
      }),
      mode: "cloud-rest-kv",
      readOnlyBrokerBoundary: true,
    });
  }

  if (!["POST", "DELETE"].includes(request.method)) {
    return response.status(405).json({
      error: "GET・POST・DELETEのみ利用できます。",
      code: "METHOD_NOT_ALLOWED",
    });
  }

  try {
    if (!requestIsSameOrigin(request)) {
      throw new CloudSessionError(
        "同一オリジンからのみ利用できます。",
        403,
        "ORIGIN_NOT_ALLOWED",
      );
    }

    if (request.method === "DELETE") {
      response.setHeader(
        "Set-Cookie",
        buildCloudSessionClearCookie({
          secure: requestIsSecure(request),
        }),
      );

      return response.status(200).json({
        authenticated: false,
        disconnected: true,
      });
    }

    if (!secret) {
      throw new CloudSessionError(
        "ARK_CLOUD_SYNC_SECRETが設定されていません。",
        503,
        "CLOUD_AUTH_NOT_CONFIGURED",
      );
    }

    if (!storageConfigured) {
      throw new CloudSessionError(
        "クラウド保存先が設定されていません。",
        503,
        "CLOUD_STORAGE_NOT_CONFIGURED",
      );
    }

    assertLoginAllowed(request);

    const payload = parseBody(request.body);
    const submitted = String(payload?.secret ?? "");

    if (!submitted || !constantTimeEqual(submitted, secret)) {
      recordLoginFailure(request);
      throw new CloudSessionError(
        "同期パスフレーズが正しくありません。",
        401,
        "INVALID_SYNC_SECRET",
      );
    }

    clearLoginFailures(request);

    const token = createCloudSessionToken(secret);

    response.setHeader(
      "Set-Cookie",
      buildCloudSessionCookie(token, {
        secure: requestIsSecure(request),
      }),
    );

    return response.status(200).json({
      authenticated: true,
      storageConfigured: true,
      expiresInSeconds: 12 * 60 * 60,
      brokerWriteAllowed: false,
      realAccountUploadAllowed: false,
    });
  }
  catch (error) {
    if (error instanceof CloudSessionError) {
      if (error.retryAfter) {
        response.setHeader(
          "Retry-After",
          String(error.retryAfter),
        );
      }

      return response.status(error.status).json({
        error: error.message,
        code: error.code,
      });
    }

    console.error("Cloud session API:", error);

    return response.status(500).json({
      error: "クラウド接続を開始できませんでした。",
      code: "CLOUD_SESSION_INTERNAL_ERROR",
    });
  }
}

export const CloudSessionInternals = {
  CloudSessionError,
  MAX_LOGIN_ATTEMPTS,
  LOGIN_WINDOW_MS,
  assertLoginAllowed,
  clearLoginFailures,
  clientKey,
  loginAttempts,
  parseBody,
  recordLoginFailure,
};
