const {
  runReadonlyHandler,
} = require("./_common");

const {
  createBrokerIntelligenceService,
} = require("./intelligence-service");

const service =
  createBrokerIntelligenceService();

module.exports = async function handler(
  req,
  res,
) {
  return runReadonlyHandler({
    req,
    res,

    action:
      async () => {
        const latency =
          Number(
            req.query?.latency ??
            0,
          );

        const uptime =
          Number(
            req.query?.uptime ??
            100,
          );

        const errors =
          Number(
            req.query?.errors ??
            0,
          );

        return service.analyze({
          latency:
            Number.isFinite(
              latency,
            )
              ? latency
              : 0,

          uptime:
            Number.isFinite(
              uptime,
            )
              ? uptime
              : 100,

          errors:
            Number.isFinite(
              errors,
            )
              ? errors
              : 0,

          connected:
            req.query?.connected !==
            "false",

          authenticated:
            req.query?.authenticated !==
            "false",
        });
      },
  });
};