export function createAccuracyDashboardPanel(viewModel = {}) {
  return {
    title: "AI Accuracy Dashboard",

    sections: [
      {
        title: "Summary",
        cards: viewModel.cards ?? [],
      },
      {
        title: "Calibration",
        data: viewModel.calibration ?? {},
      },
      {
        title: "Health",
        data: viewModel.health ?? {},
      },
      {
        title: "Metadata",
        data: viewModel.metadata ?? {},
      },
    ],
  };
}

export default createAccuracyDashboardPanel;
