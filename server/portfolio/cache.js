function createPortfolioCache({
  ttlMilliseconds = 30000,
} = {}) {
  let cached = null;

  function set(
    value,
  ) {
    cached = {
      value:
        structuredClone(
          value,
        ),

      storedAt:
        Date.now(),
    };

    return get();
  }

  function get() {
    if (!cached) {
      return null;
    }

    if (
      Date.now() -
      cached.storedAt >
      ttlMilliseconds
    ) {
      cached = null;
      return null;
    }

    return structuredClone(
      cached.value,
    );
  }

  function clear() {
    cached = null;
  }

  return {
    set,
    get,
    clear,
  };
}

module.exports = {
  createPortfolioCache,
};