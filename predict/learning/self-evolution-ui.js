import {
  summarizeSelfEvolutionPlan,
  summarizeLearningAuditHistory,
} from "./weight-optimizer.js";

function finite(value) {
  return Number.isFinite(Number(value));
}

function number(value, fallback = 0) {
  return finite(value)
    ? Number(value)
    : fallback;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function actionLabel(action) {
  const labels = {
    PROMOTE: "昇格候補",
    RETRAIN: "再学習",
    HOLD: "保留",
    UNKNOWN: "未判定",
  };

  return labels[action] ?? action;
}

function statusClass(action) {
  if (action === "PROMOTE") {
    return "positive";
  }

  if (action === "RETRAIN") {
    return "negative";
  }

  return "neutral";
}

export function createSelfEvolutionViewModel({
  plan = {},
  auditHistory = [],
} = {}) {
  const summary =
    summarizeSelfEvolutionPlan(plan);

  const audit =
    summarizeLearningAuditHistory(
      auditHistory,
    );

  return {
    version:
      "self-evolution-ui-v1",

    action:
      summary.action,

    actionLabel:
      actionLabel(
        summary.action,
      ),

    statusClass:
      statusClass(
        summary.action,
      ),

    promoted:
      summary.promoted === true,

    approvedByBacktest:
      summary.approvedByBacktest === true,

    improvementScore:
      number(
        summary.improvementScore,
      ),

    improvementLabel:
      `${
        number(
          summary.improvementScore,
        ) > 0
          ? "+"
          : ""
      }${number(
        summary.improvementScore,
      ).toFixed(2)}`,

    weightHealth:
      summary.weightHealth === true,

    changedIndicators:
      number(
        summary.changedIndicators,
      ),

    audit: {
      totalRuns:
        audit.totalRuns,

      promotedCount:
        audit.promotedCount,

      retrainingCount:
        audit.retrainingCount,

      holdCount:
        audit.holdCount,

      promotionRate:
        audit.promotionRate,

      averageImprovement:
        audit.averageImprovement,

      latest:
        audit.latest,
    },
  };
}

export function renderSelfEvolutionDashboard({
  plan = {},
  auditHistory = [],
} = {}) {
  const view =
    createSelfEvolutionViewModel({
      plan,
      auditHistory,
    });

  return `
    <section class="selfEvolutionPanel">
      <div class="selfEvolutionHeader">
        <div>
          <span class="selfEvolutionEyebrow">
            SELF EVOLUTION
          </span>

          <h3>
            自己改善ステータス
          </h3>
        </div>

        <span class="selfEvolutionStatus ${escapeHtml(
          view.statusClass,
        )}">
          ${escapeHtml(
            view.actionLabel,
          )}
        </span>
      </div>

      <div class="selfEvolutionMetrics">
        <article>
          <span>改善スコア</span>
          <strong>
            ${escapeHtml(
              view.improvementLabel,
            )}
          </strong>
        </article>

        <article>
          <span>バックテスト</span>
          <strong>
            ${
              view.approvedByBacktest
                ? "合格"
                : "未合格"
            }
          </strong>
        </article>

        <article>
          <span>変更指標</span>
          <strong>
            ${view.changedIndicators}
          </strong>
        </article>

        <article>
          <span>Weight健全性</span>
          <strong>
            ${
              view.weightHealth
                ? "正常"
                : "要確認"
            }
          </strong>
        </article>
      </div>

      <div class="selfEvolutionAudit">
        <div>
          <span>学習回数</span>
          <strong>
            ${view.audit.totalRuns}
          </strong>
        </div>

        <div>
          <span>昇格率</span>
          <strong>
            ${view.audit.promotionRate}%
          </strong>
        </div>

        <div>
          <span>平均改善</span>
          <strong>
            ${
              view.audit
                .averageImprovement > 0
                ? "+"
                : ""
            }${view.audit.averageImprovement}
          </strong>
        </div>
      </div>

      <p class="selfEvolutionNotice">
        Weightの反映には、
        バックテスト合格と明示承認の両方が必要です。
      </p>
    </section>
  `;
}

export const SelfEvolutionUiInternals = {
  actionLabel,
  escapeHtml,
  statusClass,
};
export function buildLearningDashboardData({

    plan={},

    auditHistory=[],

    registry=[]

}={}){

    const view=

        createSelfEvolutionViewModel({

            plan,

            auditHistory

        });

    return{

        generatedAt:

            new Date().toISOString(),

        status:view.action,

        promoted:view.promoted,

        approved:

            view.approvedByBacktest,

        improvementScore:

            view.improvementScore,

        changedIndicators:

            view.changedIndicators,

        registrySize:

            registry.length,

        audit:view.audit

    };

}

export function exportLearningDashboardJSON({

    plan={},

    auditHistory=[],

    registry=[]

}={}){

    return JSON.stringify(

        buildLearningDashboardData({

            plan,

            auditHistory,

            registry

        }),

        null,

        2

    );

}


export function buildAiRecommendation({

    dashboard={}

}={}){

    const recommendation=[];

    if(dashboard.approved){

        recommendation.push(

            "Candidate passed backtest"

        );

    }else{

        recommendation.push(

            "Run additional validation"

        );

    }

    if(

        dashboard.improvementScore>=3

    ){

        recommendation.push(

            "Weight optimization is effective"

        );

    }

    if(

        dashboard.changedIndicators>0

    ){

        recommendation.push(

            "Indicator weights updated"

        );

    }

    return{

        generatedAt:

            new Date().toISOString(),

        status:

            dashboard.status,

        recommendation

    };

}

export function buildAiSummaryCard({

    dashboard={}

}={}){

    return{

        title:

            "AI Learning Summary",

        status:

            dashboard.status,

        score:

            dashboard.improvementScore,

        recommendations:

            buildAiRecommendation({

                dashboard

            }).recommendation

    };

}

