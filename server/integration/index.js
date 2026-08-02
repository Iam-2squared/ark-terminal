const {
  createIntegrationService,
} = require("./service");

const service =
  createIntegrationService();

module.exports =
  async function handler(
    req,
    res,
  ) {
    if (
      req.method !==
      "POST"
    ) {
      res.status(405).json({
        ok:
          false,

        error:
          "method_not_allowed",
      });

      return;
    }

    const result =
      service.analyze({
        broker:
          req.body?.broker ||
          {},

        portfolio:
          req.body?.portfolio ||
          {},

        market:
          req.body?.market ||
          {},
      });

    res.status(200).json({
      ok:
        true,

      data:
        result,
    });
  };