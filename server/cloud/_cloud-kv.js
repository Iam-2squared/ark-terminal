export const CLOUD_KV_NAMESPACE =
  "ark-terminal:cloud-state:v1";

function cleanText(value, maximumLength = 4096) {
  return String(value ?? "")
    .trim()
    .slice(0, maximumLength);
}

export function resolveCloudKvConfig(
  environment = process.env,
) {
  const url = cleanText(
    environment?.ARK_KV_REST_API_URL ??
    environment?.KV_REST_API_URL ??
    environment?.UPSTASH_REDIS_REST_URL,
    2048,
  ).replace(/\/+$/, "");

  const token = cleanText(
    environment?.ARK_KV_REST_API_TOKEN ??
    environment?.KV_REST_API_TOKEN ??
    environment?.UPSTASH_REDIS_REST_TOKEN,
    4096,
  );

  return {
    configured: Boolean(url && token),
    url,
    token,
  };
}

export function cloudKvConfigured(
  environment = process.env,
) {
  return resolveCloudKvConfig(environment)
    .configured;
}

export async function executeCloudKvCommand(
  command,
  {
    environment = process.env,
    fetchImpl = fetch,
  } = {},
) {
  const config = resolveCloudKvConfig(environment);

  if (!config.configured) {
    const error = new Error(
      "CLOUD_KV_NOT_CONFIGURED",
    );
    error.code = "CLOUD_KV_NOT_CONFIGURED";
    throw error;
  }

  if (!Array.isArray(command) || command.length === 0) {
    throw new TypeError(
      "Cloud KV command must be a non-empty array.",
    );
  }

  const response = await fetchImpl(config.url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${config.token}`,
      "Content-Type": "application/json",
      "Cache-Control": "no-store",
    },
    body: JSON.stringify(command),
  });

  const payload = await response
    .json()
    .catch(() => null);

  if (!response.ok) {
    const error = new Error(
      payload?.error ??
      `CLOUD_KV_HTTP_${response.status}`,
    );
    error.code = "CLOUD_KV_UPSTREAM_ERROR";
    error.status = response.status;
    throw error;
  }

  if (payload?.error) {
    const error = new Error(
      String(payload.error),
    );
    error.code = "CLOUD_KV_COMMAND_ERROR";
    throw error;
  }

  return payload?.result ?? null;
}

export function cloudCollectionKey(collection) {
  return `${CLOUD_KV_NAMESPACE}:${cleanText(collection, 120)}`;
}

export async function getCloudHashField(
  collection,
  id,
  options,
) {
  return executeCloudKvCommand(
    [
      "HGET",
      cloudCollectionKey(collection),
      String(id),
    ],
    options,
  );
}

export async function setCloudHashField(
  collection,
  id,
  value,
  options,
) {
  return executeCloudKvCommand(
    [
      "HSET",
      cloudCollectionKey(collection),
      String(id),
      String(value),
    ],
    options,
  );
}

export async function setCloudHashFields(
  collection,
  entries = [],
  options,
) {
  const command = [
    "HSET",
    cloudCollectionKey(collection),
  ];

  for (const entry of entries) {
    command.push(
      String(entry.id),
      String(entry.value),
    );
  }

  if (command.length === 2) {
    return 0;
  }

  return executeCloudKvCommand(
    command,
    options,
  );
}

export async function deleteCloudHashField(
  collection,
  id,
  options,
) {
  return executeCloudKvCommand(
    [
      "HDEL",
      cloudCollectionKey(collection),
      String(id),
    ],
    options,
  );
}

export async function getAllCloudHashFields(
  collection,
  options,
) {
  const result = await executeCloudKvCommand(
    [
      "HGETALL",
      cloudCollectionKey(collection),
    ],
    options,
  );

  if (Array.isArray(result)) {
    const entries = [];

    for (let index = 0; index < result.length; index += 2) {
      const id = result[index];
      const value = result[index + 1];

      if (id !== undefined && value !== undefined) {
        entries.push({
          id: String(id),
          value: String(value),
        });
      }
    }

    return entries;
  }

  if (result && typeof result === "object") {
    return Object.entries(result)
      .map(([id, value]) => ({
        id,
        value: String(value),
      }));
  }

  return [];
}

export const CloudKvInternals = {
  cleanText,
};
