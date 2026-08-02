import AccuracyDashboardController
  from "./accuracy-dashboard-controller.js";

export function integrateAccuracyDashboard({
  controller = new AccuracyDashboardController(),
  refreshButton = null,
  autoRefresh = false,
} = {}) {

  async function refresh() {
    return controller.refresh();
  }

  if (
    refreshButton &&
    typeof refreshButton.addEventListener === "function"
  ) {
    refreshButton.addEventListener(
      "click",
      refresh,
    );
  }

  if (autoRefresh) {
    void refresh();
  }

  return {
    refresh,
    controller,
  };
}

export default integrateAccuracyDashboard;
