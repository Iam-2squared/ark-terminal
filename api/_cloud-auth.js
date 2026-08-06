import {
  createHash,
  createHmac,
  timingSafeEqual,
} from "node:crypto";

export const CLOUD_SESSION_COOKIE =
  "ark_cloud_session";

export const CLOUD_SESSION_VERSION = 1;
export const CLOUD_SESSION_MAX_AGE_SECONDS = 12 * 60 * 60;

function cleanText(value, maximumLength = 4096) {
  return String(value ?? "")
    .trim()
    .slice(0, maximumLength);
}

function base64UrlEncode(value) {
  const buffer = Buffer.isBuffer(value)
    ? value
    : Buffer.from(String(value), "utf8");

  return buffer.toString("base64url");
}

function base64UrlDecode(value) {
  return Buffer.from(String(value), "base64url");
}

function digest(value) {
  return createHash("sha256")
    .update(String(value), "utf8")
    .digest();
}

export function constantTimeEqual(first, second) {
  return timingSafeEqual(
    digest(first),
    digest(second),
  );
}

export function resolveCloudSyncSecret(
  environment = process.env,
) {
  const secret = cleanText(
    environment?.ARK_CLOUD_SYNC_SECRET,
    512,
  );

  return secret.length >= 16
    ? secret
    : null;
}

function signPayload(payload, secret) {
  return createHmac("sha256", secret)
    .update(payload, "utf8")
    .digest("base64url");
}

export function createCloudSessionToken(
  secret,
  {
    now = Date.now(),
    maxAgeSeconds = CLOUD_SESSION_MAX_AGE_SECONDS,
  } = {},
) {
  if (!secret) {
    throw new TypeError(
      "Cloud sync secret is required.",
    );
  }

  const issuedAt = Math.floor(Number(now) / 1000);
  const lifetime = Math.max(
    60,
    Math.floor(Number(maxAgeSeconds) || CLOUD_SESSION_MAX_AGE_SECONDS),
  );

  const payload = base64UrlEncode(
    JSON.stringify({
      version: CLOUD_SESSION_VERSION,
      issuedAt,
      expiresAt: issuedAt + lifetime,
    }),
  );

  return `${payload}.${signPayload(payload, secret)}`;
}

export function verifyCloudSessionToken(
  token,
  secret,
  {
    now = Date.now(),
  } = {},
) {
  if (!token || !secret) return false;

  const [payload, signature, extra] =
    String(token).split(".");

  if (!payload || !signature || extra) {
    return false;
  }

  const expected = signPayload(payload, secret);

  if (!constantTimeEqual(signature, expected)) {
    return false;
  }

  try {
    const decoded = JSON.parse(
      base64UrlDecode(payload).toString("utf8"),
    );

    const current = Math.floor(Number(now) / 1000);

    return (
      decoded?.version === CLOUD_SESSION_VERSION &&
      Number.isFinite(Number(decoded?.issuedAt)) &&
      Number.isFinite(Number(decoded?.expiresAt)) &&
      Number(decoded.issuedAt) <= current + 60 &&
      Number(decoded.expiresAt) > current
    );
  }
  catch {
    return false;
  }
}

export function parseCookies(cookieHeader = "") {
  return Object.fromEntries(
    String(cookieHeader)
      .split(";")
      .map((part) => part.trim())
      .filter(Boolean)
      .map((part) => {
        const separator = part.indexOf("=");

        if (separator === -1) {
          return [part, ""];
        }

        const key = part.slice(0, separator).trim();
        const rawValue = part.slice(separator + 1).trim();

        try {
          return [key, decodeURIComponent(rawValue)];
        }
        catch {
          return [key, rawValue];
        }
      }),
  );
}

export function requestHasCloudSession(
  request,
  {
    environment = process.env,
    now = Date.now(),
  } = {},
) {
  const secret = resolveCloudSyncSecret(environment);
  if (!secret) return false;

  const cookies = parseCookies(
    request?.headers?.cookie ??
    request?.headers?.Cookie ??
    "",
  );

  return verifyCloudSessionToken(
    cookies[CLOUD_SESSION_COOKIE],
    secret,
    { now },
  );
}

export function requestIsSecure(request) {
  const forwarded =
    request?.headers?.["x-forwarded-proto"] ??
    request?.headers?.["X-Forwarded-Proto"];

  if (String(forwarded).toLowerCase() === "https") {
    return true;
  }

  return Boolean(process.env.VERCEL);
}

export function buildCloudSessionCookie(
  token,
  {
    secure = true,
    maxAgeSeconds = CLOUD_SESSION_MAX_AGE_SECONDS,
  } = {},
) {
  const parts = [
    `${CLOUD_SESSION_COOKIE}=${encodeURIComponent(token)}`,
    "Path=/api",
    "HttpOnly",
    "SameSite=Strict",
    `Max-Age=${Math.max(0, Math.floor(Number(maxAgeSeconds) || 0))}`,
  ];

  if (secure) parts.push("Secure");

  return parts.join("; ");
}

export function buildCloudSessionClearCookie({
  secure = true,
} = {}) {
  return buildCloudSessionCookie("", {
    secure,
    maxAgeSeconds: 0,
  });
}

function requestOrigin(request) {
  return cleanText(
    request?.headers?.origin ??
    request?.headers?.Origin,
    512,
  );
}

function requestHost(request) {
  return cleanText(
    request?.headers?.["x-forwarded-host"] ??
    request?.headers?.host ??
    request?.headers?.Host,
    512,
  ).toLowerCase();
}

export function requestIsSameOrigin(request) {
  const origin = requestOrigin(request);

  // Server-to-server and test calls may omit Origin.
  if (!origin) return true;

  const host = requestHost(request);
  if (!host) return false;

  try {
    return new URL(origin).host.toLowerCase() === host;
  }
  catch {
    return false;
  }
}

export const CloudAuthInternals = {
  base64UrlDecode,
  base64UrlEncode,
  cleanText,
  digest,
  requestHost,
  requestOrigin,
  signPayload,
};
