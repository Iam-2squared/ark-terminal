function unique(values) {
  return [
    ...new Set(values),
  ];
}

export function findDuplicateValues(
  values = [],
) {
  const counts =
    new Map();

  for (const value of values) {
    counts.set(
      value,
      (
        counts.get(value) ??
        0
      ) + 1,
    );
  }

  return [
    ...counts.entries(),
  ]
    .filter(
      ([
        ,
        count,
      ]) =>
        count > 1,
    )
    .map(
      ([
        value,
        count,
      ]) => ({
        value,
        count,
      }),
    );
}

export function extractModuleScripts(
  html = "",
) {
  const pattern =
    /<script[^>]+type=["']module["'][^>]+src=["']([^"']+)["'][^>]*>/gi;

  const scripts = [];
  let match = null;

  while (
    (
      match =
        pattern.exec(html)
    ) !== null
  ) {
    scripts.push(
      match[1],
    );
  }

  return scripts;
}

export function extractExportedFunctions(
  source = "",
) {
  const pattern =
    /export\s+function\s+([A-Za-z_$][\w$]*)\s*\(/g;

  const functions = [];
  let match = null;

  while (
    (
      match =
        pattern.exec(source)
    ) !== null
  ) {
    functions.push(
      match[1],
    );
  }

  return functions;
}

export function inspectIntegrationQuality({
  html = "",
  sources = {},
  requiredScripts = [],
} = {}) {
  const scripts =
    extractModuleScripts(
      html,
    );

  const duplicateScripts =
    findDuplicateValues(
      scripts,
    );

  const missingScripts =
    requiredScripts.filter(
      (required) =>
        !scripts.includes(
          required,
        ),
    );

  const duplicateExports = [];

  for (
    const [
      file,
      source,
    ] of Object.entries(
      sources,
    )
  ) {
    const duplicates =
      findDuplicateValues(
        extractExportedFunctions(
          source,
        ),
      );

    for (const duplicate of duplicates) {
      duplicateExports.push({
        file,
        name:
          duplicate.value,
        count:
          duplicate.count,
      });
    }
  }

  const issues = [
    ...duplicateScripts.map(
      (item) =>
        `Duplicate module script: ${item.value}`,
    ),

    ...missingScripts.map(
      (item) =>
        `Missing module script: ${item}`,
    ),

    ...duplicateExports.map(
      (item) =>
        `Duplicate export in ${item.file}: ${item.name}`,
    ),
  ];

  return {
    healthy:
      issues.length === 0,

    scripts:
      unique(scripts),

    duplicateScripts,

    missingScripts,

    duplicateExports,

    issues,

    score:
      Math.max(
        0,
        100 -
        issues.length * 15,
      ),
  };
}

export function buildIntegrationQualityReport(
  input = {},
) {
  const inspection =
    inspectIntegrationQuality(
      input,
    );

  return {
    version:
      "integration-quality-gate-v1",

    generatedAt:
      new Date()
        .toISOString(),

    ...inspection,

    status:
      inspection.healthy
        ? "PASS"
        : "ATTENTION",
  };
}