import test from "node:test";
import assert from "node:assert/strict";

import {
  LearningReportV2,
  buildLearningReport,
  createLearningReportExport,
  exportLearningReportJson,
  renderLearningReportMarkdown,
} from "../learning/learning-report-v2.js";

function state() {
  return {
    modelId:
      "ark-learning",

    modelVersion:
      "v2",

    revision:
      2,

    enabled:
      true,

    updatedAt:
      "2026-08-04T00:00:00.000Z",

    metrics: {
      ready:
        true,

      sampleCount:
        100,

      accuracy:
        62,

      weightedAccuracy:
        63,

      averageReturn:
        1.8,

      medianReturn:
        1.4,

      profitFactor:
        1.6,

      maximumDrawdown:
        8,

      calibrationError:
        15,

      volatility:
        2.2,

      averageConfidence:
        70,

      streaks: {
        currentLossStreak:
          1,
      },
    },

    weights: {
      base:
        0.6,

      byRegime: {
        TRENDING_BULL:
          0.7,
      },

      byHorizon: {
        5:
          0.65,
      },
    },

    history: {
      recordCount:
        100,

      latestRecordId:
        "record-100",

      latestTimestamp:
        "2026-08-04T00:00:00.000Z",
    },

    safeguards: {
      frozen:
        false,

      promotionAllowed:
        true,

      rollbackRequired:
        false,
    },
  };
}

function evaluation() {
  return {
    decision:
      "REQUIRE_HUMAN_APPROVAL",

    approved:
      false,

    requiresHumanApproval:
      true,

    evaluationScore:
      78,

    blockers:
      [],

    warnings:
      [],

    strengths: [
      "ACCURACY_ACCEPTABLE",
      "RETURN_ACCEPTABLE",
    ],
  };
}

test(
  "Learning report builds full summary",
  () => {
    const report =
      buildLearningReport({
        state:
          state(),

        evaluation:
          evaluation(),

        promotion: {
          status:
            "PENDING_APPROVAL",

          candidate: {
            revision:
              2,
          },

          current: {
            revision:
              1,
          },
        },

        audit: {
          valid:
            true,

          entryCount:
            5,

          issueCount:
            0,
        },

        quality: {
          passed:
            true,

          qualityScore:
            100,

          summary: {
            acceptedCount:
              100,

            rejectedCount:
              0,
          },
        },

        generatedAt:
          "2026-08-04T00:00:00.000Z",
      });

    assert.equal(
      report.version,
      "learning-report-v2",
    );

    assert.equal(
      report.model.revision,
      2,
    );

    assert.equal(
      report.kpis.accuracy,
      63,
    );

    assert.equal(
      report.health.status,
      "HEALTHY",
    );

    assert.equal(
      report.recommendation.action,
      "REQUEST_HUMAN_APPROVAL",
    );
  },
);

test(
  "Learning report becomes critical when frozen",
  () => {
    const frozenState =
      state();

    frozenState.safeguards.frozen =
      true;

    frozenState.safeguards.freezeReason =
      "LOW_ACCURACY";

    const report =
      buildLearningReport({
        state:
          frozenState,
      });

    assert.equal(
      report.health.status,
      "CRITICAL",
    );

    assert.ok(
      report.health.blockers.includes(
        "LOW_ACCURACY",
      ),
    );

    assert.equal(
      report.recommendation.action,
      "STOP_AND_REVIEW",
    );
  },
);

test(
  "Learning report renders markdown",
  () => {
    const report =
      buildLearningReport({
        state:
          state(),

        generatedAt:
          "2026-08-04T00:00:00.000Z",
      });

    const markdown =
      renderLearningReportMarkdown(
        report,
      );

    assert.match(
      markdown,
      /# Ark Terminal Learning Report/,
    );

    assert.match(
      markdown,
      /## KPI Summary/,
    );

    assert.match(
      markdown,
      /Accuracy: 63%/,
    );
  },
);

test(
  "Learning report exports JSON",
  () => {
    const report =
      buildLearningReport({
        state:
          state(),
      });

    const json =
      exportLearningReportJson(
        report,
      );

    const parsed =
      JSON.parse(json);

    assert.equal(
      parsed.model.modelId,
      "ark-learning",
    );
  },
);

test(
  "Learning report creates export descriptors",
  () => {
    const report =
      buildLearningReport({
        state:
          state(),
      });

    const jsonExport =
      createLearningReportExport({
        report,

        format:
          "json",
      });

    const markdownExport =
      createLearningReportExport({
        report,

        format:
          "markdown",
      });

    assert.equal(
      jsonExport.extension,
      "json",
    );

    assert.equal(
      markdownExport.extension,
      "md",
    );

    assert.match(
      markdownExport.content,
      /Learning Report/,
    );
  },
);

test(
  "Learning report rejects unsupported format",
  () => {
    const report =
      buildLearningReport({
        state:
          state(),
      });

    assert.throws(
      () =>
        createLearningReportExport({
          report,

          format:
            "pdf",
        }),

      /Unsupported learning report format/,
    );
  },
);

test(
  "Learning report class stores history",
  () => {
    const reporter =
      new LearningReportV2({
        generatedBy:
          "test-suite",
      });

    const report =
      reporter.build({
        state:
          state(),

        generatedAt:
          "2026-08-04T00:00:00.000Z",
      });

    assert.equal(
      reporter
        .getHistory()
        .length,
      1,
    );

    assert.match(
      reporter.markdown(
        report,
      ),
      /KPI Summary/,
    );

    assert.equal(
      JSON.parse(
        reporter.json(
          report,
        ),
      ).generatedBy,
      "test-suite",
    );

    reporter.reset();

    assert.equal(
      reporter
        .getHistory()
        .length,
      0,
    );
  },
);