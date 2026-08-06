import {
  getPredictions,
} from "../backtest/storage.js";

import {
  initCloudSyncController,
} from "./cloud-sync-controller.js";

import {
  selectCloudPredictions,
} from "./prediction-cloud-repository.js";

function updateCounts() {
  const records = getPredictions();
  const eligible = selectCloudPredictions(records);

  const localCount = document.getElementById(
    "cloudLocalPredictionCount",
  );
  const eligibleCount = document.getElementById(
    "cloudEligiblePredictionCount",
  );

  if (localCount) {
    localCount.textContent = `${records.length}件`;
  }

  if (eligibleCount) {
    eligibleCount.textContent = `${eligible.length}件`;
  }
}

const controller = initCloudSyncController();
const syncNowButton = document.getElementById(
  "cloudSyncNowButton",
);

syncNowButton?.addEventListener("click", async () => {
  await controller.synchronize();
  updateCounts();
});

updateCounts();
