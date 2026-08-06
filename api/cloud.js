import cloudSessionHandler, {
  CloudSessionInternals,
} from "../server/cloud/cloud-session.js";
import cloudStateHandler, {
  CloudStateInternals,
} from "../server/cloud/cloud-state.js";

function queryValue(request, name) {
  const direct = request?.query?.[name];

  if (Array.isArray(direct)) return direct[0];
  if (direct !== undefined) return direct;

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

export function resolveCloudResource(request) {
  return String(queryValue(request, "resource") ?? "")
    .trim()
    .toLowerCase();
}

export default async function handler(request, response) {
  const resource = resolveCloudResource(request);

  if (resource === "session") {
    return cloudSessionHandler(request, response);
  }

  if (resource === "state") {
    return cloudStateHandler(request, response);
  }

  response.setHeader("Cache-Control", "no-store");
  response.setHeader("X-Content-Type-Options", "nosniff");

  return response.status(404).json({
    error: "Cloud API resource must be session or state.",
    code: "CLOUD_RESOURCE_NOT_FOUND",
  });
}

export {
  CloudSessionInternals,
  CloudStateInternals,
};

export const CloudApiInternals = {
  queryValue,
};
