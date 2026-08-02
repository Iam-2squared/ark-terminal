import test from "node:test";
import assert from "node:assert/strict";

import AccuracyDashboardPresenter
from "../analysis/accuracy-dashboard-presenter.js";

test("presenter calls renderer", () => {

    let rendered;

    const presenter =
        new AccuracyDashboardPresenter({
            renderer: vm => rendered = vm,
        });

    const result = presenter.present({
        summary: {},
        tradePerformance: {},
        riskAdjusted: {},
        health: {
            status: "healthy",
        },
    });

    assert.equal(rendered, result);
    assert.equal(result.health.status, "healthy");
    assert.ok(Array.isArray(result.cards));

});
