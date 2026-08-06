import {
  ARK_API_BASE,
} from "../config.js";

export class CloudSyncError extends Error {
  constructor(
    message,
    {
      status = 0,
      code = "CLOUD_SYNC_ERROR",
      payload = null,
    } = {},
  ) {
    super(message);
    this.name = "CloudSyncError";
    this.status = status;
    this.code = code;
    this.payload = payload;
  }
}

function apiUrl(path, query = {}) {
  const url = new URL(
    path,
    `${ARK_API_BASE.replace(/\/$/, "")}/`,
  );

  Object.entries(query).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== "") {
      url.searchParams.set(key, String(value));
    }
  });

  return url.toString();
}

async function requestJson(
  path,
  {
    method = "GET",
    body,
    query,
    fetchImpl = fetch,
  } = {},
) {
  const response = await fetchImpl(
    apiUrl(path, query),
    {
      method,
      credentials: "include",
      headers:
        body === undefined
          ? undefined
          : {
              "Content-Type": "application/json",
            },
      body:
        body === undefined
          ? undefined
          : JSON.stringify(body),
      cache: "no-store",
    },
  );

  const payload = await response
    .json()
    .catch(() => null);

  if (!response.ok) {
    throw new CloudSyncError(
      payload?.error ??
      `Cloud sync HTTP ${response.status}`,
      {
        status: response.status,
        code:
          payload?.code ??
          "CLOUD_SYNC_HTTP_ERROR",
        payload,
      },
    );
  }

  return payload ?? {};
}

export function getCloudSyncStatus(options = {}) {
  return requestJson(
    "/api/cloud-session",
    options,
  );
}

export function connectCloudSync(
  secret,
  options = {},
) {
  return requestJson(
    "/api/cloud-session",
    {
      ...options,
      method: "POST",
      body: {
        secret:
          String(secret ?? ""),
      },
    },
  );
}

export function disconnectCloudSync(options = {}) {
  return requestJson(
    "/api/cloud-session",
    {
      ...options,
      method: "DELETE",
    },
  );
}

export function saveCloudRecord({
  collection,
  id,
  data,
  ...options
} = {}) {
  return requestJson(
    "/api/cloud-state",
    {
      ...options,
      method: "PUT",
      body: {
        collection,
        id,
        data,
      },
    },
  );
}

export function saveCloudRecords({
  collection,
  records,
  ...options
} = {}) {
  return requestJson(
    "/api/cloud-state",
    {
      ...options,
      method: "POST",
      body: {
        collection,
        records,
      },
    },
  );
}

export function getCloudRecord({
  collection,
  id,
  ...options
} = {}) {
  return requestJson(
    "/api/cloud-state",
    {
      ...options,
      query: {
        collection,
        id,
      },
    },
  );
}

export function listCloudRecords({
  collection,
  limit = 100,
  ...options
} = {}) {
  return requestJson(
    "/api/cloud-state",
    {
      ...options,
      query: {
        collection,
        limit,
      },
    },
  );
}

export function deleteCloudRecord({
  collection,
  id,
  ...options
} = {}) {
  return requestJson(
    "/api/cloud-state",
    {
      ...options,
      method: "DELETE",
      query: {
        collection,
        id,
      },
    },
  );
}

export const CloudSyncClientInternals = {
  apiUrl,
  requestJson,
};
