import screenerHandler, {
  ScreenerApiInternals,
} from "../server/screener.js";
import screenerDataHandler, {
  ScreenerDataApiInternals,
} from "../server/screener-data.js";

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

export function resolveScreenerMode(request) {
  const explicit = String(queryValue(request, "mode") ?? "")
    .trim()
    .toLowerCase();

  if (explicit === "data") return "data";
  if (explicit === "scan") return "scan";

  return queryValue(request, "type") && !queryValue(request, "symbols")
    ? "data"
    : "scan";
}

export default async function handler(request, response) {
  return resolveScreenerMode(request) === "data"
    ? screenerDataHandler(request, response)
    : screenerHandler(request, response);
}

export {
  ScreenerApiInternals,
  ScreenerDataApiInternals,
};

export const ScreenerRouterInternals = {
  queryValue,
};
