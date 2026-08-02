import assert from "node:assert/strict";
import test from "node:test";

import {
  mountMarketIntelligenceDashboard,
  renderMarketIntelligenceDashboard,
} from "../analysis/market-intelligence-dashboard-presenter.js";
import { buildMarketIntelligenceDashboardViewModel } from "../analysis/market-intelligence-dashboard-view-model.js";

function element(tagName = "div") {
  return {
    tagName,
    id: "",
    className: "",
    innerHTML: "",
    dataset: {},
    children: [],
    attributes: {},

    setAttribute(name, value) {
      this.attributes[name] = value;
    },

    appendChild(child) {
      this.children.push(child);
      return child;
    },

    insertBefore(child, reference) {
      const index = this.children.indexOf(reference);
      if (index < 0) this.children.push(child);
      else this.children.splice(index, 0, child);
      return child;
    },
  };
}

function documentFixture() {
  const dashboard = element("section");
  const score = element("article");
  const prediction = element("article");
  const intraday = element("article");

  prediction.className = "predictionOutputCard fullWidthCard";
  intraday.id = "intradayTradingCard";
  dashboard.appendChild(score);
  dashboard.appendChild(prediction);
  dashboard.appendChild(intraday);

  return {
    dashboard,
    prediction,
    intraday,
    documentRef: {
      querySelector(selector) {
        return selector === ".dashboardGrid" ? dashboard : null;
      },
      getElementById(id) {
        return dashboard.children.find((child) => child.id === id) ?? null;
      },
      createElement(tagName) {
        return element(tagName);
      },
    },
  };
}

function readyView() {
  const details = Object.fromEntries(
    [
      "marketScore",
      "breadth",
      "liquidity",
      "newsScore",
      "sectorStrength",
      "compositeAI",
    ].map((key, index) => [
      key,
      {
        score: 60 + index,
        confidence: 80,
        coverage: 90,
        available: true,
        source: key,
      },
    ]),
  );
  const report = {
    status: "ready",
    selectedHorizon: 5,
    predictions: [1, 3, 5, 10, 20].map((horizon) => ({
      horizon,
      direction: "上昇",
      score: 62,
      confidence: 80,
      status: "ready",
    })),
    result: {
      features: {
        status: "ready",
        timestamp: "2026-08-02T06:00:00.000Z",
        confidence: 80,
        coverage: 90,
        details,
      },
      breadth: {
        score: 61,
        availableCount: 20,
        requestedCount: 25,
        advancers: 12,
        decliners: 7,
        unchanged: 1,
        advanceDeclineRatio: 1.71,
        coverage: 80,
      },
      sectorStrength: {
        score: 64,
        sectorCount: 2,
        leaders: [
          { sector: "<script>bad</script>", score: 74, confidence: 80 },
        ],
        laggards: [{ sector: "電力", score: 42, confidence: 80 }],
      },
    },
  };

  return buildMarketIntelligenceDashboardViewModel({
    report,
    state: {
      symbol: "<img src=x onerror=alert(1)>",
      marketBreadthSource: {
        status: "available",
        source: "Ark Screener",
        availableCount: 20,
        expectedObservationCount: 25,
        coverage: 80,
      },
      marketEnvironment: { availableCount: 10, requestedCount: 14 },
      context: { news: [], disclosures: [], status: {} },
    },
    phase: "ready",
  });
}

test("Presenter renders all dashboard sections and escapes provider content", () => {
  const root = element("article");
  const result = renderMarketIntelligenceDashboard(readyView(), root);

  assert.equal(result.rendered, true);
  assert.match(root.innerHTML, /市場インテリジェンス/);
  assert.match(root.innerHTML, /CompositeAI/);
  assert.match(root.innerHTML, /予測期間別の市場方向/);
  assert.match(root.innerHTML, /Provider Health/);
  assert.doesNotMatch(root.innerHTML, /<script>bad<\/script>/);
  assert.doesNotMatch(root.innerHTML, /<img src=x/);
  assert.match(root.innerHTML, /&lt;script&gt;bad&lt;\/script&gt;/);
  assert.equal(root.dataset.marketIntelligenceState, "ready");
  assert.equal(root.dataset.marketIntelligenceExecution, "disabled");
  assert.equal(root.attributes["aria-busy"], "false");
});

test("Unavailable values render as placeholders instead of zero scores", () => {
  const root = element("article");
  const view = buildMarketIntelligenceDashboardViewModel({
    state: { symbol: "TEST" },
    phase: "unavailable",
  });

  renderMarketIntelligenceDashboard(view, root);

  assert.match(root.innerHTML, /CompositeAI[\s\S]*--/);
  assert.match(root.innerHTML, /品質 --/);
  assert.doesNotMatch(root.innerHTML, /品質 0\.0%/);
  assert.doesNotMatch(
    root.innerHTML.match(/<progress[\s\S]*?>/)[0],
    /\bvalue=/,
  );
  assert.equal(root.dataset.marketIntelligenceState, "unavailable");
});

test("Dashboard mounts directly after Prediction Output and is reused", () => {
  const { dashboard, prediction, intraday, documentRef } = documentFixture();
  const first = mountMarketIntelligenceDashboard({ documentRef });
  const second = mountMarketIntelligenceDashboard({ documentRef });

  assert.equal(first.mounted, true);
  assert.equal(first.reused, false);
  assert.equal(dashboard.children.indexOf(first.root), 2);
  assert.equal(dashboard.children[1], prediction);
  assert.equal(dashboard.children[3], intraday);
  assert.equal(first.root.className, "marketIntelligenceDashboard fullWidthCard");
  assert.equal(second.reused, true);
  assert.equal(second.root, first.root);
  assert.equal(dashboard.children.length, 4);
});

test("Mount fails closed when the dashboard grid is unavailable", () => {
  const result = mountMarketIntelligenceDashboard({
    documentRef: {
      getElementById() {
        return null;
      },
      querySelector() {
        return null;
      },
    },
  });

  assert.equal(result.mounted, false);
  assert.equal(result.reason, "dashboard_unavailable");
});
