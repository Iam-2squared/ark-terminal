function finite(value, fallback = null) {
  const number = Number(value);

  return Number.isFinite(number)
    ? number
    : fallback;
}

function firstValue(source, paths, fallback = null) {
  for (const path of paths) {
    const value =
      path
        .split(".")
        .reduce(
          (current, key) =>
            current?.[key],
          source,
        );

    if (
      value !== undefined &&
      value !== null &&
      value !== ""
    ) {
      return value;
    }
  }

  return fallback;
}

export function normalizeAnalysisEventSource(
  source = {},
) {
  const root =
    source.detail ??
    source.result ??
    source.analysis ??
    source;

  const technicalScore =
    finite(
      firstValue(
        root,
        [
          "technicalScore",
          "totalScore",
          "score",
          "aiScore",
          "overallAiScore",
          "analysis.technicalScore",
          "analysis.totalScore",
          "aiAnalysis.overallAiScore",
        ],
        50,
      ),
      50,
    );

  const confidence =
    finite(
      firstValue(
        root,
        [
          "confidence.score",
          "confidence",
          "analysis.confidence",
          "prediction.confidence",
          "aiAnalysis.confidence.score",
        ],
        50,
      ),
      50,
    );

  const rsi =
    finite(
      firstValue(
        root,
        [
          "rsi",
          "indicators.rsi",
          "indicators.rsi.value",
        ],
        50,
      ),
      50,
    );

  const adx =
    finite(
      firstValue(
        root,
        [
          "adx",
          "indicators.adx",
          "indicators.adx.value",
        ],
        20,
      ),
      20,
    );

  const atrPercent =
    finite(
      firstValue(
        root,
        [
          "atrPercent",
          "indicators.atrPercent",
          "indicators.atr.percent",
        ],
        2.5,
      ),
      2.5,
    );

  return {
    state: {
      symbol:
        firstValue(
          root,
          [
            "symbol",
            "ticker",
            "code",
          ],
          null,
        ),

      analysis: {
        technicalScore,

        totalScore:
          finite(
            firstValue(
              root,
              [
                "totalScore",
                "analysis.totalScore",
              ],
              technicalScore,
            ),
            technicalScore,
          ),

        confidence,

        dataQualityScore:
          finite(
            firstValue(
              root,
              [
                "dataQualityScore",
                "analysis.dataQualityScore",
              ],
              75,
            ),
            75,
          ),
      },

      prediction: {
        confidence,
      },

      indicators: {
        rsi,

        adx: {
          value: adx,
        },

        atr: {
          percent:
            atrPercent,
        },
      },
    },

    macroInput: {
      nikkei:
        finite(
          firstValue(
            root,
            [
              "macro.nikkei",
              "market.nikkei",
            ],
            0,
          ),
          0,
        ),

      nasdaq:
        finite(
          firstValue(
            root,
            [
              "macro.nasdaq",
              "market.nasdaq",
            ],
            0,
          ),
          0,
        ),

      sox:
        finite(
          firstValue(
            root,
            [
              "macro.sox",
              "market.sox",
            ],
            0,
          ),
          0,
        ),

      vix:
        finite(
          firstValue(
            root,
            [
              "macro.vix",
              "market.vix",
              "vix",
            ],
            20,
          ),
          20,
        ),
    },

    marketInput: {
      trendScore:
        technicalScore,

      volatility:
        Math.max(
          0,
          atrPercent * 5,
        ),

      adx,

      rsi,

      vix:
        finite(
          firstValue(
            root,
            [
              "macro.vix",
              "market.vix",
              "vix",
            ],
            20,
          ),
          20,
        ),
    },

    portfolioPlan:
      root.portfolioPlan ??
      {},
  };
}

export function dispatchAnalysisReady({
  source = {},
  eventTarget = globalThis.window,
} = {}) {
  if (
    !eventTarget ||
    typeof eventTarget.dispatchEvent !== "function"
  ) {
    return false;
  }

  const detail =
    normalizeAnalysisEventSource(
      source,
    );

  const EventConstructor =
    eventTarget.CustomEvent ??
    globalThis.CustomEvent;

  if (
    typeof EventConstructor !== "function"
  ) {
    return false;
  }

  eventTarget.__ARK_ANALYSIS_STATE__ =
    detail;

  eventTarget.dispatchEvent(
    new EventConstructor(
      "ark:analysis-ready",
      {
        detail,
      },
    ),
  );

  return true;
}

function readKnownGlobalState(
  windowRef,
) {
  return (
    windowRef.__ARK_LATEST_ANALYSIS__ ??
    windowRef.__ARK_AI_ANALYSIS__ ??
    windowRef.__ARK_ANALYSIS_RESULT__ ??
    windowRef.latestAnalysis ??
    null
  );
}

export function connectAnalysisEventBridge({
  windowRef = globalThis.window,
  documentRef = globalThis.document,
  pollingIntervalMs = 1200,
} = {}) {
  if (!windowRef) {
    return () => {};
  }

  let previousSignature = "";

  const publish =
    (source) => {
      if (!source) {
        return;
      }

      let signature = "";

      try {
        signature =
          JSON.stringify(source);
      } catch {
        signature =
          String(Date.now());
      }

      if (
        signature ===
        previousSignature
      ) {
        return;
      }

      previousSignature =
        signature;

      dispatchAnalysisReady({
        source,
        eventTarget:
          windowRef,
      });
    };

  const customEventHandler =
    (event) => {
      publish(
        event?.detail ??
        event,
      );
    };

  const eventNames = [
    "ark:raw-analysis-ready",
    "ark:analysis-complete",
    "ark:prediction-complete",
    "ai-analysis-complete",
  ];

  for (const eventName of eventNames) {
    windowRef.addEventListener(
      eventName,
      customEventHandler,
    );
  }

  const intervalId =
    windowRef.setInterval(
      () => {
        publish(
          readKnownGlobalState(
            windowRef,
          ),
        );
      },
      Math.max(
        500,
        Number(
          pollingIntervalMs,
        ) || 1200,
      ),
    );

  let observer = null;

  if (
    documentRef &&
    typeof MutationObserver !== "undefined"
  ) {
    const target =
      documentRef.querySelector(
        "#aiAnalysisResult, #ai-analysis-result, .ai-analysis-result",
      );

    if (target) {
      observer =
        new MutationObserver(
          () => {
            publish(
              readKnownGlobalState(
                windowRef,
              ),
            );
          },
        );

      observer.observe(
        target,
        {
          childList: true,
          subtree: true,
          characterData: true,
        },
      );
    }
  }

  publish(
    readKnownGlobalState(
      windowRef,
    ),
  );

  return () => {
    windowRef.clearInterval(
      intervalId,
    );

    observer?.disconnect();

    for (const eventName of eventNames) {
      windowRef.removeEventListener(
        eventName,
        customEventHandler,
      );
    }
  };
}

if (
  typeof window !== "undefined"
) {
  window.ArkAnalysisEventBridge = {
    dispatchAnalysisReady,
    normalizeAnalysisEventSource,
  };

  if (
    typeof document !== "undefined" &&
    document.readyState === "loading"
  ) {
    document.addEventListener(
      "DOMContentLoaded",
      () => {
        connectAnalysisEventBridge();
      },
      {
        once: true,
      },
    );
  } else {
    connectAnalysisEventBridge();
  }
}