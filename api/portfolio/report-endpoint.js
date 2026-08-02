const {
  createPortfolioIntelligenceReport,
} = require("./report");

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

    const holdings =
      Array.isArray(
        req.body?.holdings,
      )
        ? req.body.holdings
        : [];

    const returns =
      Array.isArray(
        req.body?.returns,
      )
        ? req.body.returns
        : [];

    const values =
      Array.isArray(
        req.body?.values,
      )
        ? req.body.values
        : [];

    const report =
      createPortfolioIntelligenceReport({
        holdings,
        returns,
        values,
      });

    res.status(200).json({
      ok:
        true,

      data:
        report,
    });
  };