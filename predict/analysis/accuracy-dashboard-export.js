export function exportAccuracyDashboard(data = {}) {
  return JSON.stringify(data, null, 2);
}

export function exportAccuracyDashboardCSV(vm = {}) {

  const rows = [["Metric","Value"]];

  for (const card of (vm.cards ?? [])) {
    rows.push([card.title, card.value]);
  }

  return rows
    .map(r => r.join(","))
    .join("\n");
}

export default exportAccuracyDashboard;
