export const READONLY_BROKER_RECONCILER_VERSION =
  "readonly-broker-reconciler-v1";

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function numberOrZero(value) {
  return finite(value)
    ? Number(value)
    : 0;
}

function normalizeSymbol(value) {
  return String(value || "")
    .trim()
    .toUpperCase();
}

function normalizeOrderId(value) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return null;
  }

  return String(value);
}

function withinTolerance({
  left,
  right,
  tolerance = 0,
} = {}) {
  return (
    Math.abs(
      numberOrZero(left) -
      numberOrZero(right),
    ) <=
    Math.max(
      0,
      numberOrZero(tolerance),
    )
  );
}

function indexPositions(
  positions = [],
) {
  const map =
    new Map();

  for (
    const position of
    positions
  ) {
    const symbol =
      normalizeSymbol(
        position.symbol,
      );

    if (!symbol) {
      continue;
    }

    map.set(
      symbol,
      position,
    );
  }

  return map;
}

function indexOrders(
  orders = [],
) {
  const map =
    new Map();

  for (
    const order of
    orders
  ) {
    const orderId =
      normalizeOrderId(
        order.orderId ??
        order.adapterOrderId ??
        order.id,
      );

    if (!orderId) {
      continue;
    }

    map.set(
      orderId,
      order,
    );
  }

  return map;
}

function createDifference({
  type,
  severity = "warning",
  key = null,
  field = null,
  brokerValue = null,
  localValue = null,
  difference = null,
  message,
} = {}) {
  return {
    type,
    severity,
    key,
    field,
    brokerValue,
    localValue,
    difference,
    message,
  };
}

export function reconcileReadonlyAccount({
  brokerAccount = null,
  localAccount = null,

  cashTolerance = 1,
  buyingPowerTolerance = 1,
  equityTolerance = 1,
} = {}) {
  const differences = [];

  if (!brokerAccount) {
    differences.push(
      createDifference({
        type:
          "broker_account_missing",

        severity:
          "error",

        message:
          "Broker account data is missing.",
      }),
    );

    return differences;
  }

  if (!localAccount) {
    differences.push(
      createDifference({
        type:
          "local_account_missing",

        severity:
          "warning",

        message:
          "Local account data is missing.",
      }),
    );

    return differences;
  }

  const fields = [
    {
      field:
        "cash",

      tolerance:
        cashTolerance,
    },
    {
      field:
        "buyingPower",

      tolerance:
        buyingPowerTolerance,
    },
    {
      field:
        "equity",

      tolerance:
        equityTolerance,
    },
  ];

  for (
    const row of
    fields
  ) {
    const brokerValue =
      numberOrZero(
        brokerAccount[
          row.field
        ],
      );

    const localValue =
      numberOrZero(
        localAccount[
          row.field
        ],
      );

    if (
      !withinTolerance({
        left:
          brokerValue,

        right:
          localValue,

        tolerance:
          row.tolerance,
      })
    ) {
      differences.push(
        createDifference({
          type:
            "account_value_mismatch",

          severity:
            "warning",

          field:
            row.field,

          brokerValue,
          localValue,

          difference:
            brokerValue -
            localValue,

          message:
            `Account ${row.field} differs.`,
        }),
      );
    }
  }

  return differences;
}

export function reconcileReadonlyPositions({
  brokerPositions = [],
  localPositions = [],

  quantityTolerance = 0,
  priceTolerance = 0.01,
  marketValueTolerance = 1,
} = {}) {
  const differences = [];

  const brokerMap =
    indexPositions(
      brokerPositions,
    );

  const localMap =
    indexPositions(
      localPositions,
    );

  const symbols =
    new Set([
      ...brokerMap.keys(),
      ...localMap.keys(),
    ]);

  for (
    const symbol of
    symbols
  ) {
    const brokerPosition =
      brokerMap.get(
        symbol,
      );

    const localPosition =
      localMap.get(
        symbol,
      );

    if (!brokerPosition) {
      differences.push(
        createDifference({
          type:
            "position_missing_at_broker",

          severity:
            "warning",

          key:
            symbol,

          brokerValue:
            null,

          localValue:
            localPosition,

          message:
            `${symbol} exists locally but not at broker.`,
        }),
      );

      continue;
    }

    if (!localPosition) {
      differences.push(
        createDifference({
          type:
            "position_missing_locally",

          severity:
            "warning",

          key:
            symbol,

          brokerValue:
            brokerPosition,

          localValue:
            null,

          message:
            `${symbol} exists at broker but not locally.`,
        }),
      );

      continue;
    }

    const numericFields = [
      {
        field:
          "quantity",

        tolerance:
          quantityTolerance,
      },
      {
        field:
          "averagePrice",

        tolerance:
          priceTolerance,
      },
      {
        field:
          "marketValue",

        tolerance:
          marketValueTolerance,
      },
    ];

    for (
      const row of
      numericFields
    ) {
      const brokerValue =
        numberOrZero(
          brokerPosition[
            row.field
          ],
        );

      const localValue =
        numberOrZero(
          localPosition[
            row.field
          ],
        );

      if (
        !withinTolerance({
          left:
            brokerValue,

          right:
            localValue,

          tolerance:
            row.tolerance,
        })
      ) {
        differences.push(
          createDifference({
            type:
              "position_value_mismatch",

            severity:
              row.field ===
              "quantity"
                ? "error"
                : "warning",

            key:
              symbol,

            field:
              row.field,

            brokerValue,
            localValue,

            difference:
              brokerValue -
              localValue,

            message:
              `${symbol} ${row.field} differs.`,
          }),
        );
      }
    }
  }

  return differences;
}

export function reconcileReadonlyOrders({
  brokerOrders = [],
  localOrders = [],
} = {}) {
  const differences = [];

  const brokerMap =
    indexOrders(
      brokerOrders,
    );

  const localMap =
    indexOrders(
      localOrders,
    );

  const orderIds =
    new Set([
      ...brokerMap.keys(),
      ...localMap.keys(),
    ]);

  for (
    const orderId of
    orderIds
  ) {
    const brokerOrder =
      brokerMap.get(
        orderId,
      );

    const localOrder =
      localMap.get(
        orderId,
      );

    if (!brokerOrder) {
      differences.push(
        createDifference({
          type:
            "order_missing_at_broker",

          severity:
            "warning",

          key:
            orderId,

          brokerValue:
            null,

          localValue:
            localOrder,

          message:
            `Order ${orderId} exists locally but not at broker.`,
        }),
      );

      continue;
    }

    if (!localOrder) {
      differences.push(
        createDifference({
          type:
            "order_missing_locally",

          severity:
            "warning",

          key:
            orderId,

          brokerValue:
            brokerOrder,

          localValue:
            null,

          message:
            `Order ${orderId} exists at broker but not locally.`,
        }),
      );

      continue;
    }

    const brokerStatus =
      String(
        brokerOrder.status ||
        "unknown",
      );

    const localStatus =
      String(
        localOrder.status ||
        "unknown",
      );

    if (
      brokerStatus !==
      localStatus
    ) {
      differences.push(
        createDifference({
          type:
            "order_status_mismatch",

          severity:
            "warning",

          key:
            orderId,

          field:
            "status",

          brokerValue:
            brokerStatus,

          localValue:
            localStatus,

          message:
            `Order ${orderId} status differs.`,
        }),
      );
    }

    const brokerFilled =
      numberOrZero(
        brokerOrder
          .filledQuantity,
      );

    const localFilled =
      numberOrZero(
        localOrder
          .filledQuantity,
      );

    if (
      brokerFilled !==
      localFilled
    ) {
      differences.push(
        createDifference({
          type:
            "order_fill_mismatch",

          severity:
            "warning",

          key:
            orderId,

          field:
            "filledQuantity",

          brokerValue:
            brokerFilled,

          localValue:
            localFilled,

          difference:
            brokerFilled -
            localFilled,

          message:
            `Order ${orderId} filled quantity differs.`,
        }),
      );
    }
  }

  return differences;
}

export function reconcileReadonlyBrokerSnapshot({
  brokerSnapshot,
  localSnapshot,

  tolerances = {},
} = {}) {
  if (!brokerSnapshot) {
    throw new Error(
      "Broker snapshot is required.",
    );
  }

  if (!localSnapshot) {
    throw new Error(
      "Local snapshot is required.",
    );
  }

  const accountDifferences =
    reconcileReadonlyAccount({
      brokerAccount:
        brokerSnapshot.account,

      localAccount:
        localSnapshot.account,

      cashTolerance:
        tolerances.cash ?? 1,

      buyingPowerTolerance:
        tolerances.buyingPower ??
        1,

      equityTolerance:
        tolerances.equity ??
        1,
    });

  const positionDifferences =
    reconcileReadonlyPositions({
      brokerPositions:
        brokerSnapshot.positions ||
        [],

      localPositions:
        localSnapshot.positions ||
        [],

      quantityTolerance:
        tolerances.quantity ??
        0,

      priceTolerance:
        tolerances.price ??
        0.01,

      marketValueTolerance:
        tolerances.marketValue ??
        1,
    });

  const orderDifferences =
    reconcileReadonlyOrders({
      brokerOrders:
        brokerSnapshot.orders ||
        [],

      localOrders:
        localSnapshot.orders ||
        [],
    });

  const differences = [
    ...accountDifferences,
    ...positionDifferences,
    ...orderDifferences,
  ];

  const errors =
    differences.filter(
      (row) =>
        row.severity ===
        "error",
    );

  const warnings =
    differences.filter(
      (row) =>
        row.severity ===
        "warning",
    );

  return {
    version:
      READONLY_BROKER_RECONCILER_VERSION,

    matched:
      differences.length ===
      0,

    safe:
      errors.length ===
      0,

    summary: {
      totalDifferences:
        differences.length,

      errors:
        errors.length,

      warnings:
        warnings.length,

      accountDifferences:
        accountDifferences.length,

      positionDifferences:
        positionDifferences.length,

      orderDifferences:
        orderDifferences.length,
    },

    differences,
    errors,
    warnings,

    brokerSynchronizedAt:
      brokerSnapshot
        .synchronizedAt ||
      null,

    readOnly: true,
  };
}

export const ReadonlyBrokerReconcilerInternals = {
  finite,
  numberOrZero,
  normalizeSymbol,
  normalizeOrderId,
  withinTolerance,
  indexPositions,
  indexOrders,
  createDifference,
};