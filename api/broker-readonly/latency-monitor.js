function createLatencyMonitor({
  maximumSamples = 100,
} = {}) {
  const samples = [];

  function record(
    latency,
  ) {
    const value =
      Number(latency);

    if (
      !Number.isFinite(value) ||
      value < 0
    ) {
      throw new Error(
        "Latency must be a non-negative number.",
      );
    }

    samples.push(
      value,
    );

    while (
      samples.length >
      maximumSamples
    ) {
      samples.shift();
    }

    return getSummary();
  }

  function getSummary() {
    if (
      samples.length ===
      0
    ) {
      return {
        count:
          0,

        latest:
          null,

        average:
          null,

        maximum:
          null,
      };
    }

    const total =
      samples.reduce(
        (
          sum,
          value,
        ) =>
          sum + value,
        0,
      );

    return {
      count:
        samples.length,

      latest:
        samples[
          samples.length - 1
        ],

      average:
        total /
        samples.length,

      maximum:
        Math.max(
          ...samples,
        ),
    };
  }

  return {
    record,
    getSummary,
  };
}

module.exports = {
  createLatencyMonitor,
};