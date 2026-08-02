import {
  composeAccuracyDashboardData,
} from "./accuracy-dashboard-data-composer.js";

import AccuracyDashboardPresenter
  from "./accuracy-dashboard-presenter.js";

export class AccuracyDashboardController {
  constructor({
    presenter = new AccuracyDashboardPresenter(),
    dataProvider = async () => ({ rows: [] }),
  } = {}) {
    this.presenter = presenter;
    this.dataProvider = dataProvider;
  }

  async refresh(options = {}) {
    const source =
      await this.dataProvider(options);

    const dashboard =
      composeAccuracyDashboardData(source);

    return this.presenter.present(dashboard);
  }

  async updateProvider(provider) {
    if (typeof provider === "function") {
      this.dataProvider = provider;
    }

    return this;
  }

  updatePresenter(presenter) {
    if (presenter) {
      this.presenter = presenter;
    }

    return this;
  }
}

export default AccuracyDashboardController;
