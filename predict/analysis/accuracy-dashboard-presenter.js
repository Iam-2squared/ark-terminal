import { createAccuracyDashboardViewModel } from "./accuracy-dashboard-view-model.js";

function noop() {}

export class AccuracyDashboardPresenter {
  constructor({
    renderer = noop,
  } = {}) {
    this.renderer = renderer;
  }

  present(data = {}) {
    const viewModel =
      createAccuracyDashboardViewModel(data);

    this.renderer(viewModel);

    return viewModel;
  }

  updateRenderer(renderer) {
    this.renderer =
      typeof renderer === "function"
        ? renderer
        : noop;
  }
}

export default AccuracyDashboardPresenter;
