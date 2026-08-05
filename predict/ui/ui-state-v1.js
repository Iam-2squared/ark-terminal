export const UI_STATE_V1_VERSION = "ui-state-v1";

export function buildUiStateV1({ loading = false, error = null, data = null, emptyMessage = "データがありません", retryable = true } = {}) {
  const hasError = Boolean(error);
  const isEmpty = !loading && !hasError && (data == null || (Array.isArray(data) && data.length === 0));

  return {
    version: UI_STATE_V1_VERSION,
    status: loading ? "LOADING" : hasError ? "ERROR" : isEmpty ? "EMPTY" : "READY",
    loading: Boolean(loading),
    error: hasError
      ? {
          message: typeof error === "string" ? error : error?.message ?? "不明なエラー",
          code: error?.code ?? null,
          retryable: retryable !== false,
        }
      : null,
    data,
    emptyMessage,
    mobileReady: true,
    accessibility: {
      ariaBusy: Boolean(loading),
      role: hasError ? "alert" : "status",
    },
  };
}

export default buildUiStateV1;
