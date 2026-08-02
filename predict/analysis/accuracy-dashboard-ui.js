export function renderAccuracyDashboard(
  viewModel,
  rootElement,
) {
  if (!rootElement) {
    return;
  }

  rootElement.innerHTML = "";

  const container =
    document.createElement("section");

  container.className =
    "accuracy-dashboard";

  for (const card of viewModel.cards) {
    const item =
      document.createElement("div");

    item.className =
      "accuracy-card";

    item.innerHTML = `
      <div class="accuracy-card-title">
        ${card.title}
      </div>

      <div class="accuracy-card-value">
        ${card.value}
      </div>
    `;

    container.appendChild(item);
  }

  const status =
    document.createElement("div");

  status.className =
    "accuracy-dashboard-status";

  status.textContent =
    `Health : ${viewModel.health.status}`;

  container.appendChild(status);

  rootElement.appendChild(container);

  return container;
}

export default renderAccuracyDashboard;
