const {
  createAdvisorService,
} = require("./service");

const service =
  createAdvisorService();

module.exports =
  async function handler(req, res) {
    if (req.method !== "POST") {
      res.status(405).json({
        ok: false,
        error: "method_not_allowed",
      });

      return;
    }

    const result =
      service.analyze(
        req.body || {}
      );

    res.status(200).json({
      ok: true,
      data: result,
    });
  };