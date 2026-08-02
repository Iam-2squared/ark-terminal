import assert from "node:assert/strict";
import test from "node:test";

import {
  mountAIAccuracyMonitor,
  renderAIAccuracyMonitor,
} from "../analysis/ai-accuracy-monitor-ui.js";

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

      if (index < 0) {
        this.children.push(child);
      } else {
        this.children.splice(index, 0, child);
      }

      return child;
    },
  };
}

function documentFixture() {
  const dashboard = element("section");

  dashboard.appendChild(element("article"));
  dashboard.appendChild(element("article"));
  dashboard.appendChild(element("article"));

  return {
    dashboard,

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

function viewModel() {
  return {
    title: "AI Accuracy Monitor",
    heading: "現在のAI精度",
    status: { label: "算出済み", className: "ready" },
    source: {
      badge: "実績値",
      badgeClass: "observed",
      label: "実績予測・直近30件枠",
      description: "保存後に結果が確定した予測を集計",
    },
    accuracy: "75.0%",
    sampleLabel: "採用 12件 / 確定 14件",
    intervalLabel: "95%信頼区間 46.8〜91.1%",
    reliabilityLabel: "少数・暫定値",
    metrics: [
      { label: "全期間の精度", value: "72.0%", detail: "採用 25件" },
    ],
    horizons: [
      {
        horizon: 1,
        label: "1日",
        accuracy: "80.0%",
        sampleLabel: "5件",
        intervalLabel: "95%信頼区間 37.6〜96.4%",
        available: true,
      },
    ],
    evidence: [
      {
        label: "実績予測",
        accuracy: "75.0%",
        sampleLabel: "採用 12件 / 確定 14件",
        coverage: "85.7%",
        available: true,
      },
    ],
    message: "精度は確定済み評価だけで算出しています。",
    notice: "過去の評価であり、将来を保証しません。",
  };
}

test("Monitor mounts after the first two dashboard cards and is reused", () => {
  const { dashboard, documentRef } = documentFixture();
  const first = mountAIAccuracyMonitor({ documentRef });
  const second = mountAIAccuracyMonitor({ documentRef });

  assert.equal(first.mounted, true);
  assert.equal(first.reused, false);
  assert.equal(dashboard.children[2], first.root);
  assert.equal(first.root.className, "aiAccuracyMonitor fullWidthCard");
  assert.equal(second.root, first.root);
  assert.equal(second.reused, true);
  assert.equal(dashboard.children.length, 4);
});

test("Monitor renders accuracy details and escapes text", () => {
  const root = element("article");
  const view = viewModel();

  view.message = "<script>alert('x')</script>";

  const result = renderAIAccuracyMonitor(view, root);

  assert.equal(result.rendered, true);
  assert.match(root.innerHTML, /現在のAI精度/);
  assert.match(root.innerHTML, /75\.0%/);
  assert.match(root.innerHTML, /95%信頼区間/);
  assert.doesNotMatch(root.innerHTML, /<script>/);
  assert.match(root.innerHTML, /&lt;script&gt;/);
  assert.equal(root.dataset.aiAccuracyState, "ready");
  assert.equal(root.dataset.aiAccuracySource, "observed");
});

test("Mount reports unavailable dashboard without modifying the page", () => {
  const result = mountAIAccuracyMonitor({
    documentRef: {
      querySelector() {
        return null;
      },
      getElementById() {
        return null;
      },
    },
  });

  assert.equal(result.mounted, false);
  assert.equal(result.reason, "dashboard_unavailable");
});
