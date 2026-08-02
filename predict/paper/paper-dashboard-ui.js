import {
  renderPaperDashboardHtml,
} from "./paper-dashboard-presenter.js";

export const PAPER_DASHBOARD_UI_VERSION =
  "paper-dashboard-ui-v1";

export const DEFAULT_PAPER_DASHBOARD_ROOT_ID =
  "paper-trading-dashboard";

function validRoot(root) {
  return Boolean(
    root &&
    typeof root === "object" &&
    "innerHTML" in root
  );
}

export function findPaperDashboardRoot({
  documentRef =
    globalThis.document,

  rootId =
    DEFAULT_PAPER_DASHBOARD_ROOT_ID,
} = {}) {
  if (
    !documentRef ||
    typeof documentRef
      .getElementById !==
      "function"
  ) {
    return null;
  }

  return (
    documentRef.getElementById(
      rootId,
    ) || null
  );
}

export function createPaperDashboardRoot({
  documentRef =
    globalThis.document,

  parent,

  rootId =
    DEFAULT_PAPER_DASHBOARD_ROOT_ID,
} = {}) {
  const existing =
    findPaperDashboardRoot({
      documentRef,
      rootId,
    });

  if (existing) {
    return existing;
  }

  if (
    !documentRef ||
    typeof documentRef
      .createElement !==
      "function" ||
    !parent ||
    typeof parent
      .appendChild !==
      "function"
  ) {
    return null;
  }

  const root =
    documentRef.createElement(
      "div",
    );

  root.id =
    rootId;

  root.dataset.component =
    "paper-dashboard";

  parent.appendChild(
    root,
  );

  return root;
}

export function mountPaperDashboard({
  root,
  broker = {},
  sectorBySymbol = {},
  killSwitch = {
    enabled: false,
  },
} = {}) {
  if (!validRoot(root)) {
    return {
      mounted: false,
      reason:
        "missing_root",
      root: null,
      html: "",
    };
  }

  const html =
    renderPaperDashboardHtml({
      broker,
      sectorBySymbol,
      killSwitch,
    });

  root.innerHTML =
    html;

  if (root.dataset) {
    root.dataset.mounted =
      "true";

    root.dataset.version =
      PAPER_DASHBOARD_UI_VERSION;
  }

  return {
    mounted: true,
    reason: null,
    root,
    html,
  };
}

export function clearPaperDashboard({
  root,
} = {}) {
  if (!validRoot(root)) {
    return false;
  }

  root.innerHTML = "";

  if (root.dataset) {
    root.dataset.mounted =
      "false";
  }

  return true;
}

export function mountPaperDashboardById({
  documentRef =
    globalThis.document,

  rootId =
    DEFAULT_PAPER_DASHBOARD_ROOT_ID,

  broker = {},
  sectorBySymbol = {},
  killSwitch = {
    enabled: false,
  },
} = {}) {
  const root =
    findPaperDashboardRoot({
      documentRef,
      rootId,
    });

  return mountPaperDashboard({
    root,
    broker,
    sectorBySymbol,
    killSwitch,
  });
}

export const PaperDashboardUiInternals = {
  validRoot,
};