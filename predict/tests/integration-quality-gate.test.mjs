import assert from "node:assert/strict";
import test from "node:test";

import {
  buildIntegrationQualityReport,
  extractExportedFunctions,
  extractModuleScripts,
  findDuplicateValues,
  inspectIntegrationQuality,
} from "../analysis/integration-quality-gate.js";

test(
  "Duplicate values are detected",
  () => {
    const result =
      findDuplicateValues([
        "a",
        "b",
        "a",
      ]);

    assert.deepEqual(
      result,
      [
        {
          value: "a",
          count: 2,
        },
      ],
    );
  },
);

test(
  "Module scripts are extracted",
  () => {
    const result =
      extractModuleScripts(`
        <script
          type="module"
          src="./analysis/a.js"
        ></script>
      `);

    assert.deepEqual(
      result,
      [
        "./analysis/a.js",
      ],
    );
  },
);

test(
  "Exported functions are extracted",
  () => {
    const result =
      extractExportedFunctions(`
        export function alpha() {}
        export function beta() {}
      `);

    assert.deepEqual(
      result,
      [
        "alpha",
        "beta",
      ],
    );
  },
);

test(
  "Healthy integration passes",
  () => {
    const result =
      inspectIntegrationQuality({
        html: `
          <script
            type="module"
            src="./analysis/runtime.js"
          ></script>
        `,

        requiredScripts: [
          "./analysis/runtime.js",
        ],

        sources: {
          "module.js": `
            export function alpha() {}
            export function beta() {}
          `,
        },
      });

    assert.equal(
      result.healthy,
      true,
    );

    assert.equal(
      result.score,
      100,
    );
  },
);

test(
  "Duplicate exports fail quality gate",
  () => {
    const result =
      buildIntegrationQualityReport({
        html: "",

        sources: {
          "module.js": `
            export function alpha() {}
            export function alpha() {}
          `,
        },
      });

    assert.equal(
      result.status,
      "ATTENTION",
    );

    assert.equal(
      result.duplicateExports.length,
      1,
    );
  },
);