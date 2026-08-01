const REPOSITORY = "Iam-2squared/ark-terminal";
const DATA_BRANCH = "automation/screener-data";
const FALLBACK_BRANCH = "main";
const CACHE_BUCKET_MS = 3 * 60 * 1000;
const FETCH_TIMEOUT_MS = 10_000;

const FILES = Object.freeze({
  universe: "screener-universe.json",
  snapshot: "screener-snapshot.json",
});

function normalizeType(value) {
  const candidate = Array.isArray(value) ? value[0] : value;

  return Object.hasOwn(FILES, candidate) ? candidate : null;
}

function rawUrl(branch, fileName, cacheBucket) {
  return (
    `https://raw.githubusercontent.com/${REPOSITORY}/refs/heads/` +
    `${branch}/data/${fileName}?v=${cacheBucket}`
  );
}

function buildCandidateUrls(type, now = Date.now()) {
  const fileName = FILES[type];
  const cacheBucket = Math.floor(now / CACHE_BUCKET_MS);

  return [
    {
      branch: DATA_BRANCH,
      url: rawUrl(DATA_BRANCH, fileName, cacheBucket),
    },
    {
      branch: FALLBACK_BRANCH,
      url: rawUrl(FALLBACK_BRANCH, fileName, cacheBucket),
    },
  ];
}

function normalizePayload(payload, { sourceBranch, fetchedAt }) {
  const normalized = Array.isArray(payload)
    ? {
        entries: payload,
      }
    : {
        ...(payload || {}),
      };

  return {
    ...normalized,
    meta: {
      ...(normalized.meta || {}),
      delivery: {
        mode: "automatic-data-branch",
        sourceBranch,
        fetchedAt,
      },
    },
  };
}

async function fetchJson(url, fetchImpl = globalThis.fetch) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);

  try {
    const result = await fetchImpl(url, {
      headers: {
        Accept: "application/json",
        "User-Agent": "Ark-Terminal-Screener-Data",
      },
      signal: controller.signal,
    });

    if (!result.ok) {
      throw new Error(`GitHub data fetch failed (${result.status})`);
    }

    return result.json();
  } finally {
    clearTimeout(timeout);
  }
}

async function loadScreenerData(type, fetchImpl = globalThis.fetch) {
  const errors = [];

  for (const candidate of buildCandidateUrls(type)) {
    try {
      const payload = await fetchJson(candidate.url, fetchImpl);
      const fetchedAt = new Date().toISOString();

      return normalizePayload(payload, {
        sourceBranch: candidate.branch,
        fetchedAt,
      });
    } catch (error) {
      errors.push(`${candidate.branch}: ${error.message}`);
    }
  }

  throw new Error(errors.join(" / "));
}

export default async function handler(request, response) {
  response.setHeader("Access-Control-Allow-Origin", "*");
  response.setHeader("Access-Control-Allow-Methods", "GET, OPTIONS");
  response.setHeader(
    "Cache-Control",
    "public, max-age=0, s-maxage=180, stale-while-revalidate=900",
  );

  if (request.method === "OPTIONS") {
    return response.status(204).end();
  }

  if (request.method !== "GET") {
    return response.status(405).json({
      error: "GETのみ利用できます。",
    });
  }

  const type = normalizeType(request.query.type);

  if (!type) {
    return response.status(400).json({
      error: "typeはuniverseまたはsnapshotを指定してください。",
    });
  }

  try {
    const payload = await loadScreenerData(type);

    return response.status(200).json(payload);
  } catch (error) {
    console.error(`Screener data API (${type}):`, error);

    return response.status(502).json({
      error: "最新のスクリーナーデータを取得できませんでした。",
      detail: error.message,
    });
  }
}

export const ScreenerDataApiInternals = {
  DATA_BRANCH,
  FALLBACK_BRANCH,
  FILES,
  normalizeType,
  buildCandidateUrls,
  normalizePayload,
  loadScreenerData,
};
