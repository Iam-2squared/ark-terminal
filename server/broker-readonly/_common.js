function json(res, status, body) {
  res.status(status).json(body);
}

function rejectMethod(req, res) {
  if (req.method !== "GET") {
    json(res, 405, {
      code: "METHOD_NOT_ALLOWED",
      message: "Read-only endpoint."
    });
    return true;
  }
  return false;
}

module.exports = {
  json,
  rejectMethod,
};