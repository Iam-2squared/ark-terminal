const {
  json,
  rejectMethod,
} = require("./_common");

module.exports = async (
  req,
  res,
) => {

  if (
    rejectMethod(
      req,
      res,
    )
  ) {
    return;
  }

  json(res,200,{
    ok:true,
    readOnly:true,
    liveTrading:false,
    serverTime:new Date().toISOString(),
  });
};