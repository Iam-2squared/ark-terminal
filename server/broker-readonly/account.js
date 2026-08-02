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
    account:null,
    readOnly:true,
  });
};